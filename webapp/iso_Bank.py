from webapp import db
from webapp.models import Income, Accounts, users, JO, Gledger, Reconciliations, Orders
from flask import session, logging, request
import datetime
import calendar
import re
import os
import shutil
import json
import subprocess
from webapp.report_maker import reportmaker
from webapp.viewfuncs import d2s
from webapp.CCC_system_setup import scac

def reset_trial(ix, bankacct=None):
    query = Gledger.query.filter(Gledger.Reconciled == 25)
    if bankacct is not None:
        query = query.filter(Gledger.Account == bankacct)
    gdata = query.all()
    for gdat in gdata:
        gdat.Reconciled = ix
    db.session.commit()

def trial_ids(odata):
    selected = [row.id for row in odata if row.Reconciled == 25]
    return selected if selected else [0]

def parse_money(value):
    try:
        return float(str(value).replace('$', '').replace(',', '').strip())
    except:
        return 0.00

def mark_reconciled_payment_jobs(ledger_ids):
    updated = 0
    for ledger_id in ledger_ids:
        ledger_line = Gledger.query.get(ledger_id)
        if ledger_line is None or ledger_line.Type not in ['DD', 'XD']:
            continue
        if ledger_line.SourceTable == 'ManualDeposit':
            continue
        if not ledger_line.Tcode:
            continue
        order = Orders.query.filter(Orders.Jo == ledger_line.Tcode).first()
        if order is None:
            continue
        if order.Istat not in [5, 8, 9]:
            continue
        if parse_money(order.BalDue) > .01:
            continue
        if order.Istat != 9:
            order.Istat = 9
            updated += 1
    if updated:
        db.session.commit()
    return updated

def latest_reconciliation(bankacct):
    return Reconciliations.query.filter(
        (Reconciliations.Account == bankacct) &
        (Reconciliations.Status == 1)
    ).order_by(Reconciliations.Rdate.desc()).first()

def trial_reconciliation(bankacct):
    return Reconciliations.query.filter(
        (Reconciliations.Account == bankacct) &
        (Reconciliations.Status == 25)
    ).order_by(Reconciliations.Rdate.desc()).first()

def default_beginning_balance(bankacct):
    rdat = latest_reconciliation(bankacct)
    if rdat is not None and rdat.Ebal not in [None, '']:
        return rdat.Ebal
    return '0.00'

def statement_defaults(bankacct, today_str):
    defaults = {
        'rdate': today_str,
        'begbal': default_beginning_balance(bankacct),
        'endbal': '0.00',
    }
    rdat = trial_reconciliation(bankacct)
    if rdat is not None:
        if rdat.Rdate is not None:
            defaults['rdate'] = rdat.Rdate.strftime('%Y-%m-%d')
        if rdat.Bbal not in [None, '']:
            defaults['begbal'] = rdat.Bbal
        if rdat.Ebal not in [None, '']:
            defaults['endbal'] = rdat.Ebal
    return defaults

def recon_list_text(values):
    try:
        text = json.dumps(values)
    except:
        return None
    if len(text) <= 290:
        return text
    first = values[:5]
    last = values[-5:] if len(values) > 5 else []
    return json.dumps({'count': len(values), 'first': first, 'last': last})

def save_trial_reconciliation(bankacct, rdate, bbal, ebal, deposits, withdraws, servicefees, dlist, wlist, diff):
    try:
        dlists = recon_list_text(dlist)
    except:
        dlists = None
    try:
        wlists = recon_list_text(wlist)
    except:
        wlists = None

    rdat = trial_reconciliation(bankacct)
    if rdat is None:
        rdat = Reconciliations(
            Account=bankacct,
            Rdate=rdate,
            Bbal=bbal,
            Ebal=ebal,
            Deposits=deposits,
            Withdraws=withdraws,
            Servicefees=servicefees,
            DepositList=dlists,
            WithdrawList=wlists,
            Status=25,
            Diff=diff,
        )
        db.session.add(rdat)
    else:
        rdat.Account = bankacct
        rdat.Rdate = rdate
        rdat.Bbal = bbal
        rdat.Ebal = ebal
        rdat.Deposits = deposits
        rdat.Withdraws = withdraws
        rdat.Servicefees = servicefees
        rdat.DepositList = dlists
        rdat.WithdrawList = wlists
        rdat.Status = 25
        rdat.Diff = diff
    db.session.commit()
    return rdat

def baseline_reconciliation(bankacct, cutoff_date, trusted_balance):
    cutoff_end = cutoff_date + datetime.timedelta(days=1)
    rows = Gledger.query.filter(
        (Gledger.Account == bankacct) &
        (Gledger.Date < cutoff_end) &
        ((Gledger.Reconciled == 0) | (Gledger.Reconciled == 25))
    ).all()

    deposits = 0
    withdrawals = 0
    for row in rows:
        if row.Type in ['DD', 'XD']:
            deposits += row.Debit or 0
        if row.Type in ['PC', 'XC']:
            withdrawals += row.Credit or 0
        row.Reconciled = cutoff_date.month

    trusted_balance = d2s(trusted_balance)
    existing = Reconciliations.query.filter(
        (Reconciliations.Account == bankacct) &
        (Reconciliations.Rdate == cutoff_date)
    ).first()
    if existing is None:
        existing = Reconciliations(
            Account=bankacct,
            Rdate=cutoff_date,
            Bbal='0.00',
            Ebal=trusted_balance,
            Deposits=d2s(float(deposits) / 100),
            Withdraws=d2s(float(withdrawals) / 100),
            Servicefees='0.00',
            DepositList='baseline',
            WithdrawList='baseline',
            Status=1,
            Diff='0.00',
        )
        db.session.add(existing)
    else:
        existing.Bbal = '0.00'
        existing.Ebal = trusted_balance
        existing.Deposits = d2s(float(deposits) / 100)
        existing.Withdraws = d2s(float(withdrawals) / 100)
        existing.Servicefees = '0.00'
        existing.DepositList = 'baseline'
        existing.WithdrawList = 'baseline'
        existing.Status = 1
        existing.Diff = '0.00'

    db.session.commit()
    return len(rows), d2s(float(deposits) / 100), d2s(float(withdrawals) / 100), trusted_balance

def selected_bank_ids(odata):
    selected = []
    valid_ids = {row.id for row in odata}
    for row in odata:
        testone = request.values.get('oder' + str(row.id))
        if testone:
            selected.append(int(testone))
    for key, value in request.values.items():
        if key.startswith('bankgroup') and value:
            for item in value.split(','):
                try:
                    row_id = int(item)
                    if row_id in valid_ids and row_id not in selected:
                        selected.append(row_id)
                except:
                    pass
    return selected

def dataget_Bank(thismuch,bankacct):
    # 0=order,#1=proofs,#2=interchange,#3=people/services
    today = datetime.date.today()
    stopdate = today-datetime.timedelta(days=60)
    if thismuch == '1':
        odata = Gledger.query.filter((Gledger.Account==bankacct) & ( (Gledger.Reconciled==0) | (Gledger.Reconciled==25) )).all()
    elif thismuch == '5':
        odata = Gledger.query.filter((Gledger.Account==bankacct) & (Gledger.Reconciled==25)).all()
    elif thismuch == '2':
        stopdate = today-datetime.timedelta(days=45)
        odata = Gledger.query.filter((Gledger.Account==bankacct) & (Gledger.Recorded > stopdate)).all()
    elif thismuch == '3':
        stopdate = today-datetime.timedelta(days=90)
        odata = Gledger.query.filter((Gledger.Account==bankacct) & (Gledger.Recorded > stopdate)).all()
    else:
        odata = Gledger.query.filter(Gledger.Account==bankacct ).all()
    return odata

def recon_totals(bankacct):
    # Find service charges for month:
    dlist = []
    wlist = []
    gdat = Gledger.query.filter((Gledger.Account == bankacct) & (Gledger.Reconciled == 25) & (Gledger.Source == bankacct)).first()
    if gdat is not None:
        bkc = gdat.Credit
    else:
        bkc = 0
    totald, totalc = 0.0, 0.0
    gdata = Gledger.query.filter((Gledger.Account == bankacct) & (Gledger.Reconciled == 25)).all()
    for gdat in gdata:
        type = gdat.Type
        if type == 'DD' or type == 'XD':
            totald = totald + gdat.Debit
            dlist.append(gdat.id)
        if type == 'PC' or type == 'XC':
            totalc = totalc + gdat.Credit
            wlist.append(gdat.id)

    totalc = totalc - bkc
    return d2s(float(totald)/100), d2s(float(totalc)/100), d2s(float(bkc)/100), dlist, wlist

def banktotals(bankacct):
    totald=0
    totalc=0
    totald_U = 0
    totalc_U = 0
    defaults = statement_defaults(bankacct, datetime.date.today().strftime('%Y-%m-%d'))
    endbal = request.values.get('endbal')
    begbal = request.values.get('begbal')
    if endbal in [None, '']:
        endbal = defaults['endbal']
    if begbal in [None, '']:
        begbal = defaults['begbal']
    print(begbal,endbal)
    try:
        endbal = parse_money(endbal)
    except:
        endbal=0.00
    try:
        begbal = parse_money(begbal)
    except:
        begbal=0.00
    gdata = Gledger.query.filter(Gledger.Account==bankacct).all()
    for gdat in gdata:
        type = gdat.Type
        if type == 'DD' or type == 'XD':
            totald = totald + gdat.Debit
            if gdat.Reconciled==0 or gdat.Reconciled==25:
                totald_U = totald_U + gdat.Debit

        if type == 'PC' or type == 'XC':
            totalc = totalc + gdat.Credit
            if gdat.Reconciled==0 or gdat.Reconciled==25:
                totalc_U = totalc_U + gdat.Credit

    trial_dr, trial_cr, bk_charge, dlist, wlist = recon_totals(bankacct)

    totald = float(totald)/100
    totalc = float(totalc)/100
    diff = begbal + float(trial_dr) - float(trial_cr) - float(bk_charge) - endbal
    totalds = d2s(totald)
    totalcs = d2s(totalc)
    balance = d2s( (float(totald) - float(totalc))/100 )
    totald_Us = d2s(float(totald_U)/100)
    totalc_Us = d2s(float(totalc_U)/100)
    projbal = d2s( float(totald-totalc-totald_U+totalc_U)/100 )

    acctinfo=[balance,totald_Us,totalc_Us,projbal,d2s(endbal),d2s(diff),bankacct,totalds,totalcs,d2s(begbal)]

    return acctinfo





def isoBank():

    if request.method == 'POST':
# ____________________________________________________________________________________________________________________B.FormVariables.General

        from webapp.viewfuncs import parseline, popjo, jovec, newjo, timedata, nonone, nononef, enter_bk_charges
        from webapp.viewfuncs import numcheck, numcheckv, viewbuttons, get_ints, numcheckvec, numcheckv, d2s, erud

        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        hv = [0]*9

        #Zero and blank items for default
        username = session['username'].capitalize()
        cache=request.values.get('cache')
        cache=nonone(cache)

        modata=0
        modlink=0
        docref=''
        oderstring=''
        acname = request.values.get('acname')



        today = datetime.date.today()
        now = datetime.datetime.now().strftime('%I:%M %p')
        err = []

        leftsize=10

        match    =  request.values.get('Match')
        modify   =  request.values.get('Qmod')
        vmod   =  request.values.get('Vmod')
        viewo     =  request.values.get('View')
        returnhit = request.values.get('Return')
        deletehit = request.values.get('Delete')
        delfile = request.values.get('DELF')
        # hidden values
        update   =  request.values.get('Update')
        newact=request.values.get('NewA')
        thisjob=request.values.get('ThisJob')
        oder=request.values.get('oder')
        modlink = request.values.get('modlink')
        depositmake = request.values.get('depositmake')
        recdeposit = request.values.get('recdeposit')
        unrecord = request.values.get('unrecord')
        thismuch = request.values.get('thismuch')
        recothese = request.values.get('recothese')
        finalize = request.values.get('finalize')
        undothese = request.values.get('undothese')
        baselinehit = request.values.get('baseline_reconcile')
        baseline_date = request.values.get('baseline_date')
        baseline_balance = request.values.get('baseline_balance')
        defaults = statement_defaults(acname, today_str)
        rdate = request.values.get('rdate')
        if rdate is None:
            rdate = defaults['rdate']
        hv[0] = rdate
        hv[1] = [0]
        endbal = request.values.get('endbal')
        begbal = request.values.get('begbal')
        if endbal in [None, '']:
            endbal = defaults['endbal']
        if begbal in [None, '']:
            begbal = defaults['begbal']
        recready = 1
        try:
            endbal=parse_money(endbal)
        except:
            endbal=0.00
            err.append('No Statement Balance Entered for Reconciliation')
            recready=0
        try:
            begbal=parse_money(begbal)
        except:
            endbal=0.00
            err.append('No Statement Ending Entered for Reconciliation')
            recready=0


        oder=nonone(oder)
        modlink=nonone(modlink)

        leftscreen=1
        err=['All is well', ' ', ' ', ' ', ' ']

        if returnhit is not None:
            modlink=0
            depojo=0


# ____________________________________________________________________________________________________________________E.FormVariables.General
# ____________________________________________________________________________________________________________________B.DataUpdates.General

        if modlink==1:
            if oder > 0:
                modata=Income.query.get(oder)
                vals=['jo','subjo','pid','description','amount','ref','pdate','original']
                a=list(range(len(vals)))
                for i,v in enumerate(vals):
                    a[i]=request.values.get(v)

                modata.Jo=a[0]
                modata.Account=a[1]
                modata.Pid=a[2]
                modata.Description=a[3]
                modata.Amount=a[4]
                modata.Ref=a[5]
                modata.Date=a[6]
                modata.Original=a[7]
                db.session.commit()
                err[3]= 'Modification to Income id ' + str(modata.id) + ' completed.'
                if update is not None:
                    modlink=0
                    leftsize=10
                else:
                    leftsize=6
                    leftscreen=0
                    modata=Income.query.get(oder)

# ____________________________________________________________________________________________________________________B.GetData.General
        #odata = Income.query.all()
        print('acname=',acname)
        odata = dataget_Bank(thismuch,acname)
        hv[1] = trial_ids(odata)
        acctinfo = banktotals(acname)
# ____________________________________________________________________________________________________________________B.Search.General

        if baselinehit is not None:
            try:
                if baseline_balance in [None, '']:
                    raise ValueError('trusted bank balance is required')
                cutoff_date = datetime.datetime.strptime(baseline_date, "%Y-%m-%d")
                trusted_balance = parse_money(baseline_balance)
                row_count, deposits, withdrawals, trusted = baseline_reconciliation(acname, cutoff_date, trusted_balance)
                err[0] = f'Baseline completed for {acname} through {baseline_date}'
                err[1] = f'Marked {row_count} ledger rows reconciled; deposits ${deposits}; withdrawals ${withdrawals}'
                err[2] = f'Beginning balance for future reconciliation defaults to ${trusted}'
                thismuch = '1'
                odata = dataget_Bank(thismuch, acname)
                acctinfo = banktotals(acname)
            except Exception as exc:
                err[0] = f'Baseline failed: {exc}'

        if modlink==0:
            oder,numchecked=numcheck(1,odata,0,0,0,0,['oder'])
            group_ids = selected_bank_ids(odata)
            if group_ids:
                numchecked = len(group_ids)

# ____________________________________________________________________________________________________________________E.Search.General
        if (recothese is not None or finalize is not None) and recready == 1:

            if numchecked > -1:

                reset_trial(0, acname)
                #Get date of reconciliation and bank charges for month
                rdate = request.values.get('rdate')
                recdate = datetime.datetime.strptime(rdate, "%Y-%m-%d")
                recmo = recdate.month
                #if recothese is not None: recmo = 25 #Do not record month until reconciliation final
                bkcharges = request.values.get('bkcharges')
                bkcharges = d2s(bkcharges)
                bkchargeid = 0
                try:
                    bkf = float(bkcharges)
                    print('bkf=',bkf)
                    if bkf > 0.0:
                        bank_jo = enter_bk_charges(acname, bkcharges, rdate, username)
                        gdat = Gledger.query.filter((Gledger.Tcode == bank_jo) & (Gledger.Type=='PC')).first()
                        if gdat is not None:
                            bkchargeid = gdat.id
                except:
                    bkf = 0.00

                odervec = selected_bank_ids(odata)
                print('bkid=',bkchargeid)
                if bkchargeid > 0 and bkchargeid not in odervec: odervec.append(bkchargeid)
                hv[1] = odervec
                print('hv[1]', hv[1])
                for oder in odervec:
                    gdat = Gledger.query.get(oder)
                    gdat.Reconciled=25
                db.session.commit()
                acctinfo = banktotals(acname)
                hv[2], hv[3], hv[4], dlist, wlist = recon_totals(acname)
                print(hv[2],hv[3])
                save_trial_reconciliation(acname, recdate, acctinfo[9], acctinfo[4], hv[2], hv[3], hv[4], dlist, wlist, acctinfo[5])
                odata = dataget_Bank(thismuch, acname)

                if finalize is not None:
                    reset_trial(recmo, acname)
                    reconciled_jobs = mark_reconciled_payment_jobs(odervec)
                    hv[1] = [0]
                    rdat = Reconciliations.query.filter((Reconciliations.Rdate == hv[0]) & (Reconciliations.Account == acname)).first()
                    try:
                        dlists = recon_list_text(dlist)
                    except:
                        dlists = None
                    try:
                        wlists = recon_list_text(wlist)
                    except:
                        wlists = None
                    if rdat is None:
                        input = Reconciliations(Account=acname,Rdate=hv[0],Bbal=acctinfo[9],Ebal=acctinfo[4],Deposits=hv[2],Withdraws=hv[3],Servicefees=hv[4],DepositList=dlists,WithdrawList=wlists,Status=1,Diff=acctinfo[5])
                        db.session.add(input)
                        db.session.commit()
                    else:
                        print('diff', acctinfo[5])
                        rdat.Account = acname
                        rdat.Bbal = acctinfo[9]
                        rdat.Ebal = acctinfo[4]
                        rdat.Servicefees = hv[4]
                        rdat.Deposits = hv[2]
                        rdat.Withdraws = hv[3]
                        rdat.DepositList = dlists
                        rdat.WithdrawList = wlists
                        rdat.Status = 1
                        rdat.Rdate = hv[0]
                        rdat.Diff = acctinfo[5]
                        db.session.commit()
                    err.append(f'Reconciliation data saved for Account {acname} Date: {hv[0]}')
                    if reconciled_jobs:
                        err.append(f'Marked {reconciled_jobs} paid job(s) as bank reconciled')

            else:
                err.append('No items checked for reconciliation')

        if undothese is not None:

            odervec = selected_bank_ids(odata)
            for oder in odervec:
                gdat = Gledger.query.get(oder)
                gdat.Reconciled=0
                db.session.commit()
                acctinfo = banktotals(acname)
# ____________________________________________________________________________________________________________________B.Modify.General
        if (modify is not None or vmod is not None) and numchecked==1 :
            modlink=1
            leftsize=6
            if vmod is not None:
                leftscreen=0

            if oder>0:
                modata=Income.query.get(oder)
                docref=modata.Original

        if (modify is not None or vmod is not None) and numchecked!=1:
            modlink=0
            err[0]=' '
            err[2]='Must check exactly one box to use this option'
# ____________________________________________________________________________________________________________________E.Modify.General

# ____________________________________________________________________________________________________________________B.Delete.General
        if deletehit is not None and numchecked==1:
            if oder>0:
                #This section is to determine if we can delete the source file along with the data.  If other data is pointing to this
                #file then we need to keep it.
                modata=Income.query.get(oder)

                Income.query.filter(Income.id == oder).delete()
                db.session.commit()

        if deletehit is not None and numchecked != 1:
            err=[' ', ' ', 'Must have exactly one item checked to use this option', ' ',  ' ']


# ____________________________________________________________________________________________________________________E.Delete.General
        if (depositmake is not None or recdeposit is not None) and depojo is not None:
            err=['Must have exactly one item checked to use this option', ' ',  ' ']

            odervec = numcheckv(odata)
            if len(odervec)>0:
                oderstring = json.dumps(odervec)
            else:
                udat=users.query.filter(users.name=='cache').first()
                oderstring = udat.email
                odervec = json.loads(oderstring)

            if odervec is not None:
                cache = request.values.get('cache')
                if cache is None:
                    cache = 2

                if recdeposit is not None:
                    cache,docref=reportmaker('recdeposit',odervec)
                    for oder in odervec:
                        idat=Income.query.get(oder)
                        subjo = idat.SubJo
                        ref = idat.Ref
                        idata = Income.query.filter((Income.SubJo==subjo) & (Income.Ref==ref) ).all()
                        for data in idata:
                            data.SubJo = depojo
                            db.session.commit()


                    from gledger_write import gledger_write
                    gledger_write('deposit',depojo,acctsel,0, 0, 0)

                else:
                    cache,docref=reportmaker('deposit',odervec)

                leftscreen = 0


        if viewo is not None and numchecked == 1:
            if oder>0:
                modata=Income.query.get(oder)
                depojo = modata.SubJo
                docref = f'tmp/{scac}/data/vdeposits/' + depojo + '.pdf'
                leftscreen = 0



        if unrecord is not None and numchecked!=1:
            modlink=0
            err[0]=' '
            err[2]='Must check exactly one box to use this option'



        if cache is not None:
            #Save the current cache so we do not start from bad place in future
            udat=users.query.filter(users.name=='cache').first()
            udat.username=str(cache)
            udat.email=oderstring
            db.session.commit()

    #This is the else for 1st time through (not posting data from overseas.html)
    else:
        from webapp.viewfuncs import popjo, jovec, timedata, nonone, nononef, init_truck_zero,d2s, erud
        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        hv = [0]*9
        hv[0] = today_str
        hv[1] = [0]
        now = datetime.datetime.now().strftime('%I:%M %p')
        oder=0
        modata=0
        modlink=0
        odata = Income.query.all()
        leftscreen=1
        leftsize=10
        docref=''
        err=['All is well', ' ', ' ', ' ',  ' ']
        thismuch = '1'
        udat=users.query.filter(users.name=='Cache').first()
        cache=udat.username
        cache=nonone(cache)
        adat = Accounts.query.filter(Accounts.Type=='Bank').first()
        bankacct = adat.Name
        defaults = statement_defaults(bankacct, today_str)
        hv[0] = defaults['rdate']
        acctinfo = banktotals(bankacct)
        odata = dataget_Bank(thismuch,bankacct)
        hv[1] = trial_ids(odata)


    leftsize = 8
    acdata = Accounts.query.filter(Accounts.Type=='Bank').all()
    err=erud(err)



    return odata,oder,err,modata,modlink,leftscreen,leftsize,today,now,docref,cache,acdata,thismuch,acctinfo,hv

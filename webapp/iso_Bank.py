from webapp import db
from webapp.models import Income, Accounts, users, JO, Gledger, Reconciliations
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

def reset_trial(ix):
    gdata = Gledger.query.filter(Gledger.Reconciled == 25).all()
    for gdat in gdata:
        gdat.Reconciled = ix
    db.session.commit()

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
    endbal = request.values.get('endbal')
    begbal = request.values.get('begbal')
    print(begbal,endbal)
    try:
        endbal = float(endbal)
    except:
        endbal=0.00
    try:
        begbal = float(begbal)
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

        from viewfuncs import parseline, popjo, jovec, newjo, timedata, nonone, nononef, enter_bk_charges
        from viewfuncs import numcheck, numcheckv, viewbuttons, get_ints, numcheckvec, numcheckv, d2s, erud

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
        rdate = request.values.get('rdate')
        if rdate is None:
            rdate = today_str
        hv[0] = rdate
        hv[1] = [0]
        endbal = request.values.get('endbal')
        begbal = request.values.get('begbal')
        recready = 1
        try:
            endbal=float(endbal)
        except:
            endbal=0.00
            err.append('No Statement Balance Entered for Reconciliation')
            recready=0
        try:
            begbal=float(begbal)
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
        acctinfo = banktotals(acname)
# ____________________________________________________________________________________________________________________B.Search.General

        if modlink==0:
            oder,numchecked=numcheck(1,odata,0,0,0,0,['oder'])

# ____________________________________________________________________________________________________________________E.Search.General
        if (recothese is not None or finalize is not None) and recready == 1:

            if numchecked > -1:

                reset_trial(0)
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

                odervec = numcheckv(odata)
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
                odata = dataget_Bank(thismuch, acname)

                if finalize is not None:
                    reset_trial(recmo)
                    hv[1] = [0]
                    rdat = Reconciliations.query.filter((Reconciliations.Rdate == hv[0]) & (Reconciliations.Account == acname)).first()
                    try:
                        dlists = json.dumps(dlist)
                    except:
                        dlists = None
                    try:
                        wlists = json.dumps(wlist)
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

            else:
                err.append('No items checked for reconciliation')

        if undothese is not None:

            odervec = numcheckv(odata)
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
                    gledger_write('deposit',depojo,acctsel,0)

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
        from viewfuncs import popjo, jovec, timedata, nonone, nononef, init_truck_zero,d2s, erud
        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        hv = [0]*9
        hv[0] = today_str
        hv[1] = [0]
        now = datetime.datetime.now().strftime('%I:%M %p')
        reset_trial(0)
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
        acctinfo = banktotals(bankacct)
        odata = dataget_Bank(thismuch,bankacct)


    leftsize = 8
    acdata = Accounts.query.filter(Accounts.Type=='Bank').all()
    err=erud(err)



    return odata,oder,err,modata,modlink,leftscreen,leftsize,today,now,docref,cache,acdata,thismuch,acctinfo,hv

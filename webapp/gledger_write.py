from webapp import db
from webapp.models import Gledger, Invoices, JO, Income, Bills, Accounts, People, Focusareas, Deposits, Adjusting
import datetime
from webapp.viewfuncs import stripper
import json

def get_company(pid):
    cdat = People.query.get(pid)
    if cdat is not None:
        co = cdat.Company
    else:
        adat = Accounts.query.get(pid)
        if adat is not None:
            co = adat.Name
        else:
            co = 'Not There'
            print('Problem finding vendor')
    return co

def check_revenue_acct(fd):
    fdat = Focusareas.query.filter(Focusareas.Focusid==fd).first()
    if fdat is not None:
        focus = stripper(fdat.Name)
        co = fdat.Co
        revacct = f'{focus} Revenues'
        adat = Accounts.query.filter((Accounts.Name == revacct) & (Accounts.Co == co)).first()
        if adat is not None:
            return revacct
        else:
            #Need to add this revenue account
            input = Accounts(Name=revacct, Balance=0.00, AcctNumber=None, Routing=None, Payee=None,
                             Type='Income',Description='Focus Area Revenue', Category='Direct', Subcategory=focus,
                             Taxrollup='Income:Gross receipts or sales', Co=co,
                             QBmap=None, Shared=None)
            db.session.add(input)
            db.session.commit()
            return revacct
    else:
        return 'Error'

def gledger_multi_job(bus,jolist,acctdb,acctcr):
    dt = datetime.datetime.now()
    jo = jolist[0]
    cc = jo[0]  # this is the company we will be working on
    fd = jo[1]
    if bus == 'income':

        if 'Cash' in acctdb or 'Check' in acctdb or 'Mcheck' in acctdb or 'Undeposited' in acctdb:
            acctdb = 'Cash'
            dtype = 'ID'
        else:
            dtype = 'DD'
            # Else we will write directly to the bank account
        acctcr = 'Accounts Receivable'
        idat = Income.query.filter(Income.Jo == jo).first()
        pid = idat.Pid
        date = idat.Date
        co = get_company(pid)
        ref = idat.Ref

        amt = 0
        for joget in jolist:
            idat = Income.query.filter(Income.Jo == joget).first()
            amt = amt + int(float(idat.Amount) * 100)


        acr = Accounts.query.filter((Accounts.Name == acctcr) & (Accounts.Co == cc)).first()
        adb = Accounts.query.filter((Accounts.Name == acctdb) & (Accounts.Co == cc)).first()

        gdat = Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'IC')).first()
        if gdat is not None:
            gdat.Account = acctcr
            gdat.Credit = amt
            gdat.Recorded = dt
            gdat.Aid = acr.id
            gdat.Date = date
        else:
            source = json.dumps(jolist)
            input1 = Gledger(Debit=0, Credit=amt, Account=acctcr, Aid=acr.id, Source=source, Sid=pid, Type='IC', Tcode=jo,
                             Com=cc, Recorded=dt, Reconciled=0, Date=date, Ref=ref)
            db.session.add(input1)
        db.session.commit()
        gdat = Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == dtype)).first()
        if gdat is not None:
            gdat.Account = acctdb
            gdat.Debit = amt
            gdat.Recorded = dt
            gdat.Aid = adb.id
            gdat.Date = date
        else:
            input2 = Gledger(Debit=amt, Credit=0, Account=acctdb, Aid=adb.id, Source=co, Sid=pid, Type=dtype, Tcode=jo,
                             Com=cc, Recorded=dt, Reconciled=0, Date=date, Ref=ref)
            db.session.add(input2)
        db.session.commit()

def gledger_app_write(sapp,jo,cofor,id1,id2,amt):
    dt = datetime.datetime.now()
    bdat = Bills.query.filter(Bills.Jo == jo).first()
    bdate = bdat.bDate
    co = bdat.Company
    pid = bdat.Pid
    if sapp == 'app1':
        ad = 'AD'
        ac = 'AC'
    elif sapp == 'app2':
        ad = 'BD'
        ac = 'BC'

    adb = Accounts.query.get(id1)
    acr = Accounts.query.get(id2)
    acctdb = adb.Name
    acctcr = acr.Name
    amt = int(float(amt) * 100)

    gdat = Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == ad)).first()
    if gdat is not None:
        gdat.Debit = amt
        gdat.Recorded = dt
        gdat.Date = bdate
    else:
        input1 = Gledger(Debit=amt, Credit=0, Account=acctdb, Aid=adb.id, Source=co, Sid=pid, Type=ad, Tcode=jo,
                         Com=cofor, Recorded=dt, Reconciled=0, Date=bdate, Ref=bdat.Ref)
        db.session.add(input1)
    db.session.commit()

    gdat = Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == ac)).first()
    if gdat is not None:
        gdat.Credit = amt
        gdat.Recorded = dt
        gdat.Date = bdate
    else:
        input2 = Gledger(Debit=0, Credit=amt, Account=acctcr, Aid=acr.id, Source=co, Sid=pid, Type=ac, Tcode=jo,
                         Com=cofor, Recorded=dt, Reconciled=0, Date=bdate, Ref=bdat.Ref)
        db.session.add(input2)
    db.session.commit()


def gledger_write(bus,jo,acctdb,acctcr):
    if 1 == 1:
        err = []
        dt = datetime.datetime.now()
        cc=jo[0] # this is the company we will be working on
        fd=jo[1]

        if bus=='invoice':
            acctdb='Accounts Receivable'
            acctcr = check_revenue_acct(fd)
            #acctcr='Revenues'
            print(jo)
            idat=Invoices.query.filter(Invoices.Jo==jo).first()
            amt=int(float(idat.Total)*100)
            pid=idat.Pid
            date = idat.Date
            co = get_company(pid)

            adb=Accounts.query.filter((Accounts.Name==acctdb) & (Accounts.Co ==cc)).first()
            acr=Accounts.query.filter((Accounts.Name==acctcr) & (Accounts.Co ==cc)).first()

            if adb is None:
                err.append(f'Error: Do not have an Account:{acctdb} for Company:{cc}')
            elif acr is None:
                err.append(f'Error: Do not have an Account:{acctcr} for Company:{cc}')
            else:

                gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type=='VD')).first()
                if gdat is not None:
                    gdat.Debit=amt
                    gdat.Recorded=dt
                    gdat.Date = date
                else:
                    input1 = Gledger(Debit=amt,Credit=0,Account=acctdb,Aid=adb.id,Source=co,Sid=pid,Type='VD',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=date,Ref=None)
                    db.session.add(input1)
                db.session.commit()
                gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type=='VC')).first()
                if gdat is not None:
                    gdat.Credit=amt
                    gdat.Recorded=dt
                    gdat.Date = date
                else:
                    input2 = Gledger(Debit=0,Credit=amt,Account=acctcr,Aid=acr.id,Source=co,Sid=pid,Type='VC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=date,Ref=None)
                    db.session.add(input2)
                db.session.commit()

        if bus=='income':

            if 'Cash' in acctdb or 'Check' in acctdb or 'Mcheck' in acctdb or 'Undeposited' in acctdb:
                acctdb='Cash'
                dtype = 'ID'
            else:
                dtype = 'DD'
                # Else we will write directly to the bank account
            acctcr='Accounts Receivable'
            idat=Income.query.filter(Income.Jo==jo).first()
            amt=int(float(idat.Amount)*100)
            pid=idat.Pid
            date = idat.Date
            co = get_company(pid)

            acr=Accounts.query.filter((Accounts.Name==acctcr) & (Accounts.Co ==cc)).first()
            adb=Accounts.query.filter((Accounts.Name==acctdb) & (Accounts.Co ==cc)).first()

            gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type=='IC')).first()
            if gdat is not None:
                gdat.Account=acctcr
                gdat.Credit=amt
                gdat.Recorded=dt
                gdat.Aid=acr.id
                gdat.Date = date
            else:
                input1 = Gledger(Debit=0,Credit=amt,Account=acctcr,Aid=acr.id,Source=co,Sid=pid,Type='IC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=date,Ref=idat.Ref)
                db.session.add(input1)
            db.session.commit()
            gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type==dtype)).first()
            if gdat is not None:
                gdat.Account=acctdb
                gdat.Debit=amt
                gdat.Recorded=dt
                gdat.Aid=adb.id
                gdat.Date = date
            else:
                input2 = Gledger(Debit=amt,Credit=0,Account=acctdb,Aid=adb.id,Source=co,Sid=pid,Type=dtype,Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=date,Ref=idat.Ref)
                db.session.add(input2)
            db.session.commit()

        if bus=='deposit':
            idat=JO.query.filter(JO.jo==jo).first()
            amt=int(float(idat.dinc)*100)
            print('the jo is',jo)
            incdat = Deposits.query.filter(Deposits.Depositnum == jo).first()
            depdate = incdat.Date2
            #For deposits the company reference is carried in as the accr input
            cdat=People.query.filter(People.Company==acctcr).first()
            if cdat is not None:
                comp = cdat.Company
                pid = cdat.id
            else:
                pid=0
                comp = acctcr
            print('cc=',cc)
            acr=Accounts.query.filter((Accounts.Name=='Cash') & (Accounts.Co ==cc)).first()
            adb=Accounts.query.filter((Accounts.Name==acctdb) & (Accounts.Co ==cc)).first()
            # In this case jo is the deposit ticket code
            gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type=='DC')).first()
            if gdat is not None:
                gdat.Account='Cash'
                gdat.Credit=amt
                gdat.Recorded=dt
                gdat.Aid=acr.id
                gdat.Source=comp
                gdat.Sid = pid
                gdat.Date = depdate
            else:
                input1 = Gledger(Debit=0,Credit=amt,Account='Cash',Aid=acr.id,Source=comp,Sid=pid,Type='DC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=depdate,Ref=incdat.Ref)
                db.session.add(input1)

            gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type=='DD')).first()
            if gdat is not None:
                gdat.Account=acctdb
                gdat.Debit=amt
                gdat.Recorded=dt
                gdat.Aid=adb.id
                gdat.Source=comp
                gdat.Sid = pid
                gdat.Date = depdate
            else:
                input2 = Gledger(Debit=amt,Credit=0,Account=acctdb,Aid=adb.id,Source=comp,Sid=pid,Type='DD',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=depdate,Ref=incdat.Ref)
                db.session.add(input2)
            db.session.commit()

        if bus=='newbill':
            bdat=Bills.query.filter(Bills.Jo==jo).first()
            amt=int(float(bdat.bAmount)*100)
            pid=bdat.Pid
            bdate = bdat.bDate
            co = get_company(pid)

            acctcr = 'Accounts Payable'
            print(acctdb,cc)

            adb=Accounts.query.filter((Accounts.Name==acctdb) & (Accounts.Co ==cc)).first() #the expense account
            acr=Accounts.query.filter((Accounts.Name==acctcr) & (Accounts.Co ==cc)).first() #the asset account

            if bdat is not None and adb is not None and acr is not None:

                gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type=='ED')).first()
                if gdat is not None:
                    gdat.Debit=amt
                    gdat.Recorded=dt
                    gdat.Date=bdate
                    gdat.Account=acctdb
                    gdat.Sid = pid
                else:
                    input1 = Gledger(Debit=amt,Credit=0,Account=acctdb,Aid=adb.id,Source=co,Sid=pid,Type='ED',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=bdate,Ref=bdat.Ref)
                    db.session.add(input1)
                db.session.commit()

                gdat = Gledger.query.filter((Gledger.Tcode==jo) &  (Gledger.Type=='EC')).first()
                if gdat is not None:
                    gdat.Credit=amt
                    gdat.Recorded=dt
                    gdat.Date=bdate
                else:
                    input2 = Gledger(Debit=0,Credit=amt,Account=acctcr,Aid=acr.id,Source=co,Sid=pid,Type='EC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=bdate,Ref=bdat.Ref)
                    db.session.add(input2)
                db.session.commit()

            else:
                if bdat is None: err.append(f'Cannot locate Bill JO {jo}')
                if adb is None: err.append(f'Cannot locate Debit Account {acctdb} for {cc}')
                if acr is None: err.append(f'Cannot locate Credit Account {acctcr} for {cc}')

        if bus=='paybill':
            from viewfuncs import check_multi_line

            bdat=Bills.query.filter(Bills.Jo==jo).first()
            err, amt, nbills = check_multi_line(jo)
            iflag = bdat.iflag
            if iflag is not None:
                if iflag > 0:
                    jo = jo + f'-{iflag}'
                    amt = float(bdat.pAmount2)
            amt=int(amt*100)

            pid=bdat.Pid
            pdate = bdat.pDate
            co = get_company(pid)

            acctdb = 'Accounts Payable'
            print(acctcr,cc)

            adb=Accounts.query.filter((Accounts.Name==acctdb) & (Accounts.Co ==cc)).first() #the expense account
            acr=Accounts.query.filter((Accounts.Name==acctcr) & (Accounts.Co ==cc)).first() #the asset account

            if acr is None:
                #This account must be for another company and we have a cross bill situation
                acr = Accounts.query.filter(Accounts.Name == acctcr).first()
                if acr is not None:
                    acrco = acr.Co
                    if acrco != cc:
                        print('Mismatched Bills')
                        newcc = acr.Co

                adat1 = Accounts.query.filter( (Accounts.Name.contains('Due to')) & (Accounts.Name.contains(cc)) & (Accounts.Co == newcc)).first()
                duetodb = adat1.Name
                duetodbid = adat1.id
                adat2 = Accounts.query.filter( (Accounts.Name.contains('Due to')) & (Accounts.Name.contains(newcc)) & (Accounts.Co == cc)).first()
                duetocr = adat2.Name
                duetocrid = adat2.id

                gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Aid==duetoid) & (Gledger.Type=='PD')).first()
                if gdat is not None:
                    gdat.Debit=amt
                    gdat.Recorded=dt
                    gdat.Date = pdate
                else:
                    input1 = Gledger(Debit=amt,Credit=0,Account=duetodb,Aid=duetodbid,Source=co,Sid=pid,Type='PD',Tcode=jo,Com=newcc,Recorded=dt,Reconciled=0,Date=pdate,Ref=bdat.Ref)
                    db.session.add(input1)
                db.session.commit()
                gdat = Gledger.query.filter((Gledger.Tcode==jo) &  (Gledger.Type=='PC')).first()
                if gdat is not None:
                    gdat.Credit=amt
                    gdat.Recorded=dt
                    gdat.Date = pdate
                else:
                    input2 = Gledger(Debit=0,Credit=amt,Account=acctcr,Aid=acr.id,Source=co,Sid=pid,Type='PC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=pdate,Ref=bdat.Ref)
                    db.session.add(input2)
                db.session.commit()

                gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Aid==adb.id) & (Gledger.Type=='QD')).first()
                if gdat is not None:
                    gdat.Debit=amt
                    gdat.Recorded=dt
                    gdat.Date=pdate
                else:
                    input1 = Gledger(Debit=amt,Credit=0,Account=acctdb,Aid=adb.id,Source=co,Sid=pid,Type='QD',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=pdate,Ref=bdat.Ref)
                    db.session.add(input1)
                db.session.commit()
                gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type=='QC')).first()
                if gdat is not None:
                    gdat.Credit=amt
                    gdat.Recorded=dt
                    gdat.Date = pdate
                else:
                    input2 = Gledger(Debit=0,Credit=amt,Account=duetocr,Aid=duetocrid,Source=co,Sid=pid,Type='QC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=pdate,Ref=bdat.Ref)
                    db.session.add(input2)
                db.session.commit()

            else:

                gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Aid==adb.id) & (Gledger.Type=='PD')).first()
                if gdat is not None:
                    gdat.Debit=amt
                    gdat.Recorded=dt
                    gdat.Date=pdate
                else:
                    input1 = Gledger(Debit=amt,Credit=0,Account=acctdb,Aid=adb.id,Source=co,Sid=pid,Type='PD',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=pdate,Ref=bdat.Ref)
                    db.session.add(input1)
                db.session.commit()
                gdat = Gledger.query.filter((Gledger.Tcode==jo) &  (Gledger.Type=='PC')).first()
                if gdat is not None:
                    gdat.Credit=amt
                    gdat.Recorded=dt
                    gdat.Date=pdate
                else:
                    input2 = Gledger(Debit=0,Credit=amt,Account=acctcr,Aid=acr.id,Source=co,Sid=pid,Type='PC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=pdate,Ref=bdat.Ref)
                    db.session.add(input2)
                db.session.commit()

        if bus=='xfer':
            bdat=Bills.query.filter(Bills.Jo==jo).first()
            amt=int(float(bdat.bAmount)*100)
            xdate = bdat.bDate

            adb=Accounts.query.filter((Accounts.Name==acctdb)).first() #the expense account
            acr=Accounts.query.filter((Accounts.Name==acctcr)).first() #the asset account

            #if (adb.Type=='Asset' or adb.Type=='Bank') and (acr.Type=='Asset' or acr.Type=='Bank'):

            gdat1 = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Aid==adb.id) & (Gledger.Type=='XD')).first()
            gdat2 = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Aid==acr.id) & (Gledger.Type=='XC')).first()
            if gdat1 is not None:
                gdat1.Debit=amt
                gdat1.Recorded=dt
                gdat1.Date = xdate
            else:
                input1 = Gledger(Debit=amt,Credit=0,Account=acctdb,Aid=adb.id,Source=acctcr,Sid=acr.id,Type='XD',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=xdate,Ref=bdat.Ref)
                db.session.add(input1)
            db.session.commit()

            if gdat2 is not None:
                gdat2.Credit=amt
                gdat2.Recorded=dt
                gdat2.Date = xdate
            else:
                input2 = Gledger(Debit=0,Credit=amt,Account=acctcr,Aid=acr.id,Source=acctdb,Sid=adb.id,Type='XC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=xdate,Ref=bdat.Ref)
                db.session.add(input2)
            db.session.commit()

        if bus=='dircharge':
            bdat=Bills.query.filter(Bills.Jo==jo).first()
            amt=int(float(bdat.bAmount)*100)
            pid=bdat.Pid
            bdate = bdat.bDate
            co = get_company(pid)

            adb=Accounts.query.filter((Accounts.Name==acctdb) & (Accounts.Co ==cc)).first() #the expense debit account
            acr=Accounts.query.filter((Accounts.Name==acctcr) & (Accounts.Co ==cc)).first() #the paid credit asset account

            gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type=='ED')).first()
            if gdat is not None:
                gdat.Debit=amt
                gdat.Recorded=dt
                gdat.Date=bdate
            else:
                input1 = Gledger(Debit=amt,Credit=0,Account=acctdb,Aid=adb.id,Source=co,Sid=pid,Type='ED',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=bdate,Ref=bdat.Ref)
                db.session.add(input1)
            db.session.commit()

            gdat = Gledger.query.filter((Gledger.Tcode==jo) &  (Gledger.Type=='PC')).first()
            if gdat is not None:
                gdat.Credit=amt
                gdat.Recorded=dt
                gdat.Date=bdate
            else:
                input2 = Gledger(Debit=0,Credit=amt,Account=acctcr,Aid=acr.id,Source=co,Sid=pid,Type='PC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=bdate,Ref=bdat.Ref)
                db.session.add(input2)
            db.session.commit()

        if bus == 'purchase':
            bdat=Bills.query.filter(Bills.Jo==jo).first()
            amt=int(float(bdat.bAmount)*100)
            pid=bdat.Pid
            bdate = bdat.bDate
            co = get_company(pid)

            acctcr = 'Accounts Payable'
            print(acctdb,cc)

            adb=Accounts.query.filter((Accounts.Name==acctdb) & (Accounts.Co ==cc)).first() #the expense account
            acr=Accounts.query.filter((Accounts.Name==acctcr) & (Accounts.Co ==cc)).first() #the asset account

            if bdat is not None and adb is not None and acr is not None:

                gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type=='AD')).first()
                if gdat is not None:
                    gdat.Debit=amt
                    gdat.Recorded=dt
                    gdat.Date=bdate
                    gdat.Account=acctdb
                    gdat.Sid = pid
                else:
                    input1 = Gledger(Debit=amt,Credit=0,Account=acctdb,Aid=adb.id,Source=co,Sid=pid,Type='AD',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=bdate,Ref=bdat.Ref)
                    db.session.add(input1)
                db.session.commit()

                gdat = Gledger.query.filter((Gledger.Tcode==jo) &  (Gledger.Type=='AC')).first()
                if gdat is not None:
                    gdat.Credit=amt
                    gdat.Recorded=dt
                    gdat.Date=bdate
                else:
                    input2 = Gledger(Debit=0,Credit=amt,Account=acctcr,Aid=acr.id,Source=co,Sid=pid,Type='AC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=bdate,Ref=bdat.Ref)
                    db.session.add(input2)
                db.session.commit()


        if bus == 'adjusting':
            bdat=Bills.query.filter(Bills.Jo==jo).first()
            pid = bdat.Pid
            co = get_company(pid)
            adb = Accounts.query.filter((Accounts.Name == acctdb) & (Accounts.Co == cc)).first()  # the expense account
            acr = Accounts.query.filter((Accounts.Name == acctcr) & (Accounts.Co == cc)).first()  # the asset account

            adata=Adjusting.query.filter( (Adjusting.Jo.contains(jo)) & (Adjusting.Moa != 0) ).all()
            for adat in adata:
                amt=int(float(adat.Amta)*100)
                tcode = f'{jo}-{str(adat.Moa)}'
                bdate = adat.Date

                if bdat is not None and adb is not None and acr is not None:

                    gdat = Gledger.query.filter((Gledger.Tcode==tcode) & (Gledger.Type=='ED')).first()
                    if gdat is not None:
                        gdat.Debit=amt
                        gdat.Recorded=dt
                        gdat.Date=bdate
                        gdat.Account=acctdb
                        gdat.Sid = pid
                    else:
                        input1 = Gledger(Debit=amt,Credit=0,Account=acctdb,Aid=adb.id,Source=co,Sid=pid,Type='ED',Tcode=tcode,Com=cc,Recorded=dt,Reconciled=0,Date=bdate,Ref=bdat.Ref)
                        db.session.add(input1)
                    db.session.commit()

                    gdat = Gledger.query.filter((Gledger.Tcode==tcode) & (Gledger.Type=='EC')).first()
                    if gdat is not None:
                        gdat.Credit=amt
                        gdat.Recorded=dt
                        gdat.Date=bdate
                    else:
                        input2 = Gledger(Debit=0,Credit=amt,Account=acctcr,Aid=acr.id,Source=co,Sid=pid,Type='EC',Tcode=tcode,Com=cc,Recorded=dt,Reconciled=0,Date=bdate,Ref=bdat.Ref)
                        db.session.add(input2)
                    db.session.commit()

        #This return for all bus options
        return err
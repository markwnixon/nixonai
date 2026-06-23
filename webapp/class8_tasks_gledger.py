from webapp import db
from webapp.models import Gledger, Invoices, JO, Income, Bills, Accounts, People, Focusareas, Deposits, Adjusting, Orders, PaymentsRec
import datetime
from webapp.viewfuncs import stripper
from webapp.class8_utils import parse_financial_date
import json
from decimal import Decimal, ROUND_HALF_UP


def cents(value):
    try:
        clean = str(value).replace('$', '').replace(',', '').strip()
        if clean in ['', 'None', 'none']:
            clean = '0'
        return int((Decimal(clean) * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except:
        return 0


def debit_credit_for_signed_amount(amount, normal_debit=True):
    """Return positive debit/credit columns, reversing sides for refunds/credits."""
    clean_amount = abs(amount or 0)
    if amount >= 0:
        return (clean_amount, 0) if normal_debit else (0, clean_amount)
    return (0, clean_amount) if normal_debit else (clean_amount, 0)


def audit_journal_balance(journal_id):
    lines = Gledger.query.filter(Gledger.JournalId == journal_id).all()
    debit_total = sum(line.Debit or 0 for line in lines)
    credit_total = sum(line.Credit or 0 for line in lines)
    if debit_total != credit_total:
        return [f'Journal {journal_id} out of balance: debits {debit_total} credits {credit_total}']
    return []


def post_balanced_journal(lines, journal_id=None, journal_memo=None, posted_by='class8',
                          source_table=None, source_id=None):
    err = []
    debit_total = sum(line.get('debit', 0) for line in lines)
    credit_total = sum(line.get('credit', 0) for line in lines)
    if debit_total != credit_total:
        return [f'Ledger out of balance: debits {debit_total} credits {credit_total}']
    if debit_total <= 0:
        return ['Ledger amount must be greater than zero']

    required = ['account', 'aid', 'source', 'sid', 'type', 'tcode', 'com', 'date']
    for line in lines:
        for key in required:
            if line.get(key) is None:
                err.append(f"Ledger line missing {key} for {line.get('tcode')} {line.get('type')}")
        line_date = parse_financial_date(line.get('date'))
        if line_date is None:
            err.append(f"Ledger line has invalid date for {line.get('tcode')} {line.get('type')}")
        else:
            line['date'] = line_date
    if err:
        return err

    for line in lines:
        query = Gledger.query.filter(
            (Gledger.Tcode == line['tcode']) &
            (Gledger.Type == line['type'])
        )
        if line.get('match_aid', False):
            query = query.filter(Gledger.Aid == line['aid'])
        existing = query.first()
        if existing is not None and existing.Reconciled not in [None, 0, 25]:
            return [f"Cannot update reconciled ledger line {existing.Tcode} {existing.Type}. Reopen the reconciliation first."]

    try:
        posted_at = datetime.datetime.now()
        if journal_id is None:
            journal_id = lines[0].get('journal_id')
        if journal_memo is None:
            journal_memo = lines[0].get('journal_memo')
        if source_table is None:
            source_table = lines[0].get('source_table')
        if source_id is None:
            source_id = lines[0].get('source_id')

        for seq, line in enumerate(lines, start=1):
            query = Gledger.query.filter(
                (Gledger.Tcode == line['tcode']) &
                (Gledger.Type == line['type'])
            )
            if line.get('match_aid', False):
                query = query.filter(Gledger.Aid == line['aid'])
            gdat = query.first()
            if gdat is not None:
                gdat.Debit = line.get('debit', 0)
                gdat.Credit = line.get('credit', 0)
                gdat.Account = line['account']
                gdat.Aid = line['aid']
                gdat.Source = line['source']
                gdat.Sid = line['sid']
                gdat.Com = line['com']
                gdat.Recorded = line['recorded']
                gdat.Date = line['date']
                gdat.Ref = line.get('ref')
                gdat.JournalId = journal_id
                gdat.JournalSeq = seq
                gdat.JournalMemo = journal_memo
                gdat.PostedBy = posted_by
                gdat.PostedAt = posted_at
                gdat.SourceTable = source_table
                gdat.SourceId = source_id
            else:
                input_line = Gledger(Debit=line.get('debit', 0), Credit=line.get('credit', 0),
                                     Account=line['account'], Aid=line['aid'], Source=line['source'],
                                     Sid=line['sid'], Type=line['type'], Tcode=line['tcode'],
                                     Com=line['com'], Recorded=line['recorded'], Reconciled=0,
                                     Date=line['date'], Ref=line.get('ref'),
                                     JournalId=journal_id, JournalSeq=seq, JournalMemo=journal_memo,
                                     PostedBy=posted_by, PostedAt=posted_at,
                                     SourceTable=source_table, SourceId=source_id)
                db.session.add(input_line)
        db.session.commit()
        if journal_id:
            err = audit_journal_balance(journal_id)
            if err:
                db.session.rollback()
                return err
    except Exception as exc:
        db.session.rollback()
        return [f'Ledger write failed: {exc}']

    return []


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
           #print('Problem finding vendor')
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
        odat = Orders.query.filter(Orders.Jo == jo).first()
        pid = odat.Bid
        date = odat.PaidDate
        co = get_company(pid)
        ref = odat.PayRef

        print(f'Filing multiple account payments with Amount = {amt}, Account = {acctcr}, Source = {co}')
        #input_paymnt = PaymentsRec(Amount=amt, Account=acctcr, Source=co, Type=dtype, Com=cc, Recorded=dt, Date=paidon, Ref=payref)
        #db.session.add(input_paymnt)
        #db.session.commit()
        #refid = input_paymnt.id  # this links the total payment to the applied payment for the job
        #odat.QBi = refid



        amt = 0
        for joget in jolist:
            odat = Orders.query.filter(Orders.Jo == joget).first()
            amt = amt + cents(odat.InvoTotal)


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
    amt = cents(amt)

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


def gledger_write(busvec,jo,acctdb,acctcr,refid):
    if 1 == 1:
        err = []
        bus = busvec[0]
        #['income', amtpaid, paidon, payref, paymethod]
        dt = datetime.datetime.now()
        cc=jo[0] # this is the company we will be working on
        fd=jo[1]

        if bus=='invoice':
            amtinvo = busvec[1]
            amt = cents(amtinvo)
            acctdb='Accounts Receivable'
            acctcr = check_revenue_acct(fd)
            #acctcr='Revenues'
           #print('Gledger Write:',jo, acctdb, acctcr)
            idat=Invoices.query.filter(Invoices.Jo==jo).first()
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

            amtpaid, paidon, payref, paymethod = busvec[1], busvec[2], busvec[3], busvec[4]
            amt = cents(amtpaid)
            if 'Cash' in acctdb or 'Check' in acctdb or 'Mcheck' in acctdb or 'Undeposited' in acctdb:
                acctdb='Undeposited Funds'
                dtype = 'ID'
            else: dtype = 'DD'
            acctcr='Accounts Receivable'


            odat=Orders.query.filter(Orders.Jo==jo).first()
            #amt=int(float(odat.PaidAmt)*100)
            pid=odat.Bid
            #date = odat.PaidDate
            co = get_company(pid)

            acr=Accounts.query.filter((Accounts.Name==acctcr) & (Accounts.Co ==cc)).first()
            adb=Accounts.query.filter((Accounts.Name==acctdb) & (Accounts.Co ==cc)).first()

            gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type=='IC')).first()
            if gdat is not None:
                gdat.Account=acctcr
                gdat.Credit=amt
                gdat.Recorded=dt
                gdat.Aid=acr.id
                gdat.Date = paidon
                gdat.Ref = payref
            else:
                input1 = Gledger(Debit=0,Credit=amt,Account=acctcr,Aid=acr.id,Source=co,Sid=refid,Type='IC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=paidon,Ref=payref)
                db.session.add(input1)
            db.session.commit()
            gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type==dtype)).first()
            if gdat is not None:
                gdat.Account = acctdb
                gdat.Debit = amt
                gdat.Recorded = dt
                gdat.Aid = adb.id
                gdat.Date = paidon
            else:
                input2 = Gledger(Debit=amt,Credit=0,Account=acctdb,Aid=adb.id,Source=co,Sid=refid,Type=dtype,Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=paidon,Ref=payref)
                db.session.add(input2)
            db.session.commit()

        if bus=='deposit':

            odat=Orders.query.filter(Orders.Jo==jo).first()
            amt=cents(odat.PaidAmt)
            pid=odat.Bid
            date = odat.PaidDate
            co = get_company(pid)

            incdat = Deposits.query.filter(Deposits.Depositnum == jo).first()
            if incdat is None:
                #This must be a direct deposit and need to create the deposit ticket
                input = Deposits()
            depdate = incdat.Date2
            #For deposits the company reference is carried in as the accr input
            cdat=People.query.filter(People.Company==acctcr).first()
            if cdat is not None:
                comp = cdat.Company
                pid = cdat.id
            else:
                pid=0
                comp = acctcr
           #print('cc=',cc)
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
            amt=cents(bdat.bAmount)
            expense_debit, expense_credit = debit_credit_for_signed_amount(amt, normal_debit=True)
            payable_debit, payable_credit = debit_credit_for_signed_amount(amt, normal_debit=False)
            pid=bdat.Pid
            bdate = bdat.Date
            co = get_company(pid)

            acctcr = 'Accounts Payable'
           #print(acctdb,cc)

            adb=Accounts.query.filter((Accounts.Name==acctdb) & (Accounts.Co ==cc)).first() #the expense account
            acr=Accounts.query.filter((Accounts.Name==acctcr) & (Accounts.Co ==cc)).first() #the asset account

            if bdat is not None and adb is not None and acr is not None:

                gdat = Gledger.query.filter((Gledger.Tcode==jo) & (Gledger.Type=='ED')).first()
                if gdat is not None:
                    gdat.Debit=expense_debit
                    gdat.Credit=expense_credit
                    gdat.Recorded=dt
                    gdat.Date=bdate
                    gdat.Account=acctdb
                    gdat.Sid = pid
                else:
                    input1 = Gledger(Debit=expense_debit,Credit=expense_credit,Account=acctdb,Aid=adb.id,Source=co,Sid=pid,Type='ED',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=bdate,Ref=bdat.Ref)
                    db.session.add(input1)
                db.session.commit()

                gdat = Gledger.query.filter((Gledger.Tcode==jo) &  (Gledger.Type=='EC')).first()
                if gdat is not None:
                    gdat.Debit=payable_debit
                    gdat.Credit=payable_credit
                    gdat.Recorded=dt
                    gdat.Date=bdate
                else:
                    input2 = Gledger(Debit=payable_debit,Credit=payable_credit,Account=acctcr,Aid=acr.id,Source=co,Sid=pid,Type='EC',Tcode=jo,Com=cc,Recorded=dt,Reconciled=0,Date=bdate,Ref=bdat.Ref)
                    db.session.add(input2)
                db.session.commit()

            else:
                if bdat is None: err.append(f'Cannot locate Bill JO {jo}')
                if adb is None: err.append(f'Cannot locate Debit Account {acctdb} for {cc}')
                if acr is None: err.append(f'Cannot locate Credit Account {acctcr} for {cc}')

        if bus=='paybill':
            from webapp.viewfuncs import check_multi_line

            bdat=Bills.query.filter(Bills.Jo==jo).first()
            if bdat is None:
                return [f'Cannot locate Bill JO {jo}']

            err, amt, nbills = check_multi_line(jo)
            if err:
                return err

            iflag = bdat.iflag
            if iflag is not None:
                if iflag > 0:
                    jo = jo + f'-{iflag}'
                    amt = bdat.pAmount2
            amt=cents(amt)
            refund = amt < 0
            post_amt = abs(amt)
            journal_id = f'PAYBILL-{jo}'

            pid=bdat.Pid
            pdate = parse_financial_date(bdat.pDate)
            if pdate is None:
                return [f'Paid date for bill {jo} is invalid. Use a four digit year such as 2026-02-09 before recording payment.']
            co = get_company(pid)

            acctdb = 'Accounts Payable'

            adb=Accounts.query.filter((Accounts.Name==acctdb) & (Accounts.Co ==cc)).first() #the AP debit account
            acr=Accounts.query.filter((Accounts.Name==acctcr) & (Accounts.Co ==cc)).first() #the paid credit account

            if adb is None:
                return [f'Cannot locate Debit Account {acctdb} for {cc}']

            if acr is None:
                #This account must be for another company and we have a cross bill situation
                acr = Accounts.query.filter(Accounts.Name == acctcr).first()
                if acr is None:
                    return [f'Cannot locate Credit Account {acctcr}']
                newcc = acr.Co
                if newcc == cc:
                    return [f'Cannot locate Credit Account {acctcr} for {cc}']

                adat1 = Accounts.query.filter( (Accounts.Name.contains('Due to')) & (Accounts.Name.contains(cc)) & (Accounts.Co == newcc)).first()
                adat2 = Accounts.query.filter( (Accounts.Name.contains('Due to')) & (Accounts.Name.contains(newcc)) & (Accounts.Co == cc)).first()
                if adat1 is None:
                    return [f'Cannot locate due-to account for {cc} in {newcc}']
                if adat2 is None:
                    return [f'Cannot locate due-to account for {newcc} in {cc}']

                err = post_balanced_journal([
                    {'debit': 0 if refund else post_amt, 'credit': post_amt if refund else 0, 'account': adat1.Name, 'aid': adat1.id, 'source': co,
                     'sid': pid, 'type': 'PD', 'tcode': jo, 'com': newcc, 'recorded': dt,
                     'date': pdate, 'ref': bdat.Ref, 'match_aid': True},
                    {'debit': post_amt if refund else 0, 'credit': 0 if refund else post_amt, 'account': acctcr, 'aid': acr.id, 'source': co,
                     'sid': pid, 'type': 'DD' if refund else 'PC', 'tcode': jo, 'com': cc, 'recorded': dt,
                     'date': pdate, 'ref': bdat.Ref},
                    {'debit': 0 if refund else post_amt, 'credit': post_amt if refund else 0, 'account': acctdb, 'aid': adb.id, 'source': co,
                     'sid': pid, 'type': 'QD', 'tcode': jo, 'com': cc, 'recorded': dt,
                     'date': pdate, 'ref': bdat.Ref, 'match_aid': True},
                    {'debit': post_amt if refund else 0, 'credit': 0 if refund else post_amt, 'account': adat2.Name, 'aid': adat2.id, 'source': co,
                     'sid': pid, 'type': 'QC', 'tcode': jo, 'com': cc, 'recorded': dt,
                     'date': pdate, 'ref': bdat.Ref},
                ], journal_id=journal_id,
                    journal_memo=f'{"Receive refund for" if refund else "Pay"} bill {jo} to {co} from {acctcr}',
                    source_table='Bills', source_id=bdat.id)
                if err:
                    return err

            else:
                err = post_balanced_journal([
                    {'debit': 0 if refund else post_amt, 'credit': post_amt if refund else 0, 'account': acctdb, 'aid': adb.id, 'source': co,
                     'sid': pid, 'type': 'PD', 'tcode': jo, 'com': cc, 'recorded': dt,
                     'date': pdate, 'ref': bdat.Ref, 'match_aid': True},
                    {'debit': post_amt if refund else 0, 'credit': 0 if refund else post_amt, 'account': acctcr, 'aid': acr.id, 'source': co,
                     'sid': pid, 'type': 'DD' if refund else 'PC', 'tcode': jo, 'com': cc, 'recorded': dt,
                     'date': pdate, 'ref': bdat.Ref},
                ], journal_id=journal_id,
                    journal_memo=f'{"Receive refund for" if refund else "Pay"} bill {jo} to {co} from {acctcr}',
                    source_table='Bills', source_id=bdat.id)
                if err:
                    return err

        if bus=='xfer':
            bdat=Bills.query.filter(Bills.Jo==jo).first()
            amt=cents(bdat.bAmount)
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
            amt=cents(bdat.bAmount)
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
            amt=cents(bdat.bAmount)
            pid=bdat.Pid
            bdate = bdat.bDate
            co = get_company(pid)

            acctcr = 'Accounts Payable'
           #print(acctdb,cc)

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
                amt=cents(adat.Amta)
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

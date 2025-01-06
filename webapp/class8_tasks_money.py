import sqlalchemy.sql

from webapp import db
from webapp.models import Orders, Invoices, People, Services, Drops, SumInv, Interchange
from flask import render_template, flash, redirect, url_for, session, logging, request
from webapp.CCC_system_setup import myoslist, addpath, tpath, companydata, scac
from webapp.class8_utils_email import etemplate_truck, emaildata_update, invoice_mimemail, etemplate_suminv
from webapp.class8_dicts import Trucking_genre, Orders_setup, Interchange_setup, Customers_setup, Services_setup, Summaries_setup
from webapp.class8_utils_manifest import makemanifest
from webapp.class8_utils_invoice import make_invo_doc, make_summary_doc
from webapp.viewfuncs import newjo

#Python functions that require database access
from webapp.class8_utils import *
from webapp.utils import *
from webapp.class8_tasks_gledger import gledger_write

import usaddress
from datetime import timedelta

def addr2break(adv):
    ai = ''
    for ad in adv:
        ai = f'{ai} {ad}'
    testpart = usaddress.parse(ai)
    ecity, estate, ezip = '', '', ''
    #print(testpart)
    for te in testpart:
        #print(te[0],te[1])
        if te[1] == 'PlaceName':
            ecity = ecity + te[0] + ' '
        if te[1] == 'StateName':
            estate = te[0].upper()
        if te[1] == 'ZipCode':
            ezip = te[0]
    ecity = ecity.replace(',','')
    ecity = ecity.strip()
    ecity = ecity.title()
    return ecity, estate, ezip

def loginvo_m(odat,ix):
    alink = odat.Links
    #print(f'ix is {ix} and alink is {alink}')
    if hasinput(alink):
        if 1 == 1:
            alist = json.loads(alink)
            for aoder in alist:
                aoder = nonone(aoder)
                thisodat = Orders.query.get(aoder)
                amtinvo = thisodat.InvoTotal
                #print(aoder,thisodat.Istat)
                jo = thisodat.Jo
                gledger_write(['invoice',amtinvo], jo, 0, 0)
                thisodat.Istat = ix
                db.session.commit()
    else:
        jo = odat.Jo
        amtinvo = odat.InvoTotal
        err = gledger_write(['invoice', amtinvo], jo, 0, 0)
        odat.Istat = ix
        db.session.commit()
    return err

def gettimes(input):
    try:
        each = input.split('-')
        time1 = datetime.datetime.strptime(each[0], '%H:%M')
        time2 = time1 + timedelta(2 / 24)
        time3 = datetime.datetime.strptime(each[1], '%H:%M')
        serviceqty = time3 - time2
        serviceqty = serviceqty.seconds/3600

        time1 = time1.strftime('%H:%M')
        time2 = time2.strftime('%H:%M')
        time3 = time3.strftime('%H:%M')
        status = 1
    except:
        time1, time2, time3, serviceqty, status ='0:00','0:00','0:00',1.0,0

    return time1, time2, time3, serviceqty, status


def getservice(myo, service, serviceqty, serviceamt, servicestr):

    sdat = Services.query.filter(Services.Code == service).first()
    if sdat is not None:
        #print(f'Evaluating {service}, {serviceqty}, {serviceamt}, {servicestr}')
        nextservice = sdat.Service
        if str(serviceamt) == 'default':
            each = float(sdat.Price)
        else:
            each = float(serviceamt)
        if str(serviceqty) == 'default':
            amount = each
            descript = f' For {nextservice}'
        else:
            amount = each*float(serviceqty)
    else:
        nextservice = 'Nothing Here'
        each = 0.00
        amount = 0.00
        descript = 'Nothing'

    if nextservice == 'Per Diem':
        descript = 'Shipline invoiced per diem'
    elif nextservice == 'Drv Detention':
        if servicestr == 'default':
            descript = f'Actual Time of Load = {2 + serviceqty} Hours'
        else:
            time1, time2, time3, serviceqty, status = gettimes(servicestr)
            if status == 1:
                descript = f'Free time {time1}-{time2}, detention {time2}-{time3}'
                amount = each * serviceqty
            else:
                amount = 0.00
                descript = 'Improper times provided on input'

    elif nextservice == 'Storage Fee':
        if str(serviceqty) == 'default':
            qty = myo.Date2 - myo.Date
            serviceqty = qty.days - 1
            if serviceqty <= 0: serviceqty = 1
        dt1 = myo.Date + timedelta(1)
        dt2 = myo.Date2 - timedelta(1)
        descript = f'Days of Yard Storage, {dt1} to {dt2}'
        amount = each*serviceqty
    elif nextservice == 'Chassis Fees':
        if str(serviceqty) == 'default':
            qty = myo.Date2 - myo.Date
            serviceqty = qty.days + 1
            if serviceqty <= 0: serviceqty = 1
        amount = each * serviceqty
        descript = f'Days of Chassis, {myo.Date} to {myo.Date2}'

    if str(serviceqty) == 'default': serviceqty = 1.0

    return nextservice, descript, each, serviceqty, amount


def get_digits_after_character(input_string, character):
    found_character = False
    digits = []

    for char in input_string:
        if found_character:
            if char.isdigit():
                digits.append(char)
            else:
                break
        elif char == character:
            found_character = True

    return ''.join(digits)

def get_invo_data(qblines, myo):
    codes = []
    qtys = []
    prices = []
    descs = []
    labels = []
    for qbl in qblines:
        code = qbl[0:2]
        sdat = Services.query.filter(Services.Code == code).first()
        if sdat is not None:
            codes.append(qbl[0:2])
            price = float(sdat.Price)
            qty = 1.0
            label = sdat.Service
            desc = f'Code {code} description'

            #Special services based on dates

            if code == 'ch':
                qty = myo.Date2 - myo.Date
                qty = qty.days + 1
                desc = f'Days of Chassis, {myo.Date} - {myo.Date2}'

            if code == 'sf':
                qty = myo.Date2 - myo.Date
                qty = qty.days
                date2 = myo.Date2
                stodate2 = date2 - timedelta(1)
                desc = f'Days of Storage, {myo.Date} - {stodate2}'

            if code == 'dd':
                desc = 'Free time 0700-0900, detention 0900-1000'

            if code == 'ow':
                desc = 'Cargo Weight exceeds 45,000 lbs'

            if '=' in qbl:
                newqty = get_digits_after_character(qbl, '=')
                try:
                    qty = int(newqty)
                except:
                    continue

            if '$' in qbl:
                newamt = get_digits_after_character(qbl, '$')
                try:
                    price = float(newamt)
                except:
                    continue

            if '*' in qbl:
                #Need everything after the # sign
                brstrings = qbl.split('*')
                timedata = brstrings[1]
                time1, time2, time3, qty, status = gettimes(timedata)
                #print(time1, time2, time2, qty)
                if status == 1:
                    desc = f'Free time {time1}-{time2}, detention {time2}-{time3}'
                else:
                    desc = 'Improper times provided on input'



            qtys.append(qty)
            prices.append(price)
            descs.append(desc)
            labels.append(label)

    return codes, labels, descs, qtys, prices



def initialize_invoice(myo, err):
    # First time through: have an order to invoice
    shipper = myo.Shipper
    jo = myo.Jo

    ldat = Invoices.query.filter(Invoices.Jo == jo).first()
    if ldat is None:
        # Check to see if we have the required data to make an invoice or quote:
        bid = myo.Bid
        lid = myo.Lid
        did = myo.Did

        if not hasinput(bid):
            pdat = People.query.filter(People.Company==myo.Shipper).first()
            bid = pdat.id
            myo.Bid = bid

            err.append(f'Billing data added for {myo.Shipper}')

        if bid:
            err.append('Have needed items to make invoice')
            cache = myo.Icache
            if not hasvalue(cache):
                cache = 0
            myo.Icache = cache + 1
            qty = 1

            dblk = myo.Dropblock2
            dblkv = dblk.splitlines()
            ecity,est,ezip = addr2break(dblkv)
            cityzip = f'{ecity}, {est} {ezip}'
            descript = f'Baltimore Seagirt to {cityzip} and return'

            try:
                amount = float(myo.Amount)
            except:
                amount = 0.00

            # If quote block exists, create invoice matching the quote:
            qb = myo.Quote
            if hasinput(qb):
                qblines = qb.split('+')
                # First element must be the job drayage amount
                try:
                    lineamount = float(qblines[0])
                except:
                    lineamount = 0.00
                #print(f'The base amount is {lineamount}')
                input = Invoices(Jo=myo.Jo, SubJo=None, Pid=0, Service='Line Haul', Description=descript,
                                 Ea=d2s(lineamount), Qty=qty, Amount=d2s(lineamount*qty), Total=0.00, Date=today,
                                 Original=None, Status='New')
                db.session.add(input)
                db.session.commit()

                if len(qblines) > 1:
                    qblines = qblines[1:]
                    #print(qblines)
                    codes, labels, descs, qtys, prices = get_invo_data(qblines, myo)
                    #print(codes)
                    #print(labels)
                    #print(descs)
                    #print(qtys)
                    #print(prices)
                    #nextservice, descript, each, serviceqty, amount = getservice(myo, service, serviceqty, serviceamt, servicestr)
                    if len(codes)>0:
                        for jx,code in enumerate(codes):
                            label = labels[jx]
                            descript = descs[jx]
                            each = prices[jx]
                            qty = qtys[jx]
                            amount = float(each*qty)

                            input = Invoices(Jo=myo.Jo, SubJo=None, Pid=0, Service=label, Description=descript,
                                             Ea=d2s(each), Qty=qty, Amount=d2s(amount), Total=0.00, Date=today,
                                             Original=None, Status='New')
                            db.session.add(input)
                        db.session.commit()
            else:
                # No quote provided
                input = Invoices(Jo=myo.Jo, SubJo=None, Pid=0, Service='Line Haul', Description=descript,
                                 Ea=d2s(amount), Qty=qty, Amount=d2s(amount), Total=0.00, Date=today,
                                 Original=None, Status='New')
                db.session.add(input)
                db.session.commit()
    return err

def add_service(myo):
    # These are the services we wish to add to the invoice
    invoserv = request.values.get('invoserv')
    if invoserv is not None:
        servid = nonone(invoserv)
        #print('servid=',servid)
        if servid > 0:
            mys = Services.query.get(servid)
            #print('service is',mys.Service)
            if mys is not None:
                qty = 1
                descript = ' '
                if mys.Service == 'Line Haul':
                    try:
                        descript = 'Order ' + myo.Order + ' Line Haul ' + myo.Company + ' to ' + myo.Company2
                    except:
                        descript = 'Order, Load Comp, or Delv Comp Missing'
                elif mys.Service == 'Detention':
                    descript = 'Actual Time of Load = ' + str(2 + qty) + ' Hours'
                elif mys.Service == 'Storage':
                    descript = 'Days of Storage'
                elif mys.Service == 'Chassis Fees':
                    qty = myo.Date2 - myo.Date
                    qty = qty.days + 1
                    descript = f'Days of Chassis, {myo.Date} - {myo.Date2}'
                amount = float(mys.Price)
                input = Invoices(Jo=myo.Jo, SubJo=None, Pid=0, Service=mys.Service, Description=descript, Ea=d2s(
                    amount), Qty=qty, Amount=d2s(amount), Total=0.00, Date=today, Original=None, Status='New')
                db.session.add(input)
                db.session.commit()

def update_invoice(myo, err, tablesetup, invostyle):
    # Now we have an initial invoice, and may have added parts so we need to update the totals for all the components of the invoice:
    # updateinvo(myo.Jo, myo.Date)
    docref = ''
    jo = myo.Jo
    total = 0.0
    idata = Invoices.query.filter(Invoices.Jo == jo).all()
    for idat in idata:
        qty = float(idat.Qty)
        each = float(idat.Ea)
        amt = qty * each
        total = total + amt
    for idat in idata:
        idat.Total = d2s(total)
        db.session.commit()

    ldat = Invoices.query.filter(Invoices.Jo == myo.Jo).first()
    if ldat is None:
        err.append('No services on invoice yet and none selected')
    else:
        invodate = ldat.Date
        err.append('Created invoice for JO= ' + myo.Jo)
        ldata = Invoices.query.filter(Invoices.Jo == myo.Jo).order_by(Invoices.Ea.desc()).all()
        pdata1 = People.query.filter(People.id == myo.Bid).first()
        cache = myo.Icache

        docref = make_invo_doc(myo, ldata, pdata1, cache, invodate, 0, tablesetup, invostyle)

        for ldatl in ldata:
            ldatl.Pid = pdata1.id
            ldatl.Original = os.path.basename(docref)
            db.session.commit()

        myo.Invoice = os.path.basename(docref)
        myo.Icache = cache + 1
        myo.InvoTotal = d2s(total)
        myo.BalDue = d2s(total)
        myo.Payments = '0.00'
        db.session.commit()

        err.append('Viewing ' + docref)
        idata = Invoices.query.filter(Invoices.Jo == jo).all()

    return idata, docref, err, total

def rehash_invoice(myo, err, invodate):
    jo = myo.Jo
    ldata = Invoices.query.filter(Invoices.Jo == jo).all()
    itotal = 0
    icode = ''
    for data in ldata:
        iqty = request.values.get('qty' + str(data.id))
        iqty = nononef(iqty)
        data.Description = request.values.get('desc' + str(data.id))
        deach = request.values.get('cost' + str(data.id))
        deach = nononef(deach)

        damount = float(iqty) * float(deach)
        itotal = itotal + damount
        deach = "{:.2f}".format(deach)
        damount = "{:.2f}".format(damount)

        data.Qty = iqty
        data.Ea = deach
        icode = icode + '+' + str(data.Qty) + '*' + str(data.Ea)
        data.Amount = damount
        data.Date = invodate
        db.session.commit()

    for data in ldata:
        data.Total = itotal
        db.session.commit()

    # Remove zeros from invoice in case a zero was the mod
    Invoices.query.filter(Invoices.Qty == 0).delete()
    db.session.commit()

    return err


def MakeInvoice_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):

    err = [f"Running Invoice task with task_iter {task_iter} using {tablesetup['table']}"]
    entrydata, holdvec, viewport = [], [0]*30, ['0'] * 6
    #entrydata = tablesetup['entry data']
    #numitems = len(entrydata)
    #holdvec = [''] * numitems
    invoicetypes_allowed = tablesetup['invoicetypes']
    invoicetypes = [key for key, value in invoicetypes_allowed.items()]
    holdvec[3] = invoicetypes
    returnhit = request.values.get('Finished')

    if returnhit is not None:
        completed = True
    else:

        completed = False
        table = tablesetup['table']
        nextquery = f"{table}.query.get({sid})"
        odata1 = eval(nextquery)
        haultype = getattr(odata1, 'HaulType')
        #invostyle = request.values.get('invoicestyle')
        invostyle = getattr(odata1, 'HaulType')
        holdvec[16] = invostyle
        #print(f'The invoice style is {invostyle}')
        headers = tablesetup['invoicetypes'][invostyle]

        #Need to jump over to invoice database
        jo = getattr(odata1, 'Jo')
        sids = [getattr(odata1, 'id')]
        holdvec[0] = jo

        if task_iter > 0:
            failed = 0
            warned = 0

            invodate = request.values.get('invodate')
            if invodate is None:
                invodate = today
            if isinstance(invodate, str):
                invodate = datetime.datetime.strptime(invodate, '%Y-%m-%d')
            holdvec[1] = invodate

            invoserv = request.values.get('invoserv')
            if invoserv is not None:
                add_service(odata1)
            else:
                err = rehash_invoice(odata1, err, invodate)

            entrydata, docref, err, itotal = update_invoice(odata1, err, tablesetup, invostyle)


            # Create invoice code for order
            odata1.Istat = 1
            odata1.InvoTotal = d2s(itotal)
            odata1.BalDue = d2s(itotal)
            odata1.Payments = '0.00'

            db.session.commit()

            #print('entrydata=', entrydata)
            holdvec[4] = emaildata_update()
            #print('emaildata is:', holdvec[4])

        else:
            invodate = today
            if isinstance(invodate, str):
                invodate = datetime.datetime.strptime(invodate, '%Y-%m-%d')
            holdvec[1] = invodate

            err = initialize_invoice(odata1, err)
            entrydata, docref, err, itotal = update_invoice(odata1, err, tablesetup, invostyle)

            holdvec[4] = etemplate_truck('invoice', odata1)
            #print('emaildata is:', holdvec[4])

        odata1.Invoice = os.path.basename(docref)
        db.session.commit()
        #print('docref=',docref)
        viewport[0] = 'split panel left'
        viewport[1] = 'email setup'
        viewport[2] = 'show_doc_left'
        viewport[3] = '/' + tpath('invoice',odata1.Invoice)
        #print('viewport=', viewport)

        err.append(f'Viewing {docref}')
        err.append('Hit Finished to End Viewing and Return to Table View')
        holdvec[2] = Services.query.order_by(Services.Service).all()

        loginvo = request.values.get('logInvo')
        if loginvo is not None:
            odat = eval(nextquery)
            err = loginvo_m(odat, 2)
            if 'Error' not in err:
                odat.Istat = 2
                db.session.commit()
                completed = True
        logemail = request.values.get('emailInvo')
        if logemail is not None:
            odat = eval(nextquery)
            err = loginvo_m(odat, 2)
            docref = odat.Invoice
            err = invoice_mimemail(docref, err, 'vInvoice', sids)
            if 'Error' not in err:
                odat.Istat = 3
                db.session.commit()
                completed = True

    return holdvec, entrydata, err, viewport, completed

def find_zip_line(address):
    address = address.strip()
    address = address.replace('\r','')
    #print(f'*****************The address is: {address}')
    alines = address.split('\n')
    alen = len(alines)
    #print(f'The address lines are: {alines}')
    pline = re.search(r'.*(\d{5}(\-\d{4})?)$', address)
    #print(f'pline is {pline}')
    if pline:
        #print(f'Retrning the line with postal code: {pline[0]}')
        return pline[0]
    else:
        #print(f'Did not find zip, returning: {alines[alen-1]}')
        return alines[alen-1]


def set_desc(odat):
    jo = odat.Jo
    haultype = odat.HaulType
    delivery = find_zip_line(odat.Dropblock1)
    returnto = find_zip_line(odat.Dropblock2)
    #print(f'found {delivery} {returnto}')
    desc = ''
    #desc = f'{haultype} {delivery} to {returnto}'
    idata = Invoices.query.filter(Invoices.Jo == jo).all()
    for idat in idata:
        desc = f'{desc}{idat.Service}={idat.Amount}, '
    desc = desc[:-1]
    desc = f'{desc}\n'

    if odat.Shipper == 'Global Business Link':
        bk1 = odat.Booking
        bk2 = odat.BOL
        order = odat.Order
        if 'outside' in order.lower() or 'george' in order.lower():
            addon = order
        else:
            addon = ''
        if hasinput(bk2):
            if bk1 != bk2:
                desc = f'{desc} Pulled under booking {bk1} {addon}'
            else:
                desc = f'{desc} In-Out booking match. {addon}'
        else:
            # Have to double check the interchange tables
            idata = Interchange.query.filter(Interchange.Jo == odat.Jo).all()
            if len(idata) == 2:
                idat1 = idata[0]
                idat2 = idata[1]
                if idat1.Release == idat2.Release:
                    desc = f'{desc} In-Out booking match. {addon}'
                else:
                    if 'In' in idat1.Type:
                        bkin = idat1.Release
                        bkout = idat2.Release
                    else:
                        bkin = idat2.Release
                        bkout = idat1.Release
                    desc = f'{desc} Pulled under booking {bkout} {addon}'
                    odat.BOL = bkin
                    odat.Booking = bkout
                    db.session.commit()
    return desc


def same_company_all(sids, table):
    nextquery = f"{table}.query.get({sids[0]})"
    odat = eval(nextquery)
    shippertest = getattr(odat, 'Shipper')
    for sid in sids:
        nextquery = f"{table}.query.get({sid})"
        odat = eval(nextquery)
        shipper = getattr(odat, 'Shipper')
        if shipper != shippertest: return False
    return True

def make_default_invoice(odat, tablesetup):
    sid = odat.id
    jo = odat.Jo
    pid = odat.Bid

    amt = odat.Amount
    input = Invoices(Jo=jo,SubJo=None,Pid=pid,Service='Line Haul',Description='Drayage to Seagirt',Ea=f'{amt}',Qty=1.00,Amount=f'{amt}',Total=f'{amt}',Date=today,Original=None,Status='New')
    db.session.add(input)
    odat.InvoTotal = amt
    db.session.commit()

    odat = Orders.query.get(sid)
    ldata = Invoices.query.filter(Invoices.Jo == jo).order_by(Invoices.Ea.desc()).all()
    pdata1 = People.query.filter(People.id == odat.Bid).first()
    cache = odat.Icache

    docref = make_invo_doc(odat, ldata, pdata1, cache, today, 0, tablesetup, 'Dray Export')
    docref = os.path.basename(docref)
    odat.Invoice= docref
    odat.Istat = 1

    odat.BalDue = d2s('$370.00')
    odat.Payments = '0.00'

    for ldat in ldata:
        ldat.Original = docref
    db.session.commit()
    odat = Orders.query.get(sid)
    return odat




def invoice_for_all(sids, table, err, tablesetup):
    for sid in sids:
        nextquery = f"{table}.query.get({sid})"
        odat = eval(nextquery)
        inv = getattr(odat, 'Invoice')
        if not hasinput(inv):
            #If no invoice create the default invoice
            odat = make_default_invoice(odat, tablesetup)
            inv = getattr(odat, 'Invoice')
        if not hasinput(inv):
            err.append(f'Order JO {odat.Jo} has no invoice')
            return False, err
    return True, err

def get_all_sids(sids):
    #If this summary already exists we need to capture all the original sid:
    testsid = sids[0]
    odat = Orders.query.get(testsid)
    jo = odat.Jo
    sdat = SumInv.query.filter(SumInv.Jo == jo).first()
    if sdat is not None:
        #This means we have already created a summary and want to include all its parts:
        testsi = sdat.Si
        odata = Orders.query.filter(Orders.Label == testsi).all()
        sids = []
        for odat in odata:
            sids.append(odat.id)
    return sids

def convert_sids(sid):
    sdat = SumInv.query.get(sid)
    testsi = sdat.Si
    odata = Orders.query.filter(Orders.Label == testsi).all()
    sids = []
    for odat in odata:
        sids.append(odat.id)
    return sids


def MakeSummary_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sids):

    err = [f"Running Summary task with task_iter {task_iter} using {tablesetup['table']}"]
    #print(f'Executing over {sids} selections')
    entrydata, holdvec, viewport = [], [0]*30, ['0'] * 6

    headers = {
                'Top Blocks' : ['Bill To', 'Pickup and Return for Dray Import', 'Deliver To'],
                'Middle Blocks' : ['Order #', 'BOL #', 'Container #', 'Job Start', 'Job Finished'],
                'Middle Items' : ['Order', 'Booking', 'Container', 'Date', 'Date2'],
                'Lower Blocks' : ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
               }
    invostyle = 'Invoice'
    holdvec[4] = invostyle
    returnhit = request.values.get('Finished')
    cancelhit = request.values.get('Cancel')
    table = tablesetup['table']
    if table == 'SumInv':
        sids = convert_sids(sids[0])
        table = 'Orders'

    testchecks = same_company_all(sids, table)
    #print(f'testchecks={testchecks}')
    testinv, err = invoice_for_all(sids, table, err, tablesetup)

    if testchecks is False:
        completed = True
        err.append('All selection must have same biller for this task')
    elif testinv is False:
        completed = True
    elif returnhit is not None: completed = True
    elif cancelhit is not None:
        sinow = request.values.get('sinow')
        SumInv.query.filter(SumInv.Si == sinow).delete()
        db.session.commit()
        completed = True

    else:
        completed = False
        sireform = request.values.get('sireform')
        siremove = request.values.get('siremove')
        siupdate = request.values.get('siupdate')
        siadd = request.values.get('siadd')
        sinow = request.values.get('sinow')
        siremake = request.values.get('siremake')
        jovec = []
        datevec = []
        cache_start = 0
        invodate = datetime.datetime.today()

        sids = get_all_sids(sids)

        if sireform is not None:
            #Kill all the invoices on the summary
            sdat = SumInv.query.filter( (SumInv.Si == sinow) & (SumInv.Status == 1) ).first()
            if sdat is not None:
                #Even if start over the SI number will be same so dont want to restart the cache
                cache_start = sdat.Cache
                #print(f'Deleting {sinow} from database')
                SumInv.query.filter(SumInv.Si == sinow).delete()
                db.session.commit()

        if siremove is not None:
            if sinow is not None:
                slead = SumInv.query.filter( (SumInv.Si == sinow) & (SumInv.Status == 1) ).first()
                sdata = SumInv.query.filter(SumInv.Si == sinow).all()
                if sdata is not None and slead is not None:
                    cache = slead.Cache
                    for sdat in sdata:
                        sikill = sdat.id
                        jo = sdat.Jo
                        ck = request.values.get(f'box{sdat.id}')
                        #print(f'for sdat with id {sdat.id} ck is {ck}')
                        if ck == 'on':
                            #Reset the order data
                            odat = Orders.query.filter(Orders.Jo == jo).first()
                            if odat is not None:
                                oid = odat.id
                                odat.Label = 'None'
                                odat.Istat = 2
                            SumInv.query.filter(SumInv.id == sikill).delete()
                            #print(f'{sids} {oid}')
                            sids.remove(oid)
                            #print(f'new sids is: {sids}')
                        else:
                            sdat.Cache = cache
                    db.session.commit()
                #Check to see if all have been deleted, then must return to tables and task complete
                #Also must create a new lead element
                sdata = SumInv.query.filter(SumInv.Si == sinow).all()
                slead = SumInv.query.filter((SumInv.Si == sinow) & (SumInv.Status == 1)).first()
                #print(f'sdata is {sdata}')
                if sdata == []:
                    completed = True
                else:
                    if slead is None:
                        snew = sdata[0]
                        snew.Status = 1
                        db.session.commit()

        if siremake is not None:
            sdata = SumInv.query.filter(SumInv.Si == sinow).all()
            thetotal = 0.00
            bamt = request.values.get('baseamt')
            chamt = request.values.get('chasamt')
            try: fbamt = float(bamt)
            except: fbamt = 0.00
            try: fchamt = float(chamt)
            except: fchamt = 0.00
            for sdat in sdata:
                this_amt = d2s(fbamt+fchamt)
                sdat.Description = f'Line Haul={d2s(bamt)}, Chassis={d2s(chamt)}'
                famt = float(this_amt)
                thetotal += famt
                sdat.Amount = this_amt
                odat = Orders.query.filter(Orders.Jo == sdat.Jo).first()
                odat.InvoTotal = this_amt
                idata = Invoices.query.filter(Invoices.Jo == sdat.Jo).all()
                if idata != []:
                    oldrest = 0.00
                    for idat in idata:
                        idat.Total = nodollar(famt)
                        serv = idat.Service
                        if serv != 'Line Haul': oldrest = oldrest + float(idat.Amount)

                    newlineamt = famt - oldrest
                    for idat in idata:
                        serv = idat.Service
                        if serv == 'Line Haul':
                            idat.Ea = nodollar(newlineamt)
                            idat.Qty = 1.00
                            idat.Amount = nodollar(newlineamt)
                odat.Amount = d2s(newlineamt)
                odat.InvoDate = today
                odat.BalDue = this_amt
                odat.Payments = '0.00'
                db.session.commit()
                err = loginvo_m(odat, 2)

            for sdat in sdata:
                sdat.Total = d2s(thetotal)
                sdat.Baldue = d2s(thetotal)
            db.session.commit()

        if siupdate is not None:
            sdata = SumInv.query.filter(SumInv.Si == sinow).all()
            thetotal = 0.00
            for sdat in sdata:
                this_desc = request.values.get(f'ta{sdat.id}')
                sdat.Description = this_desc
                this_amt = request.values.get(f'aa{sdat.id}')
                old_amt = sdat.Amount
                famt = float(this_amt)
                thetotal += famt
                this_amt = d2s(this_amt)
                sdat.Amount = this_amt
                try:
                    old_amt = float(old_amt)
                except:
                    old_amt = 0.00
                if abs(famt - old_amt) > .005:
                    # If value changes we need to update the other databases...
                    odat = Orders.query.filter(Orders.Jo == sdat.Jo).first()
                    odat.InvoTotal = this_amt
                    idata = Invoices.query.filter(Invoices.Jo == sdat.Jo).all()
                    if idata != []:
                        oldrest = 0.00
                        for idat in idata:
                            idat.Total = nodollar(famt)
                            serv = idat.Service
                            if serv != 'Line Haul': oldrest = oldrest + float(idat.Amount)

                        newlineamt = famt - oldrest
                        for idat in idata:
                            serv = idat.Service
                            if serv == 'Line Haul':
                                idat.Ea = nodollar(newlineamt)
                                idat.Qty = 1.00
                                idat.Amount = nodollar(newlineamt)
                    odat.Amount = d2s(newlineamt)
                    odat.InvoDate = today
                    odat.BalDue = this_amt
                    odat.Payments = '0.00'
                    db.session.commit()
                    err = loginvo_m(odat, 2)

                #Update the descriptions if price changes
                if abs(famt - float(old_amt)) > .005:
                    desc = set_desc(odat)
                    sdat.Description = desc

            for sdat in sdata:
                sdat.Total = d2s(thetotal)
            db.session.commit()


        if siadd is not None:
            slead = SumInv.query.filter((SumInv.Si == sinow) & (SumInv.Status > 0)).first()
            odat = Orders.query.filter(Orders.Jo == slead.Jo).first()
            odata = Orders.query.filter((Orders.Shipper == odat.Shipper) & (Orders.Istat == 2)).all()
            for odat in odata:
                ck = request.values.get(f'obox{odat.id}')
                if ck == 'on':
                    sids.append(odat.id)



        if completed == False:

            #print(f'Looping over these sids: {sids}')
            #loop over each job and rebuild
            #get a new SI if one does not exist already
            total = 0.00
            for ix, sid in enumerate(sids):
                nextquery = f"{table}.query.get({sid})"
                odat = eval(nextquery)
                jo = getattr(odat, 'Jo')
                stat = 0
                sdat = SumInv.query.filter(SumInv.Jo == jo).first()
                try:
                    amt = float(odat.InvoTotal)
                except:
                    amt = 0.00
                total = total + amt
                #Get or create the current SINumber:
                if ix == 0:
                    stat = 1
                    if sdat is None:
                        if sinow is None:
                            sdate = today.strftime('%Y-%m-%d')
                            jbcode = 'SI'
                            si = newjo(jbcode, sdate)
                            #si = f'SI{jo[2:]}'
                        else: si = sinow
                    else:
                        si = sdat.Si

                if sdat is None:
                    # Put each line into the summary invoice database
                    desc = set_desc(odat)
                    docref = f'{si}.pdf'
                    amt = d2s(odat.InvoTotal)
                    #print(f'amt input to suminv for jo {jo} is {amt} for {odat.InvoTotal}')
                    input = SumInv(Si = si, Jo=jo, Begin=odat.Date, End=odat.Date2, Release=odat.BOL, Container=odat.Container, Type=odat.Type, Description=desc, Amount=amt, Total='0.00', Source=docref, Status=stat, Cache=cache_start, Pid = odat.Bid, Billto = odat.Shipper, Date = invodate, Paid='0.00', Baldue='0.00', Pstat=0)
                    db.session.add(input)
                    odat.Label = si
                    odat.Istat = 6
                    db.session.commit()
            sdata = SumInv.query.filter(SumInv.Si == si).all()
            for sdat in sdata:
                sdat.Total = d2s(total)
                sdat.Baldue = d2s(total)
            db.session.commit()
            sdata = SumInv.query.filter(SumInv.Si == si).all()
            sdat = SumInv.query.filter( (SumInv.Si == si) & (SumInv.Status >= 1) ).first()
            #print(f'{sdata} sdat.id is {sdat}')
            pdat = People.query.filter(People.id == sdat.Pid).first()
            cache = sdat.Cache
            docref, newbase = make_summary_doc(sdata, sdat, pdat, cache, invodate, 0, tablesetup, invostyle)
            cache = cache + 1
            sdat.Cache = cache
            sdat.Source = newbase
            db.session.commit()

            sendemail = request.values.get('siemail')
            if sendemail is not None:
                err = invoice_mimemail(newbase, err, 'vPackage', sids)
                if 'Error' not in err:
                    sdat.Status = 2
                    for sid in sids:
                        odat = Orders.query.get(sid)
                        odat.Istat = 7
                    db.session.commit()
                    completed = True

            #send over other invoices that could be added and are available for this shipper
            odata = Orders.query.filter( (Orders.Shipper == odat.Shipper) & (Orders.Istat == 2) ).all()
            holdvec[5] = odata

            holdvec[4] = etemplate_suminv('suminv', sdat)
            holdvec[0] = jovec
            holdvec[1] = datevec
            holdvec[2] = sdata
            #print('docref=',docref)
            viewport[0] = 'split panel left'
            viewport[1] = 'email setup'
            viewport[2] = 'show_doc_left'
            viewport[3] = '/' + tpath('package',newbase)
            #print('viewport=', viewport)

            err.append(f'Viewing {docref}')
            err.append('Hit Finished to End Viewing and Return to Table View')

    return holdvec, entrydata, err, viewport, completed


def income_record(jopaylist, err):
    success = False
    for jopay in jopaylist:
        #print(jopay)
        jo, amtpaid, paidon, payref, paymethod, depoacct = [jopay[i] for i in range(6)]
        #print(jo, amtpaid, paidon, payref, paymethod, depoacct)
        adderr = gledger_write(['income', amtpaid, paidon,  payref, paymethod], jo, depoacct, 0 )
        if adderr == []:
            odat = Orders.query.filter(Orders.Jo == jo).first()
            if odat is not None:
                #Successful add to ledger so now can update the database for the amount paid
                odat.PaidDate = paidon
                odat.PaidAmt = d2s(amtpaid)
                odat.PayRef = payref
                odat.PayMeth = paymethod
                odat.PayAcct = depoacct
                paysofar = odat.Payments
                if paysofar is not None:
                    paysofar = float(paysofar)
                else:
                    paysofar = 0.00
                try:
                    famt = float(odat.InvoTotal)
                except:
                    #print(f'Cannot process InvoTotal for Jo {jo}')
                    famt = 0.00
                    success = False
                totpaid = paysofar + float(amtpaid)
                baldue = famt - totpaid
                odat.BalDue = d2s(baldue)
                odat.Payments = d2s(totpaid)
                if baldue > .01:
                    odat.Istat = 4
                else:
                    istat = odat.Istat
                    hstat = odat.Hstat
                    if istat < 5:
                        odat.Istat = 5
                        if hstat == 2 or hstat == 3: odat.Hstat = 5
                    if istat == 6 or istat == 7:
                        odat.Istat = 8
                        if hstat == 2 or hstat == 3: odat.Hstat = 8
                        jo = odat.Jo
                        sumdat = SumInv.query.filter(SumInv.Jo == jo).first()
                        if sumdat is not None:
                            sumdat.Paid = d2s(totpaid)
                            sumdat.Baldue = d2s(baldue)
                            sumdat.Pstat = 1

                db.session.commit()

                idata = Invoices.query.filter(Invoices.Jo == jo).all()
                if idata != []:
                    success = True
                    for idat in idata:
                        idat.Status = 'P'
                    db.session.commit()
                else:
                    err.append(f'Invoice data not found for {jo}')
            else:
                err.append(f'Order data not found for {jo}')
        else:
            for addline in adderr: err.append(addline)
    return err, success
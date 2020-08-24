from webapp import db
from webapp.models import Orders, Invoices, People, Services, Drops
from flask import render_template, flash, redirect, url_for, session, logging, request
from webapp.CCC_system_setup import myoslist, addpath, tpath, companydata, scac
from webapp.InterchangeFuncs import Order_Container_Update, Match_Trucking_Now, Match_Ticket
from webapp.email_appl import etemplate_truck
from webapp.class8_dicts import Trucking_genre, Orders_setup, Interchange_setup, Customers_setup, Services_setup
from webapp.class8_tasks_manifest import makemanifest
from webapp.class8_tasks_invoice import make_invo_doc

from sqlalchemy import inspect
import datetime
import os
import subprocess
#from func_cal import calmodalupdate
import json
import numbers

#Python functions that require database access
from webapp.class8_utils import *
from webapp.utils import *
from webapp.viewfuncs import newjo
import uuid


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
            descript = 'Order ' + myo.Order + ' Line Haul ' + myo.Company + ' to ' + myo.Company2
            amount = float(myo.Amount)
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
        print('servid=',servid)
        if servid > 0:
            mys = Services.query.get(servid)
            print('service is',mys.Service)
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
                    descript = 'Days of Chassis'
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
        pdata2 = Drops.query.filter(Drops.id == myo.Lid).first()
        pdata3 = Drops.query.filter(Drops.id == myo.Did).first()
        cache = myo.Icache

        docref = make_invo_doc(myo, ldata, pdata1, pdata2, pdata3, cache, invodate, 0, tablesetup, invostyle)

        for ldatl in ldata:
            ldatl.Pid = pdata1.id
            ldatl.Original = os.path.basename(docref)
            db.session.commit()

        myo.Invoice = os.path.basename(docref)
        myo.Icache = cache + 1
        myo.InvoTotal = d2s(total)
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
    # set the invoice style:
    invostyle = request.values.get('invoicestyle')
    if invostyle is None:
        invostyle = 'Drayage Import'
    headers = tablesetup['invoicetypes'][invostyle]
    print('the headers are:', headers)
    holdvec[4] = invostyle

    returnhit = request.values.get('Finished')
    if returnhit is not None: completed = True
    else:

        completed = False
        table = tablesetup['table']
        nextquery = f"{table}.query.get({sid})"
        odata1 = eval(nextquery)

        #Need to jump over to invoice database
        jo = getattr(odata1, 'Jo')
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

            db.session.commit()

            print('entrydata=', entrydata)

        else:
            invodate = today
            if isinstance(invodate, str):
                invodate = datetime.datetime.strptime(invodate, '%Y-%m-%d')
            holdvec[1] = invodate

            err = initialize_invoice(odata1, err)
            entrydata, docref, err, itotal = update_invoice(odata1, err, tablesetup, invostyle)

            #emaildata = etemplate_truck('invoice', 0, modata)

        odata1.Invoice = os.path.basename(docref)
        db.session.commit()
        print('docref=',docref)
        viewport[0] = 'show_doc_left'
        viewport[2] = '/' + tpath('invoice',odata1.Invoice)
        print('viewport=', viewport)

        err.append(f'Viewing {docref}')
        err.append('Hit Finished to End Viewing and Return to Table View')
        holdvec[2] = Services.query.all()

    return holdvec, entrydata, err, viewport, completed










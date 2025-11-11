from webapp import db
from webapp.models import Vehicles, Orders, Gledger, Invoices, JO, Income, Accounts, LastMessage, People, \
                          Interchange, Drivers, ChalkBoard, Services, Drops, StreetTurns,\
                          SumInv, Autos, Bills, Divisions, Trucklog, Pins, Newjobs, Ships, Imports, Exports, PortClosed, PaymentsRec, Terminals
from flask import render_template, flash, redirect, url_for, session, logging, request
from webapp.CCC_system_setup import myoslist, addpath, tpath, companydata, scac, apikeys
from webapp.class8_utils_email import etemplate_truck, info_mimemail
from webapp.class8_dicts import *
#Trucking_genre, Auto_genre, Orders_setup, Interchange_setup, Customers_setup, Services_setup, Summaries_setup, Autos_setup, Billing_genre, Bills_setup
from webapp.class8_utils_manifest import makemanifest
from webapp.class8_tasks_money import MakeInvoice_task, MakeSummary_task, income_record
from webapp.class8_utils_package import makepackage, getdocs, blendticks, combine_ticks
from webapp.class8_utils_email import emaildata_update
from webapp.class8_utils_invoice import make_invo_doc, make_summary_doc, addpayment, writechecks
from webapp.class8_tasks_gledger import gledger_write, gledger_multi_job
from webapp.InterchangeFuncs import Order_Container_Update, Gate_Update
from webapp.class8_tasks_money import get_all_sids
from webapp.class8_tasks_scripts import Container_Update_task, Street_Turn_task, Unpulled_Containers_task, Exports_Pulled_task, Exports_Returned_task, Exports_Bk_Diff_task
import os
import ntpath
from requests import get
API_KEY_GEO = apikeys['gkey']
from sqlalchemy import inspect
import datetime
from datetime import timedelta
import subprocess
#from func_cal import calmodalupdate
import json
import numbers

#Python functions that require database access
from webapp.class8_utils import *
from webapp.utils import *
from webapp.viewfuncs import newjo
import uuid

def Add_New_Drop(dropblock):
    droplist=dropblock.splitlines()
    avec=['']*5
    for j,drop in enumerate(droplist):
        avec[j]=stripper(drop)
    entity=avec[0]
    addr1=avec[1]
    edat=Drops.query.filter((Drops.Entity==entity) & (Drops.Addr1==addr1)).first()
    if edat is None:
        input = Drops(Entity=entity,Addr1=addr1,Addr2=avec[2],Phone=avec[3],Email=avec[4])
        db.session.add(input)
        db.session.commit()
        edat = Drops.query.filter((Drops.Entity==entity) & (Drops.Addr1==addr1)).first()
    return edat

def Review_Drop(dropblock):
    droplist = dropblock.splitlines()
    avec=['']*5
    for j,drop in enumerate(droplist):
        avec[j]=stripper(drop)
    entity=avec[0]
    addr1=avec[1]
    dropdat=Drops.query.filter((Drops.Entity==entity) & (Drops.Addr1==addr1)).first()
    if dropdat is not None:
        # This entity already exists
        return dropblock
    else:
        input = Drops(Entity=entity,Addr1=addr1,Addr2=avec[2],Phone=avec[3],Email=avec[4])
        db.session.add(input)
        db.session.commit()
        return dropblock

def due_back(date):
    dw = date.weekday()
    da = 3
    if dw > 1: da = 5
    return date + timedelta(days=da)

def short_date(date):
    if date is not None:  return date.strftime("%m-%d")
    else: return 'XX-XX'




def Order_Addresses_Update(sid):
    odat = Orders.query.get(sid)
    if odat is not None:
        pdat = People.query.filter(People.Company == odat.Shipper).first()
        if pdat is not None:
            odat.Bid = pdat.id
        ldat = Drops.query.filter(Drops.Entity == odat.Company2).first()
        if ldat is None: ldat = Add_New_Drop(odat.Dropblock2)
        odat.Lid = ldat.id

        ddat = Drops.query.filter(Drops.Entity == odat.Company).first()
        if ddat is None: ddat = Add_New_Drop(odat.Dropblock1)
        odat.Did = ddat.id
        # Also set the gate date estimates based on the delivery date
        d3 = odat.Date3
        #Dont mess with gate dates once pulls start
        idat = Interchange.query.filter(Interchange.Jo == odat.Jo).first()
        if idat is None:
            d2 = d3 + timedelta(1)
            d1 = d3 - timedelta(1)
            if odat.Date is None: odat.Date = d1
            if odat.Date2 is None: odat.Date2 = d2
        db.session.commit()


def address_resolver(json):
    final = {}
    if json['results']:
        data = json['results'][0]
        for item in data['address_components']:
            #print(f'address resolver item {item}')
            for category in item['types']:
                data[category] = {}
                data[category] = item['long_name']
        final['street'] = data.get("route", None)
        final['state'] = data.get("administrative_area_level_1", None)
        final['city'] = data.get("locality", None)
        final['county'] = data.get("administrative_area_level_2", None)
        final['country'] = data.get("country", None)
        final['postal_code'] = data.get("postal_code", None)
        final['neighborhood'] = data.get("neighborhood",None)
        final['sublocality'] = data.get("sublocality", None)
        final['housenumber'] = data.get("housenumber", None)
        final['postal_town'] = data.get("postal_town", None)
        final['subpremise'] = data.get("subpremise", None)
        final['latitude'] = data.get("geometry", {}).get("location", {}).get("lat", None)
        final['longitude'] = data.get("geometry", {}).get("location", {}).get("lng", None)
        final['location_type'] = data.get("geometry", {}).get("location_type", None)
        final['postal_code_suffix'] = data.get("postal_code_suffix", None)
        final['street_number'] = data.get('street_number', None)
    return final


def get_drop(loadname):
    #print(f'In get_drop The LOADNAME is:{loadname}')
    dropdat = Drops.query.filter(Drops.Entity == loadname).first()
    if dropdat is not None:
        #print('dropdat',dropdat.Entity, dropdat.Addr1, dropdat.Addr2, dropdat.Phone, dropdat.Email)
        dline = f'{dropdat.Entity}\n{dropdat.Addr1}\n{dropdat.Addr2}\n{dropdat.Phone}\n{dropdat.Email}'
        dline = dline.replace('None','')
        return dline
    else:
        #print(f'the length of loadname is...{len(loadname)}')
        if len(loadname) == 3:
            #dropdat = Drops.query.filter(Drops.Entity.contains(loadname)).first()
            dropdat = Drops.query.filter(Drops.Entity.like(f'{loadname}%')).order_by(Drops.id.desc()).first()
            if dropdat is not None:
                #print('dropdat', dropdat.Entity, dropdat.Addr1, dropdat.Addr2, dropdat.Phone, dropdat.Email)
                dline = f'{dropdat.Entity}\n{dropdat.Addr1}\n{dropdat.Addr2}\n{dropdat.Phone}\n{dropdat.Email}'
                dline = dline.replace('None', '')
                return dline

        return ''

def get_terminal(loadname):
    dat = Terminals.query.filter(Terminals.Name == loadname).first()
    if dat is not None:
        dline = f'{dat.Address}'
        return dline
    else:
        return ''


def get_checked(thistable, data1id):
    numchecked = 0
    avec = []
    for id in data1id:
        name = thistable+str(id)
        ischeck = request.values.get(name)
        #print(name,ischeck)
        if ischeck == 'on':
            numchecked = numchecked + 1
            avec.append(int(id))

    #print(numchecked, avec)
    return numchecked, avec

def get_default_list(item, col):
    if item == 'emaildata1' or item == 'emaildata2' or item == 'emaildata3':
        emaildata = []
        #print(f'The shipper is {col}')
        sdata = People.query.filter(People.Company == col).all()
        for sdat in sdata:
            if sdat is not None:
                if hasinput(sdat.Email):
                    if sdat.Email not in emaildata: emaildata.append(sdat.Email)
                if hasinput(sdat.Associate1):
                    if sdat.Associate1 not in emaildata: emaildata.append(sdat.Associate1)
                if hasinput(sdat.Associate2):
                    if sdat.Associate2 not in emaildata: emaildata.append(sdat.Associate2)

        return emaildata

def get_Orders_keydata(keydata, checked_data):
    sid = None
    em1, em2, em3 = None, None, None
    nc = sum(cks[1] for cks in checked_data)
    tids = [cks[2] for cks in checked_data if cks[2] != []]
    tabs = [cks[0] for cks in checked_data if cks[1] != 0]
    #print('nc=', nc)
    #print(tids)
    #print(tabs)
    if nc == 1:
        thistable = tabs[0]
        sid = tids[0][0]
    if sid is not None:
        odat = Orders.query.get(sid)
        if odat is not None:
            shipper = odat.Shipper
            em1 = odat.Emailjp
            em2 = odat.Emailoa
            em3 = odat.Emailap
            kdata = Orders.query.filter(Orders.Shipper == shipper).all()
            pdat = People.query.filter(People.Company == shipper).first()
        else:
            kdata = []
            pdat = None
        #print(f'The sid is {sid}')
        if hasvalue(em1):
            keydata['emaildata1'] = []
        elif keydata['emaildata1'] == []:
            elist = []
            for kdat in kdata:
                new = kdat.Emailjp
                if hasinput(new):
                    if new not in elist: elist.append(new)

            #If no history for this customer it will still be blank to use the base values form cusotmer
            if elist == [] and pdat is not None:
                keydata['emaildata1'] = [pdat.Email]
            else:
                keydata['emaildata1'] = elist

        if hasvalue(em2):
            keydata['emaildata2'] = []
        elif keydata['emaildata2'] == []:
            elist = []
            for kdat in kdata:
                new = kdat.Emailoa
                if hasinput(new):
                    if new not in elist: elist.append(new)
            # If no history for this customer it will still be blank to use the base values form cusotmer
            if elist == [] and pdat is not None:
                keydata['emaildata2'] = [pdat.Associate1]
            else:
                keydata['emaildata2'] = elist


        if hasvalue(em3):
            keydata['emaildata3'] = []
        elif keydata['emaildata3'] == []:
            elist = []
            for kdat in kdata:
                new = kdat.Emailap
                if hasinput(new):
                    if new not in elist: elist.append(new)

            #If no history for this customer it will still be blank to use the base values form cusotmer
            if elist == []:
                if pdat is not None: keydata['emaildata3'] = [pdat.Associate2]
            else:
                keydata['emaildata3'] = elist

    else:
        keydata['emaildata1'] == []
        keydata['emaildata2'] == []
        keydata['emaildata3'] == []


    return keydata

def populate(tables_on,tabletitle,tfilters,jscripts):
    #print(int(filter(check.isdigit, check)))
    checked_data = []
    table_data = []
    labpassvec = []
    keydata = {}
    jscripts = []
    num_tables_on = len(tables_on)

    for jx, tableget in enumerate(tables_on):
        tabletitle.append(tableget)
        table_setup = eval(f'{tableget}_setup')
        #print(table_setup)
        db_data, labpass = get_dbdata(table_setup, tfilters)
        table_data.append(db_data)
        labpassvec.append(labpass)

        #Section to determine what items have been checked
        numchecked, avec = get_checked(tableget, db_data[1])
        #print('returning checks numc, avec=',numchecked, avec)
        checked_data.append([tableget,numchecked,avec])
        #print('after',checked_data)

        boxchecks = db_data[6]
        boxlist = db_data[7]
        #print('boxing:',tableget,boxchecks,boxlist)
        if tableget == 'Orders':
            if 'Job' in boxlist:
                if 'Docs' in boxlist: use_table = 'dtTrucking'
                else: use_table = 'dtTrucking9'
            else:
                use_table = 'dtTrucking1'
            if num_tables_on > 1 or tfilters['Viewer'] == 'Top-Bot':
                use_table = use_table + '_200'
            jscripts.append(use_table)

        elif tableget == 'Interchange':
            if 'Ticket' in boxlist:
                use_table ='dtInterchange'
            else: use_table = 'dtInterchange2'

            if num_tables_on > 1:
                use_table = use_table + '_200'
            jscripts.append(use_table)

        else:
            jscripts.append(eval(f"{tableget}_setup['jscript']"))


        # For tables that are on get side data required for tasks:
        side_data = eval(f"{tableget}_setup['side data']")
        defaults = eval(f"{tableget}_setup['default values']")
        #print('class8_tasks.py 86 Tablemaker() For tables on get this side data:',side_data)
        #keydata = {}  this was commented out because with mult tables it was over weitten
        for side in side_data:
            #print(f'side is: {side}')
            for key, values in side.items():
                #print('')
                #print('****************************')
                #print(f'key:{key}, values:{values}')
                ktable = values[0]
                pairs = values[1]
                keyon = values[2]
                for ix, pair in enumerate(pairs):
                    col = pair[0]
                    select_value = pair[1]
                    #print(f'col,select_value is: {col} {select_value}')
                    if ix == 0:
                        if isinstance(select_value, str):
                            # Output of the get_ could be string or integer, but have to start with string to test get_
                            if 'get_' in select_value:
                                default_val = defaults[f'{select_value}']
                                find = select_value.replace('get_', '')
                                select_value = request.values.get(find)
                                if select_value is None:
                                    #print(f'On first iteration have no data to read so use the sid')
                                    select_value = default_val

                        if isinstance(select_value, str):
                            if select_value == 'All':
                                filters = f"{ktable}.query.order_by({ktable}.{keyon}).all()"
                            else:
                                filters = f"{ktable}.query.filter(({ktable}.{col}=='{select_value}')"
                        elif isinstance(select_value, int):
                            filters = f"{ktable}.query.filter(({ktable}.{col}=={select_value})"
                    else:
                        if isinstance(select_value, str):
                            # Output of the get_ could be string or integer, but have to start with string to test get_
                            if 'get_' in select_value:
                                find = select_value.replace('get_', '')
                                select_value = request.values.get(find)
                                if select_value is None: select_value = 'All'
                        if isinstance(select_value, str):
                            filters = filters + f" & ({ktable}.{col}=='{select_value}')"
                        elif isinstance(select_value, int):
                            filters = filters + f" & ({ktable}.{col}=={select_value})"
                    #print(f'for ix:{ix}, col: {col}, select_value:{select_value} the current filters is {filters}')

            if 'all()' not in filters: filters = filters+f').order_by({ktable}.{keyon}).all()'
            dbstats = eval(filters)

            #print(f'filters is {filters}')
            #print(f'dbstats is {dbstats}')

            if dbstats is not None:
                dblist = []
                for dbstat in dbstats:
                    nextvalue = eval(f'dbstat.{keyon}')
                    #print(f'nextvalue:{nextvalue}')
                    if nextvalue is not None:  nextvalue = nextvalue.strip()
                    if nextvalue not in dblist:
                        if hasinput(nextvalue): dblist.append(nextvalue)
                keydata.update({key: dblist})
                #print(f'For the key {key} in keydata[key] is {keydata[key]} and select_value is {select_value}')
                if keydata[key] == []:
                    def_list = get_default_list(key, select_value)
                    #print(def_list)
                    keydata.update({key: def_list})
            #print(f'Final for the key {key} in keydata[key] is {keydata[key]}')
    return tabletitle, table_data, checked_data, jscripts, keydata, labpassvec

def reset_state_soft(task_boxes):
    tboxes={}
    # Default time filter on entry into table is last 60 days:
    #tfilters = {'Date Filter': 'Last 60 Days', 'Pay Filter': None, 'Haul Filter': None, 'Color Filter': 'Haul'}
    jscripts = ['dtTrucking']
    taskon, task_iter, task_focus = None, None, None
    viewport = ['tables'] + ['0'] * 5
    for box in task_boxes:
        for key, value in box.items():
            tboxes[key] = key
    return jscripts, taskon, task_iter, task_focus, tboxes, viewport

def reset_state_hard(task_boxes, genre_tables):
    tboxes={}
    genre_tables_on = ['off'] * len(genre_tables)
    genre_tables_on[0] = 'on'
    tables_on = ['Orders']
    # Default time filter on entry into table is last 60 days:
    tfilters = {'Shipper': None, 'Date Filter': 'Last 60 Days', 'Pay Filter': None, 'Haul Filter': None, 'Color Filter': 'Haul', 'Viewer': '8x4'}
    jscripts = ['dtTrucking']
    taskon, task_iter, task_focus = None, None, None
    viewport = ['tables'] + ['0'] * 5
    for box in task_boxes:
        for key, value in box.items():
            tboxes[key] = key
    return genre_tables_on, tables_on, jscripts, taskon, task_iter, task_focus, tboxes, viewport, tfilters

def run_the_task(genre, taskon, task_focus, tasktype, task_iter, checked_data, err):
    completed = False
    viewport = ['tables'] + ['0'] * 5
    # This rstring runs the task.  Task name is thetask_task and passes parameters: task_iter and focus_setup where focus is the Table data that goes with the task
    # If the task can be run for/with multiple Tables then the focus setup must be hashed wihin the specific task
    #print(f'Taskon:{taskon}, task_focus:{task_focus}, tasktype:{tasktype}, task_iter:{task_iter}')

    if tasktype == 'Table_Selected':
        tablesetup = eval(f'{task_focus}_setup')
        rstring = f"{taskon}_task({task_focus}_setup, task_iter)"
        holdvec, entrydata, err, completed = eval(rstring)

    elif tasktype == 'No_Display':
        holdvec, entrydata, tablesetup = [], [], []
        rstring = f"{taskon}_task(err)"
        completed, err = eval(rstring)

    elif tasktype == 'No_Selection_Plus_Display':
        holdvec, entrydata, tablesetup = [0,0], [], []
        rstring = f"{taskon}_task(err, holdvec, task_iter)"
        completed, err, holdvec = eval(rstring)
        viewport[3] = 'Show Text'
        #print(holdvec[0])
        #print(holdvec[1])

    elif tasktype == 'No_Selection_Plus_Display_Plus_Left_Panel_Change':
        holdvec, entrydata, tablesetup = ['']*30, [], []
        rstring = f"{taskon}_task(err, holdvec, task_iter)"
        completed, err, holdvec = eval(rstring)
        viewport[0] = 'replace panel left'
        viewport[2] = taskon
        viewport[3] = 'Show Text'
        #print(f'taskon is {taskon}')

    elif tasktype == 'Single_Item_Selection':
        holdvec, entrydata = [], []
        # See if only one box is checked and if so what table it is from
        nc = sum(cks[1] for cks in checked_data)
        tids = [cks[2] for cks in checked_data if cks[2] != []]
        tabs = [cks[0] for cks in checked_data if cks[1] != 0]
        #print('nc=', nc)
        #print(tids)
        #print(tabs)
        if nc == 1:
            thistable = tabs[0]
            sid = tids[0][0]
            #print('made it here with this table sid taskiter', thistable, sid, task_iter)
            tablesetup = eval(f'{thistable}_setup')
            rstring = f"{taskon}_task(genre, task_iter, {thistable}_setup, task_focus, checked_data, thistable, sid)"
            #print(f'rstring = {rstring}')
            holdvec, entrydata, err, viewport, completed = eval(rstring)
            #print('returned with:', viewport, completed)
        elif nc > 1:
            err.append('Too many selections made for this task')
            completed = True
            tablesetup = None
        else:
            err.append('Must make a single selection for this task')
            completed = True
            tablesetup = None

    elif tasktype == 'One_Table_Multi_Item_Selection':
        holdvec, entrydata, err = [], [], []
        # See if only one box is checked and if so what table it is from
        nc = sum(cks[1] for cks in checked_data)
        tids = [cks[2] for cks in checked_data if cks[2] != []]
        tabs = [cks[0] for cks in checked_data if cks[1] != 0]
        #print('nc=', nc)
        #print(tids)
        #print(tabs)
        if nc > 0:
            thistable = tabs[0]
            sids = tids[0]
            tablesetup = eval(f'{thistable}_setup')
            rstring = f"{taskon}_task(genre, task_iter, {thistable}_setup, task_focus, checked_data, thistable, sids)"
            holdvec, entrydata, err, viewport, completed = eval(rstring)
        else:
            err.append('Need to select item(s) for task')
            completed = True
            tablesetup = None

    elif tasktype == 'Two_Item_Selection':
        holdvec, entrydata = [], []
        # See if only one box is checked and if so what table it is from
        nc = sum(cks[1] for cks in checked_data)
        tids = [cks[2] for cks in checked_data if cks[2] != []]
        tabs = [cks[0] for cks in checked_data if cks[1] != 0]
        #print('nc=', nc)
        #print(tids)
        #print(tabs)
        if nc == 2:
            thistable1 = tabs[0]
            try:
                thistable2 = tabs[1]
            except:
                thistable2 = thistable1
            avec1 = tids[0]
            sid1 = avec1[0]
            try:
                avec2 = tids[1]
                sid2 = avec2[0]
            except:
                sid2 = avec1[1]

        elif nc > 2:
            err.append('Too many selections made for this task')
            completed = True
            tablesetup = None
        else:
            err.append('Must make exactly two selection for this task')
            completed = True
            tablesetup = None
        if nc == 2:
            tablesetup = eval(f'{thistable1}_setup')
            tablesetup2 = eval(f'{thistable2}_setup')
            rstring = f"{taskon}_task(genre, task_iter, tablesetup, tablesetup2, task_focus, checked_data, sid1, sid2)"
            holdvec, entrydata, err, viewport, completed = eval(rstring)
            #print('returned with:', viewport, completed)

    elif tasktype == 'All_Item_Selection':
        holdvec, entrydata, err = [], [], []
        # See if only one box is checked and if so what table it is from
        nc = sum(cks[1] for cks in checked_data)
        tids = [cks[2] for cks in checked_data if cks[2] != []]
        tabs = [cks[0] for cks in checked_data if cks[1] != 0]
        #print('nc=', nc)
        #print(tids)
        #print(tabs)
        if nc > 0:
            rstring = f"{taskon}_task(genre, task_focus, task_iter, nc, tids, tabs)"
            holdvec, entrydata, err, viewport, completed = eval(rstring)
            completed = True
            tablesetup = None
        else:
            err.append('Need to select item(s) to undo')
            completed = True
            tablesetup = None

    return holdvec, entrydata, err, completed, viewport, tablesetup

def get_address_details(address):
    #print(address)
    address = address.replace('\n',' ').replace('\r', '')
    address = address.replace('#', '')
    address = address.strip()
    address = address.replace(" ","+")
    url = f'https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={API_KEY_GEO}'
    response = get(url)
    data = address_resolver(response.json())
    data['address'] = address
    backupcity = 'None'
    #lat = data['latitude']
    #lon = data['longitude']
    #print(lat,lon)
    return data, backupcity

def get_dispatch(odat):
    ht = odat.HaulType
    hstat = odat.Hstat
    contype = odat.Type
    if hasinput(odat.BOL): booking = odat.BOL
    else: booking = odat.Booking
    newbook = booking.split('-', 1)[0]
    try:
        rel4 = odat.Booking[-4:]
    except:
        rel4 = odat.Booking
    ctext = ''
    if '40' in contype and '9' in contype: ctext = '40HC'
    if '40' in contype and '8' in contype: ctext = '40STD'
    if '20' in contype: ctext = '20'
    if 'R' in contype: ctext = ctext + ' Reefer'
    if 'U' in contype: ctext = ctext + ' OpenTop'
    if '45' in contype and '9' in contype: ctext = '45HC'
    if '45' in contype and '8' in contype: ctext = '45STD'

    address = odat.Dropblock2
    adata, backup = get_address_details(address)
    try:
        city = adata['city']
    except:
        city = backup

    if city == 'Baltimore':
        citiline = odat.Shipper
        citiline = citiline.split()
        city = citiline[0]

    if hstat is None: hstat = -1
    if hstat < 1:
        if 'Export' in ht: return f'Empty Out: *{newbook}* ({ctext} {city})'
        if 'Import' in ht: return f'Load Out: *{rel4}  {odat.Container}* ({ctext} {city})'
    else:
        if 'Export' in ht: return f'Load In: *{newbook}  {odat.Container}* ({ctext} {city})'
        if 'Import' in ht: return f'Empty In: *{odat.Container}* ({ctext} {city})'
    return ''

def addtopins(thisdate, opair):
    driver = None
    inbook = None
    incon = None
    inchas = None
    inpin = '0'
    outbook = None
    outcon = None
    outchas = None
    outpin = '0'
    unit = None
    tag = None
    phone = None
    intext = None
    outtext = None
    for odat in opair:
        if odat is not None:
            ht = odat.HaulType
            hstat = odat.Hstat
            contype = odat.Type
            ochassis = odat.Chassis
            if not hasinput(ochassis): ochassis=f'{scac}007'
            try:
                rel4 = odat.Booking[-4:]
            except:
                rel4 = odat.Booking
            ctext = ''
            if '45' in contype and '9' in contype: ctext = '45HC'
            if '40' in contype and '9' in contype: ctext = '40HC'
            if '40' in contype and '8' in contype: ctext = '40STD'
            if '45' in contype and '8' in contype: ctext = '45STD'
            if '20' in contype: ctext = '20'
            if 'R' in contype: ctext = ctext + ' Reefer'
            if 'U' in contype: ctext = ctext + ' OpenTop'

            address = odat.Dropblock2
            adata, backup = get_address_details(address)
            try:
                city = adata['city']
            except:
                city = backup

            if city == 'Baltimore':
                citiline = odat.Shipper
                citiline = citiline.split()
                city = citiline[0]

            if not hasinput(city):
                citiline = odat.Shipper
                citiline = citiline.split()
                city = citiline[0]

            if hstat is None: hstat = -1
            if hstat < 1:
                if 'Export' in ht:
                    outbook = odat.Booking
                    outbook = outbook.split('-',1)[0]
                    outtext = f'Empty Out: *{outbook}* ({ctext} {city})'
                    outchas = ochassis
                if 'Import' in ht:
                    outbook = rel4
                    outcon = odat.Container
                    outtext =  f'Load Out: *{rel4}  {odat.Container}* ({ctext} {city})'
                    outchas = ochassis
            else:
                if 'Export' in ht:
                    if hasinput(odat.BOL):
                        inbook = odat.BOL
                    else:
                        inbook = odat.Booking
                    inbook = inbook.split('-', 1)[0]
                    incon = odat.Container
                    inchas = ochassis
                    intext = f'Load In: *{inbook}  {odat.Container}* ({ctext} {city})'
                if 'Import' in ht:
                    incon = odat.Container
                    inchas = ochassis
                    intext = f'Empty In: *{odat.Container}* ({ctext} {city})'


    input = Pins(Date=thisdate, Driver=driver, InBook=inbook, InCon=incon, InChas = inchas, InPin=inpin, OutBook=outbook, OutCon=outcon, OutChas=outchas, OutPin=outpin, Unit=unit, Tag=tag, Phone=phone, Timeslot=0, Intext=intext, Outtext=outtext, Notes=None)
    db.session.add(input)
    db.session.commit()

    return

def get_custlist(table, tfilters):
    dtest = tfilters['Date Filter']
    today = datetime.date.today()
    query_adds = []
    if dtest is not None and dtest != 'Show All':
        daysback = None
        fromdate = None
        todate = None
        if '30' in dtest: daysback = 30
        elif '45' in dtest: daysback = 45
        elif '90' in dtest: daysback = 90
        elif '180' in dtest: daysback = 180
        elif '360' in dtest: daysback = 360
        elif dtest == 'Last Year':
            thisyear = today.year
            lastyear = thisyear - 1
            fromdate = datetime.date(lastyear, 1, 1)
            todate = datetime.date(lastyear, 12, 31)
        elif dtest == 'This Year':
            thisyear = today.year
            fromdate = datetime.date(thisyear, 1, 1)
        else:
            daysback = 45
        if daysback is not None: fromdate = today - datetime.timedelta(days=daysback)
        if fromdate is not None: query_adds.append(f'{table}.Date >= fromdate')
        if todate is not None: query_adds.append(f'{table}.Date <= todate')

    if query_adds == []:
        table_query = f'{table}.query.all()'
    elif len(query_adds) == 1:
        table_query = f'{table}.query.filter({query_adds[0]}).all()'
    elif len(query_adds) == 2:
        table_query = f'{table}.query.filter(({query_adds[0]}) & ({query_adds[1]})).all()'
    elif len(query_adds) == 3:
        table_query = f'{table}.query.filter(({query_adds[0]}) & ({query_adds[1]}) & ({query_adds[2]})).all()'

    odata = eval(table_query)
    custlist = []
    for odat in odata:
        shipper = odat.Shipper
        if shipper is not None:
            if len(shipper) > 20: shipper = shipper[0:20]
            if shipper not in custlist: custlist.append(shipper)
    custlist.sort()
    custlist.append('Show All')
    return custlist

def next_business_day(date, jx):
    next_day = date
    kx = 0
    for ix in range(15):
        if jx < 0: next_day = next_day - timedelta(days=1)
        else: next_day = next_day + timedelta(days=1)
        pdat = PortClosed.query.filter(PortClosed.Date==next_day).first()
        if pdat is None:
            kx += 1
            if kx == abs(jx): return next_day

def create_cal_data(tfilters, dlist, username, resetmod):
    # Define the dates shown for the selection based on current date
    todaynow = datetime.datetime.now()
    todaynow = todaynow.date()
    whatweek = tfilters['Date Filter']
    weekmv = dlist.index(whatweek) - 2
    # See if todaynow is a business day.  If not get the next business day.
    todaynow = todaynow + timedelta(days=weekmv*7)
    pcdat = PortClosed.query.filter(PortClosed.Date == todaynow).first()
    if pcdat is not None: todaynow = next_business_day(todaynow, 1)
    busweek = 1
    if busweek:
        sw = todaynow - timedelta(days=todaynow.weekday())
        #busdays = [sw, next_business_day(sw, 1), next_business_day(sw, 2), next_business_day(sw, 3), next_business_day(sw, 4)]
        caldays = [sw, sw+timedelta(days=1), sw+timedelta(days=2), sw+timedelta(days=3), sw+timedelta(days=4)]

    lbdate = datetime.datetime.now() - timedelta(15)
    lbdate = lbdate.date()
    userlist = []
    #podata = Orders.query.filter((Orders.Hstat < 2) & (Orders.Date3 > lbdate)).all()
    ##########################################################

    podata = Orders.query.filter(Orders.Date3 > lbdate).all()

    ##########################################################
    pdio, pdip, pdeo, pdep = [[], [], [], [], [], []], [[], [], [], [], [], []], [[], [], [], [], [], []], [[], [], [],
                                                                                                            [], [], []]
    pdic, pdec, pmon = [[], [], [], [], [], []], [[], [], [], [], [], []],[[], [], [], [], [], []]
    day_sequence = [[], [], [], [], [], []]
    complete_color = 'text-info'
    ktime = 1

    for podat in podata:
        hstat = podat.Hstat
        istat = podat.Istat
        container = podat.Container
        shipper = podat.Shipper
        order = podat.Order
        dtype = podat.Delivery
        dtime = podat.Time3
        ptime = podat.Time2

        if dtype is None:
            deliverline = 'Placeholder'
        else:
            deliverline = f'{dtype}'

        if hasinput(dtime):
            delivertime = f'{dtime}'
        else:
            delivertime = '25:00'

        if hasinput(ptime):
            picktime = f'{ptime}'
        else:
            picktime = '25:00'


        #print(f'{deliverline}: delivertime is {delivertime} and picktime is {picktime}')

        user = podat.UserMod
        if user != username:
            if user not in userlist:
                userlist.append(user)
            if resetmod is not None:
                podat.UserMod = username
                db.session.commit()

        if shipper == 'Global Business Link' and 'Outside' not in order:
            #Create special block to show loads in and empties out
            #print(f'Skipping Global Drop-Hook Runs for Calendar')
            globalrun = 1

        else:

            if shipper == 'Global Business Link': shipper = f'GBL-{order}'
            if shipper == 'FEL Ocean Div': shipper = f'FEL-{order}'
            if len(shipper) > 25: shipper = shipper[0:25]
            ht = podat.HaulType
            jo = podat.Jo
            contype = podat.Type
            location = f'{podat.Dropblock2}'
            location = location.splitlines()

            release = podat.Booking
            in_booking = podat.BOL
            description = podat.Description
            address = podat.Dropblock2
            ship = f'{podat.Ship} {podat.Voyage}'
            notes = podat.Location
            if notes is None: notes = ''
            comment = []


            on_alldates = 0
            on_calendar = 0

            gateout = podat.Date
            delivery = podat.Date3
            gatein = podat.Date2
            arrives = podat.Date6
            dueback = podat.Date7
            pick = podat.Date8
            del_s = short_date(delivery)
            arr_s = short_date(arrives)
            due_s = short_date(dueback)
            pulled = short_date(gateout)
            ret_s = short_date(gatein)

            if 'Import' in podat.HaulType:
                timport = 1
            else:
                timport = 0
            if 'Export' in podat.HaulType:
                texport = 1
            else:
                texport = 0

            if 'DP' in podat.HaulType:
                droppick = 1
            else:
                droppick = 0

            delstat = podat.DelStat
            if delstat is None: delstat = 0
            #print(f'for container {container} completion is {delstat}')

            if hstat >= 2:
                #Getting invoices for calendar date regardless of import or export
                colorline = 'bg-success text-white'

                for ix in range(5):
                    if gatein == caldays[ix]:
                        if istat > 0:
                            try:
                                amount = float(podat.InvoTotal)
                            except:
                                amount = 0.00
                            pmon[ix + 1].append([jo, container, d2s(amount), colorline, 0.00, shipper])
                            sum = 0
                            for mon in pmon[ix + 1]:
                                amt = float(mon[2])
                                sum += amt
                            pmon[ix + 1][0][4] = d2s(sum)

            if timport:
                avail = podat.Date4
                avail_s = short_date(avail)
                lfd = podat.Date5
                lfd_s = short_date(lfd)

                if hstat >= 1:
                    bc1 = f'{container} GO:{pulled}'
                    istat = podat.Istat
                    if istat >= 2 and podat.InvoTotal is not None:
                        bc2 = f'{container} GI:{ret_s}'
                    else:
                        bc2 = f'{container} GI:{ret_s} ***'

                    custline = f'{shipper}'

                    for ix in range(5):
                        if gateout == caldays[ix]:
                            pdic[ix + 1].append([bc1,custline, 'blue-text'])
                        if gatein == caldays[ix]:
                            #Need hast check because gatein can be planned
                            if hstat > 1:
                                #if istat > 0: colorline = 'green-text'
                                #else: colorline = 'purple-text'
                                colorline = 'purple-text'
                                pdic[ix + 1].append([bc2, custline, colorline])

                if hstat == 1:
                    if not isinstance(dueback, datetime.datetime): dueback = due_back(gateout)
                    due_s = short_date(dueback)

                    firstline = f'{container}'
                    custline = f'{shipper}'
                    dateline = f'GO:{pulled} DV:{del_s} DB:{due_s}'
                    colorline = 'blue-text'
                    comment = []
                    pdio[0].append([firstline, custline, dateline, colorline, comment, jo, contype, deliverline, delivertime])
                    on_alldates = 1

                    datecluster = [gateout, delivery, gatein, avail, lfd, arrives, dueback, pick, dtime, ptime, f'timepicker{ktime}', f'timepicker{ktime + 1}', ht, dtype]
                    #print(f'Import container: {container} timepicker{ktime} timepicker{ktime + 1}')
                    ktime += 2

                    for ix in range(5):
                        if delstat > 0:
                            if droppick and delstat == 1:
                                if pick == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Pick on {pick}')
                                    pdio[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location, release,
                                         in_booking, description, ship, notes, datecluster, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1
                            elif droppick and delstat == 2:
                                if gatein == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Empty due back {dueback}')
                                    pdio[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location, release,
                                         in_booking, description, ship, notes, datecluster, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1
                            else:
                                if gatein == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Empty due back {dueback}')
                                    pdio[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location, release,
                                         in_booking, description, ship, notes, datecluster, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1
                        else:
                            if delivery == caldays[ix]:
                                colorline = 'blue-text'
                                if dueback < delivery:
                                    #colorline = 'red-text'
                                    comment = ['****']
                                    comment.append(f'Past due back {dueback}')
                                elif dueback == delivery:
                                    #colorline = 'text-warning'
                                    comment = ['****']
                                    comment.append('Due back today')

                                pdio[ix + 1].append([firstline, custline, dateline, colorline, comment, jo, contype, location, release, in_booking, description, ship, notes, datecluster, deliverline, delivertime, droppick, delstat])
                                on_calendar = 1

                elif hstat < 1:

                    firstline = f'{container}'
                    custline = f'{shipper}'
                    dateline = f'AP:{avail_s} DV:{del_s} LFD:{lfd_s}'
                    colorline = 'black-text'
                    comment = []
                    pdip[0].append([firstline, custline, dateline, colorline, comment, jo, contype, deliverline, delivertime])
                    on_alldates = 1

                    datecluster = [gateout, delivery, gatein, avail, lfd, arrives, dueback, pick, dtime, ptime, f'timepicker{ktime}', f'timepicker{ktime + 1}', ht, dtype]
                    #print(f'Import container: {container} timepicker{ktime} timepicker{ktime + 1}')
                    ktime += 2

                    for ix in range(5):
                        if delstat > 0:
                            if droppick and delstat == 1:
                                if pick == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Pick on {pick}')
                                    pdip[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location, release,
                                         in_booking, description, ship, notes, datecluster, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1
                            elif droppick and delstat == 2:
                                if gatein == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Empty due back {dueback}')
                                    pdip[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location, release,
                                         in_booking, description, ship, notes, datecluster, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1
                            else:
                                if gatein == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Empty due back {dueback}')
                                    pdip[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location, release,
                                         in_booking, description, ship, notes, datecluster, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1

                        else:
                            if delivery == caldays[ix]:
                                if lfd is not None:
                                    if lfd < gateout:
                                        colorline = 'red-text'
                                        comment = ['****']
                                        comment.append('Past LFD for pull')
                                    elif lfd == gateout:
                                        colorline = 'orange-text'
                                        comment = ['****']
                                        comment.append(f'Today LFD for pull')
                                    else:
                                        colorline = 'black-text'
                                        comment.append(f'Pull on {pulled}')
                                else:
                                    colorline = 'black-text'
                                pdip[ix + 1].append([firstline, custline, dateline, colorline, comment, jo, contype, location, release, in_booking, description, ship, notes, datecluster, deliverline, delivertime, droppick, delstat])
                                on_calendar = 1



            if texport:
                erd = podat.Date4
                erd_s = short_date(erd)
                cut = podat.Date5
                cut_s = short_date(cut)

                if hstat >= 1:
                    #Breadcrumbs for Exports
                    bc1 = f'{container} GO:{pulled}'
                    istat = podat.Istat
                    if istat >= 2 and podat.InvoTotal is not None:
                        bc2 = f'{container} GI:{ret_s}'
                    else:
                        bc2 = f'{container} GI:{ret_s} ***'
                    custline = f'{shipper}'

                    for ix in range(5):
                        if gateout == caldays[ix]:
                            pdec[ix + 1].append([bc1,custline, 'blue-text'])
                        if gatein == caldays[ix]:
                            if hstat > 1:
                                colorline = 'purple-text'
                                pdec[ix + 1].append([bc2, custline, colorline])

                if hstat == 1:
                    colorline = 'blue-text'
                    comment = []
                    firstline = f'{container}'
                    custline = f'{shipper}'
                    addrline = f'{address}'
                    dateline = f'GO:{pulled} DV:{del_s} GI:{ret_s}'
                    shipdates = f'DB:{due_s} ER:{erd_s} CO:{cut_s}'


                    datecluster = [gateout, delivery, gatein, erd, cut, arrives, dueback, pick, dtime, ptime, f'timepicker{ktime}', f'timepicker{ktime + 1}', ht, dtype]
                    #print(f'Export booking:{podat.Booking} container: {container} timepicker{ktime} timepicker{ktime + 1}')
                    ktime += 2

                    if erd is not None:
                        if gatein < erd:
                            #colorline = 'orange-text'
                            comment.append(f'No return before {erd_s}')
                    if cut is not None:
                        if gatein > cut:
                            #colorline = 'orange-text'
                            comment.append(f'Ret post cut {cut_s}')
                    if not hasinput(in_booking):
                        in_booking = release
                    if in_booking != release:
                        #colorline = 'orange-text'
                        comment.append(f'Ret booking change')
                    if comment != []: comment.insert(0, '****')

                    pdeo[0].append([firstline, custline, dateline, colorline, comment, jo, contype, addrline, shipdates, deliverline, delivertime])
                    on_alldates = 1

                    for ix in range(5):
                        if delstat>0:
                            if droppick and delstat == 1:
                                if pick == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Drop Completed')
                                    comment.append(f'Pick on {pick}')
                                    pdeo[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location,
                                         release, in_booking, description, ship, notes, datecluster, addrline,
                                         shipdates, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1
                            elif droppick and delstat == 2:
                                if gatein == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Pick Completed')
                                    comment.append(f'Load due back {dueback}')
                                    pdeo[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location,
                                         release, in_booking, description, ship, notes, datecluster, addrline,
                                         shipdates, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1
                            else:
                                if gatein == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Delivery Completed')
                                    comment.append(f'Load due back {dueback}')
                                    pdeo[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location,
                                         release, in_booking, description, ship, notes, datecluster, addrline,
                                         shipdates, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1
                        else:
                            if delivery == caldays[ix]:
                                pdeo[ix + 1].append([firstline, custline, dateline, colorline, comment, jo, contype, location, release, in_booking, description, ship, notes, datecluster, addrline, shipdates, deliverline, delivertime, droppick, delstat])
                                on_calendar = 1

                elif hstat < 1:
                    firstline = f'{podat.Booking}'
                    custline = f'{shipper}'
                    addrline = f'{address}'
                    colorline = 'black-text'
                    dateline = f'GO:{pulled} DV:{del_s} GI:{ret_s}'
                    shipdates = f'AR:{arr_s} ER:{erd_s} CO:{cut_s}'

                    datecluster = [gateout, delivery, gatein, erd, cut, arrives, dueback, pick, dtime, ptime, f'timepicker{ktime}', f'timepicker{ktime + 1}', ht, dtype]
                    #print(f'Export booking:{podat.Booking} container: {container} timepicker{ktime} timepicker{ktime + 1}')
                    ktime += 2

                    if erd is not None:
                        if delivery < erd:
                            #colorline = 'orange-text'
                            comment = ['****']
                            comment.append(f'No return before {erd_s}')
                    pdep[0].append([firstline, custline, dateline, colorline, comment, jo, contype, addrline, shipdates, deliverline, delivertime])
                    on_alldates = 1
                    for ix in range(5):
                        if delstat>0:
                            if droppick and delstat == 1:
                                if pick == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Pick on {pick}')
                                    pdep[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location,
                                         release, in_booking, description, ship, notes, datecluster, addrline,
                                         shipdates, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1
                            elif droppick and delstat == 2:
                                if gatein == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Load due back {dueback}')
                                    pdep[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location,
                                         release, in_booking, description, ship, notes, datecluster, addrline,
                                         shipdates, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1
                            else:
                                if gatein == caldays[ix]:
                                    colorline = 'text-info'
                                    comment.append(f'Load due back {dueback}')
                                    pdep[ix + 1].append(
                                        [firstline, custline, dateline, colorline, comment, jo, contype, location,
                                         release, in_booking, description, ship, notes, datecluster, addrline,
                                         shipdates, deliverline, delivertime, droppick, delstat])
                                    on_calendar = 1
                        else:
                            if delivery == caldays[ix]:
                                colorline = 'black-text'
                                comment.append(f'Pull on {pulled}')
                                pdep[ix + 1].append([firstline, custline, dateline, colorline, comment, jo, contype, location, release, in_booking, description, ship, notes, datecluster, addrline, shipdates, deliverline, delivertime, droppick, delstat])
                                on_calendar = 1

            if on_alldates and not on_calendar:
                if texport:
                    if hstat == 1:
                        #print(f'Job {pdeo[0][-1]} not on the current calendar')
                        pdeo[0][-1][3] = 'blue-text'
                        pdeo[0][-1][4] = ['Not on Viewed Schedule']
                    else:
                        #print(f'Job {pdep[0][-1]} not on the current calendar')
                        pdep[0][-1][3] = 'black-text'
                        pdep[0][-1][4] = ['Not on Viewed Schedule']

                if timport:
                    if hstat == 1:
                        #print(f'Job {pdio[0][-1]} not on the current calendar')
                        pdio[0][-1][3] = 'blue-text'
                        pdio[0][-1][4] = ['Not on Viewed Schedule']
                    else:
                        #print(f'Job {pdip[0][-1]} not on the current calendar')
                        pdip[0][-1][3] = 'black-text'
                        pdip[0][-1][4] = ['Not on Viewed Schedule']

    custom_order = ['Hard Time', 'Soft Time', 'Day Window', 'Upon Notice', 'Placeholder', '']
    order_map = {level: i for i, level in enumerate(custom_order)}
    for ix in range(1,6):
        for jx, io in enumerate(pdio[ix]):
            day_sequence[ix].append(['pdio',jx,io[14],io[15]])
        for jx, ip in enumerate(pdip[ix]):
            day_sequence[ix].append(['pdip',jx,ip[14],ip[15]])
        for jx, eo in enumerate(pdeo[ix]):
            day_sequence[ix].append(['pdeo',jx,eo[16],eo[17]])
        for jx, ep in enumerate(pdep[ix]):
            day_sequence[ix].append(['pdep',jx,ep[16],ep[17]])

    new_day = [[],[],[],[],[],[]]
    for ix in range(1,6):
        #print(f'day sequence:{day_sequence[ix]}')
        new_day[ix] = sorted(day_sequence[ix], key=lambda x: ( x[3], order_map[x[2]]) )

    #for ix in range(1,6):
        #for day in new_day[ix]:
            #print(ix,day)


    if userlist == []: userchange = 0
    else: userchange = 1
    return pdio, pdip, pdeo, pdep, caldays, pdic, pdec, pmon, userchange, new_day

def initialize_calendar_checks(pdio, pdip, pdeo, pdep, jolist):
    pdiovec, pdipvec, pdeovec, pdepvec = [[], [], [], [], [], []], [[], [], [], [], [], []], [[], [], [], [], [], []], [
        [], [], [], [], [], []]
    # See which of these listed items have been checked
    #print(f'Initializing calendar checks based on jolist {jolist}')
    if jolist == 0: return pdiovec, pdipvec, pdeovec, pdepvec
    for jx in range(6):
        for ix, item in enumerate(pdio[jx]):
            if item[5] in jolist:
                pdiovec[jx].append(ix + 1)

        for ix, item in enumerate(pdip[jx]):
            if item[5] in jolist:
                pdipvec[jx].append(ix + 1)

        for ix, item in enumerate(pdeo[jx]):
            if item[5] in jolist:
                pdeovec[jx].append(ix + 1)

        for ix, item in enumerate(pdep[jx]):
            if item[5] in jolist:
                pdepvec[jx].append(ix + 1)

    return pdiovec, pdipvec, pdeovec, pdepvec

def cal_to_orders(jolist, checked_data):
    ckdatalist = []
    for jo in jolist:
        od = Orders.query.filter(Orders.Jo == jo).first()
        if od is not None:
            ckdatalist.append(od.id)
    ckdatalen = len(ckdatalist)
    new_checked_data = []
    for ck in checked_data:
        if ck[0] == 'Orders':
            new_checked_data.append(['Orders', ckdatalen, ckdatalist])
        else:
            new_checked_data.append(ck)
    return new_checked_data

def get_calendar_checks(pdio, pdip, pdeo, pdep):
    pdiovec, pdipvec, pdeovec, pdepvec = [[], [], [], [], [], []], [[], [], [], [], [], []], [[], [], [], [], [], []], [[], [], [], [], [], []]
    jolist_all = []
    jolist_cal = []
    # See which of these listed items have been checked
    for jx in range(6):
        for ix, item in enumerate(pdio[jx]):
            if jx == 0:
                test = request.values.get(f'x{item[5]}')
            else: test = request.values.get(f'{item[5]}')
            if test is not None:
                pdiovec[jx].append(ix + 1)
                if jx == 0: jolist_all.append(item[5])
                else: jolist_cal.append(item[5])

        for ix, item in enumerate(pdip[jx]):
            if jx == 0:
                test = request.values.get(f'x{item[5]}')
            else:
                test = request.values.get(f'{item[5]}')
            if test is not None:
                pdipvec[jx].append(ix + 1)
                if jx == 0:
                    jolist_all.append(item[5])
                else:
                    jolist_cal.append(item[5])

        for ix, item in enumerate(pdeo[jx]):
            if jx == 0:
                test = request.values.get(f'x{item[5]}')
            else:
                test = request.values.get(f'{item[5]}')
            if test is not None:
                pdeovec[jx].append(ix + 1)
                if jx == 0:
                    jolist_all.append(item[5])
                else:
                    jolist_cal.append(item[5])

        for ix, item in enumerate(pdep[jx]):
            if jx == 0:
                test = request.values.get(f'x{item[5]}')
            else:
                test = request.values.get(f'{item[5]}')
            if test is not None:
                pdepvec[jx].append(ix + 1)
                if jx == 0:
                    jolist_all.append(item[5])
                else:
                    jolist_cal.append(item[5])

    jolist = list(set(jolist_all + jolist_cal))

    return pdiovec, pdipvec, pdeovec, pdepvec, jolist

def update_calendar_form(pdio, pdip, pdeo, pdep):
    # Some changes on the update may require a re-update, like date moves will move the position on the calendar
    #print(f'***In update_calendar_form***')
    reupdate = 0
    #Cycle through each day
    for jx in range(1,6):
        for ix, item in enumerate(pdio[jx]):
            jo = item[5]
            note = request.values.get(f'note{jo}')
            delv = request.values.get(f'delv{jo}')
            delv2 = request.values.get(f'delv2{jo}')
            delt = request.values.get(f'delt{jo}')
            pict = request.values.get(f'pict{jo}')
            gin = request.values.get(f'gin{jo}')
            dwp = request.values.get(f'dwp{jo}')
            dwp2 = request.values.get(f'dwp2{jo}')
            ht = request.values.get(f'ht{jo}')
            dt = request.values.get(f'dt{jo}')
            odat = Orders.query.filter(Orders.Jo == jo).first()
            if odat is not None:
                if note is not None:
                    odat.Location = note
                    pdio[jx][ix][12] = note
                    reupdate = 1
                if delv is not None:
                    odat.Date3 = delv
                    pdio[jx][ix][13][1] = delv
                    reupdate = 1
                if delt is not None:
                    odat.Time3 = delt
                    pdio[jx][ix][13][8] = delt
                    reupdate = 1
                if pict is not None:
                    odat.Time2 = pict
                    pdio[jx][ix][13][9] = pict
                    reupdate = 1
                if delv2 is not None:
                    drop_date = odat.Date3
                    # In case the default is set too far away make the pick date at least equal drop
                    if delv2 < drop_date:
                        odat.Date8 = drop_date
                        pdio[jx][ix][13][7] = drop_date
                    else:
                        odat.Date8 = delv2
                        pdio[jx][ix][13][7] = delv2
                    reupdate = 1
                if gin is not None:
                    odat.Date2 = gin
                    pdio[jx][ix][13][2] = gin
                    reupdate = 1

                if ht is not None:
                    odat.HaulType = ht
                    pdio[jx][ix][13][12] = ht
                    reupdate = 1
                if dt is not None:
                    odat.Delivery = dt
                    pdio[jx][ix][13][13] = dt
                    if 'Time' not in dt:
                        odat.Time3 = None
                        odat.Time2 = None
                    reupdate = 1


                if dwp == 'on':
                    odat.DelStat = 1
                    reupdate = 1
                # Need delv to make sure not updating on a blank screen
                if delv is not None and dwp is None:
                    odat.DelStat = 0
                    reupdate = 1
                if dwp2 == 'on':
                    odat.DelStat = 2
                    reupdate = 1
                if delv2 is not None and dwp2 is None:
                    dstat = odat.DelStat
                    if dstat == 2:
                        odat.DelStat = 1
                        reupdate = 1

                db.session.commit()



        for ix, item in enumerate(pdip[jx]):
            jo = item[5]
            note = request.values.get(f'note{jo}')
            gout = request.values.get(f'gout{jo}')
            delv = request.values.get(f'delv{jo}')
            delv2 = request.values.get(f'delv2{jo}')
            gin = request.values.get(f'gin{jo}')
            dwp = request.values.get(f'dwp{jo}')
            dwp2 = request.values.get(f'dwp2{jo}')
            delt = request.values.get(f'delt{jo}')
            pict = request.values.get(f'pict{jo}')
            ht = request.values.get(f'ht{jo}')
            dt = request.values.get(f'dt{jo}')
            odat = Orders.query.filter(Orders.Jo == jo).first()
            if odat is not None:
                if note is not None:
                    odat.Location = note
                    pdip[jx][ix][12] = note
                    reupdate = 1
                if delv is not None:
                    odat.Date3 = delv
                    pdip[jx][ix][13][1] = delv
                    reupdate = 1
                if delv2 is not None:
                    drop_date = odat.Date3
                    # In case the default is set too far away make the pick date at least equal drop
                    if delv2 < drop_date:
                        odat.Date8 = drop_date
                        pdip[jx][ix][13][7] = drop_date
                    else:
                        odat.Date8 = delv2
                        pdip[jx][ix][13][7] = delv2
                    reupdate = 1
                if delt is not None:
                    odat.Time3 = delt
                    pdip[jx][ix][13][8] = delt
                    reupdate = 1
                if pict is not None:
                    odat.Time2 = pict
                    pdip[jx][ix][13][9] = pict
                    reupdate = 1
                if gin is not None:
                    odat.Date2 = gin
                    pdip[jx][ix][13][2] = gin
                    reupdate = 1
                if gout is not None:
                    odat.Date = gout
                    pdip[jx][ix][13][0] = gout
                    reupdate = 1
                if ht is not None:
                    odat.HaulType = ht
                    pdip[jx][ix][13][12] = ht
                    reupdate = 1
                if dt is not None:
                    odat.Delivery = dt
                    pdip[jx][ix][13][13] = dt
                    if 'Time' not in dt:
                        odat.Time3 = None
                        odat.Time2 = None
                    reupdate = 1


                if dwp == 'on':
                    odat.DelStat = 1
                    reupdate = 1
                # Need delv to make sure not updating on a blank screen
                if delv is not None and dwp is None:
                    odat.DelStat = 0
                    reupdate = 1
                if dwp2 == 'on':
                    odat.DelStat = 2
                    reupdate = 1
                if delv2 is not None and dwp2 is None:
                    dstat = odat.DelStat
                    if dstat == 2:
                        odat.DelStat = 1
                        reupdate = 1

                db.session.commit()


        for ix, item in enumerate(pdeo[jx]):
            jo = item[5]
            note = request.values.get(f'note{jo}')
            delv = request.values.get(f'delv{jo}')
            delv2 = request.values.get(f'delv2{jo}')
            gin = request.values.get(f'gin{jo}')
            book = request.values.get(f'book{jo}')
            dwp = request.values.get(f'dwp{jo}')
            dwp2 = request.values.get(f'dwp2{jo}')
            delt = request.values.get(f'delt{jo}')
            pict = request.values.get(f'pict{jo}')
            ht = request.values.get(f'ht{jo}')
            dt = request.values.get(f'dt{jo}')
            odat = Orders.query.filter(Orders.Jo == jo).first()
            if odat is not None:
                if note is not None:
                    odat.Location = note
                    pdeo[jx][ix][12] = note
                    reupdate = 1
                if delv is not None:
                    odat.Date3 = delv
                    pdeo[jx][ix][13][1] = delv
                    reupdate = 1
                if delv2 is not None:
                    #print(f'date8 is {delv2}')
                    drop_date = odat.Date3
                    # In case the default is set too far away make the pick date at least equal drop
                    if delv2 < drop_date:
                        odat.Date8 = drop_date
                        pdeo[jx][ix][13][7] = drop_date
                    else:
                        odat.Date8 = delv2
                        pdeo[jx][ix][13][7] = delv2
                    reupdate = 1
                if delt is not None:
                    odat.Time3 = delt
                    pdeo[jx][ix][13][8] = delt
                    reupdate = 1
                if pict is not None:
                    odat.Time2 = pict
                    pdeo[jx][ix][13][9] = pict
                    reupdate = 1
                if gin is not None:
                    odat.Date2 = gin
                    pdeo[jx][ix][13][2] = gin
                    reupdate = 1
                if ht is not None:
                    odat.HaulType = ht
                    pdeo[jx][ix][13][12] = ht
                    reupdate = 1
                if dt is not None:
                    odat.Delivery = dt
                    pdeo[jx][ix][13][13] = dt
                    if 'Time' not in dt:
                        odat.Time3 = None
                        odat.Time2 = None
                    reupdate = 1

                if book is not None:
                    odat.BOL = book
                    pdeo[jx][ix][9] = book
                    reupdate = 1

                if dwp == 'on':
                    odat.DelStat = 1
                    reupdate = 1
                # Need delv to make sure not updating on a blank screen
                if delv is not None and dwp is None:
                    odat.DelStat = 0
                    reupdate = 1
                if dwp2 == 'on':
                    odat.DelStat = 2
                    reupdate = 1
                if delv2 is not None and dwp2 is None:
                    dstat = odat.DelStat
                    if dstat == 2:
                        odat.DelStat = 1
                        reupdate = 1

                db.session.commit()


        for ix, item in enumerate(pdep[jx]):
            jo = item[5]
            note = request.values.get(f'note{jo}')
            gout = request.values.get(f'gout{jo}')
            delv = request.values.get(f'delv{jo}')
            delv2 = request.values.get(f'delv2{jo}')
            gin = request.values.get(f'gin{jo}')
            dwp = request.values.get(f'dwp{jo}')
            dwp2 = request.values.get(f'dwp2{jo}')
            delt = request.values.get(f'delt{jo}')
            pict = request.values.get(f'pict{jo}')
            ht = request.values.get(f'ht{jo}')
            dt = request.values.get(f'dt{jo}')
            odat = Orders.query.filter(Orders.Jo == jo).first()
            if odat is not None:
                if note is not None:
                    odat.Location = note
                    pdep[jx][ix][12] = note
                    reupdate = 1
                if delv is not None:
                    odat.Date3 = delv
                    pdep[jx][ix][13][1] = delv
                    reupdate = 1
                if delv2 is not None:
                    drop_date = odat.Date3
                    # In case the default is set too far away make the pick date at least equal drop
                    if delv2 < drop_date:
                        odat.Date8 = drop_date
                        pdep[jx][ix][13][7] = drop_date
                    else:
                        odat.Date8 = delv2
                        pdep[jx][ix][13][7] = delv2
                    reupdate = 1
                if delt is not None:
                    odat.Time3 = delt
                    pdep[jx][ix][13][8] = delt
                    reupdate = 1
                if pict is not None:
                    odat.Time2 = pict
                    pdep[jx][ix][13][9] = pict
                    reupdate = 1
                if gin is not None:
                    odat.Date2 = gin
                    pdep[jx][ix][13][2] = gin
                    reupdate = 1
                if gout is not None:
                    odat.Date = gout
                    pdep[jx][ix][13][0] = gout
                    reupdate = 1
                if ht is not None:
                    odat.HaulType = ht
                    pdep[jx][ix][13][12] = ht
                    reupdate = 1
                if dt is not None:
                    odat.Delivery = dt
                    pdep[jx][ix][13][13] = dt
                    if 'Time' not in dt:
                        odat.Time3 = None
                        odat.Time2 = None
                    reupdate = 1

                if dwp == 'on':
                    odat.DelStat = 1
                    reupdate = 1
                # Need delv to make sure not updating on a blank screen
                if delv is not None and dwp is None:
                    odat.DelStat = 0
                    reupdate = 1
                if dwp2 == 'on':
                    odat.DelStat = 2
                    reupdate = 1
                if delv2 is not None and dwp2 is None:
                    dstat = odat.DelStat
                    if dstat == 2:
                        odat.DelStat = 1
                        reupdate = 1

                db.session.commit()

    return pdio, pdip, pdeo, pdep, reupdate

def run_driver_upload(checked_data, upload):
    cancel = request.values.get('cancel')
    viewport = ['0'] * 6
    holdvec = [''] * 150
    holdvec[140] = upload
    entrydata = []
    sid = None
    task_iter = 1
    #table = tablesetup['table']
    #print(f'checked data is: {checked_data}')
    for ck in checked_data:
        table = ck[0]
        nc = ck[1]
        if table == 'Drivers' and nc == 1:
            sid = ck[2][0]
            print(table, nc, sid)
    if sid is None:
        err = ['No Driver Table Data Selected']
        holdvec[140] = ''
        return holdvec, entrydata, err, viewport, True



    if cancel is not None:
        completed=True
        err = ['Upload has been cancelled']
    else:
        completed = False
        err = [f'Running Upload task for {upload}']


        if task_iter == 1:
            viewport[0] = 'upload_doc_right'
        else:
            viewport[0] = request.values.get('viewport0')
            viewport[2] = request.values.get('viewport2')

        dat = Drivers.query.get(sid)

        try:
            getattr(dat, f'{upload}')
        except:
            err.append(f'{thistable} has no attribute {task_focus}')
            completed = True

        if not completed:

            viewport[3] = str(sid)
            viewport[4] = f'Trucking Drivers Item'
            uploadnow = request.values.get('uploadnow')

            if uploadnow is not None:
                viewport[0] = 'show_doc_right'
                file = request.files['docupload']
                if file.filename == '':
                    err.append('No file selected for uploading')


                name, exto = os.path.splitext(file.filename)
                ext = exto.lower()
                if upload == 'CDLpdf':
                    sname = 'Ccache'
                elif upload == 'MEDpdf':
                    sname = 'Mcache'
                elif upload == 'TWICpdf':
                    sname = 'Tcache'

                sn = getattr(dat, sname)
                try:
                    sn = int(sn)
                    bn = sn+1
                except:
                    sn = 0
                    bn = 0

                driver = dat.Name
                driver = driver.replace(" ","")

                if upload == 'CDLpdf':
                    filename1 = f'{driver}_CDL_c{str(bn)}{ext}'
                    filename2 = f'{driver}_CDL{ext}'
                    output1 = addpath(tpath(f'Drivers-CDL', filename1))
                    output2 = addpath(tpath(f'Drivers-CDL', filename2))
                elif upload == 'MEDpdf':
                    filename1 = f'{driver}_MED_c{str(bn)}{ext}'
                    filename2 = f'{driver}_MED{ext}'
                    output1 = addpath(tpath(f'Drivers-MED', filename1))
                    output2 = addpath(tpath(f'Drivers-CDL', filename2))
                elif upload == 'TWICpdf':
                    filename1 = f'{driver}_TWIC_c{str(bn)}{ext}'
                    filename2 = f'{driver}_TWIC{ext}'
                    output1 = addpath(tpath(f'Drivers-TWIC', filename1))
                    output2 = addpath(tpath(f'Drivers-CDL', filename2))

                #print(f'output1 = {output1}')
                # filename1 is for browser display which must maintain new file names to overcome caching
                # filename2 is for the api display which need to avoid the caching suffix

                file.save(output1)
                file.save(output2)
                viewport[2] = '/'+tpath(f'Drivers-Compliance', filename1)

                setattr(dat, upload, filename1)
                setattr(dat, sname, bn)
                db.session.commit()
                err.append(f'Viewing {filename1}')
                err.append('Hit Return to End Viewing and Return to Table View')
                #returnhit = request.values.get('Return')
                #if returnhit is not None: completed = True
                completed = True
                #viewport = ['0'] * 6
                holdvec[140] = ''

    return holdvec, entrydata, err, viewport, completed

def run_truck_upload(checked_data, upload):
    cancel = request.values.get('cancel')
    viewport = ['0'] * 6
    holdvec = [''] * 150
    holdvec[141] = upload
    entrydata = []
    sid = None
    task_iter = 1
    #table = tablesetup['table']
    print(f'checked data is: {checked_data}')
    for ck in checked_data:
        table = ck[0]
        nc = ck[1]
        if table == 'Trucks' and nc == 1:
            sid = ck[2][0]
            print(table, nc, sid)
    if sid is None:
        err = ['No Truck Table Data Selected']
        holdvec[141] = ''
        return holdvec, entrydata, err, viewport, True



    if cancel is not None:
        completed=True
        err = ['Upload has been cancelled']
    else:
        completed = False
        err = [f'Running Upload task for {upload}']


        if task_iter == 1:
            viewport[0] = 'upload_doc_right'
        else:
            viewport[0] = request.values.get('viewport0')
            viewport[2] = request.values.get('viewport2')

        dat = Vehicles.query.get(sid)

        try:
            getattr(dat, f'{upload}')
        except:
            err.append(f'Vehicles Table has no attribute {upload}')
            completed = True

        if not completed:

            viewport[3] = str(sid)
            viewport[4] = f'Trucking Drivers Item'
            uploadnow = request.values.get('uploadnow')

            if uploadnow is not None:
                viewport[0] = 'show_doc_right'
                file = request.files['docupload']
                if file.filename == '':
                    err.append('No file selected for uploading')

                unit = f'Unit_{dat.Unit}'
                name, exto = os.path.splitext(file.filename)
                ext = exto.lower()
                if upload == 'Regpdf':
                    sname = 'Rcache'
                elif upload == 'Titpdf':
                    sname = 'Tcache'

                sn = getattr(dat, sname)
                try:
                    sn = int(sn)
                    bn = sn+1
                except:
                    sn = 0
                    bn = 0

                if upload == 'Regpdf':
                    filename1 = f'{unit}_Reg_c{str(bn)}{ext}'
                    output1 = addpath(tpath(f'Trucks-Reg', filename1))
                elif upload == 'Titpdf':
                    filename1 = f'{unit}_Title_c{str(bn)}{ext}'
                    output1 = addpath(tpath(f'Trucks-Tit', filename1))
                #print(f'output1 = {output1}')

                file.save(output1)
                viewport[2] = '/'+tpath(f'Drivers-Compliance', filename1)

                setattr(dat, upload, filename1)
                setattr(dat, sname, bn)
                db.session.commit()
                err.append(f'Viewing {filename1}')
                err.append('Hit Return to End Viewing and Return to Table View')
                #returnhit = request.values.get('Return')
                #if returnhit is not None: completed = True
                completed = True
                #viewport = ['0'] * 6
                holdvec[141] = ''

    return holdvec, entrydata, err, viewport, completed



def Table_maker(genre):
    username = session['username'].capitalize()
    # Gather information about the tables inside the genre
    #print(f'The genre is {genre}')
    genre_tables = eval(f"{genre}_genre['genre_tables']")
    quick_buttons = eval(f"{genre}_genre['quick_buttons']")
    table_filters = eval(f"{genre}_genre['table_filters']")
    task_boxes = eval(f"{genre}_genre['task_boxes']")
    task_box_map = eval(f"{genre}_genre['task_box_map']")

    #print(f'The genre is {genre} and the genre tables are: {genre_tables}')

    # Left size is the portion out of 12 devoted to table and document display
    leftsize = 8
    # Define list variables even if not used in some tasks
    err, tabletitle, checked_data, jscripts = [], [], [], []
    viewport = ['tables'] + ['0']*5
    tfilters, tboxes = {}, {}
    returnhit = None
    driver_upload = None
    truck_upload = None
    resethit = request.values.get('Reset')
    invoicehit = request.values.get('InvoiceSet')
    resetmod = request.values.get('ResetMod')




    if request.method == 'POST' and resethit is None and resetmod is None:

        # See if a task is active and ongoing
        tasktype = nononestr(request.values.get('tasktype'))
        taskon = nononestr(request.values.get('taskon'))
        task_focus = nononestr(request.values.get('task_focus'))
        task_iter = nonone(request.values.get('task_iter'))

        driver_upload = request.values.get('driveruploads')
        truck_upload = request.values.get('truckuploads')
        #print(f'driver upload at top is {driver_upload}')
        #print(f'taskon at top is {taskon}')

        if genre == 'Planning':
            for filter in table_filters:
                for key, value in filter.items():
                    tfilters[key] = request.values.get(key)
                    #print('planner filter set 1', key, tfilters[key])
            dlist = table_filters[0]['Date Filter']

            pdio, pdip, pdeo, pdep, busdays, pdic, pdec, pmon, userchange, do = create_cal_data(tfilters, dlist, username, resetmod)

            if not userchange:
                pdio, pdip, pdeo, pdep, reupdate = update_calendar_form(pdio, pdip, pdeo, pdep)
                if resetmod is None:
                    err.append(f'User {username} has control of calendar data')
                else:
                    err.append(f'User {username} now has control of calendar data')
            else:
                reupdate = 0
                if resetmod is None:
                    err.append('Another User Has Charge of Calendar Data')
                    err.append('Hit Reset Calendar to Take Ownership of Modifications')
                else:
                    err.append(f'User {username} now has control of calendar data')

            if reupdate:
                pdio, pdip, pdeo, pdep, busdays, pdic, pdec, pmon, userchange, do = create_cal_data(tfilters, dlist, username, resetmod)

            if task_iter == 0:
                pdiovec, pdipvec, pdeovec, pdepvec, jolist = get_calendar_checks(pdio, pdip, pdeo, pdep)
                #print(f'Starting POST of genre {genre} with view of jolist: {jolist}')
            else:
                jolist = []
                for jp in range(1, 5):
                    jox = f'jo{jp}'
                    jo = request.values.get(jox)
                    if jo is not None: jolist.append(jo)

                #print(f'Starting POST of genre {genre} with return of jolist: {jolist}')
                pdiovec, pdipvec, pdeovec, pdepvec = initialize_calendar_checks(pdio, pdip, pdeo, pdep, jolist)
            # Set Orders table to checks used in calendar whether or not the Order table is on...
            checked_data = cal_to_orders(jolist, checked_data)



        #print(f'Method is POST with tasktype {tasktype}, taskon {taskon}, task_focus {task_focus}, task_iter {task_iter}')

        #Gather filter settings to keep them set as desired


        returnhit = request.values.get('Return')
        if returnhit is not None:
            #print('Resetting tables from Table_maker')
            # Asked to reset, so reset values as if not a Post (except the table filters which will be kept)
            jscripts, taskon, task_iter, task_focus, tboxes, viewport = reset_state_soft(task_boxes)

            ###############Testing this###########
            genre_tables_on = checked_tables(genre_tables)
            tables_on = [ix for jx, ix in enumerate(genre_tables) if genre_tables_on[jx] == 'on']

            for filter in table_filters:
                for key, value in filter.items(): tfilters[key] = request.values.get(key)

            if 'Orders' in tables_on: table_filters[0]['Shipper Filter'] = get_custlist('Orders', tfilters)
            pdiovec, pdipvec, pdeovec, pdepvec = [[], [], [], [], [], []], [[], [], [], [], [], []], [[], [], [], [], [], []], [[], [], [], [], [], []]

        else:

            taskon = nononestr(taskon)
            #print(f'Return hit is none so task continues with task tasktype:{tasktype}, taskon:{taskon}, task_focus:{task_focus}, task_iter:{task_iter}')

            # Get data only for tables that have been checked on and not specialized
            # However, we must convert the calendar into the order data if using the calendar.
            genre_tables_on = checked_tables(genre_tables)
            tables_on = [ix for jx, ix in enumerate(genre_tables) if genre_tables_on[jx] == 'on']
            if genre == 'Planning':
                if 'Orders' not in tables_on: tables_on.append('Orders')

            #print(f'The tables on: {tables_on} with task {taskon}')

            # Only check the launch boxes, filters, and task selections if no task is running
            if not hasinput(taskon):
                # See if a new task has been launched from quick buttons; set launched to New/Mod/Inv/Ret else set launched to None
                launched = [ix for ix in quick_buttons if request.values.get(ix) is not None]
                taskbase = launched[0] if launched != [] else None
                if taskbase:
                    tasklist = task_box_map['Quick'][taskbase]
                    tasktype = tasklist[0]
                    taskon, task_focus = tasklist[1:]

                # See if a task box has been selected, if so get task name, type, and focus
                for box in task_boxes:
                    for key, value in box.items():
                        tboxes[key] = request.values.get(key)
                        if tboxes[key] is not None:
                            tasklist = task_box_map[key][tboxes[key]]
                            tasktype = tasklist[0]
                            taskon, task_focus = tasklist[1:]

                #print('The task is:', taskon)
                #print('The task focus is:', task_focus)
                #print('The task_iter is:', task_iter)

            # See if a table filter has been selected, this can take place even during a task
            for filter in table_filters:
                for key, value in filter.items():
                    tfilters[key] = request.values.get(key)
            if 'Orders' in tables_on: table_filters[0]['Shipper Filter'] = get_custlist('Orders', tfilters)

            #Reset Pay and Haul Filters if Show All selected (no filter applied)
            if 'Pay Filter' in tfilters:
                if tfilters['Pay Filter'] == 'Show All': tfilters['Pay Filter'] = None
            if 'Haul Filter' in tfilters:
                if tfilters['Haul Filter'] == 'Show All': tfilters['Haul Filter'] = None
            if 'Shipper Filter' in tfilters:
                if tfilters['Shipper Filter'] == 'Show All': tfilters['Shipper Filter'] = None
            if 'Color Filter' in tfilters:
                if tfilters['Color Filter'] == 'Haul' or tfilters['Color Filter'] == 'Invoice':
                    #Provide filter consistency: if an invoice filter is selected make sure invoice colors are shown:
                    if tfilters['Pay Filter'] is not None and tfilters['Color Filter'] == 'Haul': tfilters['Color Filter'] = 'Both'
                    #Provide filter consistency: if an haul filter is selected make sure haul colors are shown:
                    if tfilters['Haul Filter'] is not None and tfilters['Color Filter'] == 'Invoice': tfilters['Color Filter'] = 'Both'
                    # Reset colors for color filter in primary table:
                    # eval(f"{genre}_genre['table_filters']['Color filters")

                if tfilters['Color Filter'] == 'Haul':
                    Orders_setup['colorfilter'] = ['Hstat']
                    #Newjobs_setup['colorfilter'] = ['Hstat']
                elif tfilters['Color Filter'] == 'Invoice':
                    Orders_setup['colorfilter'] = ['Istat']
                elif tfilters['Color Filter'] == 'Both':
                    Orders_setup['colorfilter'] = ['Hstat', 'Istat']



    #First time thru (not a Post) below#########################################################
    else:
        username = session['username'].capitalize()
        genre_tables_on = ['off'] * len(genre_tables)
        genre_tables_on[0] = 'on'
        tables_on = [eval(f"{genre}_genre['table']")]

        #These two session variables control the table defaults. Each time table turned on it sets default
        #session['table_defaults'] = tables_on
        #session['table_removed'] = []
        # Default time filter on entry into table is last 60 days:
        tfilters = {'Shipper Filter': None, 'Date Filter': 'Last 45 Days', 'Pay Filter': None, 'Haul Filter': None, 'Color Filter': 'Both', 'Viewer': '8x4'}
        jscripts = ['dtTrucking']
        taskon, task_iter, task_focus, tasktype = None, None, None, None
        if 'Orders' in tables_on: table_filters[0]['Shipper Filter'] = get_custlist('Orders', tfilters)

        if genre == 'Planning':
            #print(f'Executing the Calendar first time thru....')
            tfilters = {'Shipper Filter': None, 'Date Filter': 'This Week', 'Pay Filter': None, 'Haul Filter': None,
                        'Color Filter': 'Both', 'Viewer': '8x4'}
            # holdvec[100] = [pdio, pdip, pdeo, pdep, pdiovec, pdipvec, pdeovec, pdepvec, busdays]
            dlist = table_filters[0]['Date Filter']
            pdio, pdip, pdeo, pdep, busdays, pdic, pdec, pmon, userchange, do = create_cal_data(tfilters, dlist, username, resetmod)
            if not userchange:
                pdio, pdip, pdeo, pdep, reupdate = update_calendar_form(pdio, pdip, pdeo, pdep)
                if resetmod is None:
                    err.append(f'User {username} has control of calendar data')
                else:
                    err.append(f'User {username} now has control of calendar data')
            else:
                reupdate = 0
                if resetmod is None:
                    err.append('Another User Has Charge of Calendar Data')
                    err.append('Hit Reset Calendar to Take Ownership of Modifications')
                else:
                    err.append(f'User {username} now has control of calendar data')


            if reupdate: pdio, pdip, pdeo, pdep, busdays, pdic, pdec, pmon, userchange, do = create_cal_data(tfilters, dlist, username, resetmod)
            pdiovec, pdipvec, pdeovec, pdepvec = [[], [], [], [], [], []], [[], [], [], [], [], []], [[], [], [], [], [], []], [[], [], [], [], [], []]
            jolist = []

###########All done in this section##################################################################################################################
    # Execute these parts whether it is a Post or Not:
    # genre_data = [genre,genre_tables,genre_tables_on,contypes]
    genre_data = eval(f"{genre}_genre")
    genre_data['genre_tables_on'] = genre_tables_on

    #Apply shortcut for filters for various tasks
    current_view = tfilters['Viewer']
    if invoicehit is not None: tfilters = {'Shipper Filter': None, 'Date Filter': 'Last 60 Days', 'Pay Filter': 'Unsent', 'Haul Filter': 'Completed', 'Color Filter': 'Both', 'Viewer':current_view}

    # Populate the tables that are on with data
    tabletitle, table_data, checked_data, jscripts, keydata, labpassvec = populate(tables_on,tabletitle,tfilters,jscripts)
    if genre == 'Planning': checked_data = cal_to_orders(jolist, checked_data)

    # Remove the checks during reset of tables
    if resethit is not None or resetmod is not None:
        for check in checked_data:  check[2] = []
        pdiovec, pdipvec, pdeovec, pdepvec = [[], [], [], [], [], []], [[], [], [], [], [], []], [[], [], [], [], [],[]], [[], [], [], [], [], []]

    # Execute the task here if a task is on...,,,,
    if hasvalue(taskon):
        holdvec, entrydata, err, completed, viewport, tablesetup = run_the_task(genre, taskon, task_focus, tasktype, task_iter, checked_data, err)
        if completed:
            # If complete set the task on to none
            taskon = None
            if tables_on == []:
                genre_tables_on, tables_on, jscripts, taskon, task_iter, task_focus, tboxes, viewport, tfilters = reset_state_hard(task_boxes, genre_tables)
                genre_data = eval(f"{genre}_genre")
                genre_data['genre_tables_on'] = genre_tables_on
            else:
                #print(f'ongoing task: the tables on are: {tables_on} with task {taskon}')
                jscripts, taskon, task_iter, task_focus, tboxes, viewport = reset_state_soft(task_boxes)

            if genre == 'Planning':
                # If the tesk is completed and we never left the calendar then keep the checks we used
                #Reset the calendar
                dlist = table_filters[0]['Date Filter']
                pdio, pdip, pdeo, pdep, busdays, pdic, pdec, pmon, userchange, do = create_cal_data(tfilters, dlist, username, resetmod)
                if not userchange:
                    pdio, pdip, pdeo, pdep, reupdate = update_calendar_form(pdio, pdip, pdeo, pdep)
                    if resetmod is None:
                        err.append(f'User {username} has control of calendar data')
                    else:
                        err.append(f'User {username} now has control of calendar data')
                else:
                    reupdate = 0
                    if resetmod is None:
                        err.append('Another User Has Charge of Calendar Data')
                        err.append('Hit Reset Calendar to Take Ownership of Modifications')
                    else:
                        err.append(f'User {username} now has control of calendar data')

                if reupdate: pdio, pdip, pdeo, pdep, busdays, pdic, pdec, pmon, userchange, do = create_cal_data(tfilters, dlist, username, resetmod)
                pdiovec, pdipvec, pdeovec, pdepvec, jolist = get_calendar_checks(pdio, pdip, pdeo, pdep)

            tabletitle, table_data, checked_data, jscripts, keydata, labpassvec = populate(tables_on, tabletitle, tfilters, jscripts)
        else:
            #print(f'On task_iter {task_iter} keydata is {keydata}')
            task_iter = int(task_iter) + 1




            # Need to pick up some of the keydata after table build
            if checked_data != [] and checked_data is not None:
                if checked_data[0][0] == 'Orders':
                    keydata = get_Orders_keydata(keydata, checked_data)

    elif driver_upload is not None:
        print(f'driver upload is: {driver_upload}')
        tabletitle, table_data, checked_data, jscripts, keydata, labpassvec = populate(tables_on, tabletitle, tfilters, jscripts)
        holdvec, entrydata, err, viewport, completed = run_driver_upload(checked_data, driver_upload)
        taskon = None
        task_iter = 1
        tasktype = ''
        #holdvec = [''] * 150
        #print(f'labpassvec is {labpassvec}')
        #entrydata = []
        #err = ['All is well']
        tablesetup = None
        print(viewport)

    elif truck_upload is not None:
        print(f'Truck upload is: {truck_upload}')
        tabletitle, table_data, checked_data, jscripts, keydata, labpassvec = populate(tables_on, tabletitle, tfilters, jscripts)
        holdvec, entrydata, err, viewport, completed = run_truck_upload(checked_data, truck_upload)
        taskon = None
        task_iter = 1
        tasktype = ''
        #holdvec = [''] * 150
        #print(f'labpassvec is {labpassvec}')
        #entrydata = []
        #err = ['All is well']
        tablesetup = None
        print(viewport)


    else:
        taskon = None
        task_iter = 0
        tasktype = ''
        holdvec = [''] * 150
        #print(f'labpassvec is {labpassvec}')
        entrydata = []
        #err = ['All is well']
        tablesetup = None

    #print(jscripts, holdvec)

    if returnhit is not None:
        checked_data = [0,'0',['0']]

    if len(holdvec)<101: holdvec = holdvec + ['']*(101-len(holdvec))
    checkcol = [eval(f"{ix}_setup['checklocation']") for ix in tables_on]
    holdvec[98] = checkcol
    holdvec[99] = labpassvec
    holdvec[97] = f'/static/{scac}/data/v'
    timedata = ['06:00-07:00', '07:00-08:00', '08:00-09:00', '09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:30']
    #print(f"holdvec is {holdvec} and session variable is {session['table_defaults']}")
    #print(f"The session variables for tables Default {session['table_defaults']} and Removed {session['table_removed']}")

    putbuff = request.values.get('Paste Buffer')
    thisdate = datetime.datetime.today()
    thisdate = thisdate.date()
    movedate = thisdate
    #print(thisdate, thisdate.weekday())
    holdvec[96] = []
    holdvec[94] = [Drivers.query.filter(Drivers.Active == 1).all(),Vehicles.query.filter(Vehicles.Active == 1).all()]
    anyamber = 0
    for idate in range(4):
        boxid = []
        addnow = request.values.get(f'add{idate}')
        modnow = request.values.get(f'mod{idate}')
        delthis = request.values.get(f'del{idate}')
        moveup = request.values.get(f'moveup{idate}')
        movedn = request.values.get(f'movedn{idate}')
        movedate = thisdate + timedelta(idate)
        if modnow is not None or delthis is not None or moveup is not None or movedn is not None or addnow is not None:
            anyamber = 1
            default_unit = None
            pdata = Pins.query.filter(Pins.Date == movedate).all()
            for jx, pdat in enumerate(pdata):
                driver = request.values.get(f'drv{idate}{jx}')
                unit = request.values.get(f'unit{idate}{jx}')
                chas = request.values.get(f'chas{idate}{jx}')
                box = request.values.get(f'box{idate}{jx}')
                timeslot = request.values.get(f'slot{idate}{jx}')

                #print(f'this time slot is read as {timeslot}')
                if box == 'on':
                    boxid.append(pdat.id)
                #print(f'box is {box} {boxid}')

                if driver is not None:
                    #print(f'The selected driver is {driver}')
                    pdat.Driver = driver
                    ddat = Drivers.query.filter(Drivers.Name == driver).first()
                    if ddat is not None:
                        pdat.Phone = ddat.Phone
                        default_unit = ddat.Truck
                        #pdat.Unit = default_unit

                if unit is not None:
                    #print(f'The selected unit is {unit}')
                    pdat.Unit = unit
                    if unit != default_unit:
                        pdat.Carrier = f'Warning: Unit {unit} is not driver default {default_unit}'
                    else:
                        pdat.Carrier = None
                    vdat = Vehicles.query.filter(Vehicles.Unit == unit).first()
                    if vdat is not None:
                        pdat.Tag = vdat.Plate

                if chas is not None:
                    #print(f'The selected chassis is {chas}')
                    pdat.InChas = chas
                    pdat.OutChas = chas

                if timeslot is not None:
                    #pdat.Timeslot = int(timeslot)
                    pdat.Timeslot = timeslot

                if driver is not None and unit is not None and chas is not None:
                    pdat.Notes = f'Will get pin for {driver} in unit {unit} using chassis {chas}'
                    if default_unit is not None:
                        if unit != default_unit: pdat.Notes = pdat.Notes + f' **Warning this not default truck for driver'
                db.session.commit()
        else:
            pdata = Pins.query.filter(Pins.Date == movedate).all()
            for jx, pdat in enumerate(pdata):
                copythis = request.values.get(f'copy{idate}{jx}')
                if copythis is not None:
                    itext = pdat.Intext
                    otext = pdat.Outtext
                    note = pdat.Notes
                    holdvec[95] = f'{itext}\n{otext}\n{note}'

        #Perform moveup or movedn actions
        for tid in boxid:
            #print(f'Performing action on id= {tid}')
            if delthis is not None:
                Pins.query.filter(Pins.id == tid).delete()
                db.session.commit()
            if moveup is not None:
                pdat = Pins.query.get(tid)
                pdat.Date = pdat.Date - timedelta(1)
                db.session.commit()
            if movedn is not None:
                pdat = Pins.query.get(tid)
                pdat.Date = pdat.Date + timedelta(1)
                db.session.commit()

        holdvec[96].append([movedate, f'{idate}', Pins.query.filter(Pins.Date == movedate).all(), timedata])

    if (putbuff is not None or anyamber) and 'Orders' in tables_on:
        holdvec[96] = []
        #print(f'Doing the paste buffer for {checked_data} {tables_on}')
        sids = checked_data[0][2]
        if sids != []:
            if len(sids) <= 2:
                if len(sids) == 2:
                    #Determine which to do first
                    sid1, sid2 = sids[0], sids[1]
                    odat1 = Orders.query.get(sid1)
                    odat2 = Orders.query.get(sid2)
                    hstat1 = odat1.Hstat
                    hstat2 = odat2.Hstat
                    if hstat1 is None: hstat1 = -1
                    if hstat2 is None: hstat2 = -1
                    if hstat1 > hstat2:
                        indat = odat1
                        outdat = odat2
                    else:
                        indat = odat2
                        outdat = odat1

                    for idate in range(4):
                        addnow = request.values.get(f'add{idate}')
                        movedate = thisdate + timedelta(idate)
                        if addnow is not None:
                            #print(f'Adding the dispatch selection to date {movedate}')
                            addtopins(movedate, [indat,outdat])
                    holdvec[95] = f'{get_dispatch(indat)}\n{get_dispatch(outdat)}'
                else:
                    sid = sids[0]
                    odat = Orders.query.get(sid)
                    holdvec[95] = get_dispatch(odat)
                    for idate in range(4):
                        addnow = request.values.get(f'add{idate}')
                        movedate = thisdate + timedelta(idate)
                        if addnow is not None:
                            #print(f'Adding the dispatch selection to date {movedate}')
                            addtopins(movedate,[odat])
            else:
                err.append('Too many selections for paste buffer task')
        for idate in range(4):
            movedate = thisdate + timedelta(idate)
            holdvec[96].append([movedate, f'{idate}', Pins.query.filter(Pins.Date == movedate).all(), timedata])
        else:
            err.append('No selection made for paste buffer task')
    leftcheck = tfilters['Viewer']
    if leftcheck == '7x5': leftsize = 7
    if leftcheck == '8x4': leftsize = 8
    if leftcheck == '9x3': leftsize = 9
    if leftcheck == '10x2': leftsize = 10
    if leftcheck == 'Top-Bot': leftsize = 12

    #print(f'Leftsize on exit is {leftsize}')
    err = erud(err)


    holdvec[80] = request.values.get('showcolorstable')

    if genre == 'Planning':
        #print(f'The length of holdvec is {len(holdvec)}')
        #print(f'Sending over jolist = {jolist}')
        cal_labels = []
        for bday in busdays:
            bdat = PortClosed.query.filter(PortClosed.Date == bday).first()
            if bdat is None: cal_labels.append(bday)
            else: cal_labels.append(bdat.Reason)
        holdvec[100] = [pdio, pdip, pdeo, pdep, pdiovec, pdipvec, pdeovec, pdepvec, cal_labels, jolist, pdic, pdec, pmon, do]
        #print(f'Holdvec[100] = {holdvec[100]}')

    #print(checked_data)


    return genre_data, table_data, err, leftsize, tabletitle, table_filters, task_boxes, tfilters, tboxes, jscripts,\
    taskon, task_focus, task_iter, tasktype, holdvec, keydata, entrydata, username, checked_data, viewport, tablesetup

def tswap(tname, tflip, highfilter_value):
    tflip1 = tflip[0]
    tflip2 = tflip[1]
    labpass = tflip1[0]
    reverse = request.values.get(f'{tname}{tflip1[0]}')
    if reverse is not None:
        highfilter_value = tflip1[1]
        labpass = tflip2[0]
    nextreverse = request.values.get(f'{tname}{tflip2[0]}')
    if nextreverse is not None:
        highfilter_value = tflip2[1]
        labpass = tflip1[0]
    return labpass, highfilter_value

def get_dbdata(table_setup, tfilters):
    today = datetime.date.today()
    thisyear = today.year
    lastyear = thisyear - 1
    yearblast = thisyear - 2
    #print(thisyear,lastyear)
    query_adds = []
    table = table_setup['table']
    tname = table_setup['name']
    #print(table)
    highfilter = table_setup['filter']
    #print(highfilter)
    highfilter_value = table_setup['filterval']
    entrydata = table_setup['entry data']
    filteron = table_setup['filteron']
    #print(entrydata)
    color_selector = table_setup['colorfilter']
    #print(f' For table {table} the color selector is {color_selector}')
    labpass = None

    boxchecks = []
    try:
        simpler = table_setup['simplify']
        boxlist = []
    except:
        simpler = []

    #print(f"Critical Point {table} Removed:{session['table_removed']}")
    #if table not in session['table_removed']:
    if simpler != []:
        for box in simpler:
            thischeck = request.values.get(f'{box}box')
            boxchecks.append(thischeck)
            if thischeck == 'on': boxlist.append(box)
        #Do this if needing to use default values
        #If nothing on then turn 3 on
        if boxlist == []:
            boxchecks = ['off'] * len(simpler)
            boxchecks[0:3] = ['on','on','on']
            boxlist = simpler[0:3]
    else: boxchecks, boxlist = [], []


    # Apply built-in table filter:
    if highfilter is not None:
        logic = table_setup['filter logic']
        tflip = table_setup['button flip']
        if tflip is not None: labpass, highfilter_value = tswap(tname, tflip, highfilter_value)
        query_adds.append(f"{table}.{highfilter} {logic} '{highfilter_value}'")

    # If this table has no color capability then it cannot be filtered by date or type
    #print(f'the color_selector is {color_selector}')
    if color_selector is not None:
        # Determine if time filter applies to query:
        if 'Date Filter' in tfilters:
            dtest = tfilters['Date Filter']
            if dtest is not None and dtest != 'Show All' and 'Date' in filteron:
                daysback = None
                fromdate = None
                todate = None
                if '30' in dtest: daysback = 30
                elif '45' in dtest: daysback = 45
                elif '90' in dtest: daysback = 90
                elif '180' in dtest: daysback = 180
                elif '360' in dtest: daysback = 360
                elif dtest == 'Year Before Last':
                    fromdate = datetime.date(yearblast,1,1)
                    todate = datetime.date(yearblast,12,31)
                elif dtest == 'Last Year':
                    fromdate = datetime.date(lastyear,1,1)
                    todate = datetime.date(lastyear,12,31)
                elif dtest == 'This Year':
                    fromdate = datetime.date(thisyear,1,1)
                else:
                    daysback = 45
                if daysback is not None: fromdate = today - datetime.timedelta(days=daysback)
                if fromdate is not None: query_adds.append(f'{table}.Date >= fromdate')
                if todate is not None: query_adds.append(f'{table}.Date <= todate')
                #print(f'This time filter applied from fromdate = {fromdate} to todate = {todate}')
            elif 'Date' in filteron:
                daysback = 45
                if daysback is not None: fromdate = today - datetime.timedelta(days=daysback)
                if fromdate is not None: query_adds.append(f'{table}.Date >= fromdate')

        elif 'Date' in filteron:
            daysback = 45
            if daysback is not None: fromdate = today - datetime.timedelta(days=daysback)
            if fromdate is not None: query_adds.append(f'{table}.Date >= fromdate')


        # Determine if pay filter applies to query:
        if 'Pay Filter' in tfilters:
            itest = tfilters['Pay Filter']
            if itest is not None and itest != 'Show All' and 'Invoice' in filteron:
                if itest == 'Uninvoiced':
                    pfilter = f'({table}.Istat == None)  | ({table}.Istat < 1)'
                elif itest == 'Unrecorded':
                    pfilter = f'{table}.Istat == 1'
                elif itest == 'Unsent':
                    pfilter = f'({table}.Istat == None)  | ({table}.Istat < 3)'
                elif itest == 'Unpaid':
                    pfilter = f'{table}.Istat != 5'
                elif itest == 'InvoSummaries':
                    pfilter = f'{table}.Istat > 5'
                query_adds.append(pfilter)

        # Determine if haul filter applies to query:
        if 'Haul Filter' in tfilters:
            htest = tfilters['Haul Filter']
            if htest is not None and htest != 'Show All' and 'Haul' in filteron:
                if htest == 'Not Started':
                    hfilter = f'{table}.Hstat == 0'
                elif htest == 'In-Progress':
                    hfilter = f'{table}.Hstat == 1'
                elif htest == 'Incomplete':
                    hfilter = f'{table}.Hstat < 2'
                elif htest == 'Completed':
                    hfilter = f'{table}.Hstat >= 2'
                query_adds.append(hfilter)

        #print(f'the tfilters are: {tfilters}, and filteron is {filteron}')
        if 'Shipper Filter' in tfilters:
            stest = tfilters['Shipper Filter']
            if stest is not None and stest != 'Show All' and 'Shipper' in filteron:
                sfilter = f"{table}.Shipper.contains('{stest}')"
                query_adds.append(sfilter)

    # Determine if haul filter applies to query:
    if 'Driver Filter' in tfilters:
        htest = tfilters['Driver Filter']
        if htest is not None and htest != 'All Drivers' :
            hfilter = f"{table}.DriverStart == '{htest}'"
            query_adds.append(hfilter)
    #print(tfilters, query_adds)
    # Put the filters together from the 3 possible pieces: time, type1, type2
    if query_adds == []:
        table_query = f'{table}.query.all()'
    elif len(query_adds) == 1:
        table_query = f'{table}.query.filter({query_adds[0]}).all()'
    elif len(query_adds) == 2:
        table_query = f'{table}.query.filter(({query_adds[0]}) & ({query_adds[1]})).all()'
    elif len(query_adds) == 3:
        table_query = f'{table}.query.filter(({query_adds[0]}) & ({query_adds[1]}) & ({query_adds[2]})).all()'
    elif len(query_adds) == 4:
        table_query = f'{table}.query.filter(({query_adds[0]}) & ({query_adds[1]}) & ({query_adds[2]})  & ({query_adds[3]})).all()'
    elif len(queery_adds) == 5:
        table_query = f'{table}.query.filter(({query_adds[0]}) & ({query_adds[1]}) & ({query_adds[2]})  & ({query_adds[3]}) & ({query_adds[4]})).all()'

    odata = eval(table_query)

    # Determine color pallette to apply to table
    rowcolors1 = []
    rowcolors2 = []
    data1id = []
    data1 = []
    for odat in odata:
        data1id.append(odat.id)
        datarow = [0] * len(entrydata)
        if color_selector is not None:
            for kx, selector in enumerate(color_selector):
                color_selector_value = getattr(odat, selector)
                #print(f'for {odat.Jo} color selector value is {color_selector_value} on selector {selector} and kx={kx}')
                #print(f'table is {table}')
                if kx == 0: rowcolors1.append(colorcode(table, color_selector_value))
                if kx == 1: rowcolors2.append(colorcode(table, color_selector_value))
        else:
            color_selector_value = 0
            rowcolors1.append(colorcode(table, color_selector_value))
            rowcolors2.append(colorcode(table, color_selector_value))

        for jx, colist in enumerate(entrydata):
            co = colist[0]
            datarow[jx] = getattr(odat, co)
            if colist[8] is not None:
                eltest = f'{datarow[jx]}'
                #print(f'eltest {eltest} and colist is {colist[8]}')
                if len(eltest) > colist[8]: datarow[jx] = eltest[0:colist[8]]
        data1.append(datarow)

    if color_selector is not None:
        if len(color_selector) == 1: rowcolors2 = rowcolors1

    #print(f'the rowcolors1 are {rowcolors1}')
    #print(f'the rowcolors2 are {rowcolors2}')

    return [data1, data1id, rowcolors1, rowcolors2, entrydata, simpler, boxchecks, boxlist], labpass

def get_new_Jo(input):
    sdate = today.strftime('%Y-%m-%d')
    return newjo(input, sdate)


def make_new_entry(tablesetup,holdvec):
    table = tablesetup['table']
    entrydata = tablesetup['entry data']
    masks = tablesetup['haulmask']
    try:
        defaults = tablesetup['defaults']
    except:
        defaults = False
    id = None
    if masks != []: entrydata = mask_apply(entrydata, masks, None)
    try:
        hiddendata = tablesetup['hidden data']
    except:
        hiddendata = []
    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    creators = tablesetup['creators']
    ukey = tablesetup['ukey']
    documents = tablesetup['documents']
    #print(f'filter={filter},filterval={filterval}')
    if 'Source' in documents:
        sourcekeys = tablesetup['sourcenaming']
        if sourcekeys[0] is not None: basename = sourcekeys[0]
        else: basename = None
        postfix = sourcekeys[1]
        keyfinds = sourcekeys[2:]
    else:
        sourcekeys = None

    err = []
    #err = ['No Jo Created']
    from sqlalchemy import inspect
    inst = eval(f"inspect({table})")
    attr_names = [c_attr.key for c_attr in inst.mapper.column_attrs]

    for jx,entry in enumerate(entrydata):
        if entry[0] in creators:
            creation = [ix for ix in creators if ix == entry[0]][0]
            holdvec[jx] = eval(f"get_new_{creation}('{entry[3]}')")
            #err = [f'New {creation} {holdvec[jx]} created']

    #print('The attr_names are:',attr_names)
    #for c_attr in inst.mapper.column_attrs:
        #print('Attrloop:',c_attr)

    dbnew = f'{table}('
    for col in attr_names:
        if col != 'id':
            if col == ukey:
                uidtemp = uuid.uuid1().node
                dbnew = dbnew + f", {col}='{uidtemp}'"
            elif col == filter: dbnew = dbnew + f", {col}='{filterval}'"
            else: dbnew = dbnew + f', {col}=None'
    dbnew = dbnew + ')'
    dbnew = dbnew.replace('(, ', '(')
    print('class8_tasks.py 338 make_new_entry() Making new database entry using phrase:',dbnew)
    input = eval(dbnew)
    db.session.add(input)
    db.session.commit()

    newquery = f"{table}.query.filter({table}.{ukey} == '{uidtemp}').first()"
    #print('Getting the new temp entry:',newquery)
    dat = eval(newquery)
    if dat is not None:
        id = dat.id
        form_show = tablesetup['form show']['New']
        for jx,entry in enumerate(entrydata):
            if entry[4] is not None and (entry[9] == 'Always' or entry[9] in form_show):
                #print(f'Data going in is:{entry[0]} {holdvec[jx]}')
                setattr(dat, f'{entry[0]}', holdvec[jx])
        db.session.commit()
        for jx, entry in enumerate(hiddendata):
                thisvalue = getattr(dat, entry[2])
                try:
                    thisvalue = thisvalue.splitlines()
                    thissubvalue = thisvalue[0]
                except:
                    thissubvalue = ''
                setattr(dat, f'{entry[0]}', thissubvalue)
        db.session.commit()
        if defaults:
            for jx, entry in enumerate(defaults):
                    #print(f'setting {entry[0]} to {entry[1]}')
                    setattr(dat, f'{entry[0]}', entry[1])
            db.session.commit()
        #err.append(f"Updated entry in {tablesetup['table']}")

        if sourcekeys is not None:
            nextquery = f"{table}.query.get({id})"
            dat = eval(nextquery)
            #print('Check to see if we need to save a source document:')
            docsave = request.values.get('viewport2')
            #newile already set at top of routine to the base name for document
            #print(f'dirloc is {dirloc}')
            keyval = getattr(dat, keyfinds[0])
            if len(keyfinds)==2:
                keyval2 =  getattr(dat, keyfinds[1])
                keyval = f'{keyval}_{keyval2}'
            keyval = keyval.upper()
            keyval = keyval.replace(' ','_')
            if basename is not None: keyval = f'{basename}_{keyval}'
            if postfix is not None:
                newfile = f'{keyval}_{postfix}.pdf'
            else:
                newfile = f'{keyval}.pdf'

            if hasinput(docsave):
                newpath = addpath(tpath(table, newfile))
                oldpath = addpath(docsave).replace('//','/')
                #print('Need to move file from', oldpath, ' to', newpath)
                try:
                    shutil.move(oldpath, newpath)
                    #print(f'Moved file {oldpath} to {newpath}')
                except:
                    pass
                    #print('File already moved')
                # Test to see if file exists
                if not os.path.isfile(newpath): newfile = None

                #print(f'Setting Source attribute for New Entry in Table {table} with ID {id} to {newfile}')
                setattr(dat, 'Source', newfile)
                setattr(dat, 'Scache', 0)
                db.session.commit()

    return err, id

#def New_task(task_iter, tablesetup, task_focus, checked_data):
def mask_apply(entrydata, masks, ht):
    mask_to_apply = request.values.get('HaulType')
    if mask_to_apply is None:
        mask_to_apply = ht
    #print(f'The final mask being applied is: {mask_to_apply}')
    list = Trucking_genre['haul_types']
    if mask_to_apply in list:
        #print(f'the list is {list}')
        this_index = list.index(mask_to_apply)
        #print(f'the index is {this_index}')
        for jx, entry in enumerate(entrydata):
            #print(jx,entry[3],entry[4])
            if 'Release' in entry[1]:
                mask = masks['release']
                entrydata[jx][2] = mask[this_index]
            if 'Container' in entry[1]:
                mask = masks['container']
                entrydata[jx][2] = mask[this_index]
            if 'In-Book' in entry[1]:
                mask = masks['inbook']
                entrydata[jx][2] = mask[this_index]
            if 'Terminal' in entry[1]:
                mask = masks['load1']
                entrydata[jx][2] = mask[this_index]
            if 'Deliver To' in entry[1]:
                mask = masks['load2']
                entrydata[jx][2] = mask[this_index]
            if 'Load Date' in entry[1]:
                mask = masks['load1date']
                #print(f'Mask {entry[1]}, {this_index} {mask}')
                entrydata[jx][2] = mask[this_index]
                #print(f'Mask {entry[2]}')
            if 'Del Date' in entry[1]:
                mask = masks['load2date']
                entrydata[jx][2] = mask[this_index]
            if 'Third Location' in entry[1]:
                mask = masks['load3']
                entrydata[jx][2] = mask[this_index]
                #print(f'Third Location Mask {entry[2]} mask here is:{mask} and this_index is {this_index} and overwriting entry[jx][2] as {mask[this_index]}')
            if 'Third Date' in entry[1]:
                mask = masks['load3date']
                entrydata[jx][2] = mask[this_index]
            if 'ERD/APP' in entry[1]:
                mask = masks['date4']
                entrydata[jx][2] = mask[this_index]
            if 'Cut/LFD' in entry[1]:
                mask = masks['date5']
                entrydata[jx][2] = mask[this_index]
            if 'Ship Arrive' in entry[1]:
                mask = masks['date6']
                entrydata[jx][2] = mask[this_index]
            if 'Chassis' in entry[1]:
                mask = masks['chassis']
                entrydata[jx][2] = mask[this_index]

        entrydata = [v for v in entrydata if v[2] != 'no']
    return entrydata

def check_appears(tablesetup, entry, htold):
    checks = tablesetup['appears_if']
    testval = entry[4]
    testmat = checks[testval]
    ht = request.values.get(testval)
    if ht is None: ht = htold
    #print(f'*******************************It should appear if {testval}, {ht}, in {testmat}')
    if any(ht in x for x in testmat):
        #print('It should appear')
        colmat = checks[entry[0]]
        havedat = request.values.get(testval)
        if havedat is not None:
            for test in testmat:
                if test in havedat:
                    #print(f'test:{test}, havedat:{havedat}, colmat:{colmat}, entry3: {entry[3]}, entry4: {entry[4]}')
                    return colmat
        return entry[3], entry[4]
    else:
        #Reset to original table data
        return entry[3], entry[4]

def UpdatePlanner_task(tablesetup, task_iter):
    completed = True
    holdvec = [''] * 60
    err = [f"Running UpdatePlanner task with task_iter {task_iter} using {tablesetup['table']}"]
    form_show = tablesetup['form show']['New']
    form_checks = tablesetup['form checks']['New']
    #print(f'Entering UpdatePlanner Task with task iter {task_iter}')
    entrydata = tablesetup['entry data']
    # Set some date criteria:
    today = datetime.datetime.today()
    today = today.date()
    cutoff = today - timedelta(7)
    cuthigh = today + timedelta(7)
    tomorrow = today + timedelta(1)
    lookbackto = today - timedelta(30)


    # Add jobs from the Orders database that are not in the planner:
    odata = Orders.query.filter((Orders.Hstat < 2) & (Orders.Date > lookbackto)).all()
    for odat in odata:
        jo = odat.Jo
        #print(f'Looking for jo {jo}')
        ndat = Newjobs.query.filter(Newjobs.Jo == jo).first()
        if ndat is None:
            # Need to add this order to the newjobs data.
            #print(odat.Source, odat.Company, odat.Company2)
            input = Newjobs(Status=1, Jo=jo, Shipper=odat.Shipper, HaulType=odat.HaulType, Release=odat.Booking,
                            Bookingin=None, Container=odat.Container,
                            Type=odat.Type, Pickup=odat.Company, Delivery=odat.Company2, Ship=None, Date=odat.Date,
                            Date2=odat.Date2, Date3=None,
                            Date4=None, Date5=None, Date6=None, Date7=None, Time2='', Time3=None, Source=odat.Source,
                            Portbyday=None,
                            Scache=odat.Scache, Pcache=0, Truck=odat.Truck, Driver=odat.Driver, Hstat=odat.Hstat,
                            SSL=None, Changes='')
            db.session.add(input)
            db.session.commit()
            #print(f'Added Jo {jo} to Newjobs')


    ndata = Newjobs.query.filter(Newjobs.Status<8).all()
    for ndat in ndata:
        jo = ndat.Jo
        status = ndat.Status
        ship = ndat.Ship
        ht = ndat.HaulType
        sdat = Ships.query.filter(Ships.Ship == ship).first()
        if sdat is None:
            ndat.Status = 0
        else:
            win1 = ndat.Date3
            win2 = ndat.Date4

            odat = Orders.query.filter(Orders.Jo == jo).first()
            if odat is not None:
                ndat.Hstat = odat.Hstat
                hstat = odat.Hstat
            # Now push the planning along
            ts = -1
            if sdat is not None: ts = 0
            # Check if delivery set:
            del_date = ndat.Date2
            del_time = ndat.Time2
            if del_date is not None and del_time is not None:
                if ts == 0: ts = 1

            if 'Import' in ht:
                shiparrival = sdat.Date
                ndays = shiparrival - today
                ndays = ndays.days
                #print(f'Today is {today} and the ship arrives {shiparrival} which is in {ndays} days')
                if ndays < 3: #ship arrives within 3 days
                    ts = 2
                if win1 is not None:
                    ndays1 = win1 - today
                    ndays1 = ndays1.days
                    if ndays1 <= 0: ts = 3
                if win2 is not None:
                    ndays2 = win2 - today
                    ndays2 = ndays2.days
                    if ndays2 <= 0: ts = 4
                if del_date is not None and del_time is not None:
                    if ts == 3: ts = 5 #Both active and planned delivery date
                    if ts == 4 and hstat > 0: ts = 5
                proof = odat.Proof
                if proof is not None and hstat == 1: ts = 6
                if hstat == 1:
                    #check to see how long container out
                    pulled = odat.Date
                    ndays3 = pulled - today
                    ndays3 = ndays3.days
                    if ndays3 <= 0: ts = 7
                if hstat > 1 and proof is not None: ts = 8

            if 'Export' in ht:
                if win1 is not None:
                    ndays1 = win1 - today
                    ndays1 = ndays1.days
                    if ndays1 > 4: ts = 1
                    elif ndays1 > 0: ts = 2
                    elif ndays1 <= 0: ts = 3
                if win2 is not None:
                    ndays2 = win2 - today
                    ndays2 = ndays2.days
                    if ndays2 <= 0: ts = 4
                if del_date is not None and del_time is not None:
                    if ts == 3: ts = 5 #Both active and planned delivery date
                    if ts == 4 and hstat > 0: ts = 5
                proof = odat.Proof
                if proof is not None and hstat == 1: ts = 6
                if hstat == 1:
                    #check to see how long container out
                    pulled = odat.Date
                    ndays3 = pulled - today
                    ndays3 = ndays3.days
                    if ndays3 <= 0: ts = 7
                if hstat > 1 and proof is not None: ts = 8

        ndat.Status = ts
        db.session.commit()

    return holdvec, entrydata, err, completed




def New_task(tablesetup, task_iter):
    completed = False
    itable = tablesetup['table']
    err = [f"Running New task with task_iter {task_iter} using {itable}"]
    form_show = tablesetup['form show']['New']
    form_checks = tablesetup['form checks']['New']
    #print(f'Entering New Task with task iter {task_iter} and itable: {itable}')
    htold = ''

    cancelnow = request.values.get('Cancel')
    if cancelnow is not None:
        entrydata = tablesetup['entry data']
        masks = tablesetup['haulmask']
        if masks != []: entrydata = mask_apply(entrydata, masks, htold)
        numitems = len(entrydata)
        holdvec = [''] * numitems
        completed = True
    else:

        if task_iter > 0:
            if itable == 'Orders':
                htold = request.values.get('HaulType')
                #print(f'htold for orders is {htold}')
            elif itable == 'Interchange':
                htold = request.values.get('Type')
                #print(f'htold for interchange is {htold}')
            if htold is None: htold = ''

            entrydata = tablesetup['entry data']
            masks = tablesetup['haulmask']
            #print(f'Entering Masks with htold: {htold}')
            if masks != []: entrydata = mask_apply(entrydata, masks, htold)
            #print(entrydata)
            numitems = len(entrydata)
            holdvec = [''] * (numitems+1)
            failed = 0
            warned = 0

            noterminals = ['OTR', 'Box Truck', 'Transload Only', 'Transload-Deliver']
            secterminal = ['Dray Import 2T', 'Dray Export 2T']
            secstop = ['Import Extra Stop', 'Export Extra Stop']
            if htold in secterminal:
                secterm = 1
            else:
                secterm = 0
            if htold in noterminals:
                noterm = 1
            else:
                noterm = 0
            if htold in secstop:
                secst = 1
            else:
                secst = 0
            #print(f'In new task, htold:{htold} secterm: {secterm} noterm: {noterm} secstop: {secst}')
            holdvec[numitems] = [secterm, noterm, secst]

            for jx, entry in enumerate(entrydata):
                #print(f'Entry loop: jx"{jx}, entry[0]:{entry[0]}, htold:{htold}, entry[3]:{entry[3]}, entry[4]:{entry[4]}')

                if entry[3] == 'appears_if':
                    #print(f'We have an appears_if check for entry[0] = {entry[0]} with entry3:{entry[3]}, entry4:{entry[4]} and entry[9]:{entry[9]} and form_show is {form_show} and htold={htold}')
                    entry[3], entry[4] = check_appears(tablesetup, entry, htold)
                    entrydata[jx][3],entrydata[jx][4] = entry[3], entry[4]
                    #print(f'On return from check appears: entry[3]={entry[3]} and entry[4]={entry[4]}')

                if entry[4] is not None and (entry[9] == 'Always' or entry[9] in form_show):
                    if entry[1] != 'hidden':
                        holdvec[jx] = request.values.get(f'{entry[0]}')
                        if entry[0] in form_checks: required = True
                        else: required = False
                        #print(f'New Task entry[0]={entry[0]}, {entry[1]}, {entry[4]}, holdvec[jx] = {holdvec[jx]}')
                        holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], 'New', required, task_iter, htold,0, itable)
                        #print(f'After call to form_check: holdvec[jx] = {holdvec[jx]}, entry[5]={entry[5]} and entry[6]={entry[6]}')
                        if entry[5] > 1: failed = failed + 1
                        if entry[5] == 1: warned = warned + 1

            if 'bring data' in tablesetup:
                for bring in tablesetup['bring data']:
                    tab1, sel, tab2, cat, colist1, colist2 = bring
                    #print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
                    valmatch = request.values.get(sel)
                    #print(valmatch)
                    escript = f'{tab2}.query.filter({tab2}.{cat} == valmatch).first()'
                    adat = eval(escript)
                    if adat is not None:
                        for jx, col in enumerate(colist1):
                            thisval = getattr(adat, col)
                            for ix, entry in enumerate(entrydata):
                                if entry[0] == colist2[jx]:
                                    holdvec[ix] = thisval

            err.append(f'There are {failed} input errors and {warned} input warnings')


            create_item = request.values.get('Create Item')
            if create_item is not None:
                if failed == 0:
                    err,sid = make_new_entry(tablesetup,holdvec)
                    err.append(f"Created new entry in {tablesetup['table']}")
                    completed = True
                    if tablesetup['table'] == 'Orders':
                        #print(f'Updating Orders with {sid}')
                        Order_Addresses_Update(sid)
                        err = Order_Container_Update(sid, err)
                    if tablesetup['table'] == 'Interchange':
                        Gate_Update(sid)
                    if tablesetup['table'] == 'Bills':
                        bdat = Bills.query.filter(Bills.id>0).order_by(Bills.id.desc()).first()
                        if bdat is not None:
                            pdat = People.query.filter(People.Company == bdat.Company).first()
                            if pdat is not None:
                                bid = bdat.id
                                bdat.Pid = pdat.id
                                db.session.commit()
                                bdat = Bills.query.get(bid)
                            err = gledger_write(['newbill'], bdat.Jo, bdat.bAccount, bdat.pAccount, 0)
                else:
                    err.append(f'Cannot create entry until input errors shown in red below are resolved')

        else:
            holdvec = [''] * 60
            entrydata = tablesetup['entry data']
            for jx, entry in enumerate(entrydata):
                if entry[0] in form_checks: required = True
                else: required = False
                holdvec[jx], entry[5], entry[6] = form_check(entry[0],holdvec[jx], entry[4], 'New', required, task_iter, htold, 0, itable)
                #*#print(f'Entry loop: jx"{jx}, entry:{entry[0]} {entry[5]} {entry[6]} {required}')


    return holdvec, entrydata, err, completed


def Edit_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):
    itable = tablesetup['table']
    err = [f"Running Edit task with task_iter {task_iter} using {itable}"]
    completed = False
    viewport = ['0'] * 6
    #print(f'1993 Running Edit task with task_iter {task_iter} using {itable}')

    table = tablesetup['table']
    entrydata = tablesetup['entry data']

    nextquery = f"{table}.query.get({sid})"
    olddat = eval(nextquery)
    try:
        htold = olddat.HaulType
    except:
        htold = ''

    #print(f'htold is {htold}')

    if task_iter > 0:
        if itable == 'Orders':
            htold = request.values.get('HaulType')
            #print(f'htold edit task for orders is {htold}')
        elif itable == 'Interchange':
            htold = request.values.get('Type')
            #print(f'htold edit task for interchange is {htold}')

    noterminals = ['OTR', 'Box Truck', 'Transload Only', 'Transload-Deliver']
    secterminal = ['Dray Import 2T', 'Dray Export 2T']
    secstop = ['Import Extra Stop', 'Export Extra Stop']
    if htold in secterminal:
        secterm = 1
    else:
        secterm = 0
    #print(f'sectorm is {secterm}')
    if htold in noterminals:
        noterm = 1
    else:
        noterm = 0
    if htold in secstop:
        secst = 1
    else:
        secst = 0
    #print(f'In edit task, htold:{htold} secterm: {secterm} noterm: {noterm} secstop: {secst}')



    masks = tablesetup['haulmask']
    #print(f'masks is {masks}')
    if masks != []:
        entrydata = mask_apply(entrydata, masks, htold)
        #print(f'After mask applied entrydata is: {entrydata}')
    hiddendata = tablesetup['hidden data']
    numitems = len(entrydata)
    holdvec = [''] * (numitems + 1)
    holdvec[numitems] = [secterm, noterm, secst]
    #print(f'Holdvec is: {holdvec}')


    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    colorcol = tablesetup['colorfilter']
    creators = tablesetup['creators']  # Gather the data for the selected row

    form_show = tablesetup['form show']['Edit']
    form_checks = tablesetup['form checks']['Edit']

    #print('')
    #print(f'*********************************************************************')
    #print(f'***Running edit with task_iter {task_iter} and old data is {htold}***')
    #print(f'*********************************************************************')

    if task_iter > 0:
        failed = 0
        warned = 0

        for jx, entry in enumerate(entrydata):
            #print(f'Running entry {entry}')
            if entry[3] == 'appears_if':
                entry[3], entry[4] = check_appears(tablesetup, entry, htold)
                entrydata[jx][3],entrydata[jx][4] = entry[3], entry[4]
                #print(f'We have an appears_if check with entry3:{entry[3]}, entry4:{entry[4]}, entry9:{entry[9]}, formshow:{form_show}')
            #print(f'Getting values for entry4:{entry[4]} entry9:{entry[9]} formshow:{form_show}')
            if entry[4] is not None and (entry[9] == 'Always' or entry[9] in form_show):
                # Some items are part of bringdata so do not test those - make sure entry[4] is None for those
                holdvec[jx] = request.values.get(f'{entry[0]}')
                if entry[0] in form_checks: required = True
                else: required = False
                #print(f'holdvec[jx] going in is {holdvec[jx]}')
                holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], 'Edit', required, task_iter, htold, sid, itable)
                if entry[5] > 1: failed = failed + 1
                if entry[5] == 1: warned = warned + 1
                #print(f'Entry[0] is {entry[0]} and value is {holdvec[jx]} and entry[4] is {entry[4]}')

        if 'bring data' in tablesetup:
            for bring in tablesetup['bring data']:
                tab1, sel, tab2, cat, colist1, colist2 = bring
                #print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
                valmatch = request.values.get(sel)
                #print(valmatch)
                escript = f'{tab2}.query.filter({tab2}.{cat} == valmatch).first()'
                adat = eval(escript)
                if adat is not None:
                    for jx, col in enumerate(colist1):
                        thisval = getattr(adat, col)
                        for ix, entry in enumerate(entrydata):
                            if entry[0] == colist2[jx]:
                                holdvec[ix] = thisval
                                #print(f'Moving value {thisval} from {tab2} {col} to {table} {colist2[jx]}')

        err.append(f'There are {failed} input errors and {warned} input warnings')

        update_item = request.values.get('Update Item')
        if update_item is not None:
            try:
                thisvalue = getattr(olddat, colorcol[0])
                if thisvalue == -1: setattr(olddat, colorcol[0], 0)
            except:
                thisvalue = 0

            if failed == 0:
                for jx, entry in enumerate(entrydata):
                    if entry[4] is not None and (entry[9] == 'Always' or entry[9] in form_show):
                        if entry[0] not in creators:
                            #print(f'Setting entry {entry[0]} to {holdvec[jx]}')
                            setattr(olddat, f'{entry[0]}', holdvec[jx])
                db.session.commit()
                for jx, entry in enumerate(hiddendata):
                    thisvalue = getattr(olddat,entry[2])
                    try:
                        thisvalue = thisvalue.splitlines()
                        thissubvalue = thisvalue[0]
                    except:
                        thissubvalue = ''
                    #print('Updating Entry with', entry[0], thissubvalue)
                    setattr(olddat, f'{entry[0]}', thissubvalue)
                db.session.commit()
                # The amount could change on a bill, so if a bill need to update
                if table == 'Bills':
                    bdat = eval(nextquery)
                    err = gledger_write(['newbill'], bdat.Jo, bdat.bAccount, bdat.pAccount, 0)
                if table == 'Orders':
                    #print(f'Updating Orders with {sid}')
                    Order_Addresses_Update(sid)
                    err = Order_Container_Update(sid, err)
                if table == 'Interchange':
                    Gate_Update(sid)
                #err.append(f"Updated entry in {tablesetup['table']}")
                completed = True

                # Test of bring data-modify the database at this point
                if 'bring data' in tablesetup:
                    for bring in tablesetup['bring data']:
                        tab1, sel, tab2, cat, colist1, colist2 = bring
                        #print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
                        valmatch = request.values.get(sel)
                        #print(valmatch)
                        escript = f'{tab2}.query.filter({tab2}.{cat} == valmatch).first()'
                        #print(escript)
                        adat = eval(escript)
                        if adat is not None:
                            for jx, col in enumerate(colist1):
                                thisval = getattr(adat, col)
                                setattr(olddat, colist2[jx], thisval)
                                #print(f'Moving value {thisval} from {tab2} {col} to {table} {colist2[jx]}')
                            db.session.commit()
                    #olddat = eval(nextquery)
                    #for jx, entry in enumerate(entrydata): holdvec[jx] = getattr(olddat, f'{entry[0]}')
            else:
                err.append(f'Cannot update entry until input errors shown in red below are resolved')

        cancel_item = request.values.get('Cancel')
        if cancel_item is not None:
            #print('Canceling the edit')
            completed = True

    else:

        for jx, entry in enumerate(entrydata):
            if entry[3] == 'appears_if': entrydata[jx][3], entrydata[jx][4] = check_appears(tablesetup, entry, htold)
            holdvec[jx] = getattr(olddat, f'{entry[0]}')

            if entry[0] in form_checks: required = True
            else: required = False
            holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], 'Edit', required, task_iter, htold, sid, itable)
            #print(f'Entry[0] is {entry[0]} and value is {holdvec[jx]}')


    try:
        docref = getattr(olddat, 'Source')
    except:
        docref = None
    if docref is not None:
        viewport[0] = 'show_doc_left'
        viewport[2] = '/' + tpath(f'{table}', docref)

    return holdvec, entrydata, err, viewport, completed


def Status_task(genre, task_focus, task_iter, nc, tids, tabs):
    #print(f'Running Status Task with genre={genre}, task_iter={task_iter}, task_focus = {task_focus}')
    for jx, thistable in enumerate(tabs):
        tablesetup = eval(f'{thistable}_setup')
        table = tablesetup['table']
        #print('table', table)
        for sid in tids[jx]:
            rstring = f'{table}.query.get({sid})'
            odat = eval(rstring)
            if 'Haul' in task_focus:
                try:
                    nstat = odat.Hstat
                    valid = 1
                except:
                    nstat = 0
                    valid = 0
                if valid:
                    if nstat == None: nstat = 0
                    if task_focus == 'Haul+1':
                        if nstat+1 < 5: odat.Hstat = nstat+1
                    if task_focus == 'Haul-1':
                        if nstat-1 > -1: odat.Hstat = nstat-1
                    if task_focus == 'Haul Done': odat.Hstat = 3
            if 'Inv' in task_focus:
                nstat = odat.Istat
                if nstat == None: nstat = 0
                if task_focus == 'Inv+1':
                    if nstat+1 < 5: odat.Istat = nstat+1
                if task_focus == 'Inv-1':
                    if nstat-1 > -1: odat.Istat = nstat-1
                if task_focus == 'Inv Emailed': odat.Istat = 3
                if task_focus == 'Inv Paid': odat.Istat = 8

            if 'Date' in task_focus:
                nstat = odat.Date3
                if isinstance(nstat, datetime.date):
                    if task_focus == 'Date+1':
                        odat.Date3 = nstat + datetime.timedelta(days=1)
                    if task_focus == 'Date-1':
                        odat.Date3 = nstat - datetime.timedelta(days=1)

    db.session.commit()
    holdvec, entrydata, err = [], [], []
    viewport = ['0'] * 6
    completed = True


    return holdvec, entrydata, err, viewport, completed

def Undo_task(genre, task_focus, task_iter, nc, tids, tabs):
    err = []
    #print(f'Running Undo Task with genre={genre}, task_iter={task_iter}, task_focus = {task_focus}, tids= {tids} tabs= {tabs}')
    for jx, thistable in enumerate(tabs):
        tablesetup = eval(f'{thistable}_setup')
        table = tablesetup['table']

        #Convert to allow on single item undo:
        if len(tids[jx]) > 1:
            err.append('Too Many Selections')
        else:
            for sid in tids[jx]:
                err.append(f'Working on single item {sid}')
                if task_focus == 'Delete':
                    #print('made it here with jx, thistable sid', jx, thistable, sid)
                    rstring = f'{table}.query.filter({table}.id == {sid}).delete()'
                    eval(rstring)
                    db.session.commit()
                elif task_focus == 'Invoice':
                    # Need to add the undo of the journal entries
                    rstring = f'{table}.query.get({sid})'
                    odat = eval(rstring)

                    invoice = addpath(tpath(f'{thistable}-Invoice',odat.Invoice))
                    package = addpath(tpath(f'{thistable}-Package',odat.Package))
                    try:
                        os.remove(invoice)
                    except:
                        err.append(f'File {odat.Invoice} not found')
                    try:
                        os.remove(package)
                    except:
                        err.append(f'File {odat.Package} not found')

                    odat.Invoice = None
                    odat.Package = None
                    odat.Istat = 0
                    odat.Links = None
                    odat.BalDue = None
                    odat.InvoTotal = None
                    odat.Payments = '0.00'
                    db.session.commit()
                    Invoices.query.filter(Invoices.Jo == odat.Jo).delete()
                    #Income.query.filter(Income.Jo == odat.Jo).delete()
                    Gledger.query.filter(Gledger.Tcode == odat.Jo).delete()
                    db.session.commit()

                elif table == 'Orders' and task_focus == 'Payment':
                    rstring = f'{table}.query.get({sid})'
                    odat = eval(rstring)
                    refid = odat.QBi
                    sinow = odat.Label
                    if sinow is not None:
                        slead = SumInv.query.filter((SumInv.Si == sinow) & (SumInv.Status > 0)).first()
                        odata = Orders.query.filter(Orders.Label == sinow).all()
                        olen = len(odata)
                    else:
                        olen = 0
                        slead = None

                    if refid is not None:
                        pdata = Orders.query.filter(Orders.QBi == refid).all()
                        plen = len(pdata)
                    else:
                        plen = 0

                    if olen == 1 or plen == 1:
                        odat.Istat = 3
                        if odat.Hstat == 5:
                            odat.Hstat = 3
                        odat.PaidInvoice = None
                        odat.PayRef = None
                        odat.PayMeth = None
                        odat.PayAcct = None
                        odat.PaidDate = None
                        odat.PaidAmt = None
                        odat.Payments = '0.00'
                        odat.QBi = None
                        odat.BalDue = odat.InvoTotal
                        db.session.commit()
                        jo = odat.Jo
                        idata = Invoices.query.filter(Invoices.Jo == jo).all()
                        for data in idata:
                            data.Status = 'New'
                        db.session.commit()
                        if refid is not None:
                            PaymentsRec.query.filter(PaymentsRec.id == refid).delete()
                        Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'IC')).delete()
                        Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'ID')).delete()
                        Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'DD')).delete()
                        db.session.commit()

                    elif plen > 1:

                        if refid is not None:
                            PaymentsRec.query.filter(PaymentsRec.id == refid).delete()

                        if slead is not None:
                            slead.Status = 2

                        for each in pdata:
                            each.Istat = 3
                            if each.Hstat == 5:
                                each.Hstat = 3

                            each.PaidInvoice = None
                            each.PayRef = None
                            each.PayMeth = None
                            each.PayAcct = None
                            each.PaidDate = None
                            each.PaidAmt = None
                            each.QBi = None
                            each.Payments = None
                            each.BalDue = each.InvoTotal
                            jo = each.Jo
                            idata = Invoices.query.filter(Invoices.Jo == jo).all()
                            for data in idata:
                                data.Status = 'New'
                            Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'IC')).delete()
                            Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'ID')).delete()
                            Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'DD')).delete()
                        db.session.commit()

                    elif olen > 1:

                        if refid is not None:
                            PaymentsRec.query.filter(PaymentsRec.id == refid).delete()

                        for each in odata:
                            each.PaidInvoice = None
                            each.PayRef = None
                            each.PayMeth = None
                            each.PayAcct = None
                            each.PaidDate = None
                            each.PaidAmt = None
                            each.Istat = 6
                            each.QBi = None
                            each.Payments = None
                            each.BalDue = each.InvoTotal
                            if each.Hstat == 5:
                                each.Hstat = 3

                            jo = each.Jo
                            idata = Invoices.query.filter(Invoices.Jo == jo).all()
                            for data in idata:
                                data.Status = 'New'
                            Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'IC')).delete()
                            Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'ID')).delete()
                            Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'DD')).delete()
                        slead.Status = 2
                        db.session.commit()



                elif table == 'Bills' and task_focus == 'Payment':
                    #print('In the unpay bill section')
                    rstring = f'{table}.query.get({sid})'
                    odat = eval(rstring)
                    if odat is not None:
                        if odat.Status == 'Paid':
                            check = odat.Check
                            pacctlist = odat.PacctList
                            if pacctlist is None: multi = False
                            else: multi = True
                            if multi:
                                kill_list = eval(pacctlist)
                                for k in kill_list:
                                    kdat = Bills.query.get(k)
                                    kdat.Status = None
                                    kdat.PmtList = None
                                    kdat.PacctList = None
                                    kdat.Pmulti = None
                                    kdat.PAmount2 = None
                                    jo = kdat.Jo
                                    Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'PD')).delete()
                                    Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'PC')).delete()
                            else:
                                odat.Status = None
                                jo = odat.Jo
                                Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'PD')).delete()
                                Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'PC')).delete()


                    db.session.commit()

                elif table == 'Orders' and (task_focus == 'Docs' or task_focus == 'DocsNotSource' or task_focus == 'xProof' or task_focus == 'yProof' or task_focus == 'xRateCon' or task_focus == 'xDrvProof' or task_focus == 'xDrvSeal'):
                    rstring = f'{table}.query.get({sid})'
                    odat = eval(rstring)
                    source = addpath(tpath(f'{thistable}-Source',odat.Source))
                    proof = addpath(tpath(f'{thistable}-Proof',odat.Proof))
                    proof2 = addpath(tpath(f'{thistable}-Proof', odat.Proof2))
                    drvproof = addpath(tpath(f'{thistable}-Proof', odat.DrvProof))
                    drvseal = addpath(tpath(f'{thistable}-Proof', odat.DrvSeal))
                    ratecon = addpath(tpath(f'{thistable}-RateCon', odat.RateCon))
                    manifest = addpath(tpath(f'{thistable}-Manifest',odat.Manifest))
                    gate = addpath(tpath(f'{thistable}-Gate',odat.Gate))
                    invoice = addpath(tpath(f'{thistable}-Invoice',odat.Invoice))
                    package = addpath(tpath(f'{thistable}-Package',odat.Package))
                    #print(f'task focus is {task_focus} and proof2 is {proof2}')

                    if task_focus == 'xProof':
                        try:
                            os.remove(proof)
                        except:
                            err.append(f'File {odat.Proof} not found')
                        #print(f'Setting Proof for sid {sid} with value {odat.Proof} to None')
                        odat.Proof = None
                        db.session.commit()
                    elif task_focus == 'yProof':
                        try:
                            os.remove(proof2)
                        except:
                            err.append(f'File {odat.Proof2} not found')
                        #print(f'Setting Proof for sid {sid} with value {odat.Proof} to None')
                        odat.Proof2 = None
                        db.session.commit()
                    elif task_focus == 'xRateCon':
                        try:
                            os.remove(ratecon)
                        except:
                            err.append(f'File {odat.RateCon} not found')
                        #print(f'Setting Proof for sid {sid} with value {odat.Proof} to None')
                        odat.RateCon = None
                        db.session.commit()

                    elif task_focus == 'xDrvProof':
                        try:
                            os.remove(drvproof)
                        except:
                            err.append(f'File {odat.DrvProof} not found')
                        #print(f'Setting Proof for sid {sid} with value {odat.Proof} to None')
                        odat.DrvProof = None
                        db.session.commit()

                    elif task_focus == 'xDrvSeal':
                        try:
                            os.remove(drvseal)
                        except:
                            err.append(f'File {odat.DrvSeal} not found')
                        #print(f'Setting Proof for sid {sid} with value {odat.Proof} to None')
                        odat.DrvSeal = None
                        db.session.commit()

                    else:

                        if task_focus == 'Docs':
                            try:
                                os.remove(source)
                            except:
                                err.append(f'File {odat.Source} not found')

                        try:
                            os.remove(proof)
                        except:
                            err.append(f'File {odat.Proof} not found')

                        try:
                            os.remove(manifest)
                        except:
                            err.append(f'File {odat.Manifest} not found')

                        try:
                            os.remove(gate)
                        except:
                            err.append(f'File {odat.Gate} not found')

                        try:
                            os.remove(ratecon)
                        except:
                            err.append(f'File {odat.RateCon} not found')

                        try:
                            os.remove(invoice)
                        except:
                            err.append(f'File {odat.Invoice} not found')
                        try:
                            os.remove(package)
                        except:
                            err.append(f'File {odat.Package} not found')

                        try:
                            os.remove(drvproof)
                        except:
                            err.append(f'File {odat.DrvProof} not found')

                        try:
                            os.remove(drvseal)
                        except:
                            err.append(f'File {odat.DrvSeal} not found')

                        if task_focus == 'Docs':  odat.Source = None
                        odat.Proof = None
                        odat.Manifest = None
                        odat.Gate = None
                        odat.RateCon = None
                        odat.Invoice = None
                        odat.Package = None
                        odat.Proof2 = None
                        odat.DrvProof = None
                        odat.DrvSeal = None
                        db.session.commit()


    holdvec, entrydata = [], []
    viewport = ['0'] * 6
    completed = True


    return holdvec, entrydata, err, viewport, completed


def View_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):
    #print(f'Running View Task with genre={genre}, task_iter={task_iter}, task_focus = {task_focus}, sid={sid}')
    cancel = request.values.get('cancel')
    viewport = ['0'] * 6
    holdvec = []
    entrydata = []
    table = tablesetup['table']

    if cancel is not None:
        completed = True
    else:
        completed = False
        err = [f'Running View task with iter {task_iter}']

        nextquery = f"{table}.query.get({sid})"
        dat = eval(nextquery)

        #print('The task focus is:', task_focus)
        try:
            docref = getattr(dat, f'{task_focus}')
            tpointer = f'{table}-{task_focus}'
            #print(f'Viewing for table: {table} and focus {task_focus}')
            try:
                viewport[0] = 'show_doc_left'
                viewport[2] = '/' + tpath(f'{tpointer}', docref)
                #print(f'path director:{tpointer} and path found:{viewport[2]}')
                err.append(f'Viewing {viewport[2]}')
                err.append('Hit Return to End Viewing and Return to Table View')
            except:
                completed = True
                err.append(f'Selection has no {task_focus} document')
        except:
            completed = True
            err.append(f'{table} has no attribute {task_focus}')

        returnhit = request.values.get('Return')
        if returnhit is not None: completed = True

    return holdvec, entrydata, err, viewport, completed



def Upload_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):

    cancel = request.values.get('cancel')
    viewport = ['0'] * 6
    holdvec = []
    entrydata = []
    #table = tablesetup['table']

    if cancel is not None:
        completed=True
        err = ['Upload has been cancelled']
    else:
        completed = False
        err = [f'Running Upload task with iter {task_iter} table {thistable} and focus {task_focus}']


        if task_iter == 0:
            viewport[0] = 'upload_doc_right'
        else:
            viewport[0] = request.values.get('viewport0')
            viewport[2] = request.values.get('viewport2')

        nextquery = f"{thistable}.query.get({sid})"
        dat = eval(nextquery)

        try:
            getattr(dat, f'{task_focus}')
        except:
            err.append(f'{thistable} has no attribute {task_focus}')
            completed = True

        if not completed:

            viewport[3] = str(sid)
            viewport[4] = f'{genre} {thistable} Item'
            ukey = eval(f"{thistable}_setup['ukey']")
            #print('the ukey=', ukey)
            directedpart = eval(f"dat.{ukey}")
            #viewport[5] = ukey + ': ' + eval(f"dat.{ukey}")
            viewport[5] = f'{ukey}: {directedpart}'
            #fileout = ukey + '_' + eval(f"dat.{ukey}")
            fileout = f'{ukey}_{directedpart}'
            #print(f'Fileout:{fileout} ukey:{ukey}')

            uploadnow = request.values.get('uploadnow')

            if uploadnow is not None:
                viewport[0] = 'show_doc_right'
                file = request.files['docupload']
                if file.filename == '':
                    err.append('No file selected for uploading')

                name, exto = os.path.splitext(file.filename)
                ext = exto.lower()
                if task_focus == 'Source':
                    sname = 'Scache'
                elif task_focus == 'Proof':
                    sname = 'Pcache'
                elif task_focus == 'TitleDoc':
                    sname = 'Tcache'
                elif task_focus == 'RateCon':
                    sname = 'Rcache'
                elif task_focus == 'Proof2':
                    sname = 'Pcache2'

                if thistable == 'Orders':
                    sn = getattr(dat, sname)
                    try:
                        sn = int(sn)
                        bn = sn+1
                    except:
                        sn = 0
                        bn = 0

                    filename1 = f'{task_focus}_{fileout}_c{str(bn)}{ext}'
                    output1 = addpath(tpath(f'{thistable}-{task_focus}', filename1))
                    #print(f'output1 for thistable {thistable}-{task_focus} = {output1}')

                if thistable == 'Interchange':
                    bn = 0
                    con = dat.Container
                    type = dat.Type
                    type = type.upper()
                    type = type.replace(' ','_')
                    filename1 = f'{con}_{type}{ext}'
                    output1 = addpath(tpath(f'{thistable}-{task_focus}', filename1))
                    #print(f'output1 for thistable {thistable}-{task_focus} = {output1}')


                file.save(output1)
                viewport[2] = '/'+tpath(f'{thistable}-{task_focus}', filename1)

                if bn > 0:
                    if thistable == 'Orders':
                        oldfile = f'{task_focus}_{fileout}_c{str(sn)}{exto}'
                        oldoutput = addpath(tpath(f'{thistable}-{task_focus}', oldfile))
                        #print(f'the old file is {oldfile}')

                        try:
                            os.remove(oldoutput)
                            err.append('Cleaning up old files successful')
                        except:
                            err.append('Cleaning up old files NOT successful')
                            err.append(f'Could not find {oldoutput}')

                setattr(dat, f'{task_focus}', filename1)
                if thistable == 'Orders': setattr(dat, sname, bn)
                if thistable == 'Interchange':
                    setattr(dat, sname, bn)
                    setattr(dat, 'Other', 'File Upload Manually')
                db.session.commit()
                err.append(f'Viewing {filename1}')
                err.append('Hit Return to End Viewing and Return to Table View')
                returnhit = request.values.get('Return')
                if returnhit is not None: completed = True

    return holdvec, entrydata, err, viewport, completed

def BlendGate_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):

    completed = False
    err = [f'Running Blend Gate task with iter {task_iter}']
    today = datetime.date.today()
    holdvec = []
    entrydata = []

    table = tablesetup['table']
    entrydata = tablesetup['entry data']
    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    colorcol = tablesetup['colorfilter']
    creators = tablesetup['creators']    # Gather the data for the selected row
    nextquery = f"{table}.query.get({sid})"
    odat = eval(nextquery)
    try:
        defaults = tablesetup['defaults']
    except:
        defaults = False

    from sqlalchemy import inspect
    inst = eval(f"inspect({table})")
    attr_names = [c_attr.key for c_attr in inst.mapper.column_attrs]
    ukey = tablesetup['ukey']
    documents = tablesetup['documents']
    viewport = None

    try:
        con = odat.Container
        jo = odat.Jo
    except:
        err.append('Could not find Container or Jo in the Order')
        return holdvec, entrydata, err, viewport, True
    if 1 == 1:
        idata = Interchange.query.filter(Interchange.Jo == jo).all()
        if idata:
            if len(idata) > 1:
                # Try to get a blended ticket
                con = idata[0].Container
                newdoc = f'static/{scac}/data/vGate/{con}_Blended.pdf'
                if os.path.isfile(addpath(newdoc)):
                    #print(f'{newdoc} exists already, removing and remaking the file')
                    err.append(f'{con}_Blended.pdf already exists, deleting and remaking the file')
                    os.remove(addpath(newdoc))
                g1 = addpath(f'static/{scac}/data/vGate/{idata[0].Source}')
                g2 = addpath(f'static/{scac}/data/vGate/{idata[1].Source}')
                note1 = idata[0].Other
                note2 = idata[1].Other
                if os.path.isfile(g1) and os.path.isfile(g2):
                    if note1 is not None or note2 is not None:
                        combine_ticks(g1, g2, addpath(newdoc))
                    else:
                        blendticks(g1, g2, addpath(newdoc))
                    odat.Gate = f'{con}_Blended.pdf'
                    db.session.commit()
                    err.append('Gate Blend Created and added Successfully')
                else:
                    if not os.path.isfile(g1):
                        err.append(f'Could not find file {g1}')
                    if not os.path.isfile(g2):
                        err.append(f'Could not find file {g2}')
    if 1 == 2:
        err.append('Could not create blended ticket')

    return holdvec, entrydata, err, viewport, True


def quote_strip(tv):
    tvitems = tv.split('+')
    tvnew = tvitems[0]
    for ei in tvitems[1:]:
        if 'dd' not in ei and 'rd' not in ei:
            tvnew = f'{tvnew}+{ei}'
    return tvnew



def NewCopy_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):

    completed = False
    err = [f'Running NewCopy task with iter {task_iter}']
    today = datetime.date.today()
    holdvec = []
    entrydata = []

    table = tablesetup['table']
    entrydata = tablesetup['entry data']
    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    colorcol = tablesetup['colorfilter']
    creators = tablesetup['creators']    # Gather the data for the selected row
    nextquery = f"{table}.query.get({sid})"
    olddat = eval(nextquery)
    try:
        defaults = tablesetup['ncdefaults']
    except:
        defaults = False

    from sqlalchemy import inspect
    inst = eval(f"inspect({table})")
    attr_names = [c_attr.key for c_attr in inst.mapper.column_attrs]
    ukey = tablesetup['ukey']
    documents = tablesetup['documents']
    viewport = None

    #Swaps are to auto-change the copy to have compliment values to the original value
    #print('*******Running NewCopy_task************')
    swaps = tablesetup['copyswaps']
    ckswaps = [key for key, value in swaps.items()]


    # Get a new JO or other creator value required for a table (can be none)
    for jx, entry in enumerate(entrydata):
        if entry[0] in creators:
            creation = [ix for ix in creators if ix == entry[0]][0]
            thisitem = eval(f"get_new_{creation}('{entry[3]}')")
            err = [f'New {creation} {thisitem} created']
            #print(f'New {creation} {thisitem} created')

    # Gather the data for the selected row
    nextquery = f"{table}.query.get({sid})"
    olddat = eval(nextquery)

    from sqlalchemy import inspect
    inst = eval(f"inspect({table})")
    attr_names = [c_attr.key for c_attr in inst.mapper.column_attrs]

    # Create the new entry dynamically
    dbnew = f'{table}('
    for col in attr_names:
        if col != 'id':
            if col in creators:
                dbnew = dbnew + f", {col}='{thisitem}'"
            else:
                thisvalue = getattr(olddat, f'{col}')
                if col == colorcol[0]: thisvalue = -1
                # Check if thisvalue requires a compliment value
                if thisvalue in ckswaps:
                    thisvalue = swaps[thisvalue]
                #Special exemption for the Order Quote Builder, take out items that are just for one invoice
                if col == 'Quote':
                    if thisvalue is not None:
                        thisvalue = quote_strip(thisvalue)
                if defaults:
                    for thisdef in defaults:
                        if col in thisdef:  thisvalue = thisdef[1]
                if isinstance(thisvalue, numbers.Number): dbnew = dbnew + f", {col}={thisvalue}"
                # String requires the triple single quotes because of the container type 45'96" quotes
                elif isinstance(thisvalue, str): dbnew = dbnew + f", {col}='''{thisvalue}'''"
                elif isinstance(thisvalue, datetime.date): dbnew = dbnew + f", {col}=today"
                else: dbnew = dbnew + f", {col}=None"

    #Clean up db string for evaluation
    dbnew = dbnew + ')'
    dbnew = dbnew.replace('(, ', '(')
    input = eval(dbnew)
    db.session.add(input)
    db.session.commit()

    completed = True

    return holdvec, entrydata, err, viewport, completed


def New_Manifest_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):
    itable = tablesetup['table']
    err = [f"Running Manifest task with task_iter {task_iter} using {tablesetup['table']}"]
    completed = False
    viewport = ['0'] * 6
    container = ''
    city = 'Baltimore'

    table = tablesetup['table']
    entrydata = tablesetup['entry data']

    nextquery = f"{table}.query.get({sid})"
    modata = eval(nextquery)
    try:
        htold = modata.HaulType
    except:
        htold = 'temp'


    hiddendata = tablesetup['hidden data']
    numitems = len(entrydata)
    holdvec = [''] * 200
    masks = tablesetup['haulmask']
    if masks != []: entrydata = mask_apply(entrydata, masks, htold)

    form_checks = tablesetup['form checks']['Manifest']
    form_show = tablesetup['form show']['Manifest']

    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    creators = tablesetup['creators']  # Gather the data for the selected row



    returnhit = request.values.get('Finished')
    if returnhit is not None: completed = True
    else:
        if task_iter > 0:
            failed = 0
            warned = 0
            for jx, entry in enumerate(entrydata):
                if entry[3] == 'appears_if':
                    entry[3], entry[4] = check_appears(tablesetup, entry, htold)
                    entrydata[jx][3], entrydata[jx][4] = entry[3], entry[4]
                    #print(f'Return from check_appears is {entry[3]} and {entry[4]}')
                #print(f'Getting values for entry4:{entry[4]} entry9:{entry[9]} formshow:{form_show}')
                if entry[4] is not None and (entry[9] == 'Always' or entry[9] in form_show):
                    # Some items are part of bringdata so do not test those - make sure entry[4] is None for those
                    holdvec[jx] = request.values.get(f'{entry[0]}')
                    if entry[0] in form_checks: required = True
                    else: required = False
                    holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], 'Manifest', required, task_iter, htold, sid, itable)
                    if entry[5] > 1: failed = failed + 1
                    if entry[5] == 1: warned = warned + 1

                    if entry[0] == 'Container':  container = holdvec[jx]
                    if entry[0] == 'Dropblock2':
                        adata, backup = get_address_details(holdvec[jx])
                        try:
                            city = adata['city']
                        except:
                            city = backup

            if 'bring data' in tablesetup:
                for bring in tablesetup['bring data']:
                    tab1, sel, tab2, cat, colist1, colist2 = bring
                    #print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
                    valmatch = request.values.get(sel)
                    #print(valmatch)
                    escript = f'{tab2}.query.filter({tab2}.{cat} == valmatch).first()'
                    adat = eval(escript)
                    if adat is not None:
                        for jx, col in enumerate(colist1):
                            thisval = getattr(adat, col)
                            for ix, entry in enumerate(entrydata):
                                if entry[0] == colist2[jx]:
                                    holdvec[ix] = thisval
                                    #print(f'Moving value {thisval} from {tab2} {col} to {table} {colist2[jx]}')

            err.append(f'There are {failed} input errors and {warned} input warnings')

            update_item = request.values.get('Update Manifest')
            if update_item is not None:
                try:
                    thisvalue = getattr(modata, colorcol[0])
                    if thisvalue == -1: setattr(modata, colorcol[0], 0)
                except:
                    thisvalue = 0

                if failed == 0:
                    for jx, entry in enumerate(entrydata):
                        if entry[4] is not None and (entry[9] == 'Always' or entry[9] in form_show):
                            if entry[0] not in creators:
                                #print(f'Setting entry {entry[0]} to {holdvec[jx]}')
                                setattr(modata, f'{entry[0]}', holdvec[jx])
                    db.session.commit()
                    for jx, entry in enumerate(hiddendata):
                        thisvalue = getattr(modata, entry[2])
                        try:
                            thisvalue = thisvalue.splitlines()
                            thissubvalue = thisvalue[0]
                        except:
                            thissubvalue = ''
                        #print('Updating Entry with', entry[0], thissubvalue)
                        setattr(modata, f'{entry[0]}', thissubvalue)
                    db.session.commit()
                else:
                    err.append(f'Cannot update entry until input errors shown in red below are resolved')

        else:
            # Gather the data for the selected row
            nextquery = f"{table}.query.get({sid})"
            modata = eval(nextquery)

            for jx, entry in enumerate(entrydata):
                if entry[3] == 'appears_if': entrydata[jx][3], entrydata[jx][4] = check_appears(tablesetup, entry, htold)
                holdvec[jx] = getattr(modata, f'{entry[0]}')
                if entry[0] in form_checks: required = True
                else: required = False
                holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], 'Manifest', required, task_iter, htold, sid, itable)

                if entry[0] == 'Container':  container = holdvec[jx]
                if entry[0] == 'Dropblock2':
                    adata, backup = get_address_details(holdvec[jx])
                    try:
                        city = adata['city']
                    except:
                        city = backup

        docref = makemanifest(modata, tablesetup)
        try:
            modata.Mcache = int(modata.Mcache) + 1
            modata.Manifest = ntpath.basename(docref)
        except:
            modata.Mcache = 1
            modata.Manifest = ntpath.basename(docref)
        db.session.commit()


        viewport[0] = 'show_doc_left'
        viewport[2] = '/' + tpath(f'manifest', docref)
        #print('viewport=', viewport)

        err.append(f'Viewing {docref}')
        err.append('Hit Finished to End Viewing and Return to Table View')
        # The base name for the manifest is stored permanently, but a copy is created with a familiar name for the driver:

        if container is not None:
            fname=f'{container}_{city}.pdf'
            servercopy = addpath(viewport[2])
            tempview = f'/static/{scac}/data/vManifest/{fname}'
            tempcopy = addpath(tempview)
            holdvec[199] = fname
            #print(f'Will copy from {servercopy}')
            #print(f'Will copy to {tempcopy}')

        convert = request.values.get('Convert')
        if convert is not None:
            shutil.copy(servercopy,tempcopy)
            viewport[2] = tempview

        finished = request.values.get('Finished')
        if finished is not None: completed = True

    return holdvec, entrydata, err, viewport, completed

def get_company(eprof, odat):
    emaildata = ['']*9
    pdat = People.query.get(odat.Bid)
    if pdat is None:
        pdat = People.query.filter(People.Company == odat.Shipper).first()
    if pdat is not None:
        emaildata = etemplate_truck(eprof,odat)
        #emaildata = get_company_email(pdat)
    return emaildata

def get_stamps_from_form(doc_stamps, doc_signatures, odat):
    stamplist = []
    stampdata = []
    # Have to create numeric sequence to allow using stamps more than once
    for doc in doc_stamps:
        for ix in range(1,29):
            docnamed = doc + str(ix)
            thisdoc = request.values.get(docnamed)
            if thisdoc is not None:
                thischeck = thisdoc + '_c'
                checked = request.values.get(thischeck)
                if checked == 'on':
                    stamplist.append(thisdoc)
                    page = request.values.get(thisdoc + '_p')
                    up = request.values.get(thisdoc + '_h')
                    right = request.values.get(thisdoc + '_r')
                    scale = request.values.get(thisdoc + '_s')
                    stampdata = stampdata + [int(page), int(up), int(right), float(scale), checked, doc, thisdoc]
                else: break
    for doc in doc_signatures:
        for ix in range(1,29):
            docnamed = doc + str(ix)
            thisdoc = request.values.get(docnamed)
            if thisdoc is not None:
                thischeck = thisdoc + '_c'
                checked = request.values.get(thischeck)
                if checked == 'on':
                    stamplist.append(thisdoc)
                    page = request.values.get(thisdoc + '_p')
                    up = request.values.get(thisdoc + '_h')
                    right = request.values.get(thisdoc + '_r')
                    scale = request.values.get(thisdoc + '_s')
                    stampdata = stampdata + [int(page), int(up), int(right), float(scale), checked, doc, thisdoc]
                else: break

    adding_stamp = request.values.get('stampname')
    if adding_stamp != None:
        for jx in range(1,29):
            test = adding_stamp + str(jx)
            if test not in stamplist:
                stamplist.append(test)
                stampdata = stampdata + [1, 300, 200, .5, 'on', adding_stamp, test]
                break
    adding_sig = request.values.get('signame')
    if adding_sig != None:
        for jx in range(1,29):
            test = adding_sig + str(jx)
            if test not in stamplist:
                stamplist.append(test)
                stampdata = stampdata + [1, 300, 200, .5, 'on', adding_sig, test]
                break

    stampstring = json.dumps(stampdata)
    odat.Status = stampstring
    db.session.commit()
    return stamplist, stampdata

def get_last_used_stamps(odat):
    stamplist = []
    stampdata = []
    stampstring = odat.Status
    if isinstance(stampstring, str):
        try:
            stampdata = json.loads(stampstring)
            vlen = int(len(stampdata) / 7)
            for ix in range(vlen):
                if isinstance(stampdata[7 * ix + 6], str): stamplist.append(stampdata[7 * ix + 6])
        except:
            pass
            #print(f'String for stamp in this location is {stampstring} and not in json format')
    return stamplist, stampdata

def make_bool(input):
    if input is not None: return True
    else: return False

def MakePackage_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):

    err = [f"Running Package task with task_iter {task_iter} using {tablesetup['table']}"]
    completed = False
    viewport = ['0'] * 6
    document_profiles = eval(f"{genre}_genre['document_profiles']")
    document_stamps = eval(f"{genre}_genre['image_stamps']")
    document_signatures = eval(f"{genre}_genre['signature_stamps']")
    doc_profile_names, doc_stamps, doc_signatures = [], [], []
    for key in document_profiles:
        doc_profile_names.append(key)
    for key in document_stamps:
        doc_stamps.append(key)
    for key in document_signatures:
        doc_signatures.append(key)

    table = tablesetup['table']
    entrydata = tablesetup['entry data']
    hiddendata = tablesetup['hidden data']
    numitems = len(entrydata)
    holdvec = [''] * numitems
    holdvec[7] = doc_profile_names
    holdvec[10] = doc_stamps
    holdvec[11] = doc_signatures

    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    creators = tablesetup['creators']  # Gather the data for the selected row
    nextquery = f"{table}.query.get({sid})"
    odat = eval(nextquery)

    returnhit = request.values.get('Finished')
    if returnhit is not None: completed = True
    else:

        if task_iter == 0:
            dockind = getdocs(odat)
            if 'Invoice' in dockind:
                eprof = 'Custom-Invoice'
            else:
                eprof = 'Custom'
            emaildata = get_company(eprof, odat)
            stamplist, stampdata = get_last_used_stamps(odat)
            email_requested = 0

        else:
            # Save the current stamps to database for future launch
            stamplist, stampdata = get_stamps_from_form(doc_stamps, doc_signatures, odat)
            eprof = request.values.get('emlprofile')
            #lock = request.values.get('prolock')
            reorder_requested = make_bool(request.values.get('reorder'))
            stamp_requested = make_bool(request.values.get('stampnow'))
            email_requested = make_bool(request.values.get('emailnow'))
            if reorder_requested or stamp_requested or email_requested:
                emaildata = emaildata_update()
            else:
                emaildata = get_company(eprof, odat)
            if email_requested:
                info_mimemail(emaildata, [sid])

        holdvec[15] = stamplist
        #holdvec[4] = emaildata
        # Send in the emaildata in case it get modified by the stamps
        emaildata, holdvec[5], dockind, docref, err, fexist = makepackage(genre, odat, task_iter, document_profiles, stamplist, stampdata, eprof, err, emaildata)
        holdvec[4] = emaildata
        holdvec[6] = eprof
        holdvec[8] = dockind
        holdvec[9] = fexist


        viewport[0] = 'split panel left'
        viewport[1] = 'email setup'
        viewport[2] = 'show_doc_left'
        viewport[3] = '/' + docref
        #print('viewport=', viewport)

        err.append(f'Viewing {docref} on iteration {task_iter}')
        err.append('Hit Finished to End Viewing and Return to Table View')
        finished = request.values.get('Finished')
        if finished is not None: completed = True

        if email_requested:
            #print('Exiting after email requested completed')
            if 'Invoice' in dockind:
                #print('This is an invoice based package')
                odat.Istat = 3
                db.session.commit()
            completed = True

    return holdvec, entrydata, err, viewport, completed


def Match_task(genre, task_iter, tablesetup1, tablesetup2, task_focus, checked_data, sid1, sid2):

    #The match task copies key items from one selection in a table to another selection in another table
    completed = False
    err = [f'Running Match task with iter {task_iter}']
    today = datetime.date.today()
    holdvec = []
    entrydata = []

    table1, table2 = tablesetup1['table'], tablesetup2['table']
    entrydata1, entrydata2 = tablesetup1['entry data'], tablesetup2['entry data']
    filter1, filter2 = tablesetup1['filter'], tablesetup2['filter']
    filterval1, filterval2 = tablesetup1['filterval'], tablesetup2['filterval']
    creators1, creators2 = tablesetup1['creators'], tablesetup2['creators']    # Gather the data for the selected row
    nextquery1, nextquery2 = f"{table1}.query.get({sid1})", f"{table2}.query.get({sid2})"
    olddat1, olddat2 = eval(nextquery1), eval(nextquery2)
    colmatch1, colmatch2 = tablesetup1['matchfrom'][table2], tablesetup2['matchfrom'][table1]
    c11, c12 = [colm[0] for colm in colmatch1], [colm[1] for colm in colmatch1]
    c21, c22 = [colm[0] for colm in colmatch2], [colm[1] for colm in colmatch2]

    viewport = None
    #print('c11, c12', c11, c12)
    #print('c21, c22', c21, c22)

    for jx, col in enumerate(c11):
        thisvalue1 = getattr(olddat1, f'{col}')
        thisvalue2 = getattr(olddat2, f'{c12[jx]}')
        #print(f'For {col} comparing the values of {thisvalue1} in {table1} to {thisvalue2} in {table2}')
        setattr(olddat1, f'{col}', thisvalue2)
    db.session.commit()

    for jx, col in enumerate(c21):
        thisvalue1 = getattr(olddat1, f'{c22[jx]}')
        thisvalue2 = getattr(olddat2, f'{col}')
        #print(f'For {col} comparing the values of {thisvalue1} in {table1} to {thisvalue2} in {table2}')
        setattr(olddat2, f'{col}', thisvalue1)
    db.session.commit()

    completed = True
    return holdvec, entrydata, err, viewport, completed

def check_income(odat, ldat, err):

    invojo = odat.Jo
    co = invojo[0]
    invodate = ldat.Date
    invoamt = ldat.Total
    if ldat.Original is not None:
        docref = ldat.Original
    else:
        docref = ''

    lastpr = request.values.get('lastpr')
    if hasvalue(lastpr):
        ltext = lastpr.splitlines()
        custref = ltext[0]
        acctdb = ltext[1]
    else:
        custref = 'ChkNo'
        acctdb = request.values.get('acctto')

    incdat = Income.query.filter(Income.Jo == invojo).first()
    if incdat is None:
        #print('incdat is none')
        err.append('Creating New Payment on Jo')
        paydesc = 'Receive payment on Invoice ' + invojo
        recamount = ldat.Total

        recdate = datetime.date.today()
        acctdb = 'Undeposited Funds'

        #print('acctdb=', acctdb)
        input = Income(Jo=invojo, Account=acctdb, Pid=odat.Bid, Description=paydesc,
                       Amount=d2s(recamount), Ref=custref, Date=recdate, Original=os.path.basename(docref),
                       From=odat.Shipper, Bank=None, Date2=None, Depositnum=None)
        db.session.add(input)
        db.session.commit()

    else:
        #print('incdat is not none')
        recamount = request.values.get('recamount')
        custref = request.values.get('custref')
        desc = request.values.get('desc')
        recdate = request.values.get('recdate')
        acctdb = request.values.get('acctto')
        if acctdb is None:
            acctdb = 'Cash'
        if custref is None:
            custref = 'ChkNo'
        #print('acctdb2=', acctdb)
        if isinstance(invodate, str):
            recdate = datetime.datetime.strptime(recdate, '%Y-%m-%d')
        incdat.Amount = recamount
        incdat.Ref = custref
        incdat.Description = desc
        incdat.Date = recdate
        incdat.Original = docref
        incdat.Account = acctdb
        adat = Accounts.query.filter((Accounts.Name == acctdb) & (Accounts.Co == co)).first()
        if adat is not None:
            if adat.Type == 'Bank':
                incdat.Bank = acctdb
                incdat.Date2 = recdate
                incdat.Depositnum = custref
            else:
                incdat.Bank = None
                incdat.Date2 = None
                incdat.Depositnum = None
        else:
            incdat.Bank, incdat.Date2, incdat.Depositnum = None, None, None
        db.session.commit()

    return err

def check_invoice(odat, err):
    invojo = odat.Jo
    ldat = Invoices.query.filter(Invoices.Jo == invojo).first()

    if ldat is not None:
        co = invojo[0]
        acdata = Accounts.query.filter((Accounts.Type == 'Bank') & (Accounts.Co == co)).order_by(Accounts.Name).all()
        bklist = ['Undeposited Funds']
        for adat in acdata:
            bklist.append(adat.Name)

        lastpr = request.values.get('lastpr')
        if hasvalue(lastpr):
            ltext = lastpr.splitlines()
            custref = ltext[0]
            acctdb = ltext[1]
        else:
            custref = 'ChkNo'
            acctdb = request.values.get('acctto')

        err = check_income(odat, ldat, err)

        incdat = Income.query.filter(Income.Jo == invojo).first()
        payment = [incdat.Amount, incdat.Ref, incdat.Date, incdat.Bank]
        err.append('Amend Payment for Invoice ' + invojo)

    return ldat, payment, err


def ReceivePay_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):
    # Receive Pay for a Single Invoice
    err = [f"Running Receive Pay task with task_iter {task_iter} using {tablesetup['table']}"]
    completed = False
    slead = None
    viewport = ['0'] * 6
    document_profiles = eval(f"{genre}_genre['document_profiles']")
    document_stamps = eval(f"{genre}_genre['image_stamps']")
    document_signatures = eval(f"{genre}_genre['signature_stamps']")
    doc_profile_names, doc_stamps, doc_signatures = [], [], []
    for key in document_profiles:
        doc_profile_names.append(key)
    for key in document_stamps:
        doc_stamps.append(key)
    for key in document_signatures:
        doc_signatures.append(key)

    table = tablesetup['table']
    entrydata = tablesetup['entry data']
    hiddendata = tablesetup['hidden data']
    numitems = len(entrydata)
    holdvec = [''] * numitems
    holdvec[7] = doc_profile_names
    holdvec[10] = doc_stamps
    holdvec[11] = doc_signatures
    holdvec[12] = task_iter

    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    creators = tablesetup['creators']  # Gather the data for the selected row
    nextquery = f"{table}.query.get({sid})"
    odat = eval(nextquery)
    istat = odat.Istat

    if istat == 6 or istat == 7:
        # This is a summary invoice and must receive against all elements
        sinow = odat.Label
        slead = SumInv.query.filter( (SumInv.Si == sinow) & (SumInv.Status > 0) ).first()
        odata = Orders.query.filter(Orders.Label == sinow).all()
        sdata = SumInv.query.filter(SumInv.Si == sinow).all()
        #print(f'Using the summary invoice sinow={sinow} slead is {slead.id}')


    returnhit = request.values.get('Finished')
    if returnhit is not None:
        completed = True
    else:
        if task_iter == 0:
            eprof = 'Paid Invoice'
            emaildata = get_company(eprof, odat)
            paidon = today
            if slead is None:
                amtpaid = d2s(odat.InvoTotal)
            else:
                amtpaid = d2s(slead.Total)
            payref = odat.PayRef
            paymethod = odat.PayMeth
            depoacct = odat.PayAcct
            if payref is None: payref = 'Check No.'
            if paymethod is None:
                paymethod = 'Check'
                depoacct = 'Undeposited Funds'
            record_requested, email_requested = None, None

        else:
            # Save the current stamps to database for future launch
            eprof = request.values.get('emlprofile')
            update_requested = make_bool(request.values.get('update'))
            record_requested = make_bool(request.values.get('recordnow'))
            email_requested = make_bool(request.values.get('emailnow'))
            if update_requested or email_requested:
                emaildata = emaildata_update()
            else:
                emaildata = get_company(eprof, odat)
            amtpaid = request.values.get('paidamt')
            paidon = request.values.get('paidon')
            paidon = datetime.datetime.strptime(paidon, '%Y-%m-%d')
            paymethod = request.values.get('paymethod')
            payref = request.values.get('payref')
            depoacct = request.values.get('acctfordeposit')
            if paymethod == 'Cash' or paymethod == 'Check': depoacct = 'Undeposited Funds'


        holdvec[0] = [d2s(amtpaid), paidon, payref, paymethod]
        adata = Accounts.query.filter(Accounts.Type == 'Bank')
        acctlist = ['Undeposited Funds']
        for adat in adata: acctlist.append(adat.Name)
        holdvec[1] = acctlist
        holdvec[2] = depoacct

        #Create payment invoice off the unpaid invoice
        if slead is None:
            jo = odat.Jo
            invofile = addpath(tpath('Orders-Invoice', odat.Invoice))
            cache = odat.Icache
            basefile = addpayment(invofile, cache, odat.InvoTotal, amtpaid, paidon,  payref, paymethod)
            #print(f'The updated paid invoice file is {basefile}')
            odat.PaidInvoice = basefile
            odat.Icache = cache+1
            db.session.commit()
            #print(f'The updated paid invoice file is {basefile}')
            docref = f'static/{scac}/data/vPaidInvoice/{basefile}'
        else:
            invofile = addpath(tpath('Orders-Invoice', slead.Source))
            cache = odat.Icache
            basefile = addpayment(invofile, cache, slead.Total, amtpaid, paidon,  payref, paymethod)
            #print(f'The updated paid summary invoice file is {basefile}')
            for each in odata:
                each.PaidInvoice = basefile
                each.Icache = cache+1
            slead.Status = 4
            db.session.commit()
            #print(f'The updated paid summery invoice file is {basefile}')
            docref = f'static/{scac}/data/vPaidInvoice/{basefile}'

        # Need to update the hardcoded file name just updated:
        srcfile = emaildata[6]
        namfile = emaildata[7]
        if hasinput(srcfile) and hasinput(namfile):
            if namfile == srcfile:  emaildata[7] = basefile
        else: emaildata[7] = basefile
        emaildata[6] = basefile


        holdvec[4] = emaildata
        holdvec[6] = eprof
        #print(f'holdvec at this point 1616 is {holdvec}')
        # Save the default payment parameters in holdvec[0]


        if record_requested or email_requested:
            if slead is None:
                jopaylist = [[jo, amtpaid, paidon,  payref, paymethod, depoacct, amtpaid]]
                err, success = income_record(jopaylist, err)
                if success:
                    if email_requested: info_mimemail(emaildata, [sid])
                    completed = True

            else:
                jopaylist = []
                err_check = 0
                for each in odata:
                    odat_amount = d2s(each.InvoTotal)
                    scheck = SumInv.query.filter(SumInv.Jo == each.Jo).first()
                    if odat_amount != scheck.Amount:
                        err_check = err_check+1
                        err.append(f'Amounts do no match for JO {each.Jo} {odat_amount} vs. {scheck.Amount}')
                if err_check == 0:
                    for each in odata:
                        jo = each.Jo
                        amtpaid = each.InvoTotal
                        jopaylist.append([jo, amtpaid, paidon,  payref, paymethod, depoacct])
                    err, success = income_record(jopaylist, err)
                    if success:
                        if email_requested: info_mimemail(emaildata, [sid])
                        completed = True
                else: err.append('Could not process paid invoice')


        viewport[0] = 'split panel left'
        viewport[1] = 'email setup'
        viewport[2] = 'show_doc_left'
        viewport[3] = '/' + docref

        err.append(f'Viewing {docref}')
        err.append('Hit Finished to End Viewing and Return to Table View')

    return holdvec, entrydata, err, viewport, completed


def ReceiveByAccount_task(err, holdvec, task_iter):

    err = [f"Running Receive By Account task with task_iter {task_iter}"]
    completed = False

    viewport = ['0'] * 6
    #table = tablesetup['table']
    #entrydata = tablesetup['entry data']
    #hiddendata = tablesetup['hidden data']
    #numitems = len(entrydata)
    #holdvec = [''] * 30

    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')
    lookbacktime = request.values.get('lookbacktime')
    if lookbacktime is None or lookbacktime == 'One Year':
        lookbacktime = 'One Year'
        lookback = 364
    elif lookbacktime == 'Two Years':
        lookback = 728
    elif lookbacktime == 'Three Years':
        lookback = 1092
    holdvec[20] = lookbacktime
    stopdate = today-datetime.timedelta(days=lookback)
    err=[]

    #Determine unique shippers:
    comps = []
    tjobs = Orders.query.filter( ((Orders.Istat == 2) | (Orders.Istat == 3) | (Orders.Istat == 6) | (Orders.Istat == 7)) & (Orders.Date > stopdate) ).all()
    for job in tjobs:
        com = job.Shipper
        if com not in comps:
            comps.append(com)
    co = request.values.get('getaccount')
    holdvec[0] = co

    # If first time up there is not selection so set to todays date
    if co is None:
        holdvec[7] = today_str
    else:
        holdvec[7] = request.values.get('thisdate')

    #This is the relevant data for selection
    odata = Orders.query.filter((Orders.Shipper == co) & ((Orders.Istat == 2) | (Orders.Istat == 3) | (Orders.Istat == 6) | (Orders.Istat == 7)) & (Orders.Date > stopdate)).all()
    lenod = len(odata)
    if lenod < 1:
        if co is None:
            err.append('Choose Account to Receive Payments On')
        else:
            err.append(f'{holdvec[0]} has only uninvoiced orders')
    else:
        err.append(f'Showing invoices for {holdvec[0]}')
    holdvec[1] = odata
    holdvec[2] = comps

    thechecks = [0]*len(odata)
    amts = ['0.00']*len(odata)
    invts = ['0.00']*len(odata)
    checkall = request.values.get('checkall')
    runck = request.values.get('previewpay')
    recordnow = request.values.get('recordpayment')
    invotot = 0.0
    paytot = 0.0
    if runck is not None or recordnow is not None:
        if runck is not None:
            err.append(f'Totaling Open Invoices for {holdvec[0]}')
        else:
            err.append(f'Recording Invoices for {holdvec[0]}')

        for jx,odat in enumerate(odata):

            #Make sure we have an invoice and get the invoice total if we do
            idat = Invoices.query.filter(Invoices.Jo == odat.Jo).first()
            if idat is not None:
                invototal = idat.Total
                invts[jx] = invototal
                amts[jx] = invototal

            ckon = request.values.get('oder'+str(odat.id))
            if ckon is not None:
                thechecks[jx]=1
                invotot = invotot + float(invts[jx])
                recthis = request.values.get('amount'+str(odat.id))
                try:
                    paytot = paytot+float(recthis)
                    amts[jx] = d2s(recthis)
                except:
                    err.append(f'Bad Amt Received JO {odat.Jo}')
                    amts[jx] = '0.00'
                #Check and repair odat if necessary
                o_invototal = odat.InvoTotal
                if o_invototal is not None:
                    if abs(float(o_invototal) - float(invts[jx])) > .01:
                        odat.InvoTotal = d2s(invts[jx])
                        db.session.commit()
                else:
                    odat.InvoTotal = d2s(invts[jx])
                    db.session.commit()
    else:
        #Need to get the invoice totals even on the first pass:
        for jx, odat in enumerate(odata):
            idat = Invoices.query.filter(Invoices.Jo == odat.Jo).first()
            if idat is not None:
                invototal = idat.Total
                invts[jx] = invototal
                amts[jx] = invototal
    if checkall is not None: thechecks = [1]*len(odata)
    holdvec[3] = thechecks
    holdvec[4] = d2s(invotot)
    holdvec[5] = d2s(paytot)
    holdvec[6] = amts
    holdvec[8] = request.values.get('thisref')
    holdvec[12] = invts
    #print('amts=',amts)
    #print(holdvec[7],holdvec[8])
    depmethod = request.values.get('paymethod')
    depref=None
    if depmethod is None:
        deps = ['Choose Pay Method First']
        acctdb = 'None'
        bank = None
    elif depmethod == 'Cash' or depmethod == 'Check':
        deps = ['Undeposited Funds']
        acctdb = 'Undeposited Funds'
        bank = None
    elif depmethod == 'Credit Card':
        acctdb = request.values.get('acctfordeposit')
        bank = acctdb
        deps = []
        acdata = Accounts.query.filter((Accounts.Type == 'Bank') & (Accounts.Description.contains('Merchant'))).all()
        for acd in acdata:
            deps.append(acd.Name)
    elif depmethod == 'Direct Deposit':
        acctdb = request.values.get('acctfordeposit')
        bank = acctdb
        depref = holdvec[8]
        #Get the account for deposit listing and the account for deposit selection:
        deps = []
        acdata = Accounts.query.filter( (Accounts.Type == 'Bank') | (Accounts.Type == 'Exch') ).all()
        for acd in acdata:
            deps.append(acd.Name)

    holdvec[9] = deps
    holdvec[14] = depmethod
    holdvec[10] = acctdb
    autodis = request.values.get('autodisbox')
    autodis = nonone(autodis)
    holdvec[11] = autodis

    # Enable Record button if all selections required are made
    try:
        paytotf = float(paytot)
        if paytotf > 0.0 and hasvalue(acctdb):
            #print(f'The acctdb is {acctdb}')
            holdvec[13] = 1
            err.append('Record capability enabled')
        else:
            holdvec[13] = 0
            if co is not None:
                if paytotf == 0.00:
                    err.append('Choose Invoices to Receive Against')
                if not hasvalue(acctdb):
                    err.append('Choose Account to Deposit Funds')
    except:
        holdvec[13] = 0

    if recordnow is not None:
        err = []
        jopaylist = []
        success = True
        #print(f'Length of odata is {len(odata)}')
        #Apply the payments
        for jx, odat in enumerate(odata):
            if thechecks[jx]==1:
            #Just means this job is included
                if amts[jx] != '0.00':
                    invojo = odat.Jo
                    # Begin Income Creation:
                    recamount = amts[jx]
                    recdate = datetime.datetime.strptime(holdvec[7], '%Y-%m-%d')

                    try:
                        rec = float(recamount)
                    except:
                        rec = 0.00
                    try:
                        owe = float(invts[jx])
                    except:
                        owe = 0.00

                    #print('autodis=',autodis,rec,owe)
                    if autodis == 1 and rec < owe:
                        disamt = rec - owe
                        #Need to add a discounting invoice to zero out the balance
                        input = Invoices(Jo=invojo, SubJo=None, Pid=odat.Bid, Service='Discount', Description='Auto Discount',
                                         Ea=d2s(disamt), Qty=1, Amount=d2s(disamt), Total=d2s(rec), Date=today,
                                         Original=None, Status='P')
                        db.session.add(input)
                        db.session.commit()
                        #Adjust Invoice Totals for all Line Items on this Order:
                        ldata = Invoices.query.filter(Invoices.Jo == invojo).all()
                        for data in ldata:
                            data.Total = d2s(rec)
                            db.session.commit()
                        err.append(f'Info: Discount created for JO {odat.Jo} to balance invoice')
                        owe = 0.00

                    if rec < owe:
                        err.append(f'Warning: Payment for JO {odat.Jo} less than invoiced')

                    #odat.PaidInvoice = basefile
                    #odat.Icache = cache + 1
                    jopaylist.append([invojo, recamount, recdate, holdvec[8], depmethod, acctdb, holdvec[5]])
                else:
                    success = False
                    err.append(f'Have no Invoice to Receive Against for JO={invojo}')
                    #print(f'Have no Invoice to Receive Against for JO={invojo}')
            else:
                continue
                #print(f'This job not included {thechecks[jx]}')

        if success:
            err, success = income_record(jopaylist, err)
            if success: completed = True
    return completed, err, holdvec

def get_billform_data(entrydata, tablesetup, holdvec, err, thisform, itable):
    form_show = tablesetup['form show'][thisform]
    form_checks = tablesetup['form checks'][thisform]
    task_iter = 1
    if thisform != 'MultiChecks': form_show.append('Always')
    failed = 0
    warned = 0
    for jx, entry in enumerate(entrydata):
        if entry[4] is not None and entry[9] in form_show:
            # Some items are part of bringdata so do not test those - make sure entry[4] is None for those
            holdvec[jx] = request.values.get(f'{entry[0]}')
            if entry[0] in form_checks: required = True
            else: required = False
            holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], thisform, required, task_iter, 'unknown', 0, itable)
            if entry[5] > 1: failed = failed + 1
            if entry[5] == 1: warned = warned + 1

    if 'bring data' in tablesetup:
        for bring in tablesetup['bring data']:
            tab1, sel, tab2, cat, colist1, colist2 = bring
            #print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
            valmatch = request.values.get(sel)
            #print(valmatch)
            escript = f'{tab2}.query.filter({tab2}.{cat} == valmatch).first()'
            adat = eval(escript)
            if adat is not None:
                for jx, col in enumerate(colist1):
                    thisval = getattr(adat, col)
                    for ix, entry in enumerate(entrydata):
                        if entry[0] == colist2[jx]:
                            holdvec[ix] = thisval
                            #print(f'Moving value {thisval} from {tab2} {col} to {table} {colist2[jx]}')

    err.append(f'There are {failed} input errors and {warned} input warnings')
    return holdvec, err, failed

def altersids(bdata, locked):
    allsids = []
    for bdat in bdata:
        pd = bdat.Status
        #print(f'For id {bdat.id} pd is {pd} and locked is {locked}')
        if locked: allsids.append(bdat.id)
        elif pd != 'Paid': allsids.append(bdat.id)
    sidon = []
    for sid in allsids:
        ck1 = request.values.get(f'Billout{sid}')
        ck2 = request.values.get(f'Billin{sid}')
        ck3 = request.values.get(f'Billhid{sid}')
        #print(f'for sid {sid} ck1 is {ck1} and ck2 is {ck2} and ck3 is {ck3}')
        if ck1 == 'on': sidon.append(sid)
        if ck2 == 'on': sidon.append(sid)
    return allsids, sidon



def MultiChecks_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sids):

    err = [f"Running MultiChecks task with task_iter {task_iter} using {tablesetup['table']}"]
    #print(f"Running MultiChecks task with task_iter {task_iter} using {tablesetup['table']} and sids {sids}")
    table = tablesetup['table']
    plist, bid_list, pamt_list, status_list = [], [], [], []
    ptot = 0.00
    gofwd = 1
    postdata, postdata2, allsids = [], [], []
    #posdata is summary of bill data on check currently
    #postdata2 is summary of bill data with same company
    record_item = request.values.get('Record Item')
    locked = request.values.get('locked')

    #Get preliminary setup data based on first sid (want all the bills that match company and baccount
    nextquery = f"{table}.query.get({sids[0]})"
    bdat = eval(nextquery)
    pdat = People.query.get(bdat.Pid)
    #print(f'data trouble {bdat.id} {pdat.id} {bdat.bAccount}')
    bdata = Bills.query.filter(Bills.Pid == pdat.id).all()
    #This prelinary data provides all similar bills to the ones being referred
    if task_iter > 0:
        # Now can alter the mutli-bill check to include other bills of similar nature and remove as well per selections
        allsids, sids = altersids(bdata, locked)
    else:
        for dat in bdata:
            if dat.Status != 'Paid': allsids.append(dat.id)
    #print(f"Updated MultiChecks task with task_iter {task_iter} using {tablesetup['table']} and sids {sids} and allsids {allsids}")

    if sids != []:

        for sid in sids:
            nextquery = f"{table}.query.get({sid})"
            bdat = eval(nextquery)
            pdat = People.query.get(bdat.Pid)
            plist.append(pdat.id)
            bid_list.append(bdat.id)
            pamt_list.append(d2s(bdat.bAmount))
            bdat.pAmount = bdat.bAmount
            status_list.append(bdat.Status)
            ptot = ptot + float(bdat.bAmount)
            postdata.append([str(sid), bdat.Jo, bdat.bAmount, bdat.bAccount])

        if not sameall(plist):
            err.append('Billing Company does not Match for all Bill Items')
            gofwd = 0
        if 'Paid' in status_list:
            if task_iter == 0:
                err.append('Some Billing Items have been Paid')
                completed = True
                holdvec = []
                entrydata = []
                viewport = []
                #print('Exiting in the paid out location')
                return holdvec, entrydata, err, viewport, completed
        err.append(f'Writing check for {bid_list}')
        err.append(f'Checks amounts are: {pamt_list}')
        err.append(f'Total amount is: {d2s(ptot)}')
        if gofwd:
            db.session.commit()
            for sid in sids:
                nextquery = f"{table}.query.get({sid})"
                bdat = eval(nextquery)
                bdat.pAmount2 = d2s(ptot)
                bdat.PmtList = f'{pamt_list}'
                bdat.PacctList = f'{bid_list}'
            db.session.commit()
            #Find other items for this biller
            for thisid in allsids:
                if thisid not in sids:
                    adat = Bills.query.get(thisid)
                    postdata2.append([str(thisid), adat.Jo, adat.bAmount, adat.bAccount])

            nextquery = f"{table}.query.get({sids[0]})"
            bdat = eval(nextquery)

            viewport = ['0'] * 6
            holdvec = [''] * 50
            completed = False
            creators = tablesetup['creators']
            entrydata = tablesetup['entry data']
            form_show = tablesetup['form show']['MultiChecks']
            form_checks = tablesetup['form checks']['MultiChecks']
            hiddendata = tablesetup['hidden data']

            if task_iter > 0:
                if locked:
                    for jx, entry in enumerate(entrydata):
                        holdvec[jx] = getattr(bdat, f'{entry[0]}')
                else:
                    holdvec, err, failed = get_billform_data(entrydata, tablesetup, holdvec, err, 'MultiChecks', table)
                    err.append(f'Failed is {failed}')

                    update_item = request.values.get('Update Item')
                    if update_item is not None or record_item is not None:
                        try:
                            thisvalue = getattr(bdat, colorcol[0])
                            if thisvalue == -1: setattr(bdat, colorcol[0], 0)
                        except:
                            thisvalue = 0

                        if failed == 0:
                            for sid in sids:
                                nextquery = f"{table}.query.get({sid})"
                                each_bdat = eval(nextquery)
                                for jx, entry in enumerate(entrydata):
                                    if entry[4] is not None and entry[9] in form_show:
                                        if entry[0] not in creators: setattr(each_bdat, f'{entry[0]}', holdvec[jx])
                                db.session.commit()
                                for jx, entry in enumerate(hiddendata):
                                    thisvalue = getattr(bdat, entry[2])
                                    try:
                                        thisvalue = thisvalue.splitlines()
                                        thissubvalue = thisvalue[0]
                                    except:
                                        thissubvalue = ''
                                    #print('Updating Entry with', entry[0], thissubvalue)
                                    setattr(each_bdat, f'{entry[0]}', thissubvalue)
                                db.session.commit()
                            # err.append(f"Updated entry in {tablesetup['table']}")
                            # Test if Bill is completely paid and set status attribute accordingly:
                            #If Recording need to mark each item Paid to get signature on the check!!
                            if record_item is not None:
                                for sid in sids:
                                    nextquery = f"{table}.query.get({sid})"
                                    each_bdat = eval(nextquery)
                                    each_bdat.Status = 'Paid'
                                db.session.commit()

                            # Test of bring data-modify the database at this point
                            if 'bring data' in tablesetup:
                                for bring in tablesetup['bring data']:
                                    tab1, sel, tab2, cat, colist1, colist2 = bring
                                    #print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
                                    valmatch = request.values.get(sel)
                                    #print(valmatch)
                                    escript = f'{tab2}.query.filter({tab2}.{cat} == valmatch).first()'
                                    #print(escript)
                                    adat = eval(escript)
                                    if adat is not None:
                                        for jx, col in enumerate(colist1):
                                            thisval = getattr(adat, col)
                                            for sid in sids:
                                                nextquery = f"{table}.query.get({sid})"
                                                bdat = eval(nextquery)
                                                setattr(bdat, colist2[jx], thisval)
                                                #print(f'Moving value {thisval} from {tab2} {col} to {table} {colist2[jx]}')
                                        db.session.commit()
                            bdat = eval(nextquery)
                            pdat = People.query.get(bdat.Pid)
                            for jx, entry in enumerate(entrydata): holdvec[jx] = getattr(bdat, f'{entry[0]}')
                        else:
                            err.append(f'Cannot update entry until input errors shown in red below are resolved')

            else:

                nextquery = f"{table}.query.get({sids[0]})"
                bdat = eval(nextquery)
                # Get Default Account Data
                #print('co is', co[10])
                adat = Accounts.query.filter((Accounts.Type == 'Bank') & (Accounts.Co == co[10])).first()
                for jx, entry in enumerate(entrydata):
                    holdvec[jx] = getattr(bdat, f'{entry[0]}')
                    aj = hasinput(holdvec[jx])
                    if aj == 0:
                        #print(f'{entry[0]} {holdvec[jx]} {aj}')
                        if entry[0] == 'pMeth':
                            holdvec[jx], entry[5], entry[6] = 'Check', 1, 'Warning: Inserted Default Value'
                        elif entry[0] == 'pAccount':
                            holdvec[jx], entry[5], entry[6] = adat.Name, 1, 'Warning: Inserted Default Value'
                        elif entry[0] == 'pAmount':
                            holdvec[jx], entry[5], entry[6] = bdat.bAmount, 1, 'Warning: Inserted Default Value'
                        elif entry[0] == 'pDate':
                            holdvec[jx], entry[5], entry[6] = today, 1, 'Warning: Inserted Default Value'
                        elif entry[0] == 'Memo':
                            holdvec[jx], entry[5], entry[6] = f'{bdat.bSubcat} {bdat.bAccount}', 1, 'Warning: Inserted Default Value'
                        elif entry[0] == 'Ref':
                            blast = Bills.query.filter(
                                (Bills.pAccount == adat.Name) & (Bills.pMeth == 'Check') & (Bills.Status == 'Paid')).order_by(
                                Bills.id.desc()).first()
                            try:
                                next_check = int(blast.Ref) + 1
                            except:
                                next_check = ''
                            if blast is not None:  holdvec[jx], entry[5], entry[6] = f'{next_check}', 1, 'Warning: Inserted Default Value'
####################################################################
            #print(f'Writing checks with sids = {sids}')
            pmeth = request.values.get('pMeth')
            if pmeth is None: pmeth = 'Check'
            docref, file1, cache, style = writechecks(sids,pmeth)
            #print(f'The check style is {style}')
            #######################################################
            holdvec[40] = str(style)
            holdvec[39] = postdata
            holdvec[38] = postdata2
            holdvec[37] = locked
            holdvec[36] = pmeth
            if cache > 0:
                lastcache = cache - 1
                lastfile = file1.replace(f'_c{cache}', f'_c{lastcache}')
                try: os.remove(lastfile)
                except:
                    pass
                    #print(f'{lastfile} does not exist')

            if record_item is not None:
                for sid in sids:
                    nextquery = f"{table}.query.get({sid})"
                    each_bdat = eval(nextquery)
                    err = gledger_write(['paybill'], each_bdat.Jo, each_bdat.bAccount, each_bdat.pAccount, 0)
                    err.append(f'Ledger paid {each_bdat.Jo} to {each_bdat.bAccount} from {each_bdat.pAccount}')
                    each_bdat.Check = docref
                    each_bdat.Ccache = cache + 1
                db.session.commit()
                holdvec[37] = 1
            else:
                bdat.Ccache = cache + 1
                db.session.commit()

            returnnow = request.values.get('Return')
            if returnnow is not None:
                completed = True
            elif record_item is None:
                # In case we have locked the check but still going back/forth on address labels
                for sid in sids:
                    nextquery = f"{table}.query.get({sid})"
                    each_bdat = eval(nextquery)
                    each_bdat.Check = docref
                    each_bdat.Ccache = cache + 1
                db.session.commit()

            if docref is not None:
                viewport[0] = 'show_doc_left'
                viewport[2] = '/' + tpath(f'{table}-Check', docref)


            #print(f'Exiting in the comleted section completed is {completed}')

            return holdvec, entrydata, err, viewport, completed

        else:
            #print('Exiting in the gofwd section')
            completed = True
            holdvec = []
            entrydata = []
            viewport = []
            return holdvec, entrydata, err, viewport, completed

    else:
        completed = True
        holdvec = []
        entrydata = []
        viewport = []
        #print('Exiting in the no sids location')
        return holdvec, entrydata, err, viewport, completed


def Truck_Logs_task(err, holdvec, task_iter):

    err = [f"Running Truck_Logs task with task_iter {task_iter}"]
    completed = False
    returnhit = request.values.get('return')
    if returnhit is not None: completed = True

    viewport = ['0'] * 6

    today = datetime.date.today()
    daysback = 400
    lookback = today - datetime.timedelta(days=daysback)
    today_str = today.strftime('%Y-%m-%d')
    err=[]

    #Get a list of the active drivers:
    drivers = ['All Drivers']
    ddata = Drivers.query.filter(Drivers.Active == 1).all()
    for ddat in ddata:
        drv = ddat.Name
        if drv not in drivers:
            drivers.append(drv)
    selected_driver = request.values.get('getdriver')
    if selected_driver is None: selected_driver = 'All Drivers'
    holdvec[0] = selected_driver

    # If first time up there is not selection so set to todays date
    if task_iter == 0:
        holdvec[7] = today_str
    else:
        holdvec[7] = request.values.get('thisdate')

    #This is the relevant data for the table
    tableget = 'Trucklog'
    table_setup = eval(f'{tableget}_setup')
    #print(table_setup['table'])
    tfilters = {}
    tfilters['Driver Filter'] = selected_driver
    #print(tfilters)
    db_data, labpass = get_dbdata(table_setup, tfilters)
    data1 = db_data[0]
    data1id = db_data[1]
    entrydata = db_data[4]
    headers = []
    for entry in entrydata:
        headers.append(entry[1])
    holdvec[5] = headers
    holdvec[1] = data1
    holdvec[6] = data1id
    holdvec[2] = drivers

    thechecks = [0]*len(data1id)

    action = None
    if action is None:
        for jx,sid in enumerate(data1id):
            ckon = request.values.get('oder'+str(sid))
            if ckon is not None:
                thechecks[jx]=1

    holdvec[4] = thechecks

    return completed, err, holdvec

from webapp import db
from webapp.models import Vehicles, Orders, Gledger, Invoices, JO, Income, Accounts, LastMessage, People, Interchange, Drivers, ChalkBoard, Services, Drops, StreetTurns, SumInv, Autos, Bills, Divisions, Trucklog, Pins
from flask import render_template, flash, redirect, url_for, session, logging, request
from webapp.CCC_system_setup import myoslist, addpath, tpath, companydata, scac, apikeys
from webapp.InterchangeFuncs import Order_Container_Update, Match_Trucking_Now, Match_Ticket
from webapp.class8_utils_email import etemplate_truck, info_mimemail
from webapp.class8_dicts import *
#Trucking_genre, Auto_genre, Orders_setup, Interchange_setup, Customers_setup, Services_setup, Summaries_setup, Autos_setup, Billing_genre, Bills_setup
from webapp.class8_utils_manifest import makemanifest
from webapp.class8_tasks_money import MakeInvoice_task, MakeSummary_task, income_record
from webapp.class8_utils_package import makepackage
from webapp.class8_utils_email import emaildata_update
from webapp.class8_utils_invoice import make_invo_doc, make_summary_doc, addpayment, writechecks
from webapp.class8_tasks_gledger import gledger_write, gledger_multi_job
from webapp.InterchangeFuncs import Order_Container_Update
from webapp.class8_tasks_money import get_all_sids
from webapp.class8_tasks_scripts import Container_Update_task, Street_Turn_task, Unpulled_Containers_task, Assign_Drivers_task, Driver_Hours_task, CMA_APL_task
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

def address_resolver(json):
    final = {}
    if json['results']:
        data = json['results'][0]
        for item in data['address_components']:
            print(f'address resolver item {item}')
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
    print(f'In get_drop The LOADNAME is:{loadname}')
    dropdat = Drops.query.filter(Drops.Entity == loadname).first()
    if dropdat is not None:
        #print('dropdat',dropdat.Entity, dropdat.Addr1, dropdat.Addr2, dropdat.Phone, dropdat.Email)
        dline = f'{dropdat.Entity}\n{dropdat.Addr1}\n{dropdat.Addr2}\n{dropdat.Phone}\n{dropdat.Email}'
        dline = dline.replace('None','')
        return dline
    else:
        #print(f'the lenght of loadname is...{len(loadname)}')
        if len(loadname) == 3:
            dropdat = Drops.query.filter(Drops.Entity.contains(loadname)).first()
            if dropdat is not None:
                #print('dropdat', dropdat.Entity, dropdat.Addr1, dropdat.Addr2, dropdat.Phone, dropdat.Email)
                dline = f'{dropdat.Entity}\n{dropdat.Addr1}\n{dropdat.Addr2}\n{dropdat.Phone}\n{dropdat.Email}'
                dline = dline.replace('None', '')
                return dline

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

def populate(tables_on,tabletitle,tfilters,jscripts):
    # print(int(filter(check.isdigit, check)))
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
            if num_tables_on > 1:
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
                                if select_value is None: select_value = default_val

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

            if dbstats is not None:
                dblist = []
                for dbstat in dbstats:
                    nextvalue = eval(f'dbstat.{keyon}')
                    #print(f'nextvalue:{nextvalue}')
                    if nextvalue is not None:  nextvalue = nextvalue.strip()
                    if nextvalue not in dblist:
                        dblist.append(nextvalue)
                keydata.update({key: dblist})
                #print(f'keydata is {keydata[key]}')
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
    tfilters = {'Shipper': None, 'Date Filter': 'Last 60 Days', 'Pay Filter': None, 'Haul Filter': None, 'Color Filter': 'Haul'}
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
    print(f'Taskon:{taskon}, task_focus:{task_focus}, tasktype:{tasktype}, task_iter:{task_iter}')

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
            #print('made it here with thistable sid taskiter', thistable, sid, task_iter)
            tablesetup = eval(f'{thistable}_setup')
            rstring = f"{taskon}_task(genre, task_iter, {thistable}_setup, task_focus, checked_data, thistable, sid)"
            holdvec, entrydata, err, viewport, completed = eval(rstring)
            print('returned with:', viewport, completed)
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
        print('nc=', nc)
        print(tids)
        print(tabs)
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
    print(f'Returning from runthetask with viewport = {viewport} and completed {completed}')
    return holdvec, entrydata, err, completed, viewport, tablesetup

def get_address_details(address):
    print(address)
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
        if 'Export' in ht: return f'Empty Out: *{odat.Booking}* ({ctext} {city})'
        if 'Import' in ht: return f'Load Out: *{rel4}  {odat.Container}* ({ctext} {city})'
    else:
        if 'Export' in ht: return f'Load In: *{odat.Booking}  {odat.Container}* ({ctext} {city})'
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
    carrier = None
    intext = None
    outtext = None
    for odat in opair:
        if odat is not None:
            ht = odat.HaulType
            hstat = odat.Hstat
            contype = odat.Type
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
                if 'Export' in ht:
                    outbook = odat.Booking
                    outtext = f'Empty Out: *{odat.Booking}* ({ctext} {city})'
                if 'Import' in ht:
                    outbook = rel4
                    outcon = odat.Container
                    outtext =  f'Load Out: *{rel4}  {odat.Container}* ({ctext} {city})'
            else:
                if 'Export' in ht:
                    inbook = odat.Booking
                    incon = odat.Container
                    inchas = odat.Chassis
                    intext = f'Load In: *{odat.Booking}  {odat.Container}* ({ctext} {city})'
                if 'Import' in ht:
                    incom = odat.Container
                    inchas = odat.Chassis
                    intext = f'Empty In: *{odat.Container}* ({ctext} {city})'

    if intext: print(f'About to add {len(intext)} {intext}')
    if outtext: print(f'About to add {len(outtext)} {outtext}')

    input = Pins(Date=thisdate, Driver=driver, InBook=inbook, InCon=incon, InChas = inchas, InPin=inpin, OutBook=outbook, OutCon=outcon, OutChas=outchas, OutPin=outpin, Unit=unit, Tag=tag, Phone=phone, Carrier=carrier, Intext=intext, Outtext=outtext)
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
        if '30' in dtest:
            daysback = 30
        elif '60' in dtest:
            daysback = 60
        elif '90' in dtest:
            daysback = 90
        elif '120' in dtest:
            daysback = 120
        elif '180' in dtest:
            daysback = 180
        elif dtest == 'Last Year':
            thisyear = today.year
            lastyear = thisyear - 1
            fromdate = datetime.date(lastyear, 1, 1)
            todate = datetime.date(lastyear, 12, 31)
        elif dtest == 'This Year':
            thisyear = today.year
            fromdate = datetime.date(thisyear, 1, 1)
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
        if len(shipper) > 20: shipper = shipper[0:20]
        if shipper not in custlist: custlist.append(shipper)
    custlist.sort()
    custlist.append('Show All')
    return custlist

def Table_maker(genre):
    username = session['username'].capitalize()
    # Gather information about the tables inside the genre
    print(f'The genre is {genre}')
    genre_tables = eval(f"{genre}_genre['genre_tables']")
    quick_buttons = eval(f"{genre}_genre['quick_buttons']")
    table_filters = eval(f"{genre}_genre['table_filters']")
    task_boxes = eval(f"{genre}_genre['task_boxes']")
    task_box_map = eval(f"{genre}_genre['task_box_map']")

    # Left size is the portion out of 12 devoted to table and document display
    leftsize = 8
    # Define list variables even if not used in some tasks
    err, tabletitle, checked_data, jscripts = [], [], [], []
    viewport = ['tables'] + ['0']*5
    tfilters, tboxes = {}, {}
    returnhit = None
    resethit = request.values.get('Reset')
    invoicehit = request.values.get('InvoiceSet')

    if request.method == 'POST' and resethit is None:
        print('Method is POST')
        # See if a task is active and ongoing
        tasktype = nononestr(request.values.get('tasktype'))
        taskon = nononestr(request.values.get('taskon'))
        task_focus = nononestr(request.values.get('task_focus'))
        task_iter = nonone(request.values.get('task_iter'))

        #Gather filter settings to keep them set as desired


        returnhit = request.values.get('Return')
        if returnhit is not None:
            print('Resetting tables from Table_maker')
            # Asked to reset, so reset values as if not a Post (except the table filters which will be kept)
            jscripts, taskon, task_iter, task_focus, tboxes, viewport = reset_state_soft(task_boxes)

            ###############Testing this###########
            genre_tables_on = checked_tables(genre_tables)
            tables_on = [ix for jx, ix in enumerate(genre_tables) if genre_tables_on[jx] == 'on']

            for filter in table_filters:
                for key, value in filter.items(): tfilters[key] = request.values.get(key)

            if 'Orders' in tables_on: table_filters[0]['Shipper Filter'] = get_custlist('Orders', tfilters)

        else:

            taskon = nononestr(taskon)
            print(f'Return hit is none so task continues with task tasktype:{tasktype}, taskon:{taskon}, task_focus:{task_focus}, task_iter:{task_iter}')

            # Get data only for tables that have been checked on
            genre_tables_on = checked_tables(genre_tables)
            tables_on = [ix for jx, ix in enumerate(genre_tables) if genre_tables_on[jx] == 'on']
            print(f'The tables on: {tables_on} with task {taskon}')

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
                    print('check1',key,tfilters[key])
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
                elif tfilters['Color Filter'] == 'Invoice':
                    Orders_setup['colorfilter'] = ['Istat']
                elif tfilters['Color Filter'] == 'Both':
                    Orders_setup['colorfilter'] = ['Hstat', 'Istat']



    #First time thru (not a Post)
    else:
        print('Method is NOT POST')
        genre_tables_on = ['off'] * len(genre_tables)
        genre_tables_on[0] = 'on'
        tables_on = [eval(f"{genre}_genre['table']")]

        #These two session variables control the table defaults. Each time table turned on it sets default
        #session['table_defaults'] = tables_on
        #session['table_removed'] = []
        # Default time filter on entry into table is last 60 days:
        tfilters = {'Shipper Filter': None, 'Date Filter': 'Last 60 Days', 'Pay Filter': None, 'Haul Filter': None, 'Color Filter': 'Both'}
        jscripts = ['dtTrucking']
        taskon, task_iter, task_focus, tasktype = None, None, None, None
        if 'Orders' in tables_on: table_filters[0]['Shipper Filter'] = get_custlist('Orders', tfilters)


    # Execute these parts whether it is a Post or Not:
    # genre_data = [genre,genre_tables,genre_tables_on,contypes]
    genre_data = eval(f"{genre}_genre")
    genre_data['genre_tables_on'] = genre_tables_on

    #Apply shortcut for filters for various tasks
    if invoicehit is not None: tfilters = {'Shipper Filter': None, 'Date Filter': 'Last 60 Days', 'Pay Filter': 'Uninvoiced', 'Haul Filter': 'Completed', 'Color Filter': 'Both'}

    # Populate the tables that are on with data
    tabletitle, table_data, checked_data, jscripts, keydata, labpassvec = populate(tables_on,tabletitle,tfilters,jscripts)

    # Remove the checks during reset of tables
    if resethit is not None:
        for check in checked_data:  check[2] = []

    # Execute the task here if a task is on...,,,,
    if hasvalue(taskon):
        print(f'About to execute task with tasktype:{tasktype}, taskon:{taskon}, task_focus:{task_focus}, task_iter:{task_iter}')
        holdvec, entrydata, err, completed, viewport, tablesetup = run_the_task(genre, taskon, task_focus, tasktype, task_iter, checked_data, err)
        if completed:
            # If complete set the task on to none
            taskon = None
            #print(f'completed task: the tables on are: {tables_on} with task {taskon}')
            if tables_on == []:
                genre_tables_on, tables_on, jscripts, taskon, task_iter, task_focus, tboxes, viewport, tfilters = reset_state_hard(task_boxes, genre_tables)
                genre_data = eval(f"{genre}_genre")
                genre_data['genre_tables_on'] = genre_tables_on
            else:
                #print(f'ongoing task: the tables on are: {tables_on} with task {taskon}')
                jscripts, taskon, task_iter, task_focus, tboxes, viewport = reset_state_soft(task_boxes)
            tabletitle, table_data, checked_data, jscripts, keydata, labpassvec = populate(tables_on, tabletitle, tfilters, jscripts)
        else: task_iter = int(task_iter) + 1

        #for e in err:
            #if 'Created' in e:
                #taskon = None
                #task_iter = 0
        # Treat a cancel job as a completed task instead of this........
        #if request.values.get('Cancel') is not None:
            #jscripts, taskon, task_iter, task_focus, tboxes, viewport = reset_state_soft(task_boxes)
            #err = ['Entry canceled']
            #taskon = None
            #task_iter = 0
            #holdvec = [''] * 50
            #entrydata = []
            #viewport = ['tables'] + ['0']*5
    else:
        taskon = None
        task_iter = 0
        tasktype = ''
        holdvec = [''] * 50
        #print(f'labpassvec is {labpassvec}')
        entrydata = []
        #err = ['All is well']
        tablesetup = None

    #print(jscripts, holdvec)

    if returnhit is not None:
        checked_data = [0,'0',['0']]

    if len(holdvec)<50: holdvec = holdvec + ['']*(50-len(holdvec))
    checkcol = [eval(f"{ix}_setup['checklocation']") for ix in tables_on]
    holdvec[48] = checkcol
    holdvec[49] = labpassvec
    holdvec[47] = f'/static/{scac}/data/v'
    #print(f"holdvec is {holdvec} and session variable is {session['table_defaults']}")
    #print(f"The session variables for tables Default {session['table_defaults']} and Removed {session['table_removed']}")

    getpin = request.values.get('PinGet')
    if getpin is not None and 'Orders' in tables_on:
        print(f'Running the pin script')
        #tes = subprocess.run(['ssh', '10.0.0.105','/home/mark/flask/crontasks/getpin.sh','FELA'], timeout=120)
        try:
            tes = subprocess.run(['ssh', 'mark@70.88.236.49', '/crontasks/getpin.sh', f'{scac}'], timeout=180)
            print(tes)
            print(f'The pin script is completed')
        except:
            print('The subprocess had at least one error')
        #res = command.run(['ls'])
        #print(res.output)
        #print(res.exit)

    putbuff = request.values.get('Paste Buffer')
    thisdate = datetime.datetime.today()
    thisdate = thisdate.date()
    movedate = thisdate
    print(thisdate, thisdate.weekday())
    holdvec[46] = []
    holdvec[44] = [Drivers.query.filter(Drivers.Active == 1).all(),Vehicles.query.filter(Vehicles.Active == 1).all()]
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
            pdata = Pins.query.filter(Pins.Date == movedate).all()
            for jx, pdat in enumerate(pdata):
                driver = request.values.get(f'drv{idate}{jx}')
                unit = request.values.get(f'unit{idate}{jx}')
                chas = request.values.get(f'chas{idate}{jx}')
                box = request.values.get(f'box{idate}{jx}')
                if box == 'on':
                    boxid.append(pdat.id)
                print(f'box is {box} {boxid}')

                if driver is not None:
                    print(f'The selected driver is {driver}')
                    pdat.Driver = driver
                    ddat = Drivers.query.filter(Drivers.Name == driver).first()
                    if ddat is not None:
                        pdat.Phone = ddat.Phone
                        pdat.Carrier = ddat.Carrier

                if unit is not None:
                    print(f'The selected unit is {unit}')
                    pdat.Unit = unit
                    vdat = Vehicles.query.filter(Vehicles.Unit == unit).first()
                    if vdat is not None:
                        pdat.Tag = vdat.Plate

                if chas is not None:
                    print(f'The selected chassis is {chas}')
                    pdat.InChas = chas
                    pdat.OutChas = chas
                db.session.commit()
            print(f'Modifying the selection')

        #Perform moveup or movedn actions
        for tid in boxid:
            print(f'Performing action on id= {tid}')
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

        holdvec[46].append([movedate, f'{idate}', Pins.query.filter(Pins.Date == movedate).all()])

    if (putbuff is not None or anyamber) and 'Orders' in tables_on:
        holdvec[46] = []
        print(f'Doing the paste buffer for {checked_data} {tables_on}')
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
                            print(f'Adding the dispatch selection to date {movedate}')
                            addtopins(movedate, [indat,outdat])
                    holdvec[45] = f'{get_dispatch(indat)}\n{get_dispatch(outdat)}'
                else:
                    sid = sids[0]
                    odat = Orders.query.get(sid)
                    holdvec[45] = get_dispatch(odat)
                    for idate in range(4):
                        addnow = request.values.get(f'add{idate}')
                        movedate = thisdate + timedelta(idate)
                        if addnow is not None:
                            print(f'Adding the dispatch selection to date {movedate}')
                            addtopins(movedate,[odat])
            else:
                err.append('Too many selections for paste buffer task')
        for idate in range(4):
            movedate = thisdate + timedelta(idate)
            holdvec[46].append([movedate, f'{idate}', Pins.query.filter(Pins.Date == movedate).all()])
        else:
            err.append('No selection made for paste buffer task')

    err = erud(err)
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
    if color_selector is not None:

        # Determine if time filter applies to query:
        if 'Date Filter' in tfilters:
            dtest = tfilters['Date Filter']
            if dtest is not None and dtest != 'Show All' and 'Date' in filteron:
                daysback = None
                fromdate = None
                todate = None
                if '30' in dtest: daysback = 30
                elif '60' in dtest: daysback = 60
                elif '90' in dtest: daysback = 90
                elif '120' in dtest: daysback = 120
                elif '180' in dtest: daysback = 180
                elif dtest == 'Last Year':
                    fromdate = datetime.date(lastyear,1,1)
                    todate = datetime.date(lastyear,12,31)
                elif dtest == 'This Year':
                    fromdate = datetime.date(thisyear,1,1)
                if daysback is not None: fromdate = today - datetime.timedelta(days=daysback)
                if fromdate is not None: query_adds.append(f'{table}.Date >= fromdate')
                if todate is not None: query_adds.append(f'{table}.Date <= todate')
                #print(f'This time filter applied from fromdate = {fromdate} to todate = {todate}')

        # Determine if pay filter applies to query:
        if 'Pay Filter' in tfilters:
            itest = tfilters['Pay Filter']
            if itest is not None and itest != 'Show All' and 'Invoice' in filteron:
                if itest == 'Uninvoiced':
                    pfilter = f'({table}.Istat == None)  | ({table}.Istat < 1)'
                elif itest == 'Unrecorded':
                    pfilter = f'{table}.Istat == 1'
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

        print(tfilters,filteron)
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

    #print(table_query)
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
                #print(f'for {odat.Jo} color selector value is {color_selector_value} on selector {selector}')
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

    return [data1, data1id, rowcolors1, rowcolors2, entrydata, simpler, boxchecks, boxlist], labpass

def get_new_Jo(input):
    sdate = today.strftime('%Y-%m-%d')
    return newjo(input, sdate)


def make_new_entry(tablesetup,holdvec):
    table = tablesetup['table']
    entrydata = tablesetup['entry data']
    masks = tablesetup['haulmask']
    id = None
    if masks != []: entrydata = mask_apply(entrydata, masks)
    try:
        hiddendata = tablesetup['hidden data']
    except:
        hiddendata = []
    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    creators = tablesetup['creators']
    ukey = tablesetup['ukey']
    documents = tablesetup['documents']
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
    #print('class8_tasks.py 338 make_new_entry() Making new database entry using phrase:',dbnew)
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
                    print(f'Moved file {oldpath} to {newpath}')
                except:
                    print('File already moved')
                # Test to see if file exists
                if os.path.isfile(newpath):
                    print('The file exists')
                else:
                    print('The file does not exist')
                    newfile = None

                print(f'Setting Source attribute for New Entry in Table {table} with ID {id} to {newfile}')
                setattr(dat, 'Source', newfile)
                setattr(dat, 'Scache', 0)
                db.session.commit()


    else:
        print('Data not found')

    return err, id

#def New_task(task_iter, tablesetup, task_focus, checked_data):
def mask_apply(entrydata, masks):
    mask_to_apply = request.values.get('HaulType')
    list = Trucking_genre['haul_types']
    #print(mask_to_apply)
    if mask_to_apply in list:
        #print(f'the list is {list}')
        this_index = list.index(mask_to_apply)
        #print(f'the index is {this_index}')
        for jx, entry in enumerate(entrydata):
            if 'Release' in entry[1]:
                mask = masks['release']
                entrydata[jx][2] = mask[this_index]
            if 'Container' in entry[1]:
                mask = masks['container']
                entrydata[jx][2] = mask[this_index]
            if 'Load At' in entry[1]:
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
            if 'Third Date' in entry[1]:
                mask = masks['load3date']
                entrydata[jx][2] = mask[this_index]

        entrydata = [v for v in entrydata if v[2] != 'no']
    return entrydata

def check_appears(tablesetup, entry):
    checks = tablesetup['appears_if']
    testval = entry[4]
    testmat = checks[testval]
    colmat = checks[entry[0]]
    havedat = request.values.get(testval)
    if havedat is not None:
        for test in testmat:
            if test in havedat:
                print(test,havedat)
                return colmat
        print('checkappears',testval,testmat,colmat,havedat)
    #print(f'checkvals returning {entry[3]} and {entry[4]}')
    return entry[3], entry[4]

def New_task(tablesetup, task_iter):
    completed = False
    err = [f"Running New task with task_iter {task_iter} using {tablesetup['table']}"]
    form_show = tablesetup['form show']['New']
    form_checks = tablesetup['form checks']['New']
    print(f'Entering New Task with task iter {task_iter}')

    cancelnow = request.values.get('Cancel')
    if cancelnow is not None:
        entrydata = tablesetup['entry data']
        masks = tablesetup['haulmask']
        if masks != []: entrydata = mask_apply(entrydata, masks)
        numitems = len(entrydata)
        holdvec = [''] * numitems
        completed = True
    else:

        if task_iter > 0:
            entrydata = tablesetup['entry data']
            masks = tablesetup['haulmask']
            if masks != []: entrydata = mask_apply(entrydata, masks)
            numitems = len(entrydata)
            holdvec = [''] * numitems
            failed = 0
            warned = 0

            for jx, entry in enumerate(entrydata):
                print(f'Entry loop: jx"{jx}, entry:{entry}')
                if entry[3] == 'appears_if':
                    entry[3], entry[4] = check_appears(tablesetup, entry)
                    entrydata[jx][3],entrydata[jx][4] = entry[3], entry[4]
                print(f'form show is:{form_show}')
                if entry[4] is not None and (entry[9] == 'Always' or entry[9] in form_show):
                    if entry[1] != 'hidden':
                        holdvec[jx] = request.values.get(f'{entry[0]}')
                        if entry[0] in form_checks: required = True
                        else: required = False
                        holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], 'New', required)
                        if entry[5] > 1: failed = failed + 1
                        if entry[5] == 1: warned = warned + 1

            if 'bring data' in tablesetup:
                for bring in tablesetup['bring data']:
                    tab1, sel, tab2, cat, colist1, colist2 = bring
                    print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
                    valmatch = request.values.get(sel)
                    print(valmatch)
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
                        print(f'Updating Orders with {sid}')
                        Order_Container_Update(sid)
                    if tablesetup['table'] == 'Bills':
                        bdat = Bills.query.filter(Bills.id>0).order_by(Bills.id.desc()).first()
                        if bdat is not None:
                            pdat = People.query.filter(People.Company == bdat.Company).first()
                            if pdat is not None:
                                bid = bdat.id
                                bdat.Pid = pdat.id
                                db.session.commit()
                                bdat = Bills.query.get(bid)
                            err = gledger_write(['newbill'], bdat.Jo, bdat.bAccount, bdat.pAccount)
                else:
                    err.append(f'Cannot create entry until input errors shown in red below are resolved')

        else:
            holdvec = [''] * 60
            entrydata = tablesetup['entry data']
            for jx, entry in enumerate(entrydata):
                if entry[0] in form_checks: required = True
                else: required = False
                holdvec[jx], entry[5], entry[6] = form_check(entry[0],holdvec[jx], entry[4], 'New', required)


    return holdvec, entrydata, err, completed


def Edit_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):
    err = [f"Running Edit task with task_iter {task_iter} using {tablesetup['table']}"]
    completed = False
    viewport = ['0'] * 6

    table = tablesetup['table']
    entrydata = tablesetup['entry data']
    masks = tablesetup['haulmask']
    if masks != []: entrydata = mask_apply(entrydata, masks)
    hiddendata = tablesetup['hidden data']
    numitems = len(entrydata)
    holdvec = [''] * numitems

    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    colorcol = tablesetup['colorfilter']
    creators = tablesetup['creators']  # Gather the data for the selected row
    nextquery = f"{table}.query.get({sid})"
    olddat = eval(nextquery)
    form_show = tablesetup['form show']['Edit']
    form_checks = tablesetup['form checks']['Edit']

    print(f'Running edit with task_iter {task_iter}')

    if task_iter > 0:
        failed = 0
        warned = 0

        for jx, entry in enumerate(entrydata):
            if entry[3] == 'appears_if':
                entry[3], entry[4] = check_appears(tablesetup, entry)
                entrydata[jx][3],entrydata[jx][4] = entry[3], entry[4]
                print(f'Return from check_appears is {entry[3]} and {entry[4]}')
            #print(f'Getting values for entry4:{entry[4]} entry9:{entry[9]} formshow:{form_show}')
            if entry[4] is not None and (entry[9] == 'Always' or entry[9] in form_show):
                # Some items are part of bringdata so do not test those - make sure entry[4] is None for those
                holdvec[jx] = request.values.get(f'{entry[0]}')
                if entry[0] in form_checks: required = True
                else: required = False
                holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], 'Edit', required)
                if entry[5] > 1: failed = failed + 1
                if entry[5] == 1: warned = warned + 1

        if 'bring data' in tablesetup:
            for bring in tablesetup['bring data']:
                tab1, sel, tab2, cat, colist1, colist2 = bring
                print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
                valmatch = request.values.get(sel)
                print(valmatch)
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
                print('No color selector found')

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
                    err = gledger_write(['newbill'], bdat.Jo, bdat.bAccount, bdat.pAccount)
                if table == 'Orders':
                    print(f'Updating Orders with {sid}')
                    Order_Container_Update(sid)
                #err.append(f"Updated entry in {tablesetup['table']}")
                completed = True

                # Test of bring data-modify the database at this point
                if 'bring data' in tablesetup:
                    for bring in tablesetup['bring data']:
                        tab1, sel, tab2, cat, colist1, colist2 = bring
                        print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
                        valmatch = request.values.get(sel)
                        print(valmatch)
                        escript = f'{tab2}.query.filter({tab2}.{cat} == valmatch).first()'
                        print(escript)
                        adat = eval(escript)
                        if adat is not None:
                            for jx, col in enumerate(colist1):
                                thisval = getattr(adat, col)
                                setattr(olddat, colist2[jx], thisval)
                                print(f'Moving value {thisval} from {tab2} {col} to {table} {colist2[jx]}')
                            db.session.commit()
                    #olddat = eval(nextquery)
                    #for jx, entry in enumerate(entrydata): holdvec[jx] = getattr(olddat, f'{entry[0]}')
            else:
                err.append(f'Cannot update entry until input errors shown in red below are resolved')

        cancel_item = request.values.get('Cancel')
        if cancel_item is not None:
            print('Canceling the edit')
            completed = True

    else:
        # Gather the data for the selected row
        nextquery = f"{table}.query.get({sid})"
        olddat = eval(nextquery)

        for jx, entry in enumerate(entrydata):
            if entry[3] == 'appears_if': entrydata[jx][3], entrydata[jx][4] = check_appears(tablesetup, entry)
            holdvec[jx] = getattr(olddat, f'{entry[0]}')
            if entry[0] in form_checks: required = True
            else: required = False
            holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], 'Edit', required)





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
                nstat = odat.Hstat
                if task_focus == 'Haul+1':
                    if nstat+1 < 5: odat.Hstat = nstat+1
                if task_focus == 'Haul-1':
                    if nstat-1 > -1: odat.Hstat = nstat-1
                if task_focus == 'Haul Done': odat.Hstat = 3
            if 'Inv' in task_focus:
                nstat = odat.Istat
                if task_focus == 'Inv+1':
                    if nstat+1 < 5: odat.Istat = nstat+1
                if task_focus == 'Inv-1':
                    if nstat-1 > -1: odat.Istat = nstat-1
                if task_focus == 'Inv Emailed': odat.Istat = 3
    db.session.commit()
    holdvec, entrydata, err = [], [], []
    viewport = ['0'] * 6
    completed = True


    return holdvec, entrydata, err, viewport, completed

def Undo_task(genre, task_focus, task_iter, nc, tids, tabs):
    print(f'Running Undo Task with genre={genre}, task_iter={task_iter}, task_focus = {task_focus}, tids= {tids} tabs= {tabs}')
    for jx, thistable in enumerate(tabs):
        tablesetup = eval(f'{thistable}_setup')
        table = tablesetup['table']
        print('table', table)
        for sid in tids[jx]:
            if task_focus == 'Delete':
                #print('made it here with jx, thistable sid', jx, thistable, sid)
                rstring = f'{table}.query.filter({table}.id == {sid}).delete()'
                eval(rstring)
                db.session.commit()
            elif task_focus == 'Invoice':
                # Need to add the undo of the journal entries
                rstring = f'{table}.query.get({sid})'
                odat = eval(rstring)
                odat.Invoice = None
                odat.Istat = 0
                odat.Links = None
                odat.BalDue = None
                odat.InvoTotal = None
                odat.Payments = '0.00'
                db.session.commit()
                Invoices.query.filter(Invoices.Jo == odat.Jo).delete()
                Income.query.filter(Income.Jo == odat.Jo).delete()
                Gledger.query.filter(Gledger.Tcode == odat.Jo).delete()
                db.session.commit()

            elif table == 'Orders' and task_focus == 'Payment':
                rstring = f'{table}.query.get({sid})'
                odat = eval(rstring)
                sinow = odat.Label
                slead = SumInv.query.filter((SumInv.Si == sinow) & (SumInv.Status > 0)).first()
                odata = Orders.query.filter(Orders.Label == sinow).all()
                if slead is not None: print(f'Undoing sinow {sinow} slead id {slead.id} number of odata {len(odata)}')

                if slead is None:
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
                    odat.BalDue = odat.InvoTotal
                    db.session.commit()
                    jo = odat.Jo
                    idata = Invoices.query.filter(Invoices.Jo == jo).all()
                    for data in idata:
                        data.Status = 'New'
                    db.session.commit()
                    Income.query.filter(Income.Jo == jo).delete()
                    Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'IC')).delete()
                    Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'ID')).delete()
                    Gledger.query.filter((Gledger.Tcode == jo) & (Gledger.Type == 'DD')).delete()
                    db.session.commit()
                else:

                    for each in odata:
                        each.PaidInvoice = None
                        each.PayRef = None
                        each.PayMeth = None
                        each.PayAcct = None
                        each.PaidDate = None
                        each.PaidAmt = None
                        each.Istat = 6
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
                print('In the unpay bill section')
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



    #db.session.commit()

    holdvec, entrydata, err = [], [], []
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
            print(f'Viewing for table: {table} and focus {task_focus}')
            try:
                viewport[0] = 'show_doc_left'
                viewport[2] = '/' + tpath(f'{tpointer}', docref)
                print(f'path director:{tpointer} and path found:{viewport[2]}')
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
            print(f'Fileout:{fileout} ukey:{ukey}')

            uploadnow = request.values.get('uploadnow')

            if uploadnow is not None:
                viewport[0] = 'show_doc_right'
                file = request.files['docupload']
                if file.filename == '':
                    err.append('No file selected for uploading')

                name, ext = os.path.splitext(file.filename)
                if task_focus == 'Source':
                    sname = 'Scache'
                elif task_focus == 'Proof':
                    sname = 'Pcache'
                elif task_focus == 'TitleDoc':
                    sname = 'Tcache'

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
                    print(f'output1 for thistable {thistable}-{task_focus} = {output1}')

                if thistable == 'Interchange':
                    bn = 0
                    filename1 = f'{task_focus}_{fileout}{ext}'
                    output1 = addpath(tpath(f'{thistable}-{task_focus}', filename1))
                    print(f'output1 for thistable {thistable}-{task_focus} = {output1}')


                file.save(output1)
                viewport[2] = '/'+tpath(f'{thistable}-{task_focus}', filename1)

                if bn > 0:
                    if thistable == 'Orders':
                        oldfile = f'{task_focus}_{fileout}_c{str(sn)}{ext}'
                        oldoutput = addpath(tpath(f'{thistable}-{task_focus}', oldfile))

                        try:
                            os.remove(oldoutput)
                            err.append('Cleaning up old files successful')
                        except:
                            err.append('Cleaning up old files NOT successful')
                            err.append(f'Could not find {oldoutput}')

                setattr(dat, f'{task_focus}', filename1)
                if thistable == 'Orders': setattr(dat, sname, bn)
                db.session.commit()
                err.append(f'Viewing {filename1}')
                err.append('Hit Return to End Viewing and Return to Table View')
                returnhit = request.values.get('Return')
                if returnhit is not None: completed = True

    return holdvec, entrydata, err, viewport, completed



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

    from sqlalchemy import inspect
    inst = eval(f"inspect({table})")
    attr_names = [c_attr.key for c_attr in inst.mapper.column_attrs]
    ukey = tablesetup['ukey']
    documents = tablesetup['documents']
    viewport = None

    #Swaps are to auto-change the copy to have compliment values to the original value
    swaps = tablesetup['copyswaps']
    ckswaps = [key for key, value in swaps.items()]


    # Get a new JO or other creator value required for a table (can be none)
    for jx, entry in enumerate(entrydata):
        if entry[0] in creators:
            creation = [ix for ix in creators if ix == entry[0]][0]
            thisitem = eval(f"get_new_{creation}('{entry[3]}')")
            err = [f'New {creation} {thisitem} created']
            print(f'New {creation} {thisitem} created')

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

    err = [f"Running Manifest task with task_iter {task_iter} using {tablesetup['table']}"]
    completed = False
    viewport = ['0'] * 6

    table = tablesetup['table']
    entrydata = tablesetup['entry data']
    hiddendata = tablesetup['hidden data']
    numitems = len(entrydata)
    holdvec = [''] * numitems
    masks = tablesetup['haulmask']
    if masks != []: entrydata = mask_apply(entrydata, masks)

    form_checks = tablesetup['form checks']['Manifest']
    form_show = tablesetup['form show']['Manifest']

    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    creators = tablesetup['creators']  # Gather the data for the selected row
    nextquery = f"{table}.query.get({sid})"
    modata = eval(nextquery)


    returnhit = request.values.get('Finished')
    if returnhit is not None: completed = True
    else:
        if task_iter > 0:
            failed = 0
            warned = 0
            for jx, entry in enumerate(entrydata):
                if entry[3] == 'appears_if':
                    entry[3], entry[4] = check_appears(tablesetup, entry)
                    entrydata[jx][3], entrydata[jx][4] = entry[3], entry[4]
                    print(f'Return from check_appears is {entry[3]} and {entry[4]}')
                #print(f'Getting values for entry4:{entry[4]} entry9:{entry[9]} formshow:{form_show}')
                if entry[4] is not None and (entry[9] == 'Always' or entry[9] in form_show):
                    # Some items are part of bringdata so do not test those - make sure entry[4] is None for those
                    holdvec[jx] = request.values.get(f'{entry[0]}')
                    if entry[0] in form_checks: required = True
                    else: required = False
                    holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], 'Manifest', required)
                    if entry[5] > 1: failed = failed + 1
                    if entry[5] == 1: warned = warned + 1

            if 'bring data' in tablesetup:
                for bring in tablesetup['bring data']:
                    tab1, sel, tab2, cat, colist1, colist2 = bring
                    print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
                    valmatch = request.values.get(sel)
                    print(valmatch)
                    escript = f'{tab2}.query.filter({tab2}.{cat} == valmatch).first()'
                    adat = eval(escript)
                    if adat is not None:
                        for jx, col in enumerate(colist1):
                            thisval = getattr(adat, col)
                            for ix, entry in enumerate(entrydata):
                                if entry[0] == colist2[jx]:
                                    holdvec[ix] = thisval
                                    # print(f'Moving value {thisval} from {tab2} {col} to {table} {colist2[jx]}')

            err.append(f'There are {failed} input errors and {warned} input warnings')

            update_item = request.values.get('Update Manifest')
            if update_item is not None:
                try:
                    thisvalue = getattr(modata, colorcol[0])
                    if thisvalue == -1: setattr(modata, colorcol[0], 0)
                except:
                    print('No color selector found')

                if failed == 0:
                    for jx, entry in enumerate(entrydata):
                        if entry[4] is not None and (entry[9] == 'Always' or entry[9] in form_show):
                            if entry[0] not in creators:
                                print(f'Setting entry {entry[0]} to {holdvec[jx]}')
                                setattr(modata, f'{entry[0]}', holdvec[jx])
                    db.session.commit()
                    for jx, entry in enumerate(hiddendata):
                        thisvalue = getattr(modata, entry[2])
                        try:
                            thisvalue = thisvalue.splitlines()
                            thissubvalue = thisvalue[0]
                        except:
                            thissubvalue = ''
                        # print('Updating Entry with', entry[0], thissubvalue)
                        setattr(modata, f'{entry[0]}', thissubvalue)
                    db.session.commit()
                else:
                    err.append(f'Cannot update entry until input errors shown in red below are resolved')

        else:
            # Gather the data for the selected row
            nextquery = f"{table}.query.get({sid})"
            modata = eval(nextquery)

            for jx, entry in enumerate(entrydata):
                if entry[3] == 'appears_if': entrydata[jx][3], entrydata[jx][4] = check_appears(tablesetup, entry)
                holdvec[jx] = getattr(modata, f'{entry[0]}')
                if entry[0] in form_checks: required = True
                else: required = False
                holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], 'Manifest', required)

        docref = makemanifest(modata)
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
            print(f'String for stamp in this location is {stampstring} and not in json format')
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
                info_mimemail(emaildata)

        holdvec[15] = stamplist
        #holdvec[4] = emaildata
        # Send in the emaildata in case it get modified by the stamps
        holdvec[4], holdvec[5], dockind, docref, err, fexist = makepackage(genre, odat, task_iter, document_profiles, stamplist, stampdata, eprof, err, emaildata)
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
            print('Exiting after email requested completed')
            if 'Invoice' in dockind:
                print('This is an invoice based package')
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
        print(f'Using the summary invoice sinow={sinow} slead is {slead.id}')


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
            print(f'The updated paid invoice file is {basefile}')
            odat.PaidInvoice = basefile
            odat.Icache = cache+1
            db.session.commit()
            print(f'The updated paid invoice file is {basefile}')
            docref = f'static/{scac}/data/vPaidInvoice/{basefile}'
        else:
            invofile = addpath(tpath('Orders-Invoice', slead.Source))
            cache = odat.Icache
            basefile = addpayment(invofile, cache, slead.Total, amtpaid, paidon,  payref, paymethod)
            print(f'The updated paid summary invoice file is {basefile}')
            for each in odata:
                each.PaidInvoice = basefile
                each.Icache = cache+1
            slead.Status = 4
            db.session.commit()
            print(f'The updated paid summery invoice file is {basefile}')
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
        print(f'holdvec at this point 1616 is {holdvec}')
        # Save the default payment parameters in holdvec[0]


        if record_requested or email_requested:
            if slead is None:
                jopaylist = [[jo, amtpaid, paidon,  payref, paymethod, depoacct]]
                err, success = income_record(jopaylist, err)
                if success:
                    if email_requested: info_mimemail(emaildata)
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
                        if email_requested: info_mimemail(emaildata)
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
    stopdate = today-datetime.timedelta(days=300)
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
    print('amts=',amts)
    print(holdvec[7],holdvec[8])
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
            print(f'The acctdb is {acctdb}')
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
        print(f'Length of odata is {len(odata)}')
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

                    print('autodis=',autodis,rec,owe)
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
                    jopaylist.append([invojo, recamount, recdate, holdvec[8], depmethod, acctdb])
                else:
                    success = False
                    err.append(f'Have no Invoice to Receive Against for JO={invojo}')
                    print(f'Have no Invoice to Receive Against for JO={invojo}')
            else:
                print(f'This job not included {thechecks[jx]}')

        if success:
            err, success = income_record(jopaylist, err)
            if success: completed = True
    return completed, err, holdvec

def get_billform_data(entrydata, tablesetup, holdvec, err, thisform):
    form_show = tablesetup['form show'][thisform]
    form_checks = tablesetup['form checks'][thisform]
    if thisform != 'MultiChecks': form_show.append('Always')
    failed = 0
    warned = 0
    for jx, entry in enumerate(entrydata):
        if entry[4] is not None and entry[9] in form_show:
            # Some items are part of bringdata so do not test those - make sure entry[4] is None for those
            holdvec[jx] = request.values.get(f'{entry[0]}')
            if entry[0] in form_checks: required = True
            else: required = False
            holdvec[jx], entry[5], entry[6] = form_check(entry[0], holdvec[jx], entry[4], thisform, required)
            if entry[5] > 1: failed = failed + 1
            if entry[5] == 1: warned = warned + 1

    if 'bring data' in tablesetup:
        for bring in tablesetup['bring data']:
            tab1, sel, tab2, cat, colist1, colist2 = bring
            print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
            valmatch = request.values.get(sel)
            print(valmatch)
            escript = f'{tab2}.query.filter({tab2}.{cat} == valmatch).first()'
            adat = eval(escript)
            if adat is not None:
                for jx, col in enumerate(colist1):
                    thisval = getattr(adat, col)
                    for ix, entry in enumerate(entrydata):
                        if entry[0] == colist2[jx]:
                            holdvec[ix] = thisval
                            # print(f'Moving value {thisval} from {tab2} {col} to {table} {colist2[jx]}')

    err.append(f'There are {failed} input errors and {warned} input warnings')
    return holdvec, err, failed

def altersids(bdata, locked):
    allsids = []
    for bdat in bdata:
        pd = bdat.Status
        print(f'For id {bdat.id} pd is {pd} and locked is {locked}')
        if locked: allsids.append(bdat.id)
        elif pd != 'Paid': allsids.append(bdat.id)
    sidon = []
    for sid in allsids:
        ck1 = request.values.get(f'Billout{sid}')
        ck2 = request.values.get(f'Billin{sid}')
        ck3 = request.values.get(f'Billhid{sid}')
        print(f'for sid {sid} ck1 is {ck1} and ck2 is {ck2} and ck3 is {ck3}')
        if ck1 == 'on': sidon.append(sid)
        if ck2 == 'on': sidon.append(sid)
    return allsids, sidon



def MultiChecks_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sids):

    err = [f"Running MultiChecks task with task_iter {task_iter} using {tablesetup['table']}"]
    print(f"Running MultiChecks task with task_iter {task_iter} using {tablesetup['table']} and sids {sids}")
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
    print(f'data trouble {bdat.id} {pdat.id} {bdat.bAccount}')
    bdata = Bills.query.filter(Bills.Pid == pdat.id).all()
    #This prelinary data provides all similar bills to the ones being referred
    if task_iter > 0:
        # Now can alter the mutli-bill check to include other bills of similar nature and remove as well per selections
        allsids, sids = altersids(bdata, locked)
    else:
        for dat in bdata:
            if dat.Status != 'Paid': allsids.append(dat.id)
    print(f"Updated MultiChecks task with task_iter {task_iter} using {tablesetup['table']} and sids {sids} and allsids {allsids}")

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
                print('Exiting in the paid out location')
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
                    holdvec, err, failed = get_billform_data(entrydata, tablesetup, holdvec, err, 'MultiChecks')
                    err.append(f'Failed is {failed}')

                    update_item = request.values.get('Update Item')
                    if update_item is not None or record_item is not None:
                        try:
                            thisvalue = getattr(bdat, colorcol[0])
                            if thisvalue == -1: setattr(bdat, colorcol[0], 0)
                        except:
                            print('No color selector found')

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
                                    # print('Updating Entry with', entry[0], thissubvalue)
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
                                    print(f'Bring Data: {tab1} {sel} {tab2} {cat} {colist1} {colist2}')
                                    valmatch = request.values.get(sel)
                                    print(valmatch)
                                    escript = f'{tab2}.query.filter({tab2}.{cat} == valmatch).first()'
                                    print(escript)
                                    adat = eval(escript)
                                    if adat is not None:
                                        for jx, col in enumerate(colist1):
                                            thisval = getattr(adat, col)
                                            for sid in sids:
                                                nextquery = f"{table}.query.get({sid})"
                                                bdat = eval(nextquery)
                                                setattr(bdat, colist2[jx], thisval)
                                                print(f'Moving value {thisval} from {tab2} {col} to {table} {colist2[jx]}')
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
                print('co is', co[10])
                adat = Accounts.query.filter((Accounts.Type == 'Bank') & (Accounts.Co == co[10])).first()
                for jx, entry in enumerate(entrydata):
                    holdvec[jx] = getattr(bdat, f'{entry[0]}')
                    aj = hasinput(holdvec[jx])
                    if aj == 0:
                        print(f'{entry[0]} {holdvec[jx]} {aj}')
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
            print(f'Writing checks with sids = {sids}')
            pmeth = request.values.get('pMeth')
            if pmeth is None: pmeth = 'Check'
            docref, file1, cache, style = writechecks(sids,pmeth)
            print(f'The check style is {style}')
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
                except: print(f'{lastfile} does not exist')

            if record_item is not None:
                for sid in sids:
                    nextquery = f"{table}.query.get({sid})"
                    each_bdat = eval(nextquery)
                    err = gledger_write(['paybill'], each_bdat.Jo, each_bdat.bAccount, each_bdat.pAccount)
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


            print(f'Exiting in the comleted section completed is {completed}')

            return holdvec, entrydata, err, viewport, completed

        else:
            print('Exiting in the gofwd section')
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
        print('Exiting in the no sids location')
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
    print(table_setup['table'])
    tfilters = {}
    tfilters['Driver Filter'] = selected_driver
    print(tfilters)
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

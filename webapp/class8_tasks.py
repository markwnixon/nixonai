from webapp import db
from webapp.models import DriverAssign, Gledger, Vehicles, Invoices, JO, Income, Orders, Accounts, LastMessage, People, Interchange, Drivers, ChalkBoard, Services, Drops, StreetTurns
from flask import render_template, flash, redirect, url_for, session, logging, request
from webapp.CCC_system_setup import myoslist, addpath, tpath, companydata, scac
from webapp.InterchangeFuncs import Order_Container_Update, Match_Trucking_Now, Match_Ticket
from webapp.email_appl import etemplate_truck

import datetime
import os
import subprocess
from func_cal import calmodalupdate
import json

#Python functions that require database access
from webapp.class8_utils import *
from webapp.utils import *
from webapp.viewfuncs import newjo
import uuid

def get_drop(loadname):
    dropdat = Drops.query.filter(Drops.Entity == loadname).first()
    if dropdat is not None:
        print('dropdat',dropdat.Entity, dropdat.Addr1, dropdat.Addr2, dropdat.Phone, dropdat.Email)
        dline = f'{dropdat.Entity}\n{dropdat.Addr1}\n{dropdat.Addr2}\n{dropdat.Phone}\n{dropdat.Email}'
        dline = dline.replace('None','')
        return dline
    else:
        return ''

def Table_maker(genre):
    username = session['username'].capitalize()
    # Gather information about the tables inside the genre
    if genre == 'Trucking':
        from class8_dicts import Trucking_genre, Orders_setup, Interchange_setup, Customers_setup, Services_setup
    elif genre == 'Ocean':
        from class8_dicts import Ocean_genre, OverSeas_setup, Interchange_setup, Customers_setup, Services_setup

    genre_tables = eval(f"{genre}_genre['genre_tables']")
    quick_buttons = eval(f"{genre}_genre['quick_buttons']")
    table_filters = eval(f"{genre}_genre['table_filters']")
    task_boxes = eval(f"{genre}_genre['task_boxes']")

    scac = 'FELA'
    leftsize = 8
    rightsize = 12 - leftsize
    leftscreen = 1
    err = []
    table_data = []
    tabletitle = []
    jscripts = []
    tfilters = {}
    tboxes = {}

    if request.method == 'POST':

        # See if a task is active and ongoing
        taskon = nononestr(request.values.get('taskon'))
        focus = nononestr(request.values.get('focus'))
        task_iter = nonone(request.values.get('task_iter'))

        cancel = request.values.get('Cancel')
        if cancel is not None:
            taskon = None
            task_iter = 0

        print('taskon here is', taskon)
        taskon = nononestr(taskon)

        # Get data only for tables that have been checked on
        genre_tables_on = checked_tables(genre_tables)
        tables_on = [ix for jx, ix in enumerate(genre_tables) if genre_tables_on[jx] == 'on']

        # Only check the launch filter menus if no task is running
        if not hasinput(taskon):
            # See if a new task has been launched from quick buttons; set launched to New/Mod/Inv/Ret else set launched to None
            launched = [ix for ix in quick_buttons if request.values.get(ix) is not None]
            taskon = launched[0] if launched != [] else None
            focus = eval(f"{genre}_genre['table']")

        if not hasinput(taskon):
            # See if a task box has been selected
            for box in task_boxes:
                for key, value in box.items():
                    tboxes[key] = request.values.get(key)
                    if tboxes[key] is not None:
                        taskon_list = tboxes[key].split()
                        taskon = taskon_list[0]
                        remainder = tboxes[key].replace(taskon,'')
                        remainder = remainder.strip()
                        focus = eval(f"{genre}_genre['task_mapping']['{remainder}']")


            print('Tboxes:', tboxes)

        # See if a table filter has been selected, this can take place even during a task
        for filter in table_filters:
            for key, value in filter.items(): tfilters[key] = request.values.get(key)
        print(tfilters)

        # Reset colors for color filter in primary table:
        # eval(f"{genre}_genre['table_filters']['Color filters")
        if tfilters['Color Filter'] == 'Haul':
            Orders_setup['colorfilter'] = ['Hstat']
        elif tfilters['Color Filter'] == 'Invoice':
            Orders_setup['colorfilter'] = ['Istat']
        elif tfilters['Color Filter'] == 'Both':
            Orders_setup['colorfilter'] = ['Hstat', 'Istat']


    else:
        genre_tables_on = ['off'] * len(genre_tables)
        genre_tables_on[0] = 'on'
        tables_on = ['Orders']
        # Default time filter on entry into table is last 60 days:
        tfilters = {'Date Filter': 'Last 60 Days', 'Pay Filter': None, 'Haul Filter': None, 'Color Filter': 'Haul'}
        jscripts = ['dtTrucking']
        taskon, task_iter, focus = None, None, None

    # genre_data = [genre,genre_tables,genre_tables_on,contypes]
    genre_data = eval(f"{genre}_genre")
    genre_data['genre_tables_on'] = genre_tables_on
    print(genre_data['table'])
    print(genre_data['genre_tables'])
    print(genre_data['genre_tables_on'])
    print(genre_data['container_types'])
    print(genre_data['load_types'])

    # Execute the task here if a task is on...,,,,
    if taskon != '' and taskon != None:
        rstring = f"{taskon}_task(task_iter,{focus}_setup)"
        print(rstring)
        holdvec, entrydata, err = eval(rstring)
        task_iter = int(task_iter) + 1
        for e in err:
            if 'Created' in e:
                taskon = None
                task_iter = 0
        if request.values.get('Cancel') is not None:
            err = ['New entry cancelled']
            taskon = None
            task_iter = 0
            holdvec = [''] * 30
            entrydata = []
    else:
        task_iter = 0
        holdvec = [''] * 30
        entrydata = []
        err = ['All is well']

    # print(int(filter(check.isdigit, check)))
    docref = ''
    oder = 0
    modata = 0
    modlink = 0

    # color_selectors = ['Istat', 'Status']
    for jx, tableget in enumerate(tables_on):
        tabletitle.append(tableget)
        table_setup = eval(f'{tableget}_setup')
        print(table_setup)
        db_data = get_dbdata(table_setup, tfilters)
        table_data.append(db_data)
        jscripts.append(eval(f"{tableget}_setup['jscript']"))

        # For tables that are on get side data required for tasks:
        side_data = eval(f"{tableget}_setup['side data']")
        keydata = {}
        for side in side_data:
            for key, values in side.items():
                select_value = values[2]
                if 'get_' in select_value:
                    find = select_value.replace('get_','')
                    select_value = request.values.get(find)
                    print(select_value)
                if select_value is not None:
                    print(key, values, tableget)
                    dbstats = eval(
                        f"{values[0]}.query.filter({values[0]}.{values[1]}=='{select_value}').order_by({values[0]}.{values[3]}).all()")
                    if dbstats is not None:
                        dblist = []
                        for dbstat in dbstats:
                            nextvalue = eval(f'dbstat.{values[3]}')
                            nextvalue = nextvalue.strip()
                            if nextvalue not in dblist:
                                dblist.append(nextvalue)
                        keydata.update({key: dblist})
                        print(keydata)

    print(jscripts, holdvec)
    err = erud(err)
    return genre_data, table_data, err, oder, leftscreen,leftsize,docref, tabletitle, table_filters, task_boxes, tfilters, tboxes, jscripts,\
    taskon, task_iter, holdvec, keydata, entrydata, username, modata, focus

def get_dbdata(table_setup, tfilters):
    today = datetime.date.today()
    query_adds = []
    table = table_setup['table']
    print(table)
    highfilter = table_setup['filter']
    print(highfilter)
    highfilter_value = table_setup['filterval']
    entrydata = table_setup['entry data']
    print(entrydata)
    color_selector = table_setup['colorfilter']
    print(color_selector)

    # Apply built-in table filter:
    if highfilter is not None:
        query_adds.append(f"{table}.{highfilter} == '{highfilter_value}'")

    # If this table has no color capability then it cannot be filtered by date or type
    if color_selector is not None:

        # Determine if time filter applies to query:
        daysback = [int(word) for word in tfilters['Date Filter'].split() if word.isdigit()]
        daysback = daysback[0] if daysback != [] else None
        if daysback is not None:
            stopdate = today - datetime.timedelta(days=daysback)
            print('stopdate =', stopdate)
            query_adds.append(f'{table}.Date > stopdate')

        # Determine if pay filter applies to query:
        itest = tfilters['Pay Filter']
        if itest is not None and itest != 'Show All':
            if itest == 'Uninvoiced':
                pfilter = f'{table}.Istat == 0'
            elif itest == 'Unrecorded':
                pfilter = f'{table}.Istat == 1'
            elif itest == 'Unpaid':
                pfilter = f'{table}.Istat < 4'
            query_adds.append(pfilter)

        # Determine if haul filter applies to query:
        htest = tfilters['Haul Filter']
        if htest is not None and htest != 'Show All':
            if htest == 'Not Started':
                hfilter = f'{table}.Hstat == 0'
            elif htest == 'In-Progress':
                hfilter = f'{table}.Hstat == 1'
            elif htest == 'Incomplete':
                hfilter = f'{table}.Hstat < 2'
            elif htest == 'Completed':
                hfilter = f'{table}.Hstat >= 2'
            query_adds.append(hfilter)

    # Put the filters together from the 3 possible pieces: time, type1, type2
    if query_adds == []:
        table_query = f'{table}.query.all()'
    elif len(query_adds) == 1:
        table_query = f'{table}.query.filter({query_adds[0]}).all()'
    elif len(query_adds) == 2:
        table_query = f'{table}.query.filter(({query_adds[0]}) & ({query_adds[1]})).all()'
    else:
        table_query = f'{table}.query.filter(({query_adds[0]}) & ({query_adds[1]}) & ({query_adds[2]})).all()'

    print(table_query)
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
                if kx == 0: rowcolors1.append(colorcode(color_selector_value))
                if kx == 1: rowcolors2.append(colorcode(color_selector_value))
        else:
            color_selector_value = 0
            rowcolors1.append(colorcode(color_selector_value))
            rowcolors2.append(colorcode(color_selector_value))

        for jx, colist in enumerate(entrydata):
            co = colist[0]
            datarow[jx] = getattr(odat, co)
        data1.append(datarow)

    if color_selector is not None:
        if len(color_selector) == 1: rowcolors2 = rowcolors1

    return [data1, data1id, rowcolors1, rowcolors2, entrydata]

def get_new_Jo(input):
    sdate = today.strftime('%Y-%m-%d')
    return newjo(input, sdate)


def make_new_entry(tablesetup,data):
    table = tablesetup['table']
    entrydata = tablesetup['entry data']
    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    creators = tablesetup['creators']
    ukey = tablesetup['ukey']

    err = 'No Jo Created'
    from sqlalchemy import inspect
    inst = eval(f"inspect({table})")
    attr_names = [c_attr.key for c_attr in inst.mapper.column_attrs]

    for jx,entry in enumerate(entrydata):
        if entry[0] in creators:
            creation = [ix for ix in creators if ix == entry[0]][0]
            data[jx] = eval(f"get_new_{creation}('{entry[3]}')")
            err = f'New {creation} {data[jx]} created'

    print('The attr_names are:',attr_names)
    for c_attr in inst.mapper.column_attrs:
        print('Attrloop:',c_attr)

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
    print('The dbnew phrase is:',dbnew)
    input = eval(dbnew)
    db.session.add(input)
    db.session.commit()

    def checksplit(entry,dat):
        if entry == 'Company' or entry == 'Company2':
            return dat.splitlines()[0]
        else:
            return dat


    newquery = f"{table}.query.filter({table}.{ukey} == '{uidtemp}').first()"
    print(newquery)
    dat = eval(newquery)
    if dat is not None:
        for jx,entry in enumerate(entrydata):
            tdat = checksplit(entry,data[jx])
            setattr(dat,f'{entry[0]}',tdat)
        db.session.commit()
    else:
        print('Data not found')

    return err

def New_task(iter,tablesetup):
    err = [f'Running New task with iter {iter}']
    print(err)

    if iter > 0:
        entrydata = tablesetup['entry data']
        numitems = len(entrydata)
        holdvec = [''] * numitems
        failed = 0
        warned = 0

        for jx, entry in enumerate(entrydata):
            holdvec[jx] = request.values.get(f'{entry[0]}')
            holdvec[jx], entry[5], entry[6] = form_check(holdvec[jx], entry[4])
            if entry[5] > 1: failed = failed + 1
            if entry[5] == 1: warned = warned + 1
        err.append(f'There are {failed} input errors and {warned} input warnings')

        create_job = request.values.get('Create Job')
        if create_job is not None:
            if failed == 0:
                err.append(make_new_entry(tablesetup,holdvec))
                err.append(f"Created new entry in {tablesetup['table']}")
            else:
                err.append(f'Cannot create entry until input errors shown in red below are resolved')

    else:
        holdvec = [''] * 30
        entrydata = tablesetup['entry data']


    return holdvec, entrydata, err


def Mod_task(iter):
    print(f'Running Mod task with iter {iter}')

def Inv_task(iter):
    print(f'Running Inv task with iter {iter}')

def Rec_task(iter):
    print(f'Running Rec task with iter {iter}')

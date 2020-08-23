from webapp import db
from webapp.models import DriverAssign, Gledger, Vehicles, Invoices, JO, Income, Orders, Accounts, LastMessage, People, Interchange, Drivers, ChalkBoard, Services, Drops, StreetTurns
from flask import render_template, flash, redirect, url_for, session, logging, request
from webapp.CCC_system_setup import myoslist, addpath, tpath, companydata, scac
from webapp.InterchangeFuncs import Order_Container_Update, Match_Trucking_Now, Match_Ticket
from webapp.email_appl import etemplate_truck
from webapp.class8_dicts import Trucking_genre, Orders_setup, Interchange_setup, Customers_setup, Services_setup
from webapp.class8_tasks_manifest import makemanifest
from webapp.class8_money_tasks import MakeInvoice_task

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

def get_drop(loadname):
    dropdat = Drops.query.filter(Drops.Entity == loadname).first()
    if dropdat is not None:
        print('dropdat',dropdat.Entity, dropdat.Addr1, dropdat.Addr2, dropdat.Phone, dropdat.Email)
        dline = f'{dropdat.Entity}\n{dropdat.Addr1}\n{dropdat.Addr2}\n{dropdat.Phone}\n{dropdat.Email}'
        dline = dline.replace('None','')
        return dline
    else:
        return ''

def get_checked(thistable, data1id):
    numchecked = 0
    avec = []
    for id in data1id:
        name = thistable+str(id)
        ischeck = request.values.get(name)
        print(name,ischeck)
        if ischeck == 'on':
            numchecked = numchecked + 1
            avec.append(int(id))

    print(numchecked, avec)
    return numchecked, avec

def populate(tables_on,tabletitle,tfilters,jscripts):
    # print(int(filter(check.isdigit, check)))
    checked_data = []
    table_data = []
    keydata = {}

    # color_selectors = ['Istat', 'Status']
    for jx, tableget in enumerate(tables_on):
        tabletitle.append(tableget)
        table_setup = eval(f'{tableget}_setup')
        print(table_setup)
        db_data = get_dbdata(table_setup, tfilters)
        table_data.append(db_data)

        #Section to determine what items have been checked
        numchecked, avec = get_checked(tableget, db_data[1])
        print('returning checks numc, avec=',numchecked, avec)
        checked_data.append([tableget,numchecked,avec])
        print('after',checked_data)

        jscripts.append(eval(f"{tableget}_setup['jscript']"))

        # For tables that are on get side data required for tasks:
        side_data = eval(f"{tableget}_setup['side data']")
        print('class8_tasks.py 179 Tablemaker() For tables on get this side data:',side_data)
        keydata = {}
        for side in side_data:
            for key, values in side.items():
                select_value = values[2]
                if isinstance(select_value, str):
                    if 'get_' in select_value:
                        find = select_value.replace('get_','')
                        select_value = request.values.get(find)
                        print('class8_tasks.py 187 Tablemaker() select_value:',select_value)
                if select_value is not None:
                    print(key, values, tableget)
                    if isinstance(select_value, str):
                        dbstats = eval(
                        f"{values[0]}.query.filter({values[0]}.{values[1]}=='{select_value}').order_by({values[0]}.{values[3]}).all()")
                    if isinstance(select_value, int):
                        dbstats = eval(
                        f"{values[0]}.query.filter({values[0]}.{values[1]}=={select_value}).order_by({values[0]}.{values[3]}).all()")
                    if dbstats is not None:
                        dblist = []
                        for dbstat in dbstats:
                            nextvalue = eval(f'dbstat.{values[3]}')
                            if nextvalue is not None:  nextvalue = nextvalue.strip()
                            if nextvalue not in dblist:
                                dblist.append(nextvalue)
                        keydata.update({key: dblist})
                        print(keydata)
    return tabletitle, table_data, checked_data, jscripts, keydata

def reset_state(task_boxes, genre_tables):
    tboxes={}
    genre_tables_on = ['off'] * len(genre_tables)
    genre_tables_on[0] = 'on'
    tables_on = ['Orders']
    # Default time filter on entry into table is last 60 days:
    tfilters = {'Date Filter': 'Last 60 Days', 'Pay Filter': None, 'Haul Filter': None, 'Color Filter': 'Haul'}
    jscripts = ['dtTrucking']
    taskon, task_iter, task_focus = None, None, None
    viewport = ['tables'] + ['0'] * 5
    for box in task_boxes:
        for key, value in box.items():
            tboxes[key] = key
    return genre_tables_on, tables_on, tfilters, jscripts, taskon, task_iter, task_focus, tboxes, viewport

def run_the_task(genre, taskon, task_focus, tasktype, task_iter, checked_data, err):
    completed = False
    viewport = ['tables'] + ['0'] * 5
    # This rstring runs the task.  Task name is thetask_task and passes parameters: task_iter and focus_setup where focus is the Table data that goes with the task
    # If the task can be run for/with multiple Tables then the focus setup must be hashed wihin the specific task
    print('Ready to run the task:', taskon, 'with task focus', task_focus)

    if tasktype == 'Table_Selected':
        tablesetup = eval(f'{task_focus}_setup')
        rstring = f"{taskon}_task({task_focus}_setup, task_iter)"
        holdvec, entrydata, err, completed = eval(rstring)

    elif tasktype == 'Single_Item_Selection':
        holdvec, entrydata = [], []
        # See if only one box is checked and if so what table it is from
        nc = sum(cks[1] for cks in checked_data)
        tids = [cks[2] for cks in checked_data if cks[2] != []]
        tabs = [cks[0] for cks in checked_data if cks[1] != 0]
        print('nc=', nc)
        print(tids)
        print(tabs)
        if nc == 1:
            thistable = tabs[0]
            sid = tids[0][0]
            print('made it here with thistable sid taskiter', thistable, sid, task_iter)
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

    elif tasktype == 'Two_Item_Selection':
        holdvec, entrydata = [], []
        # See if only one box is checked and if so what table it is from
        nc = sum(cks[1] for cks in checked_data)
        tids = [cks[2] for cks in checked_data if cks[2] != []]
        tabs = [cks[0] for cks in checked_data if cks[1] != 0]
        print('nc=', nc)
        print(tids)
        print(tabs)
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
            print('returned with:', viewport, completed)

    return holdvec, entrydata, err, completed, viewport, tablesetup


def Table_maker(genre):
    username = session['username'].capitalize()

    # Gather information about the tables inside the genre
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

    if request.method == 'POST':

        # See if a task is active and ongoing
        tasktype = nononestr(request.values.get('tasktype'))
        taskon = nononestr(request.values.get('taskon'))
        task_focus = nononestr(request.values.get('task_focus'))
        task_iter = nonone(request.values.get('task_iter'))

        returnhit = request.values.get('Return')
        if returnhit is not None:
            # Asked to reset, so reset values as if not a Post
            genre_tables_on, tables_on, tfilters, jscripts, taskon, task_iter, task_focus, tboxes, viewport = reset_state(task_boxes, genre_tables)
        else:
            taskon = nononestr(taskon)

            # Get data only for tables that have been checked on
            genre_tables_on = checked_tables(genre_tables)
            tables_on = [ix for jx, ix in enumerate(genre_tables) if genre_tables_on[jx] == 'on']

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

                print('The task is:', taskon)
                print('The task focus is:', task_focus)
                print('The task_iter is:', task_iter)

            # See if a table filter has been selected, this can take place even during a task
            for filter in table_filters:
                for key, value in filter.items(): tfilters[key] = request.values.get(key)
            print('class8_tasks.py 110 Tablemaker() The filter settings are:',tfilters)

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
        genre_tables_on = ['off'] * len(genre_tables)
        genre_tables_on[0] = 'on'
        tables_on = ['Orders']
        # Default time filter on entry into table is last 60 days:
        tfilters = {'Date Filter': 'Last 60 Days', 'Pay Filter': None, 'Haul Filter': None, 'Color Filter': 'Haul'}
        jscripts = ['dtTrucking']
        taskon, task_iter, task_focus = None, None, None


    # Execute these parts whether it is a Post or Not:
    # genre_data = [genre,genre_tables,genre_tables_on,contypes]
    genre_data = eval(f"{genre}_genre")
    genre_data['genre_tables_on'] = genre_tables_on
    #print('class8_tasks.py 134 Tablemaker() Working table:',genre_data['table'])
    #print('class8_tasks.py 135 Tablemaker() Its genre tables',genre_data['genre_tables'])
    #print('class8_tasks.py 136 Tablemaker() Its genre tables on',genre_data['genre_tables_on'])
    #print('class8_tasks.py 137 Tablemaker() container types',genre_data['container_types'])
    #print('class8_tasks.py 138 Tablemaker() load types',genre_data['load_types'])

    # Populate the tables that are on with data
    tabletitle, table_data, checked_data, jscripts, keydata = populate(tables_on,tabletitle,tfilters,jscripts)

    # Execute the task here if a task is on...,,,,
    if hasvalue(taskon):
        holdvec, entrydata, err, completed, viewport, tablesetup = run_the_task(genre, taskon, task_focus, tasktype, task_iter, checked_data, err)
        if completed:
            genre_tables_on, tables_on, tfilters, jscripts, taskon, task_iter, task_focus, tboxes, viewport = reset_state(task_boxes, genre_tables)
            tabletitle, table_data, checked_data, jscripts, keydata = populate(tables_on, tabletitle, tfilters, jscripts)
        else: task_iter = int(task_iter) + 1

        #for e in err:
            #if 'Created' in e:
                #taskon = None
                #task_iter = 0
        if request.values.get('Cancel') is not None:
            genre_tables_on, tables_on, tfilters, jscripts, taskon, task_iter, task_focus, tboxes, viewport = reset_state(
                task_boxes, genre_tables)
            err = ['Entry canceled']
            taskon = None
            task_iter = 0
            holdvec = [''] * 30
            entrydata = []
            viewport = ['tables'] + ['0']*5
    else:
        taskon = None
        task_iter = 0
        tasktype = ''
        holdvec = [''] * 30
        entrydata = []
        err = ['All is well']
        tablesetup = None

    print(jscripts, holdvec)
    err = erud(err)
    if returnhit is not None:
        checked_data = [0,'0',['0']]

    return genre_data, table_data, err, leftsize, tabletitle, table_filters, task_boxes, tfilters, tboxes, jscripts,\
    taskon, task_focus, task_iter, tasktype, holdvec, keydata, entrydata, username, checked_data, viewport, tablesetup




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
    documents = tablesetup['documents']
    if 'Source' in documents:
        sourcekeys = tablesetup['source']
        newfile = sourcekeys[0]
        sourcekey = sourcekeys[1:]
    else:
        sourcekeys = None

    print(documents)
    print(sourcekeys)

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
    print('class8_tasks.py 338 make_new_entry() Making new database entry using phrase:',dbnew)
    input = eval(dbnew)
    db.session.add(input)
    db.session.commit()

    def checkmultisplit(entry,dat):
        print('entryis',entry,dat)
        if entry[3] == 'multitext' and len(dat)>0:
            return [dat.splitlines()[0], dat]
        else:
            return [dat]


    newquery = f"{table}.query.filter({table}.{ukey} == '{uidtemp}').first()"
    print('Getting the new temp entry:',newquery)
    dat = eval(newquery)
    if dat is not None:
        id = dat.id
        for jx,entry in enumerate(entrydata):
            tdat = checkmultisplit(entry,data[jx])
            if len(tdat)==1:
                print('About to set attribute:',dat,entry[0],tdat[0])
                setattr(dat,f'{entry[0]}',tdat[0])
            elif len(tdat)==2:
                print('About to set attribute:',dat,entry[0],tdat[0])
                setattr(dat,f'{entry[0]}',tdat[0])
                print('About to set attribute:',dat,entry[4],tdat[1])
                setattr(dat,f'{entry[4]}',tdat[1])
        db.session.commit()
        print('')

        if sourcekeys is not None:
            nextquery = f"{table}.query.get({id})"
            dat = eval(nextquery)
            print('Check to see if we need to save a source document:')
            docsave = request.values.get('viewport2')
            #newile already set at top of routine to the base name for document
            for eachsource in sourcekey:
                keyval = getattr(dat,eachsource)
                newfile = newfile + f'_Jo_{keyval}'

            newfile = newfile + '_c0.pdf'
            newfile = newfile.replace('None_','')
            print('Jo, viewport2, newfile', keyval, docsave, newfile)
            if hasinput(docsave):
                newpath = addpath(tpath(table, newfile))
                oldpath = addpath(docsave).replace('//','/')
                print('Need to move file from', oldpath, ' to', newpath)
                shutil.move(oldpath, newpath)
                setattr(dat, 'Source', newfile)
                setattr(dat, 'Scache', 0)
                db.session.commit()


    else:
        print('Data not found')

    return err

#def New_task(task_iter, tablesetup, task_focus, checked_data):

def New_task(tablesetup, task_iter):
    completed = False
    err = [f"Running New task with task_iter {task_iter} using {tablesetup['table']}"]

    if task_iter > 0:
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

        create_item = request.values.get('Create Item')
        if create_item is not None:
            if failed == 0:
                err.append(make_new_entry(tablesetup,holdvec))
                err.append(f"Created new entry in {tablesetup['table']}")
                completed = True
            else:
                err.append(f'Cannot create entry until input errors shown in red below are resolved')

    else:
        holdvec = [''] * 30
        entrydata = tablesetup['entry data']


    return holdvec, entrydata, err, completed


def Edit_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):
    err = [f"Running Edit task with task_iter {task_iter} using {tablesetup['table']}"]
    completed = False
    viewport = ['0'] * 6

    table = tablesetup['table']
    entrydata = tablesetup['entry data']
    numitems = len(entrydata)
    holdvec = [''] * numitems

    filter = tablesetup['filter']
    filterval = tablesetup['filterval']
    creators = tablesetup['creators']  # Gather the data for the selected row
    nextquery = f"{table}.query.get({sid})"
    olddat = eval(nextquery)

    if task_iter > 0:
        failed = 0
        warned = 0

        for jx, entry in enumerate(entrydata):
            holdvec[jx] = request.values.get(f'{entry[0]}')
            holdvec[jx], entry[5], entry[6] = form_check(holdvec[jx], entry[4])
            if entry[5] > 1: failed = failed + 1
            if entry[5] == 1: warned = warned + 1
        err.append(f'There are {failed} input errors and {warned} input warnings')

        update_item = request.values.get('Update Item')
        if update_item is not None:
            if failed == 0:
                for jx, entry in enumerate(entrydata): setattr(olddat, f'{entry[0]}', holdvec[jx])
                db.session.commit()
                err.append(f"Updated entry in {tablesetup['table']}")
                completed = True
            else:
                err.append(f'Cannot update entry until input errors shown in red below are resolved')

    else:
        # Gather the data for the selected row
        nextquery = f"{table}.query.get({sid})"
        olddat = eval(nextquery)

        for jx, entry in enumerate(entrydata): holdvec[jx] = getattr(olddat, f'{entry[0]}')

    viewport[0] = 'show_doc_left'
    docref = getattr(olddat, 'Source')
    viewport[2] = '/' + tpath(f'{table}', docref)

    return holdvec, entrydata, err, viewport, completed

def Inv_task(iter):
    print(f'Running Inv task with iter {iter}')

def Rec_task(iter):
    print(f'Running Rec task with iter {iter}')





def View_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):
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

        viewport[0] = 'show_doc_left'
        nextquery = f"{table}.query.get({sid})"
        dat = eval(nextquery)

        print('The task focus is:', task_focus)
        try:
            docref = getattr(dat, f'{task_focus}')
            try:
                viewport[2] = '/' + tpath(f'{table}', docref)
                err.append(f'Viewing {viewport[2]}')
                err.append('Hit Return to End Viewing and Return to Table View')
            except:
                err.append(f'Pathname {viewport[2]} not found')
        except:
            err.append(f'{table} has no attribute {task_focus}')

        returnhit = request.values.get('Return')
        if returnhit is not None: completed = True

    return holdvec, entrydata, err, viewport, completed



def Upload_task(genre, task_iter, tablesetup, task_focus, checked_data, thistable, sid):

    cancel = request.values.get('cancel')
    viewport = ['0'] * 6
    holdvec = []
    entrydata = []

    if cancel is not None:
        completed=True
        err = ['Upload has been cancelled']
    else:
        completed = False
        err = [f'Running Upload task with iter {task_iter}']


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
            print('the ukey=', ukey)
            viewport[5] = ukey + ': ' + eval(f"dat.{ukey}")
            fileout = ukey + '_' + eval(f"dat.{ukey}")
            print(viewport)

            uploadnow = request.values.get('uploadnow')

            if uploadnow is not None:
                viewport[0] = 'show_doc_right'
                file = request.files['docupload']
                if file.filename == '':
                    err.append('No file selected for uploading')
                else:
                    print('file is', file.filename)

                name, ext = os.path.splitext(file.filename)
                if task_focus == 'Source':
                    sname = 'Scache'
                elif task_focus == 'Proof':
                    sname = 'Pcache'

                sn = getattr(dat, sname)
                try:
                    sn = int(sn)
                    bn = sn+1
                except:
                    sn = 0
                    bn = 0

                filename1 = f'{task_focus}_{fileout}_c{str(bn)}{ext}'
                output1 = addpath(tpath(f'{thistable}', filename1))
                print('output1=',output1)

                file.save(output1)
                viewport[2] = '/'+tpath(f'{thistable}', filename1)

                if bn > 0:
                    oldfile = f'{task_focus}_{fileout}_c{str(sn)}{ext}'
                    oldoutput = addpath(tpath(f'{thistable}', oldfile))
                    try:
                        os.remove(oldoutput)
                        err.append('Cleaning up old files successful')
                    except:
                        err.append('Cleaning up old files NOT successful')
                        err.append(f'Could not find {oldoutput}')

                setattr(dat, f'{task_focus}', filename1)
                setattr(dat, sname, bn)
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

    err = [f"Running Edit task with task_iter {task_iter} using {tablesetup['table']}"]
    viewport = ['0'] * 6
    entrydata = tablesetup['entry data']
    numitems = len(entrydata)
    holdvec = [''] * numitems

    returnhit = request.values.get('Finished')
    if returnhit is not None: completed = True
    else:

        completed = False
        table = tablesetup['table']
        filter = tablesetup['filter']
        filterval = tablesetup['filterval']
        creators = tablesetup['creators']  # Gather the data for the selected row
        nextquery = f"{table}.query.get({sid})"
        modata = eval(nextquery)

        if task_iter > 0:
            failed = 0
            warned = 0

            for jx, entry in enumerate(entrydata):
                holdvec[jx] = request.values.get(f'{entry[0]}')
                holdvec[jx], entry[5], entry[6] = form_check(holdvec[jx], entry[4])
                if entry[5] > 1: failed = failed + 1
                if entry[5] == 1: warned = warned + 1
            err.append(f'There are {failed} input errors and {warned} input warnings')

            update_item = request.values.get('Update Item')
            if update_item is not None:
                if failed == 0:
                    for jx, entry in enumerate(entrydata): setattr(modata, f'{entry[0]}', holdvec[jx])
                    db.session.commit()
                    err.append(f"Updated entry in {tablesetup['table']}")
                    completed = True
                else:
                    err.append(f'Cannot update entry until input errors shown in red below are resolved')

        else:
            # Gather the data for the selected row
            nextquery = f"{table}.query.get({sid})"
            modata = eval(nextquery)
            for jx, entry in enumerate(entrydata): holdvec[jx] = getattr(modata, f'{entry[0]}')

        docref = makemanifest(modata)
        viewport[0] = 'show_doc_left'
        viewport[2] = '/' + tpath(f'manifest', docref)
        print('viewport=', viewport)

        err.append(f'Viewing {docref}')
        err.append('Hit Finished to End Viewing and Return to Table View')

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
    print('c11, c12', c11, c12)
    print('c21, c22', c21, c22)

    for jx, col in enumerate(c11):
        thisvalue1 = getattr(olddat1, f'{col}')
        thisvalue2 = getattr(olddat2, f'{c12[jx]}')
        print(f'For {col} comparing the values of {thisvalue1} in {table1} to {thisvalue2} in {table2}')
        setattr(olddat1, f'{col}', thisvalue2)
    db.session.commit()

    for jx, col in enumerate(c21):
        thisvalue1 = getattr(olddat1, f'{c22[jx]}')
        thisvalue2 = getattr(olddat2, f'{col}')
        print(f'For {col} comparing the values of {thisvalue1} in {table1} to {thisvalue2} in {table2}')
        setattr(olddat2, f'{col}', thisvalue1)
    db.session.commit()

    completed = True
    return holdvec, entrydata, err, viewport, completed










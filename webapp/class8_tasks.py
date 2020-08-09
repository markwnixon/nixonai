from webapp import db
from webapp.models import DriverAssign, Gledger, Vehicles, Invoices, JO, Income, Orders, Accounts, LastMessage, People, Interchange, Drivers, ChalkBoard, Services, Drops, StreetTurns
from flask import render_template, flash, redirect, url_for, session, logging, request
from webapp.CCC_system_setup import myoslist, addpath, tpath, companydata, scac
from webapp.InterchangeFuncs import Order_Container_Update, Match_Trucking_Now, Match_Ticket
from webapp.email_appl import etemplate_truck
from webapp.class8_dicts import Trucking_genre, Orders_setup, Interchange_setup, Customers_setup, Services_setup, Checkbox_Table1_setup

import datetime
import os
import subprocess
#from func_cal import calmodalupdate
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
    docref = ''
    oder = 0
    modata = 0
    modlink = 0
    checked_data = []
    table_data = []

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
                if 'get_' in select_value:
                    find = select_value.replace('get_','')
                    select_value = request.values.get(find)
                    print('class8_tasks.py 187 Tablemaker() select_value:',select_value)
                if select_value is not None:
                    print(key, values, tableget)
                    dbstats = eval(
                        f"{values[0]}.query.filter({values[0]}.{values[1]}=='{select_value}').order_by({values[0]}.{values[3]}).all()")
                    if dbstats is not None:
                        dblist = []
                        for dbstat in dbstats:
                            nextvalue = eval(f'dbstat.{values[3]}')
                            if nextvalue is not None:  nextvalue = nextvalue.strip()
                            if nextvalue not in dblist:
                                dblist.append(nextvalue)
                        keydata.update({key: dblist})
                        print(keydata)
    return tabletitle, table_data, checked_data, jscripts, keydata, oder, docref, modata

def Table_maker(genre):
    username = session['username'].capitalize()
    # Gather information about the tables inside the genre
    genre_tables = eval(f"{genre}_genre['genre_tables']")
    quick_buttons = eval(f"{genre}_genre['quick_buttons']")
    table_filters = eval(f"{genre}_genre['table_filters']")
    task_boxes = eval(f"{genre}_genre['task_boxes']")

    leftsize = 8
    rightsize = 12 - leftsize
    leftscreen = 1
    err = []

    tabletitle = []
    jscripts = []
    tfilters = {}
    tboxes = {}
    keydata = {}
    checked_data = []
    viewport = ['0']*6
    viewport[0] = 'tables'
    returnhit = None

    if request.method == 'POST':

        # See if a task is active and ongoing
        taskon = nononestr(request.values.get('taskon'))
        task_table = nononestr(request.values.get('task_table'))
        task_focus = nononestr(request.values.get('task_focus'))
        task_iter = nonone(request.values.get('task_iter'))

        returnhit = request.values.get('Return')
        if returnhit is not None:

            # Reset values as if not a Post
            genre_tables_on = ['off'] * len(genre_tables)
            genre_tables_on[0] = 'on'
            tables_on = ['Orders']
            # Default time filter on entry into table is last 60 days:
            tfilters = {'Date Filter': 'Last 60 Days', 'Pay Filter': None, 'Haul Filter': None, 'Color Filter': 'Haul'}
            jscripts = ['dtTrucking']
            taskon, task_iter, task_table, task_focus = None, None, None, None

        else:

            print('class8_tasks.py 78 Tablemaker() The taskon here is:', taskon)
            taskon = nononestr(taskon)

            # Get data only for tables that have been checked on
            genre_tables_on = checked_tables(genre_tables)
            tables_on = [ix for jx, ix in enumerate(genre_tables) if genre_tables_on[jx] == 'on']

            # Only check the launch boxes, filters, and task selections if no task is running
            if not hasinput(taskon):
                # See if a new task has been launched from quick buttons; set launched to New/Mod/Inv/Ret else set launched to None
                launched = [ix for ix in quick_buttons if request.values.get(ix) is not None]
                taskbase = launched[0].split() if launched != [] else None
                if taskbase:
                    taskon = taskbase[0]
                    task_focus = taskbase[1]
                    task_table = eval(f"{genre}_genre['table']")

                # See if a task box has been selected task has a focus and table where focus is the type of information
                for box in task_boxes:
                    for key, value in box.items():
                        tboxes[key] = request.values.get(key)
                        if tboxes[key] is not None:
                            taskon_list = tboxes[key].split()
                            taskon = taskon_list[0]
                            task_focus = tboxes[key].replace(taskon,'')
                            task_focus = task_focus.strip()
                            #task_focus = f"{genre}_genre['task_mapping']['{taskactive}']"
                            #print('The task focus is:', task_focus)
                            task_table = eval(f"{genre}_genre['task_mapping']['{task_focus}']")
                            print('The task_table is:', task_table)


                print('class8_tasks.py 105 Tablemaker() Tboxes:', tboxes)

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
        taskon, task_iter, task_table, task_focus = None, None, None, None


    # Execute these parts whether it is a Post or Not:
    # genre_data = [genre,genre_tables,genre_tables_on,contypes]
    genre_data = eval(f"{genre}_genre")
    genre_data['genre_tables_on'] = genre_tables_on
    print('class8_tasks.py 134 Tablemaker() Working table:',genre_data['table'])
    print('class8_tasks.py 135 Tablemaker() Its genre tables',genre_data['genre_tables'])
    print('class8_tasks.py 136 Tablemaker() Its genre tables on',genre_data['genre_tables_on'])
    print('class8_tasks.py 137 Tablemaker() container types',genre_data['container_types'])
    print('class8_tasks.py 138 Tablemaker() load types',genre_data['load_types'])

    tabletitle, table_data, checked_data, jscripts, keydata, oder, docref, modata = populate(tables_on,tabletitle,tfilters,jscripts)

    # Execute the task here if a task is on...,,,,
    #if taskon != '' and taskon != None:
    if hasvalue(taskon):

        #This rstring runs the task.  Task name is thetask_task and passes parameters: task_iter and focus_setup where focus is the Table data that goes with the task
        #If the task can be run for/with multiple Tables then the focus setup must be hashed wihin the specific task
        print('Ready to run the task:',taskon,'with task focus',task_focus, ' and using table:', task_table)
        if taskon == 'New' or taskon == 'Edit':
            rstring = f"{taskon}_task(task_iter, {task_table}_setup, task_focus, checked_data)"
            holdvec, entrydata, err, completed = eval(rstring)
            if completed:
                tabletitle, table_data, checked_data, jscripts, keydata, oder, docref, modata = populate(tables_on,tabletitle,tfilters,jscripts)

        elif taskon == 'Upload':
            holdvec, entrydata = [], []
            rstring = f"{taskon}_task(genre, task_iter, {task_table}_setup, task_focus, checked_data)"
            err, viewport, docref, completed = eval(rstring)
            print('returned with:',viewport,docref,completed)
            if completed:
                taskon, task_iter, task_table, task_focus = None, 0, None, None
                tabletitle, table_data, checked_data, jscripts, keydata, oder, docref, modata = populate(tables_on,tabletitle,tfilters,jscripts)

        if not completed: task_iter = int(task_iter) + 1
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
        taskon = None
        task_iter = 0
        holdvec = [''] * 30
        entrydata = []
        err = ['All is well']

    print(jscripts, holdvec)
    err = erud(err)
    if returnhit is not None:
        checked_data = [0,'0',['0']]
    return genre_data, table_data, err, oder, leftscreen, leftsize, docref, tabletitle, table_filters, task_boxes, tfilters, tboxes, jscripts,\
    taskon, task_focus, task_iter, holdvec, keydata, entrydata, username, modata, task_table, checked_data, viewport




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

def New_task(task_iter, tablesetup, task_focus, checked_data):
    completed = False
    err = [f'Running New task with task_iter {task_iter} and task_focus {task_focus}']
    print(err)

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


def Edit_Item_task(iter):
    print(f'Running Mod task with iter {iter}')

def Inv_task(iter):
    print(f'Running Inv task with iter {iter}')

def Rec_task(iter):
    print(f'Running Rec task with iter {iter}')

def View_task(genre, task_iter, tablesetup, task_focus, checked_data):
    cancel = request.values.get('cancel')
    viewport = ['0'] * 6
    docref = ''

    if cancel is not None:
        completed=True
        err = ['View has been cancelled']
    else:
        completed = False
        err = [f'Running View task with iter {task_iter}']
        err.append(f'genre:',genre)
        err.append(f'task_focus:', task_focus)

        print('checkeddata',checked_data)

        if task_iter == 0:
            viewport[0] = 'view_doc_left'
        else:
            viewport[0] = request.values.get('viewport0')
            viewport[2] = request.values.get('viewport2')

        #See if only one box is checked and if so what table it is from
        nc = sum(cks[1] for cks in checked_data)
        tids = (cks[2] for cks in checked_data if cks[2] != [])
        tabs = (cks[0] for cks in checked_data if cks[1] != 0)

        if nc == 1:
            thistable = next(tabs)
            avec = next(tids)

        elif nc > 1: err.append('Too many selections made for this task')
        else: err.append('Must make a single selection for this task')

        if nc == 1:
            sid = avec[0]
            nextquery = f"{thistable}.query.get({sid})"
            dat = eval(nextquery)
            viewport[3] = str(sid)
            viewport[4] = f'{genre} {thistable} Item'
            ukey = eval(f"{thistable}_setup['ukey']")
            print('the ukey=', ukey)
            viewport[5] = ukey + ': ' + eval(f"dat.{ukey}")
            fileout = ukey + '_' + eval(f"dat.{ukey}")
            print(viewport)

            viewitem = request.values.get('')

            filename1 = getattr(dat, sname)
            output1 = addpath(tpath(f'{thistable}', filename1))

            err.append(f'Viewing {filename1}')
            err.append('Hit Return to End Viewing and Return to Table View')
            returnhit = request.values.get('Return')
            if returnhit is not None: completed = True
        else:
            completed = True

        return err, viewport, docref, completed



def Upload_task(genre, task_iter, tablesetup, task_focus, checked_data):

    cancel = request.values.get('cancel')
    viewport = ['0'] * 6
    docref = ''

    if cancel is not None:
        completed=True
        err = ['Upload has been cancelled']
    else:
        completed = False
        err = [f'Running Source task with iter {task_iter}']


        if task_iter == 0:
            viewport[0] = 'upload_doc_right'
        else:
            viewport[0] = request.values.get('viewport0')
            viewport[2] = request.values.get('viewport2')

        #See if only one box is checked and if so what table it is from
        nc = sum(cks[1] for cks in checked_data)
        tids = (cks[2] for cks in checked_data if cks[2] != [])
        tabs = (cks[0] for cks in checked_data if cks[1] != 0)

        if nc == 1:
            thistable = next(tabs)
            avec = next(tids)

        elif nc > 1: err.append('Too many selections made for this task')
        else: err.append('Must make a single selection for this task')

        if nc == 1:
            sid = avec[0]
            nextquery = f"{thistable}.query.get({sid})"
            dat = eval(nextquery)
            viewport[3] = str(sid)
            viewport[4] = f'{genre} {thistable} Item'
            ukey = eval(f"{thistable}_setup['ukey']")
            print('the ukey=', ukey)
            viewport[5] = ukey + ': ' + eval(f"dat.{ukey}")
            fileout = ukey + '_' + eval(f"dat.{ukey}")
            print(viewport)

            uploadnow = request.values.get('uploadnow')
            if uploadnow is not None and nc == 1:
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

                file.save(output1)
                viewport[2] = '/'+tpath(f'{thistable}', filename1)

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
        else:
            completed = True

    return err, viewport, docref, completed







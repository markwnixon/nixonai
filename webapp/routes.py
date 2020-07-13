from flask import render_template, flash, redirect, url_for, session, logging, request, jsonify

from webapp import app, db, bcrypt
from webapp.models import users, ChalkBoard, Interchange, Orders, General
from webapp.models import Services, Drivers, JO, People, OverSeas, Chassis, LastMessage
from webapp.models import Autos, Bookings, Vehicles, Invoices, Income, Accounts, Bills, Drops, IEroll
from webapp.forms import RegistrationForm, LoginForm, TruckingFormNew
from flask_login import login_user, current_user, logout_user, login_required


import math
from decimal import Decimal
from random import sample

import datetime
from datetime import timedelta
import os
import json


from twilio.twiml.messaging_response import MessagingResponse
from webapp.messager import msg_analysis
import requests
import mimetypes
from urllib.parse import urlparse
import img2pdf
from webapp.viewfuncs import make_new_order, nonone, monvals, getmonths, nononestr, hasinput, d2s, erud

from webapp.class8_utils import *

today = datetime.datetime.today()
year = str(today.year)
day = str(today.day)
month = str(today.month)
now = datetime.datetime.now()

from webapp.CCC_system_setup import companydata, statpath, addpath, scac, tpath
cmpdata = companydata()

@app.route('/FileUpload', methods=['GET', 'POST'])
def FileUpload():
    err=[]
    uptype = request.values['uptype']
    print(uptype)
    oder = request.values['oid']
    oder = nonone(oder)
    print(oder)
    user = request.values['user']
    print(user)
    odat = Orders.query.get(oder)
    jo = odat.Jo
    pcache = odat.Pcache
    scache = odat.Scache
    fileob = request.files["file2upload"]
    name, ext = os.path.splitext(fileob.filename)
    if uptype == 'proof':
        filename1 = f'Proof_{jo}_c{str(pcache)}{ext}'
        filename2 = f'Proof_{jo}_c{str(pcache)}.pdf'
        output1 = addpath(tpath('poof', filename1))
        output2 = addpath(tpath('poof', filename2))
        odat.Pcache = pcache + 1
        db.session.commit()
    elif uptype == 'source':
        filename1 = f'Source_{jo}_c{str(scache)}{ext}'
        filename2 = f'Source_{jo}_c{str(scache)}.pdf'
        output1 = addpath(tpath('oder', filename1))
        output2 = addpath(tpath('oder', filename2))
        odat.Scache = scache + 1
        db.session.commit()
    if ext != '.pdf':
        try:
            fileob.save(output1)
            with open(output2, "wb") as f:
                f.write(img2pdf.convert(output1))
            os.remove(output1)
        except:
            filename2 = filename1
    else:
        fileob.save(output2)
    if uptype == 'proof':
        odat.Proof = filename2
    elif uptype == 'source':
        odat.Original = filename2
    db.session.commit()

    print(f'File {fileob.filename} uploaded as {filename2}')

    return "successful_upload"

@app.route('/chartdata', methods=['GET', 'POST'])
def chartdata():
    acct = request.values['thisacct']
    timestyle = request.values['thesemonths']
    import ast
    acct = ast.literal_eval(acct)
    print(acct,timestyle)
    print(type(timestyle))
    if timestyle in ['6', '12', '18', '24']:
        nmonths = int(timestyle)
        labeld = []
        datad = []
        lablist=monvals(nmonths)
        rgba = []
        rgb = []
        colors = [[31,105,161], [31,161,65], [161,141,31], [161,57,31], [161,31,141], [161,31,63], [31,53,161], [31,161,126]]
        for ix, plotitem in enumerate(acct):
            datad.append(getmonths(plotitem,nmonths,1))
            labeld.append(plotitem)
            rgba.append(f'rgba({colors[ix][0]}, {colors[ix][1]}, {colors[ix][2]}, 0.3)')
            rgb.append(f'rgb({colors[ix][0]}, {colors[ix][1]}, {colors[ix][2]})')
        return jsonify({'lablist' : lablist,
                        'labeld'  : labeld,
                        'datad'   : datad,
                        'rgba'    : rgba,
                        'rgb'     : rgb
                        })
    elif timestyle == 'lymon' or 'tymon':
        thisyear = datetime.datetime.today().year
        thismonth = datetime.datetime.today().month
        lastyear = thisyear - 1
        print(lastyear,thismonth)
        labeld = []
        datad = []
        lablist=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        if timestyle == 'lymon':
            start = thismonth
            stop = thismonth+12
            for ix, lab in enumerate(lablist):
                lablist[ix] = f'{lab} {lastyear}'
        else:
            start = 1
            stop = thismonth
            lablist = lablist[:stop-1]
            for ix, lab in enumerate(lablist):
                lablist[ix] = f'{lab} {thisyear}'


        rgba = []
        rgb = []
        colors = [[31,105,161], [31,161,65], [161,141,31], [161,57,31], [161,31,141], [161,31,63], [31,53,161], [31,161,126]]
        for ix, plotitem in enumerate(acct):
            datad.append(getmonths(plotitem,start,stop))
            labeld.append(plotitem)
            rgba.append(f'rgba({colors[ix][0]}, {colors[ix][1]}, {colors[ix][2]}, 0.3)')
            rgb.append(f'rgb({colors[ix][0]}, {colors[ix][1]}, {colors[ix][2]})')
        return jsonify({'lablist' : lablist,
                        'labeld'  : labeld,
                        'datad'   : datad,
                        'rgba'    : rgba,
                        'rgb'     : rgb
                        })


@app.route('/')
def index():
    srcpath = statpath('')
    return render_template(f'companysite/{scac}/about.html',srcpath=srcpath, cmpdata=cmpdata, scac=scac)

@app.route('/About')
def About():
    lang = 'English'
    srcpath = statpath('')
    return render_template(f'companysite/{scac}/about.html',srcpath=srcpath,cmpdata=cmpdata, scac=scac, lang=lang)

@app.route('/Whatapp', methods=['GET', 'POST'])
def Whatapp():
    token = os.environ['TWILIO_AUTH_TOKEN']
    print('token=',token)
    msg = request.form.get('Body')
    msg = msg.strip()
    sessionph = request.form.get('From')
    print('sessionph =',sessionph)
    media_files = []
    num_media = int(request.values.get("NumMedia"))
    if num_media > 0:
        for idx in range(num_media):
            media_url = request.values.get(f'MediaUrl{idx}')
            mime_type = request.values.get(f'MediaContentType{idx}')
            req = requests.get(media_url)
            file_extension = mimetypes.guess_extension(mime_type)
            file_extension = file_extension.replace('.jpe', '.jpg')
            file_extension = file_extension.replace('.jpeg', '.jpg')
            media_sid = os.path.basename(urlparse(media_url).path)
            media_files.append(media_sid+file_extension)
            media_path = addpath('static/data/processing/whatsapp/')
            with open(f"{media_path}{media_sid}{file_extension}", 'wb') as f:
                f.write(req.content)
        print(media_files)

    respmsg = msg_analysis(msg, sessionph, media_files)

    resp = MessagingResponse()
    msg = resp.message("{}".format(respmsg))

    lines = respmsg.splitlines()
    line1 = lines[0]

    if 'Attachment' in line1 and len(lines)>1:
        file1 = lines[1].strip()
        my_path = 'https://www.onestoplogisticsco.com/'
        #my_path = 'http://12c157d5.ngrok.io/'
        my_url = my_path + file1
        print('myurl = ',my_url)
        msg.media(my_url)
    return str(resp)


@app.route('/AboutClass8', methods=['GET', 'POST'])
def AboutClass8():
    info = ['']*6
    thisnow = now + timedelta(1)
    info[0] = thisnow.strftime("%Y-%m-%dT%H:%M")
    if request.method == 'POST':
        setappt = request.values.get('setappt')
        if setappt is not None:
            info[0] = request.values.get('date')
            info[1] = request.values.get('location')
            info[2] = request.values.get('email')
            info[3] = request.values.get('phone')
            info[4] = request.values.get('contact')
            info[5] = True

    for i in info:
        print(i)

    srcpath = statpath('')
    return render_template('AboutClass8.html', srcpath=srcpath, cmpdata=cmpdata, scac=scac, info = info)








@app.route('/Class8Main/<genre>', methods=['GET', 'POST'])
@login_required


def Class8Main(genre):

    from class8_tasks import Table_maker
    form = TruckingFormNew()
    #genre = 'Trucking'
    print('genre is',genre)
    genre_data, table_data, err, oder, leftscreen, leftsize, docref, tabletitle, table_filters, task_boxes, tfilters, tboxes, jscripts,\
    taskon, task_iter, holdvec, keydata, entrydata, username, modata, focus = Table_maker(genre)
    rightsize = 12 - leftsize

    return render_template('Class8.html',cmpdata=cmpdata, scac=scac,  genre_data = genre_data, table_data=table_data, err=err, oder=oder, modata=modata, leftscreen=leftscreen,
                           leftsize=leftsize, rightsize=rightsize, docref=docref, tabletitle=tabletitle, table_filters = table_filters,task_boxes = task_boxes, tfilters=tfilters, tboxes=tboxes, dt1 = jscripts,
                           taskon=taskon, task_iter=task_iter, holdvec=holdvec, keydata = keydata, entrydata = entrydata, username=username, focus = focus, genre=genre, form=form)




@app.route('/EasyStart', methods=['GET', 'POST'])
def EasyStart():
    calbut=request.values.get('calbut')
    if calbut is not None:
        return redirect(url_for('CalendarBig'))

    srcpath = statpath('')
    return render_template('easystart.html', srcpath=srcpath, cmpdata=cmpdata, scac=scac)


@app.route('/Reports', methods=['GET', 'POST'])
@login_required
def Reports():

    from iso_R import isoR
    idata1, idata2, idata3, idata4, hv, cache, err, leftscreen, docref, leftsize, today, now, doctxt, sdate, fdate, fyear, customerlist, thiscomp, clist = isoR()
    rightsize = 12-leftsize
    return render_template('Areports.html', cmpdata=cmpdata, scac=scac, clist=clist, thiscomp=thiscomp, customerlist=customerlist, fyear=fyear, cache=cache, sdate=sdate, fdate=fdate, err=err, doctxt=doctxt, leftscreen=leftscreen, docref=docref, leftsize=leftsize, rightsize=rightsize, idata1 = idata1, idata2=idata2, idata3=idata3, idata4=idata4, hv=hv)



# ____________________________________________________________________________________________________________________B.Login
# ____________________________________________________________________________________________________________________B.Login
# ____________________________________________________________________________________________________________________B.Login
# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        thisuser = users.query.filter_by(username=form.username.data).first()
        if thisuser is not None:
            app.logger.info('USER FOUND')
            passhash = thisuser.password
            passcheck = bcrypt.check_password_hash(passhash, form.password.data)

            if passcheck:
                session['logged_in'] = True
                session['username'] = thisuser.username
                session['authority'] = thisuser.authority
                login_user(thisuser, remember=form.remember.data)
                return redirect(url_for('EasyStart'))
            else:
                flash('Passwords do not match', 'danger')
                return render_template('login.html', error=error, cmpdata=cmpdata, scac=scac, form=form)
        else:
            flash('Username not found', 'danger')
    else:
        return render_template('login.html', cmpdata=cmpdata, scac=scac, form=form)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@login_required

def register():
    if session['authority'] == 'superuser':
        print('user is', session['username'])
        print('authority is', session['authority'])
        form = RegistrationForm()
        if form.validate_on_submit():
            flash(f'New User Created for {form.fullname.data}:', 'success')
            hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            input = users(name=form.fullname.data, email=form.email.data, username=form.username.data, password=hashed_pw, register_date=None, authority=form.authority.data)
            db.session.add(input)
            db.session.commit()
            return redirect(url_for('login'))
        return render_template('register.html', title='Register', form=form, cmpdata=cmpdata, scac=scac)
    else:
        flash(f'Do not have authority to register new users', 'danger')
        return redirect(url_for('EasyStart'))



from flask import render_template, flash, redirect, url_for, session, logging, request, jsonify

from webapp import app, db
from webapp.models import Orders
#from webapp.forms import TruckingFormNew
from webapp.class8_tasks import Table_maker
from flask_login import login_required



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
from webapp.viewfuncs import make_new_order, nonone, monvals, getmonths, nononestr, hasinput, d2s, erud, docuploader
from webapp.class8_utils_email import email_template, info_mimemail, check_person, add_person

from webapp.class8_utils import *

today = datetime.datetime.today()
year = str(today.year)
day = str(today.day)
month = str(today.month)
now = datetime.datetime.now()
today_str = today.strftime('%Y-%m-%d')

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


@app.route('/', methods=['GET', 'POST'])
def index():
    info = [''] * 9
    if request.method == 'POST':
        sendnow = request.values.get('sendnow')
        if sendnow is not None:
            name = request.values.get('name')
            email = request.values.get('email')
            phone = request.values.get('phone')
            message = request.values.get('message')
            print(f'Sending email from {name}, {email}, {phone}, {message}')
            info[0] = today_str
            info[1] = message
            info[2] = email
            info[3] = phone
            info[4] = name
            info[5] = True
            info[6] = f'Your contact request has been sent'
            num_finds = check_person(info)
            if num_finds < 2:
                add_person(info)
                emaildata = email_template('contact', info)
                print('Sending Email to', emaildata)
                info_mimemail(emaildata)
            else:
                print('Too many attempts to contact')
                info[5] = True
                info[6] = f'Already received request, please allow time to respond'

    srcpath = statpath('')
    return render_template(f'companysite/{scac}/index.html',srcpath=srcpath, cmpdata=cmpdata, scac=scac,info=info)

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
    info = ['']*7
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
            info[6] = f'Email Sent To {info[2]} at {info[1]} confirming appointment on {info[0]} at {info[1]}'
            emaildata = email_template('class8demo', info)
            print('Sending Email to', emaildata)
            info_mimemail(emaildata)

        cancel = request.values.get('cancel')
        if cancel is not None: info = ['']*7

    for i in info:
        print(i)

    srcpath = statpath('')
    return render_template('AboutClass8.html', srcpath=srcpath, cmpdata=cmpdata, scac=scac, info = info)



@app.route('/Class8Main/<genre>', methods=['GET', 'POST'])
@login_required

def Class8Main(genre):

    print('routes.py 237: The genre is',genre)
    genre_data, table_data, err, leftsize, tabletitle, table_filters, task_boxes, tfilters, tboxes, jscripts,\
    taskon, task_focus, task_iter, tasktype, holdvec, keydata, entrydata, username, checked_data, viewport, tablesetup = Table_maker(genre)
    if taskon == 'New': err, viewport = checkfor_fileupload(err, task_iter, viewport)

    rightsize = 12 - leftsize
    print('heading to class8.html with genre:',genre, keydata)
    return render_template('Class8.html',cmpdata=cmpdata, scac=scac,  genre_data = genre_data, table_data=table_data, err=err, checked_data = checked_data,
                           leftsize=leftsize, rightsize=rightsize, tabletitle=tabletitle, table_filters = table_filters,task_boxes = task_boxes, tfilters=tfilters, tboxes=tboxes, dt1 = jscripts,
                           taskon=taskon, task_focus=task_focus, task_iter=task_iter, tasktype=tasktype, holdvec=holdvec, keydata = keydata, entrydata = entrydata, username=username, genre=genre, viewport=viewport, tablesetup=tablesetup)


@app.route('/EasyStart', methods=['GET', 'POST'])
def EasyStart():
    calbut=request.values.get('calbut')
    if calbut is not None:
        return redirect(url_for('CalendarBig'))
    print('Working the EasyStart route!!')
    srcpath = statpath('')
    return render_template('easystart.html', srcpath=srcpath, cmpdata=cmpdata, scac=scac)


@app.route('/Reports', methods=['GET', 'POST'])
@login_required
def Reports():

    from iso_R import isoR
    idata1, idata2, idata3, idata4, hv, cache, err, leftscreen, docref, leftsize, today, now, doctxt, sdate, fdate, fyear, customerlist, thiscomp, clist = isoR()
    rightsize = 12-leftsize
    return render_template('Areports.html', cmpdata=cmpdata, scac=scac, clist=clist, thiscomp=thiscomp, customerlist=customerlist, fyear=fyear, cache=cache, sdate=sdate, fdate=fdate, err=err, doctxt=doctxt, leftscreen=leftscreen, docref=docref, leftsize=leftsize, rightsize=rightsize, idata1 = idata1, idata2=idata2, idata3=idata3, idata4=idata4, hv=hv)






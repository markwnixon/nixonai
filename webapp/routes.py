from flask import render_template, flash, redirect, url_for, session, logging, request, jsonify
from flask import Blueprint

from webapp.extensions import db
from webapp.models import Orders, People
#from webapp.forms import TruckingFormNew
from webapp.class8_tasks import Table_maker
from webapp.revenues import get_revenues
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


main = Blueprint('main',__name__)


@main.route('/get_containers_out', methods=['GET'])
def get_data():
    lbdate = now.date()
    lbdate = lbdate - timedelta(days=360)
    odata = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat < 2)).all()
    data = []
    for odat in odata:
        data.append([{'id':odat.id,'JO':odat.Jo,'SCAC':scac,'Shipper':odat.Shipper,'Container':odat.Container,'Hstat':odat.Hstat}])
    #row_dict = {key: value for key, value in row.__dict__.items() if not key.startswith('_')}
    #row_json = json.dumps(row_dict)
    #odata = [{'SCAC': scac},{'MACHINE': 'test'},{'TUNNEL': 'test'}]
    #return jsonify(odat)
    #jsonify([dict(odat) for odat in odata])
    #jdata = json.dumps(data)
    return data


@main.route('/FileUpload', methods=['GET', 'POST'])
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
    ext = ext.lower()
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

@main.route('/chartdata', methods=['GET', 'POST'])
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


@main.route('/', methods=['GET', 'POST'])
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

@main.route('/About')
def About():
    lang = 'English'
    srcpath = statpath('')
    return render_template(f'companysite/{scac}/about.html',srcpath=srcpath,cmpdata=cmpdata, scac=scac, lang=lang)

@main.route('/Whatapp', methods=['GET', 'POST'])
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
        my_path = 'https://www.oslbox.com/'
        #my_path = 'https://7223-2601-150-100-8c10-2928-d420-6968-460f.ngrok.io/'
        my_url = my_path + file1
        print('myurl = ',my_url)
        msg.media(my_url)
    return str(resp)


@main.route('/AboutClass8', methods=['GET', 'POST'])
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

@main.route('/People_Forms', methods=['GET', 'POST'])
def People_Forms():
    if request.method == 'POST':
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        appnum = 0
        vals = ['fname', 'mnames', 'lname', 'addr1', 'addr2', 'addr3',
                'idtype', 'tid', 'tel', 'email', 'assoc1', 'assoc2', 'date1', 'yrs']
        a = list(range(len(vals)))
        i = 0
        for v in vals:
            a[i] = request.values.get(v)
            i = i+1
        exporter = request.values.get('exporter')
        consignee = request.values.get('consignee')
        notify = request.values.get('notify')
        driver = request.values.get('driver')
        if exporter is not None:
            ptype = "exporter"
        if consignee is not None:
            ptype = "consignee"
        if notify is not None:
            ptype = "notify"
        if driver is not None:
            ptype = "applicant"
        try:
            company = a[0] + ' ' + a[2]
        except:
            company = a[0]

        input = People(Ptype=ptype, Company=company, First=a[0], Middle=a[1], Last=a[2], Addr1=a[3], Addr2=a[4], Addr3=a[5], Temp1=a[13], Temp2='NewApp',
                       Idtype=a[6], Idnumber=a[7], Telephone=a[8], Email=a[9], Associate1=a[10], Associate2=a[11], Date1=today, Date2=None, Source=None, Accountid=None)
        db.session.add(input)
        db.session.commit()

        if exporter is not None:
            ptype = "consignee"
        if consignee is not None:
            ptype = "notify"
        if notify is not None:
            ptype = "completed"
            pdata = People.query.filter(People.Temp2 == 'NewApp').all()
            for pdat in pdata:
                pdat.Temp2 = '2'
                db.session.commit()
            from email_appl import email_app_exporter
            email_app_exporter(pdata)

        if driver is not None:

            pdat = People.query.filter((People.Ptype == 'applicant') &
                                       (People.Company == company)).first()
            appnum = 'Fapp'+str(pdat.id)
            ptype = "completed"
            from email_appl import email_app
            email_app(pdat)

            return render_template('employment.html', cmpdata=cmpdata, scac=scac, ptype=ptype, appnum=appnum, phone=phone, today=today)
    else:
        ptype = "exporter"

    srcpath = statpath('')
    return render_template(f'companysite/{scac}/pforms.html', cmpdata=cmpdata, scac=scac, ptype=ptype, srcpath=srcpath)

@main.route('/Employment')
def Employment():
    ptype = 'driver'
    srcpath = statpath('')
    return render_template('employment.html', srcpath=srcpath, cmpdata=cmpdata, scac=scac, ptype=ptype, today=today.date(), phone=cmpdata[7],email=cmpdata[8])

@main.route('/Calculator', methods=['GET', 'POST'])
def Calculator():
    import ast
    from viewfuncs import d2s
    if request.method == 'POST':
        alldata = request.values.get('alldata')
        alldata = ast.literal_eval(alldata)
        print(alldata)
        l = len(alldata)
        print(l)
        a1 = request.form['len']
        a2 = request.form['wid']
        a3 = request.form['hei']
        a4 = float(a1)*float(a2)*float(a3)
        a6 = request.form['unt']
        a7 = request.form['wtunt']
        b1 = request.form['cst']
        b1 = Decimal(b1.strip('$'))
        a6 = int(a6)
        a7 = int(a7)
        if a6 == 1:
            a4 = a4/61023.7
        if a6 == 2:
            a4 = a4/35.3147
        if a6 == 3:
            a4 = a4/1000000.
        wtkg = a4*166.67
        wtlb = wtkg*2.20462
        wtkgstr = d2s(str(wtkg))
        wtlbstr = d2s(str(wtlb))
        a5 = math.ceil(a4)
        a4 = round(a4, 2)
        b2 = a5*float(b1)
        if a7 == 1:
            wt = wtlbstr
        else:
            wt = wtkgstr
        total = float(wt)
        for data in alldata:
            total = total+float(data[3])

        alldata.append([a1, a2, a3, wt])

        # Recalculate all in case units have changed
        newalldata = []
        total = 0
        for data in alldata:
            a1 = data[0]
            a2 = data[1]
            a3 = data[2]
            a4 = float(a1)*float(a2)*float(a3)
            if a6 == 1:
                a4 = a4/61023.7
            if a6 == 2:
                a4 = a4/35.3147
            if a6 == 3:
                a4 = a4/1000000.
            if a7 == 2:
                wt = a4*166.67
            if a7 == 1:
                wt = a4*166.67*2.20462
            total = total+float(wt)
            newalldata.append([a1, a2, a3, d2s(wt)])
        a4 = round(a4, 2)
        finalcost = total*float(b1)
        finalwt = d2s(total)
        finalcost = d2s(finalcost)

    else:
        a1 = 1
        a2 = 1
        a3 = 1
        a4 = 1
        a5 = 1
        a6 = 1
        a7 = 1
        b1 = 25
        b2 = 1
        wtkgstr = ''
        wtlbstr = ''
        alldata = []
        fdata = []
        newalldata = []
        finalwt = ''
        finalcost = ''
    srcpath = statpath('')
    return render_template('calculator.html', srcpath=srcpath,cmpdata=cmpdata, scac=scac, finalcost=finalcost, a1=a1, a2=a2, a3=a3, a4=a4, a5=a5, a6=a6, a7=a7, b1=b1, b2=b2, wtkg=wtkgstr, wtlb=wtlbstr, alldata=newalldata, finalwt=finalwt)


@main.route('/Class8Main/<genre>', methods=['GET', 'POST'])
@login_required

def Class8Main(genre):

    #print('routes.py 237: The genre is',genre)
    genre_data, table_data, err, leftsize, tabletitle, table_filters, task_boxes, tfilters, tboxes, jscripts,\
    taskon, task_focus, task_iter, tasktype, holdvec, keydata, entrydata, username, checked_data, viewport, tablesetup = Table_maker(genre)
    if taskon == 'New': err, viewport = checkfor_fileupload(err, task_iter, viewport)

    rightsize = 12 - leftsize
    return render_template('Class8.html',cmpdata=cmpdata, scac=scac,  genre_data = genre_data, table_data=table_data, err=err, checked_data = checked_data,
                           leftsize=leftsize, rightsize=rightsize, tabletitle=tabletitle, table_filters = table_filters,task_boxes = task_boxes, tfilters=tfilters, tboxes=tboxes, dt1 = jscripts,
                           taskon=taskon, task_focus=task_focus, task_iter=task_iter, tasktype=tasktype, holdvec=holdvec, keydata = keydata, entrydata = entrydata, username=username, genre=genre, viewport=viewport, tablesetup=tablesetup)




@main.route('/Revenue', methods=['GET', 'POST'])
@login_required
def Revenue():
    #print('Made it to the Revenue Data Center')
    title1,col1,data1,title2,col2,data2,title3,col3,data3,tabon = get_revenues()
    return render_template('revenues.html', cmpdata=cmpdata, scac=scac, title1=title1, col1=col1, data1=data1, title2=title2, col2=col2, data2=data2, title3=title3, col3=col3, data3=data3, tabon=tabon)



@main.route('/EasyStart', methods=['GET', 'POST'])
def EasyStart():
    calbut=request.values.get('calbut')
    if calbut is not None:
        return redirect(url_for('main.CalendarBig'))
    #print('Working the EasyStart route!!')
    srcpath = statpath('')
    return render_template('easystart.html', srcpath=srcpath, cmpdata=cmpdata, scac=scac)


#@app.route('/hello', methods=['GET', 'POST'])
#def hello():

    # POST request
    #    if request.method == 'POST':
    #       print('Incoming..')
    #      print(request.get_json())  # parse as JSON
    #      return 'OK', 200

    # GET request
    #   else:
    #       message = {'greeting':'Hello from Flask!'}
#       return jsonify(message)  # serialize and use JSON headers

#@app.route('/CalendarTest', methods=['GET', 'POST'])
#def CalendarTest():
#    print('Working the Calendar route!!')
#    srcpath = statpath('')
#    return render_template('CalendarTest.html', srcpath=srcpath, cmpdata=cmpdata, scac=scac)

@main.route('/QuoteMaker', methods=['GET', 'POST'])
@login_required
def QuoteMaker():
    from iso_Q import isoQuote
    bidname, costdata, biddata, expdata, timedata, distdata, emaildata, locto, locfrom, dirdata, qdata, bidthis, taskbox, thismuch, quot, qdat, tbox, ebodytxt, multibid, newmarkup = isoQuote()
    if bidname == 'exitnow': return redirect(url_for('main.Class8Main',genre='Trucking'))
    else:
        return render_template('Aquotemaker.html', cmpdata=cmpdata, scac=scac, costdata = costdata, biddata=biddata, expdata = expdata, timedata = timedata,
                           distdata=distdata, locto=locto, locfrom=locfrom, emaildata = emaildata, dirdata=dirdata, qdata = qdata, bidthis=bidthis, taskbox=taskbox, thismuch=thismuch, quot=quot, qdat=qdat, bidname=bidname, tbox=tbox, ebodytxt=ebodytxt, multibid=multibid, newmarkup=newmarkup)

@main.route('/ARMaker', methods=['GET', 'POST'])
@login_required
def ARMaker():
    from iso_AR import isoAR
    status, ardata, arsent, this_shipper, odata, sdata, task, emaildata, boxes, sboxes, tboxes, invoname, packname, pdat, emailsend, ar_emails_cust, rview= isoAR()
    if status == 'exitnow': return redirect(url_for('main.Class8Main',genre='Trucking'))
    else:
        return render_template('ARmaker.html', cmpdata=cmpdata, scac=scac, ardata=ardata, arsent=arsent, this_shipper=this_shipper, odata=odata, sdata=sdata, task=task, emaildata=emaildata, boxes=boxes, sboxes=sboxes, tboxes=tboxes, invoname=invoname, packname=packname, pdat=pdat, emailsend=emailsend, ar_emails_cust=ar_emails_cust, rview=rview)


@main.route('/Reports', methods=['GET', 'POST'])
@login_required
def Reports():

    from iso_R import isoR
    idata1, idata2, idata3, idata4, hv, cache, err, leftscreen, docref, leftsize, today, now, doctxt, sdate, fdate, fyear, customerlist, thiscomp, clist = isoR()
    rightsize = 12-leftsize
    return render_template('Areports.html', cmpdata=cmpdata, scac=scac, clist=clist, thiscomp=thiscomp, customerlist=customerlist, fyear=fyear, cache=cache, sdate=sdate, fdate=fdate, err=err, doctxt=doctxt, leftscreen=leftscreen, docref=docref, leftsize=leftsize, rightsize=rightsize, idata1 = idata1, idata2=idata2, idata3=idata3, idata4=idata4, hv=hv)






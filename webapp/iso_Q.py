from webapp import db
from flask import render_template, flash, redirect, url_for, session, logging, request
from requests import get
from CCC_system_setup import apikeys
from CCC_system_setup import myoslist, addpath, tpath, companydata, usernames, passwords, scac, imap_url, accessorials, signoff
from webapp.viewfuncs import d2s, stat_update, hasinput, d1s
#from viewfuncs import d2s, d1s
import imaplib, email
import math
import re
from email.header import decode_header
import webbrowser
import os
from email.utils import parsedate_tz, mktime_tz
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

import datetime
from webapp.models import Quotes, Quoteinput
from send_mimemail import send_mimemail
from pyzipcode import ZipCodeDatabase
zcdb = ZipCodeDatabase()

API_KEY_GEO = apikeys['gkey']
API_KEY_DIS = apikeys['dkey']
cdata = companydata()

date_y4=re.compile(r'([1-9]|0[1-9]|[12][0-9]|3[01]) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4})')

def roundup(x):
    return int(math.ceil(x / 10.0)) * 10

def get_body(msg):
    if msg.is_multipart():
        return get_body(msg.get_payload(0))
    else:
        return msg.get_payload(None,True)

def search(key,value,con):
    result,data=con.search(None,key,'"{}"'.format(value))
    return data

def search_from_date(key,value,con,datefrom):
    result,data=con.search( None, '(SENTSINCE {0})'.format(datefrom) , key, '"{}"'.format(value) )
    return data

def get_emails(result_bytes,con):
    msgs=[]
    for num in result_bytes[0].split():
        typ,data=con.fetch(num,'(RFC822)')
        msgs.append(data)
    return msgs

def get_date(data):
    for response_part in data:
        if isinstance(response_part, tuple):
            try:
                part = response_part[1].decode('utf-8')
                msg = email.message_from_string(part)
                date=msg['Date']
            except:
                date=None
    return date

def get_subject(data):
    subject = 'none'
    mid = 'none'
    for response_part in data:
        if isinstance(response_part, tuple):
            part = response_part[1].decode('utf-8')
            msg = email.message_from_string(part)
            subject=msg['Subject']
            mid = msg['Message-ID']
    return subject, mid

def get_from(data):
    for response_part in data:
        if isinstance(response_part, tuple):
            part = response_part[1]
            try:
                part = part.decode('utf-8')
                msg = email.message_from_string(part)
                thisfrom=msg['From']
                return thisfrom
            except:
                return 'Nonefound'

def get_msgs():
    username = usernames['quot']
    password = passwords['quot']
    dayback = 100
    #datefrom = (datetime.date.today() - datetime.timedelta(dayback)).strftime("%d-%b-%Y")
    con = imaplib.IMAP4_SSL(imap_url)
    con.login(username, password)
    con.select('INBOX')
    result, data = con.search(None,'ALL')
    msgs = get_emails(data, con)
    return msgs


def compact(body):
    newbody = ''
    blines = body.splitlines()
    for line in blines:
        #Remove non-ascii characters
        line = re.sub(r'[^\x00-\x7F]+', ' ', line)
        line = re.sub(r'=[A-Z,0-9][A-Z,0-9]', '', line)
        if len(line.strip())>1:
            if 'Forwarded Message' in line or 'Subject:' in line or 'Date:' in line or 'To:' in line or 'CC:' in line or 'From:' in line or 'Content-Type' in line or 'Content-Transfer' in line:
                print('Line from FWD Preamble')
            else:
                newbody = newbody + line +'\n' + '<br>'
    return newbody

def hard_decode(raw):
    raw = str(raw)
    rawl = raw.splitlines()
    appendit = 0
    ebody=''
    efrom=''
    edate=''
    mid=''
    for line in rawl:
        test = line[0:5]
        line = re.sub(r'[^\x00-\x7F]+', ' ', line)
        line = re.sub(r'=[A-Z,0-9][A-Z,0-9]', '', line)
        line = line.replace('=09','')
        if 'Subj' in test:
            subject = line.split('Subject:')[1]
            subject = subject.replace('Fwd:','')
            subject = subject.strip()
            print(f'Subject:{subject}')
        if 'Message-ID' in line:
            mid = line.split('Message-ID:')[1]
            mid = mid.replace('Fwd:', '')
            mid = mid.strip()
            print(f'MID:{mid}')
        if 'From' in test and '@' in line and 'firsteagle' not in line and 'onestop' not in line:
            print('efrom',line)
            efrom = line.split('From:')[1]
            efrom = efrom.strip()
            print(f'From:{efrom}')
        if 'Date' in test:
            edate = line.split('Date:')[1]
            edate = edate.strip()
            print(f'Date:{edate}')
        if 'Content-Type:' in line and 'plain' in line:
            print(f'BodyStart:{line}')
            appendit = 1
        if 'Content-Type:' in line and 'html' in line:
            print(f'BodyStop:{line}')
            appendit = 0
        if appendit == 1:
            line = line.strip()
            if len(line)>0:
                ebody=ebody+line+'\n'
    #print(f'ebody={ebody}')
    return subject,efrom,edate,ebody,mid

def clean(text):
    # clean text for creating a folder
    return "".join(c if c.isalnum() else "_" for c in text)

def extract_for_code(data):
    text, encoding = decode_header(data)[0]
    if isinstance(text, bytes):
        if encoding is not None: text = text.decode(encoding)
    return text


def add_quote_emails():
    username = usernames['quot']
    password = passwords['quot']
    imap = imaplib.IMAP4_SSL(imap_url)
    imap.login(username, password)
    status, messages = imap.select('INBOX')
    # total number of emails
    messages = int(messages[0])
    print(f'Total number of messages in inbox is {messages}')

    N = 50
    #for i in range(messages, messages - N, -1):
    for i in range(messages - N + 1, messages + 1):
        # fetch the email message by ID
        #res, msg = imap.fetch(str(i), "(RFC822)")
        # Insert the GPTChat solution
        result, email_data = imap.fetch(str(i), "(RFC822)")
        # convert the email message data into an email object
        email_message = email.message_from_bytes(email_data[0][1])

        # extract the subject of the email
        subject = extract_for_code(email_message["Subject"])
        mid = extract_for_code(email_message["Message-ID"])
        fromp = extract_for_code(email_message["From"])

        # extract the date and time the email was sent
        date_time_str = email_message["Date"]
        date_time = parsedate_to_datetime(date_time_str)

        # print the email content
        thisdate = date_time.date()
        thistime = date_time.time()
        print("Message ID: " + mid)
        print("Subject: " + subject)
        print("From: " + fromp)
        print("Date: " + str(thisdate))
        print("Time: " + str(thistime))

        qdat = Quotes.query.filter(Quotes.Mid == mid).first()
        if qdat is None:
            try:
                input = Quotes(Date=date_time, From=fromp, Subject=subject, Mid=mid, Person=None, Emailto=None, Subjectsend=None,
                               Response=None, Amount=None, Location=None, Status=0, Responder=None, RespDate=None, Start='Seagirt Marine Terminal, Baltimore, MD')
                db.session.add(input)
                db.session.commit()
            except:
                print(f'Could not input the body of the email with subject {subject}')

    # close the connection and logout
    imap.close()
    imap.logout()
    return




def extract_values(obj, key):
    """Pull all values of specified key from nested JSON."""
    arr = []
    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    results = extract(obj, arr, key)
    return results

def direct_resolver(json):
    di, du, ht, la, lo = [],[],[],[],[]
    t1 = json['routes'][0]['legs'][0]['steps']
    for t2 in t1:
        di.append(t2['distance']['text'])
        du.append(t2['duration']['text'])
        ht.append(t2['html_instructions'])
        la.append(t2['end_location']['lat'])
        lo.append(t2['end_location']['lng'])

    return di, du, ht, la, lo

def route_resolver(json):
    ##print(json)
    final = json['rows']
    final = final[0]
    next = final['elements']
    next = next[0]
    bi = next['distance']
    ci = next['duration']
    di = bi['text']
    du = ci['text']
    return di, du

def address_resolver(json):
    final = {}
    if json['results']:
        data = json['results'][0]
        for item in data['address_components']:
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

def checkcross(lam,la_last,la,lom,lo_last,lo):
    lacross = 0
    locross = 0
    if (la_last<lam and la>lam) or (la_last>lam and la<lam):
        lacross = 1
    if (lo_last<lom and lo>lom) or (lo_last>lom and lo<lom):
        locross = 1
    return lacross, locross

def maketable(expdata):
    bdata = '<br><br>\n'
    bdata = bdata + '<table>\n'
    alist = ['Tandem Chassis', 'Triaxle Chassis', 'Prepull Fee', 'Yard Storage', 'Driver Detention', 'Extra Stop', 'Overweight', 'Overweight', 'Reefer Fee', 'Scale Tickets', 'Residential', 'Port Congestion', 'Chassis Split']
    blist = ['Per Day', 'Per Day', 'Per Pull', 'Per Day', 'Per Hour', 'Per Stop', 'Base Fee', 'Per Mile', '', '', '', '', '']
    clist = expdata[15:]
    for jx, item in enumerate(alist):
        #print(item,blist[jx],clist[jx])
        bdata = bdata + f'<tr><td><font size="+0">{item}&nbsp;</font></td><td>&nbsp&nbsp&nbsp&nbsp</td><td><font size="+0">{blist[jx]}&nbsp;</font></td><td>&nbsp&nbsp&nbsp&nbsp</td><td><font size="+0">${clist[jx]}&nbsp;</font></td></tr>\n'
    bdata = bdata + '</table><br><br>'
    bdata = bdata + f'<em>{signoff}</em>'

    return bdata


def sendquote():
    etitle = request.values.get('edat0')
    ebody = request.values.get('edat1')
    emailin1 = request.values.get('edat2')
    emailin2 = request.values.get('edat3')
    emailcc1 = request.values.get('edat4')
    emailcc2 = request.values.get('edat5')
    emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2]
    send_mimemail(emaildata,'qsnd')
    return emaildata




def get_address_details(address):
    url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    url = url + 'address='+ address.replace(" ","+")
    url = url + f'&key={API_KEY_GEO}'
    #print(url)
    response = get(url)
    data  = address_resolver(response.json())
    data['address'] = address
    lat = data['latitude']
    lon = data['longitude']
    #print(lat,lon)
    return data

def get_distance(start,end):
    start = start.replace(" ", "+")
    end = end.replace(" ", "+")
    url = f'https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&origins={start}&destinations={end}'
    url = url + f'&key={API_KEY_DIS}'
    #print(url)
    response = get(url)
    #print(response)
    data = route_resolver(response.json())
    return data

def get_directions(start,end):
    dists, duras, lats, lons = [], [], [], []
    tot_dist = 0.0
    tot_dura = 0.0
    start = start.replace(" ", "+")
    end = end.replace(" ", "+")
    url = f'https://maps.googleapis.com/maps/api/directions/json?origin={start}&destination={end}'
    url = url + f'&key={API_KEY_DIS}'
    #print(url)
    response = get(url)
    dis, dus, hts, las, los  = direct_resolver(response.json())

    #Convert all mixed units to miles, hours and convert from text to floats
    for di in dis:
        if 'mi' in di:
            nu = float(di.replace('mi',''))
        elif 'ft' in di:
            nu = float(di.replace('ft',''))/5280.0
        else:
            nu = 0.0
        dists.append(nu)
        tot_dist += nu

    for du in dus:
        dul = du.split()
        if len(dul) == 4:
            hr = float(dul[0])
            min = float(dul[2])
            hrs = hr + min/60.0
        elif len(dul) == 2:
            if 'hr' in du:
                hrs = float(dul[0])
            elif 'min' in du:
                hrs = float(dul[0])/60.0
            else:
                hrs = 0.0
        duras.append(hrs)
        tot_dura += hrs

    for la in las:
        lats.append(float(la))
    for lo in los:
        lons.append(float(lo))

    return dists, duras, lats, lons, hts, tot_dist, tot_dura

def get_place(subject, body, multibid):
    loci = []
    location = 'Upper Marlboro, MD  20743'
    zip_c = re.compile(r'\w+[,.]?\s+\w+[,.]?\s+[0-9]{5}')
    zip_p = re.compile(r'[\s,]\d{5}(?:[-\s]\d{4})?')
    nozip = re.compile(r'\w+[,.]?\s+(MD|PA|VA|DE|NJ|OH|NC)')
    testp = zip_p.findall(subject)
    testp2 = zip_c.findall(subject)
    testq = zip_p.findall(body)
    testq2 = zip_c.findall(body)
    testp3 = nozip.match(subject)
    testq3 = nozip.match(body)
    print(f'the subject has these zipcodes {testp}')
    print(f'the body has these zipcodes {testq}')
    print(f'the subject has these city-zips {testp2}')
    print(f'the body has these city-zips {testq2}')
    print(f'the subject has these city-states {testp3}')
    print(f'the body has these city-states {testq3}')
    print('The body is:',body)
    print(f'the address is {testp}, {testq}, {testq2}, {testq3}')
    for test in testp:
        ziptest = test.strip()
        try:
            zb = zcdb[ziptest]
            location = f'{zb.city}, {zb.state}  {ziptest}'
            # print(zcdb[location])
            # print(f'zb is {zb} {zb.city}')
            print(f'In subject: test is {test} and location is **{location}**')
        except:
            print(f'{ziptest} does not work')
            location = 'nogood'

        if location != 'nogood' and multibid[0]=='off': loci.append(location)

    for test in testq:
        ziptest = test.strip()
        try:
            zb = zcdb[ziptest]
            location = f'{zb.city}, {zb.state}  {ziptest}'
            print(f'In body: test is {test} and location is **{location}**')
        except:
            print(f'{ziptest} does not work')
            location = 'nogood'

        if location != 'nogood': loci.append(location)


    if (len(testp)==0 and len(testq)==0) or len(loci)==0:
        location = 'Upper Marlboro, MD  20743'
        print(f'Both subject and body failed to find a location')
    else:
        #Find best and most likely loci
        print('loci is:', loci)
        location = loci[0]

    if len(location) > 199: location = location[0:199]

    # if multibid is on need to make sure loci has same number of locations as multibid request
    requested = multibid[1]
    if len(loci) < requested:
        while len(loci) < requested:
            loci.append('Upper Marlboro, MD  20743')
    if len(loci) > requested:
        loci = loci[0:requested]

    return location, loci

def friendly(emailin):
    try:
        efront = emailin.split('<')[0]
        efront = efront.replace('"','')
        return efront
    except:
        return emailin

def emailonly(emailin):
    try:
        eback = emailin.split('<')[1]
        eback = eback.replace('>','')
        return eback
    except:
        return emailin

def bodymaker(customer,cdata,bidthis,locto,tbox,expdata,takedef,distdata,multibid, etitle):
    sen, tbox, btype, stype, mixtype = insert_adds(tbox,expdata,takedef,distdata,multibid)
    #print(f'btype is {btype}')
    tabover = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
    ebody = ''
    if multibid[0] == 'on':
        loci = multibid[2]
        bids = multibid[3]
        etitle = f'{cdata[0]} Quotes to'
        for loc in loci:
            if hasinput(loc): etitle = etitle + f' {loc};'
        etitle = etitle[:-1]
        if 'all-in' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>All-In</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'
            ebody = ebody + f'{sen}<br>The {cdata[0]} full accessorial table is shown below.  Some accessorial charges from this table may apply if circumstances warrant.'

        elif 'live' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b>is pleased to offer the following <b>Live-Load</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'
            ebody = ebody + f'<br>These quotes are inclusive of tolls, fuel, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'
            ebody = ebody + f'{sen}<br><br>Added charges are based on the full accessorial table shown below.  Additional accessorial charges from this table may apply as circumstances warrant.'


        elif 'dr' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b>is pleased to offer the following <b>Drop-Pick</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'
            ebody = ebody + f'<br>These quotes are inclusive of tolls and fuel.'
            ebody = ebody + f'{sen}<br><br>Added charges are based on the full accessorial table shown below.  Additional accessorial charges from this table may apply as circumstances warrant.'

        elif 'dp' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>Drop-Hook</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'
            ebody = ebody + f'<br>These quotes are inclusive of tolls and fuel.  A return container must be available and ready upon delivery or bobtail charges may apply.'
            ebody = ebody + f'{sen}<br><br>Added charges are based on the full accessorial table shown below.  Additional accessorial charges from this table may apply if circumstances warrant.'

        elif 'fsc' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>Live-Load</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                ebody = ebody + f'{tabover}<b>{bids[ix]}plus {d1s(expdata[5])}% FSC</b> to {loc}<br>'
            ebody = ebody + f'<br>These quotes are inclusive of tolls, fuel, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'
            ebody = ebody + f'{sen}<br><br>Added charges are based on the full accessorial table shown below.  Additional accessorial charges from this table may apply if circumstances warrant.'

    else:
        if 'all-in' in btype:
            ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote of <b>${bidthis[4]} All-In</b> for this load to {locto}.' \
                    f'\nThe quote is inclusive of tolls, 2-days chassis, pre-pull, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'
            ebody = ebody + f'{sen}<br><br>The {cdata[0]} full accessorial table is shown below.  Some accessorial charges from this table may apply if circumstances warrant.'
        elif len(btype) == 1:

            if 'live' in btype:
                ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote of <b>${bidthis[0]}</b> for this live load to {locto}.' \
                        f'\nThe quote is inclusive of tolls, fuel, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'

            if 'dr' in btype:
                ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote of <b>${bidthis[1]}</b> for this drop-pick load at {locto}.' \
                        f'\nThe quote is inclusive of tolls and fuel and two bobtails to load site.'

            if 'dp' in btype:
                ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote of <b>${bidthis[2]}</b> for this drop-hook load to {locto}.' \
                        f'\nThe quote is inclusive of tolls, fuel, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).  No bobtailing included for drop-hook.'

            if 'fsc' in btype:
                ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote of <b>${bidthis[3]} plus {d1s(expdata[5])}% FSC</b> for this load to {locto}.' \
                        f'\nThe quote is inclusive of tolls and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'

            ebody = ebody + f'{sen}<br><br>Added charges are based on the full accessorial table shown below.  Additional accessorial charges from this table may apply as circumstances warrant.'


        elif len(btype) > 1:
            if mixtype == 'mix':
                ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer these quotes for loads to {locto}, which apply to both 20ft and 40ft containers.<br><br>'
            else:
                ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer these quotes for loads to {locto}.<br><br>'

            if 'live' in btype:
                ebody =  ebody + f'<b>${bidthis[0]}</b> for a live load which includes 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).<br>'

            if 'dr' in btype:
                ebody = ebody + f'<b>${bidthis[1]}</b> for a drop-pick (two bobtails included).<br>'

            if 'dp' in btype:
                ebody = ebody + f'<b>${bidthis[2]}</b> for a drop-hook (no bobtailing).<br>'

            if 'fsc' in btype:
                ebody = ebody + f'<b>${bidthis[3]} plus {d1s(expdata[5])}% FSC</b> for a live load which includes 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).<br>'


            ebody = ebody + f'<br>The quotes are inclusive of all tolls and fuel costs.'
            ebody = ebody + f'{sen}<br><br>Added charges are based on the full accessorial table shown below.  Additional accessorial charges from this table may apply as circumstances warrant.'

    if len(btype) == 1 and stype == 'ml':
        ebody = ebody.replace('this','these').replace('load', 'loads')
        ebody = ebody.replace('these quote', 'this quote')

    if len(btype) == 1 and mixtype == 'mix':
        ebody = ebody.replace('is inclusive','is for both 20ft and 40ft containers and is inclusive')

    if len(btype) > 1 and mixtype == 'mix':
        ebody = ebody.replace('is inclusive','is for both 20ft and 40ft containers and is inclusive')

    return ebody, tbox, etitle

def insert_adds(tbox, expdata, takedef, distdata, multibid):
    sen = ''
    adds = []
    btype = []
    if tbox[12]: btype.append('live')
    if tbox[13]: btype.append('dr')
    if tbox[14]: btype.append('dp')
    if tbox[16]: btype.append('fsc')
    if tbox[15]: btype.append('all-in')
    if not takedef:
        for ix in range(len(tbox)):
            tbox[ix] = request.values.get(f'tbox{str(ix)}')
            print(ix,tbox[ix])

    if 'all-in' not in btype:
        if tbox[0]:
            adds.append(f'Standard 2-axle Chassis:  <b>${expdata[15]}/day</b>')
        if tbox[1]:
            adds.append(f'3-axle Chassis:  <b>${expdata[16]}/day</b>')
        if tbox[2]:
            adds.append(f'Pre-pull Fee: <b>${expdata[17]}</b> (includes one day of yard storage)')
        if tbox[3]:
            adds.append(f'Yard Storage: <b>${expdata[18]}/day</b>')
        if tbox[4]:
            owfee1 = round(int(float(expdata[21])))
            adds.append(f'Overweight Base Fee:  <b>${d2s(owfee1)}</b>')
        if tbox[5]:
            owfee2 = round(int(float(expdata[22]) * float(distdata[0])/2)/10)*10
            adds.append(f'Overweight Miles:  <b>${d2s(owfee2)}</b>')
        if tbox[6]:
            adds.append(f'Extra Stop Fee: <b>${expdata[20]}</b>')
        if tbox[7]:
            adds.append(f'Reefer Fee:  <b>${expdata[23]}</b>')
        if tbox[8]:
            adds.append(f'Scale Ticket Set:  <b>${expdata[24]}</b>')
        if tbox[9]:
            adds.append(f'Residential Fee:  <b>${expdata[25]}</b>')
        if tbox[10]:
            adds.append(f'Port Congestion:  <b>${expdata[26]}/hr</b> over 2 hrs')
        if tbox[11]:
            adds.append(f'Chassis Split:  <b>${expdata[27]}</b>')
    num_items = len(adds)
    tabover = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
    if len(btype) == 1:
        if multibid[0] == 'on':
            if num_items == 1:
                sen = '<br><br>An added charge to these quotes will include: '
            elif num_items > 1:
                sen = '<br><br>Added charges to these quotes will include: '
        else:
            if num_items == 1: sen = '<br><br>An added charge to this quote will include: '
            if num_items > 1: sen = '<br><br>Added charges to this quote will include: '
    if len(btype) > 1:
        if num_items == 1: sen = '<br><br>An added charge to these quotes will include: '
        elif num_items > 1: sen = '<br><br>Added charges to these quotes will include: '
    for ix, add in enumerate(adds):
        if ix == 0: sen = sen + f'<br>{tabover}' + add
        elif ix == num_items-1: sen = sen + f'<br>{tabover}' + add
        else: sen = sen + f'<br>{tabover}' + add
    if num_items>0: sen = sen + '.  '
    stype = 'reg'
    mixtype = 'none'
    if tbox[17]: stype = 'ml'
    if tbox[18]:
        mixtype = 'mix'
        stype = 'ml'

    if tbox[19] and tbox[20]:  sen = sen + f'<br><br>We have immediate capacity and capacity into next week to execute the job quoted. '
    elif tbox[19]: sen = sen + f'<br><br>We have immediate capacity to execute the job quoted. '
    elif tbox[20]: sen = sen + f'<br><br>We have capacity for next week and beyond to execute the job quoted. '

    return sen, tbox, btype, stype, mixtype

def get_costs(miles, hours, lats, lons, dirdata, tot_dist, tot_dura, qidat):
    # Get the base inputs costs:
    ph_driver = float(qidat.ph_driver) / 100
    fuel = float(qidat.fuelpergal) / 100
    mpg = float(qidat.mpg) / 100
    pm_fuel = fuel / mpg
    ins = float(qidat.insurance_annual_truck) / 100
    ph_insurance = ins / 1992  # based on 249 work days 8 hrs per day
    markup = float(qidat.markup) / 100
    toll = float(qidat.toll) / 100
    gapct = float(qidat.ga) / 100
    pm_repairs = float(qidat.pm_repairs) / 100
    pm_fees = float(qidat.pm_fees) / 100
    pm_other = float(qidat.pm_other) / 100
    pmc = pm_fuel + pm_repairs + pm_fees + pm_other
    phc = ph_driver + ph_insurance
    fsc = float(qidat.FSC) / 100
    chassis2 = float(qidat.chassis2) / 100
    chassis3 = float(qidat.chassis3) / 100
    prepull = float(qidat.prepull) / 100
    store = float(qidat.store) / 100
    detention = float(qidat.detention) / 100
    extrastop = float(qidat.extrastop) / 100
    overweight = float(qidat.overweight) / 100
    reefer = float(qidat.reefer) / 100
    scale = float(qidat.scale) / 100
    resid = float(qidat.residential) / 100

    # Calculate road tolls
    tollroadlist = ['I-76', 'NJ Tpke']
    tollroadcpm = [.784, .275]
    legtolls = len(dirdata) * [0.0]
    legcodes = len(dirdata) * ['None']
    for lx, mi in enumerate(miles):
        for nx, tollrd in enumerate(tollroadlist):
            if tollrd in dirdata[lx]:
                legtolls[lx] = tollroadcpm[nx] * mi
                legcodes[lx] = tollrd

    # Calculate plaza tolls
    fm_tollbox = [39.267757, -76.610192, 39.261248, -76.563158]
    bht_tollbox = [39.259962, -76.566240, 39.239063, -76.603324]
    fsk_tollbox = [39.232770, -76.502453, 39.202279, -76.569906]
    bay_tollbox = [39.026893, -76.417512, 38.964938, -76.290104]
    sus_tollbox = [39.585193, -76.142883, 39.552328, -76.033975]
    new_tollbox = [39.647121, -75.774523, 39.642613, -75.757187]  # Newark Delaware Toll Center
    dmb_tollbox = [39.702146, -75.553479, 39.669730, -75.483284]
    tollcodes = ['FM', 'BHT', 'FSK', 'BAY', 'SUS', 'NEW', 'DMB']
    tollboxes = [fm_tollbox, bht_tollbox, fsk_tollbox, bay_tollbox, sus_tollbox, new_tollbox, dmb_tollbox]

    for jx, lat in enumerate(lats):
        stat1 = 'ok'
        stat2 = 'ok'
        stat3 = 0
        stat4 = 0
        tollcode = 'None'
        la = float(lat)
        lo = float(lons[jx])
        for kx, tollbox in enumerate(tollboxes):
            lah = max([tollbox[0], tollbox[2]])
            lal = min([tollbox[0], tollbox[2]])
            loh = max([tollbox[1], tollbox[3]])
            lol = min([tollbox[1], tollbox[3]])
            if la > lal and la < lah:
                stat1 = 'toll'
                if lo > lol and lo < loh:
                    stat2 = 'toll'
                    tollcode = tollcodes[kx]
                    legtolls[jx] = 24.00
                    legcodes[jx] = tollcode
            if jx > 0:
                lam = (lah + lal) / 2.0
                lom = (loh + lol) / 2.0
                la_last = float(lats[jx - 1])
                lo_last = float(lons[jx - 1])
                stat3, stat4 = checkcross(lam, la_last, la, lom, lo_last, lo)
                if stat3 == 1 and stat4 == 1:
                    tollcode = tollcodes[kx]
                    legtolls[jx] = 24.00
                    legcodes[jx] = tollcode
        ##print(lat,lons[jx],stat1, stat2, stat3, stat4, tollcode)

    tot_tolls = 0.00
    porttime = 1.4
    loadtime = 2.0
    triptime = tot_dura * 2.0
    handling = .5 + triptime * .01
    dphandling = .75 + triptime * .05
    tottime = porttime + loadtime + triptime + handling
    dptime = porttime + triptime + dphandling
    timedata = [d1s(triptime), d1s(porttime), d1s(loadtime), d1s(handling), d1s(tottime)]

    tripmiles = tot_dist * 2.0
    portmiles = .4
    glidemiles = 10 + .005 * tripmiles
    totmiles = tripmiles + portmiles + glidemiles
    distdata = [d1s(tripmiles), d1s(portmiles), '0.0', d1s(glidemiles), d1s(totmiles)]

    newdirdata = []
    for lx, aline in enumerate(dirdata):
        tot_tolls += legtolls[lx]
        aline = aline.replace('<div style="font-size:0.9em">Toll road</div>', '')
        aline = aline.strip()
        # print(aline)
        # print(f'Dist:{d1s(miles[lx])}, Time:{d1s(hours[lx])}, ')
        if legtolls[lx] < .000001:
            newdirdata.append(f'{d1s(miles[lx])} MI {d2s(hours[lx])} HRS {aline}')
        else:
            newdirdata.append(
                f'{d1s(miles[lx])} MI {d2s(hours[lx])} HRS {aline} Tolls:${d2s(legtolls[lx])}, TollCode:{legcodes[lx]}')

    # Cost Analysis:
    cost_drv = tottime * ph_driver
    cost_fuel = totmiles * pm_fuel
    cost_tolls = 2.0 * tot_tolls

    cost_insur = tottime * ph_insurance
    cost_rm = totmiles * pm_repairs
    cost_misc = totmiles * (pm_fees + pm_other)

    cost_direct = cost_drv + cost_fuel + cost_tolls + cost_insur + cost_rm + cost_misc
    cost_ga = cost_direct * gapct / 100.0
    cost_total = cost_direct + cost_ga
    costdata = [d2s(cost_drv), d2s(cost_fuel), d2s(cost_tolls), d2s(cost_insur), d2s(cost_rm), d2s(cost_misc),
                d2s(cost_ga), d2s(cost_direct), d2s(cost_total)]

    bid = cost_total * markup
    dpcost = (dptime * (ph_driver + ph_insurance) + totmiles * (
                pm_fuel + pm_repairs + pm_fees + pm_other) + cost_tolls) * (1 + gapct / 100)
    dpbid = dpcost * markup
    bobtailcost = ((dptime - .25) * (ph_driver + ph_insurance) + (totmiles - 8) * (
                pm_fuel + pm_repairs + pm_fees + pm_other)) * (1 + gapct / 100)
    drbid = dpbid + bobtailcost * markup
    fuelbid = bid / (1 + fsc / 100)
    allbid = bid + 2 * 40

    biddata = [d2s(roundup(bid)), d2s(roundup(drbid)), d2s(roundup(dpbid)), d2s(roundup(fuelbid)), d2s(roundup(allbid))]
    return biddata

def get_body_text(qdat):

    mid = qdat.Mid
    print(f'this mid is {mid}')
    username = usernames['quot']
    password = passwords['quot']
    imap = imaplib.IMAP4_SSL(imap_url)
    imap.login(username, password)
    status, messages = imap.select('INBOX')
    try:
        result, data = imap.search(None, f'HEADER Message-ID {mid}')
        msg_id_list = data[0].split()
        result, data = imap.fetch(msg_id_list[0], '(RFC822)')
        email_message = email.message_from_bytes(data[0][1])

        # extract the subject of the email
        subject = extract_for_code(email_message["Subject"])
        print(f'****Getting the Body Text***** for Subject: {subject}')
    except:
        print('Could not locate this email header')
        return 'Email ID not found', None

    # Set default text particulars
    plain_text_content = ''
    html_content = None

    # extract the email content as a string
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == 'text/plain':
                try:
                    plain_text_content = part.get_payload(decode=True).decode('utf-8')
                except UnicodeDecodeError as e:
                    plain_text_content = part.get_payload(decode=True).decode('utf-8', errors='replace')
            if part.get_content_type() == "text/html":
                try:
                    html_content = part.get_payload(decode=True).decode("utf-8")
                except UnicodeDecodeError as e:
                    html_content = part.get_payload(decode=True).decode("utf-8", errors='replace')

                soup = BeautifulSoup(html_content, "html.parser")
                plain_text_content = soup.get_text()
    else:
        plain_text_content = email_message.get_payload(decode=True).decode('utf-8')

    #print('Returning from get_body_text', plain_text_content)
    return plain_text_content, html_content


def isoQuote():
    username = session['username'].capitalize()
    #define User variables
    # Qote being worked
    uquot = f'{username}_quot'
    uiter = f'{username}_iter'
    umid= f'{username}_mid'
    utext= f'{username}_text'
    uhtml= f'{username}_html'
    quot=0
    tbox = [0]*28
    bidthis = [0]*5
    expdata=[]
    costdata=[]
    multibid=['off', 1, 0, 0]
    locs = []
    ebodytxt=''
    qdat = None
    htmltext = None
    plaintext = None
    mid = ''
    locto = None


    from viewfuncs import dataget_Q, nonone, numcheck

    if request.method == 'POST':
        try:
            iter = int(os.environ[uiter])
            oldmid = os.environ[umid]
        except:
            iter = 1
            oldmid = 'Not Defined'
        try:
            plaintext = os.environ[utext]
        except:
            plaintext = ''
        try:
            htmltext = os.environ[uhtml]
        except:
            htmltext = ''
        print(f'This is a POST with iter {iter} and last mid {oldmid}')
        emailgo = request.values.get('Email')
        updatego = request.values.get('GetQuote')
        updatebid = request.values.get('Update')
        updateE = request.values.get('UpdateE')
        returnhit = request.values.get('Return')
        removego = request.values.get('RemoveGo')
        bidname = request.values.get('bidname')
        ware = request.values.get('Ware')
        exitnow = request.values.get('exitquotes')
        if exitnow is not None:
            print('Exiting quotes')
            return 'exitnow', costdata, None, expdata, None, None, None, locto, None, None, None, None, None, None, None, None, None, None, None

        for jx in range(5):
            #print(f'jx={jx} and bidthis[jx]={bidthis[jx]}')
            bidthis[jx] = request.values.get(f'bidthis{jx}')
            bidthis[jx] = d2s(bidthis[jx])
            #print(f'after jx={jx} and bidthis[jx]={bidthis[jx]}')

        locfrom = request.values.get('locfrom')
        thismuch = request.values.get('thismuch')
        taskbox = request.values.get('taskbox')
        taskbox = nonone(taskbox)
        qbid = request.values.get('quickbid')
        qdel = request.values.get('quickdel')
        getnumq = request.values.get('numcit')
        if getnumq is not None:
            if 1 == 1:
                try: multibid[1] = int(getnumq)
                except: multibid[1] = 1
                if multibid[1] > 1:
                    multibid[0] = 'on'
                    for ix in range(multibid[1]):
                        locs.append(request.values.get(f'locto{ix}'))
                    multibid[2] = locs
                else: multibid[0] = 'off'
            elif 1 == 2:
                multibid[0] = 'off'
                multibid[1] = 1
        else:
            multibid[0] = 'off'
            multibid[1] = 1
        print(f'mutlibid is {multibid[0]} and {multibid[1]}')


        if qbid is not None: taskbox = 1
        if qdel is not None: taskbox = 2
        refresh = request.values.get('refresh')
        if refresh is not None: taskbox = 6
        quotbut = request.values.get('optradio')
        updatecosts = request.values.get('newcosts')
        def_costs = request.values.get('oldcosts')
        updatefees = request.values.get('newfees')

        if updatecosts is not None or updatefees is not None:
            alist = [request.values.get('driver'), request.values.get('fuel'), request.values.get('mpg'), request.values.get('insurance'), request.values.get('markup'),
                     request.values.get('toll'), request.values.get('gapct'), request.values.get('rm'), request.values.get('fees'), request.values.get('other'),
                     request.values.get('fsc'), request.values.get('chassis2'), request.values.get('chassis3'), request.values.get('prepull'), request.values.get('store'), request.values.get('detention'),
                     request.values.get('extrastop'),request.values.get('overweight'), request.values.get('reefer'), request.values.get('scale'), request.values.get('residential'),
                     request.values.get('congestion'), request.values.get('chassplit'), request.values.get('owmile')]
            blist = [int(float(a)*100) for a in alist]
            pmf=int(100*float(alist[1])/float(alist[2]))
            phi=int(100*float(alist[3])/1992)
            #print(f'pmf={pmf} and phi={phi}')
            pmt = pmf+blist[7]+blist[8]+blist[9]
            pht = blist[0] + phi
            input = Quoteinput(ph_driver=blist[0],fuelpergal=blist[1],mpg=blist[2],insurance_annual_truck=blist[3],markup=blist[4],toll=blist[5],ga=blist[6],pm_repairs=blist[7],pm_fees=blist[8],pm_other=blist[9],pm_fuel=pmf,ph_insurance=phi,pm_total=pmt,ph_total=pht,FSC=blist[10],
                               chassis2=blist[11], chassis3=blist[12], prepull=blist[13], store=blist[14], detention=blist[15], extrastop=blist[16], overweight=blist[17], reefer=blist[18], scale=blist[19], residential=blist[20], congestion=blist[21], chassplit=blist[22], owmile=blist[23])
            db.session.add(input)
            db.session.commit()
            qidat = Quoteinput.query.order_by(Quoteinput.id.desc()).first()

        elif def_costs is not None:
            #only update the cost data, retain the current fee data
            qidat = Quoteinput.query.first()
            qfdat = Quoteinput.query.order_by(Quoteinput.id.desc()).first()
            input = Quoteinput(ph_driver=qidat.ph_driver, fuelpergal=qidat.fuelpergal, mpg=qidat.fuelpergal, insurance_annual_truck=qidat.insurance_annual_truck,
                               markup=qidat.markup, toll=qidat.toll, ga=qidat.toll, pm_repairs=qidat.pm_repairs, pm_fees=qidat.pm_fees,
                               pm_other=qidat.pm_other, pm_fuel=qidat.pm_fuel, ph_insurance=qidat.ph_insurance, pm_total=qidat.pm_total, ph_total=qidat.ph_total,
                               FSC=qfdat.FSC, chassis2=qfdat.chassis2, chassis3=qfdat.chassis3, prepull=qfdat.prepull, store=qfdat.detention, extrastop=qfdat.extrastop, overweight=qfdat.overweight,
                               reefer=qfdat.reefer, scale=qfdat.scale, residential=qfdat.residential, congestion=qfdat.congestion, chassplit=qfdat.chassplit, owmile=qfdat.owmile)
            db.session.add(input)
            db.session.commit()
            #This makes first and last records the same so from now on will get original values until a change is made
        else:
            qidat = Quoteinput.query.order_by(Quoteinput.id.desc()).first()

        ph_driver = float(qidat.ph_driver) / 100
        fuel = float(qidat.fuelpergal) / 100
        mpg = float(qidat.mpg) / 100
        pm_fuel = fuel / mpg
        ins = float(qidat.insurance_annual_truck) / 100
        ph_insurance = ins / 1992  # based on 249 work days 8 hrs per day
        markup = float(qidat.markup)/100
        toll = float(qidat.toll) / 100
        gapct = float(qidat.ga)/100
        pm_repairs = float(qidat.pm_repairs) / 100
        pm_fees = float(qidat.pm_fees) / 100
        pm_other = float(qidat.pm_other) / 100
        pmc = pm_fuel + pm_repairs + pm_fees + pm_other
        phc = ph_driver + ph_insurance
        fsc = float(qidat.FSC)/100
        chassis2 = float(qidat.chassis2) / 100
        chassis3 = float(qidat.chassis3) / 100
        prepull = float(qidat.prepull) / 100
        store = float(qidat.store) / 100
        detention = float(qidat.detention) / 100
        extrastop = float(qidat.extrastop) / 100
        overweight = float(qidat.overweight) / 100
        reefer = float(qidat.reefer)/100
        scale = float(qidat.scale) / 100
        resid = float(qidat.residential) / 100
        congest = float(qidat.congestion) / 100
        chassplit = float(qidat.chassplit) / 100
        owmile = float(qidat.owmile) / 100

        #print(f'ph_driver is {ph_driver} and d2s gives {d2s(ph_driver)}')
        expdata = [d2s(ph_driver), d2s(fuel), d2s(mpg), d2s(ins), d2s(markup), d2s(toll), d2s(gapct),
                   d2s(pm_repairs), d2s(pm_fees), d2s(pm_other), d2s(pm_fuel), d2s(ph_insurance), d2s(pmc), d2s(phc),
                   d1s(fsc), d2s(chassis2), d2s(chassis3), d2s(prepull), d2s(store), d2s(detention), d2s(extrastop),
                   d2s(overweight), d2s(owmile), d2s(reefer), d2s(scale), d2s(resid), d2s(congest), d2s(chassplit)]

        qdata = dataget_Q(thismuch)
        #quot, numchecked = numcheck(1, qdata, 0, 0, 0, 0, ['quot'])

        if quotbut is not None:
            quot=nonone(quotbut)
        if quot == 0:
            quot = request.values.get('quotpass')
            quot = nonone(quot)

        qdat = Quotes.query.get(quot)
        print(f'quot:{quot} quotbut:{quotbut} username:{username} taskbox:{taskbox}')
        if qdat is not None:
            mid = qdat.Mid
            if mid == oldmid:
                print(f'No need to update, this is the same mid {mid}')
            else:
                print(f'Getting body_text 1011 because mid is {mid} and oldmid is {oldmid}')
                plaintext, htmltext = get_body_text(qdat)

        if returnhit is not None:
            taskbox = 0
            quot = 0

        if removego is not None or ware is not None:
            if removego is not None:  qdat.Status = -1
            else: qdat.Status = 7
            db.session.commit()
            #New get the new item not removed from the list
            qdat = Quotes.query.filter(Quotes.Status == 0).order_by(Quotes.id.desc()).first()
            if qdat is not None:
                quot = qdat.id
                quotbut = qdat.id
                # Check to see if we have rolled into a new date, if so then go back to the table
                datethis = f'{qdat.Date}'
                datelast = request.values.get('datelast')

                if datelast is not None:
                    try:
                        datethis = datethis[0:10]
                        datelast = datelast[0:10]
                    except:
                        datethis = '0'
                        datelast = '1'
                    print(f'comparing {datethis} to {datelast}')
                    if datethis == datelast:
                        print(f'Getting body_text because it is a successful remove and go')
                        plaintext, htmltext = get_body_text(qdat)
                        mid = qdat.Mid
                        oldmid = qdat.Mid
                    else:
                        taskbox = 0
                        quot = 0
            multibid = ['off', 1, 0, 0]

        #If no radio button selected then go with generic
        if taskbox == 1 and quot == 0: taskbox = 5

        if taskbox == 2:
            if qdat is not None:
                print(f'quot is {quot}')
                qdat.Status = -1
                db.session.commit()
                taskbox = 0

        if taskbox == 3:
            if qdat is not None:
                qdat.Status = 0
                db.session.commit()
                taskbox = 0

        if taskbox == 4:
            if qdat is not None:
                qdat.Status = 3
                db.session.commit()
                taskbox = 0

        if taskbox == 7:
            if qdat is not None:
                qdat.Status = 7
                db.session.commit()
                taskbox = 0

        if taskbox == 6:
            add_quote_emails()
            # Set quotes to top of the table:
            qdat = Quotes.query.filter(Quotes.Status == 0).order_by(Quotes.id.desc()).first()
            if qdat is not None:
                quot = qdat.id
                quotbut = qdat.id
                mid = qdat.Mid
                print(f'Getting body_text because we just refreshed the emails')
                plaintext, htmltext = get_body_text(qdat)

        if taskbox == 1 or taskbox == 5:
            if qdat is None:
                qdat = Quotes.query.filter(Quotes.Status==0).order_by(Quotes.id.desc()).first()
                if qdat is not None:
                    quot = qdat.id
                    quotbut = qdat.id
                    locto = qdat.Location
            if quot>0 and qdat is not None:
                if mid != oldmid:
                    print(f'Getting body_text because we are updating but mid: {mid} not oldmid {oldmid}')
                    plaintext, htmltext = get_body_text(qdat)
                if locto is None:
                    locto, loci = get_place(qdat.Subject, plaintext, multibid)
                    qdat.Location = locto
                    multibid[2] = loci
                    db.session.commit()
                if multibid[0] == 'on':
                    # Test if all locs are None then try to extract from email:
                    testloc, testloci = get_place(qdat.Subject, plaintext, multibid)
                    locs = multibid[2]
                    print(f'Here is multibid[1]:{multibid[1]} and here is multibid[2]: {multibid[2]}')
                    print(f'Here is locs:{locs} and here is testloci:{testloci}')
                    for ix in range(multibid[1]):
                        if not hasinput(locs[ix]): locs[ix] = testloci[ix]

                emailto = qdat.From
                if emailto is None:
                    emailto = qdat.From
                    qdat.From = emailto
                    db.session.commit()
            else:
                print('No radio button selected, default is top of the current list')
                comdata = companydata()
                locto = comdata[6]
                emailto = usernames['serv']

            if quot > 0 or taskbox == 5:
                if qdat is not None:
                    locfrom = qdat.Start
                    if locfrom is None:
                        locfrom = 'Seagirt Marine Terminal, Baltimore, MD 21224'
                else:
                    locfrom = 'Seagirt Marine Terminal, Baltimore, MD 21224'

                if updatego is not None or updatebid is not None or emailgo is not None or updateE is not None:
                    if multibid[0] == 'on':
                        mbids = []
                        for ix in range(len(tbox)):
                            tbox[ix] = request.values.get(f'tbox{str(ix)}')
                        for locto in locs:
                            print(f'Getting data for going to location {locto}')
                            if hasinput(locto):
                                miles, hours, lats, lons, dirdata, tot_dist, tot_dura = get_directions(locfrom, locto)
                                biddata = get_costs(miles, hours, lats, lons, dirdata, tot_dist, tot_dura, qidat)
                                print(biddata)
                                if tbox[15]: mbids.append(biddata[4])
                                elif tbox[12]: mbids.append(biddata[0])
                                elif tbox[13]: mbids.append(biddata[1])
                                elif tbox[14]: mbids.append(biddata[2])
                                elif tbox[16]: mbids.append(biddata[3])
                            else:
                                mbids.append('0.00')
                        print(mbids)
                        multibid[3] = mbids


                    locto = request.values.get('locto')
                    if locto is None:
                        locto = 'Capitol Heights, MD  20743'
                    locfrom = request.values.get('locfrom')
                    emailto = request.values.get('edat2')
                    respondnow = datetime.datetime.now()
                    if taskbox == 1 or taskbox == 5:
                        qdat.Start = locfrom
                        qdat.Location = locto
                        qdat.From = emailto
                        try:
                            bidshort = [float(bid) for bid in bidthis if hasinput(bid)]
                            qdat.Amount = d2s(max(bidshort))
                        except:
                            qdat.Amount = '0.00'
                        qdat.Person = bidname
                        qdat.Responder = username
                        qdat.RespDate = respondnow
                        qdat.Status = 1
                        db.session.commit()

                if emailgo is not None:
                    print(f'The task box is {taskbox}')
                    emaildata = sendquote()
                    if taskbox == 1 or taskbox == 5:
                        qdat.Status = 2
                        qdat.Subjectsend = emaildata[0]
                        qdat.Response = emaildata[1]
                        qdat.Emailto = emaildata[2]
                        db.session.commit()


                    # Now get the new item not removed from the list
                    qdat = Quotes.query.filter(Quotes.Status == 0).order_by(Quotes.id.desc()).first()
                    if qdat is not None:
                        quot = qdat.id
                        quotbut = qdat.id
                        mid = qdat.Mid
                        plaintext, htmltext = get_body_text(qdat)

                        # Check to see if we have tolled into a new date, if so then go back to the table
                        datethis = f'{qdat.Date}'
                        datelast = request.values.get('datelast')

                        if datelast is not None:
                            try:
                                datethis = datethis[0:10]
                                datelast = datelast[0:10]
                            except:
                                datethis = '0'
                                datelast = '1'
                            print(f'comparing {datethis} to {datelast}')
                            if datethis == datelast:
                                multibid = ['off', 1, 0, 0]
                                taskbox = 5
                                emailto = qdat.From
                                if emailto is None:
                                    emailto = qdat.From
                                    qdat.From = emailto
                                    db.session.commit()
                                locto, loci = get_place(qdat.Subject, plaintext, multibid)
                                qdat.Location = locto
                                db.session.commit()
                            else:
                                taskbox = 0
                                quot = 0
                        else:
                            taskbox = 0
                            quot = 0
                    else:
                        taskbox = 0
                        quot = 0



                print('Running Directions:',locfrom,locto,bidthis[0],bidname,taskbox,quot)
                try:
                    ####################################  Directions Section  ######################################
                    miles, hours, lats, lons, dirdata, tot_dist, tot_dura = get_directions(locfrom,locto)

                    #Calculate road tolls
                    tollroadlist = ['I-76','NJ Tpke']
                    tollroadcpm = [.784, .275]
                    legtolls = len(dirdata)*[0.0]
                    legcodes = len(dirdata)*['None']
                    for lx,mi in enumerate(miles):
                        for nx,tollrd in enumerate(tollroadlist):
                            if tollrd in dirdata[lx]:
                                legtolls[lx] = tollroadcpm[nx]*mi
                                legcodes[lx] = tollrd

                    #Calculate plaza tolls
                    fm_tollbox =  [39.267757, -76.610192, 39.261248, -76.563158]
                    bht_tollbox = [39.259962, -76.566240, 39.239063, -76.603324]
                    fsk_tollbox = [39.232770, -76.502453, 39.202279, -76.569906]
                    bay_tollbox = [39.026893, -76.417512, 38.964938, -76.290104]
                    sus_tollbox = [39.585193, -76.142883, 39.552328, -76.033975]
                    new_tollbox = [39.647121, -75.774523, 39.642613, -75.757187] #Newark Delaware Toll Center
                    dmb_tollbox = [39.702146, -75.553479, 39.669730, -75.483284]
                    tollcodes = ['FM', 'BHT', 'FSK', 'BAY', 'SUS', 'NEW', 'DMB']
                    tollboxes = [fm_tollbox, bht_tollbox, fsk_tollbox, bay_tollbox, sus_tollbox, new_tollbox, dmb_tollbox]

                    for jx,lat in enumerate(lats):
                        stat1 = 'ok'
                        stat2 = 'ok'
                        stat3 = 0
                        stat4 = 0
                        tollcode = 'None'
                        la = float(lat)
                        lo = float(lons[jx])
                        for kx, tollbox in enumerate(tollboxes):
                            lah = max([tollbox[0],tollbox[2]])
                            lal = min([tollbox[0], tollbox[2]])
                            loh = max([tollbox[1],tollbox[3]])
                            lol = min([tollbox[1], tollbox[3]])
                            if la > lal and la < lah:
                                stat1 = 'toll'
                                if lo > lol and lo < loh:
                                    stat2 = 'toll'
                                    tollcode = tollcodes[kx]
                                    legtolls[jx] = 24.00
                                    legcodes[jx] = tollcode
                            if jx > 0:
                                lam = (lah + lal)/2.0
                                lom = (loh + lol)/2.0
                                la_last = float(lats[jx-1])
                                lo_last= float(lons[jx-1])
                                stat3, stat4 = checkcross(lam,la_last,la,lom,lo_last,lo)
                                if stat3 == 1 and stat4 ==1:
                                    tollcode = tollcodes[kx]
                                    legtolls[jx] = 24.00
                                    legcodes[jx] = tollcode
                        ##print(lat,lons[jx],stat1, stat2, stat3, stat4, tollcode)



                    tot_tolls = 0.00
                    porttime = 1.4
                    loadtime = 2.0
                    triptime = tot_dura * 2.0
                    handling = .5 + triptime*.01
                    dphandling = .75 + triptime*.05
                    tottime = porttime + loadtime + triptime + handling
                    dptime = porttime + triptime + dphandling
                    timedata = [d1s(triptime), d1s(porttime), d1s(loadtime), d1s(handling), d1s(tottime)]

                    tripmiles = tot_dist * 2.0
                    portmiles = .4
                    glidemiles = 10 + .005*tripmiles
                    totmiles = tripmiles + portmiles + glidemiles
                    distdata = [d1s(tripmiles), d1s(portmiles), '0.0', d1s(glidemiles), d1s(totmiles)]

                    newdirdata=[]
                    for lx, aline in enumerate(dirdata):
                        tot_tolls += legtolls[lx]
                        aline = aline.replace('<div style="font-size:0.9em">Toll road</div>','')
                        aline = aline.strip()
                        #print(aline)
                        #print(f'Dist:{d1s(miles[lx])}, Time:{d1s(hours[lx])}, ')
                        if legtolls[lx] < .000001:
                            newdirdata.append(f'{d1s(miles[lx])} MI {d2s(hours[lx])} HRS {aline}')
                        else:
                            newdirdata.append(f'{d1s(miles[lx])} MI {d2s(hours[lx])} HRS {aline} Tolls:${d2s(legtolls[lx])}, TollCode:{legcodes[lx]}')

                    # Cost Analysis:
                    cost_drv = tottime * ph_driver
                    cost_fuel = totmiles * pm_fuel
                    cost_tolls = 2.0 * tot_tolls

                    cost_insur = tottime * ph_insurance
                    cost_rm = totmiles * pm_repairs
                    cost_misc = totmiles * (pm_fees + pm_other)

                    cost_direct = cost_drv + cost_fuel + cost_tolls + cost_insur + cost_rm + cost_misc
                    cost_ga = cost_direct * gapct/100.0
                    cost_total = cost_direct + cost_ga
                    costdata = [d2s(cost_drv),d2s(cost_fuel),d2s(cost_tolls),d2s(cost_insur), d2s(cost_rm), d2s(cost_misc), d2s(cost_ga), d2s(cost_direct), d2s(cost_total)]

                    bid = cost_total * markup
                    dpcost = (dptime*(ph_driver+ph_insurance) + totmiles*(pm_fuel+pm_repairs+pm_fees+pm_other) + cost_tolls)*(1+gapct/100)
                    dpbid = dpcost*markup
                    bobtailcost = ((dptime-.25)*(ph_driver+ph_insurance) + (totmiles-8)*(pm_fuel+pm_repairs+pm_fees+pm_other))*(1+gapct/100)
                    drbid = dpbid+bobtailcost*markup
                    fuelbid = bid/(1+fsc/100)
                    allbid = bid + 2*40

                    biddata = [d2s(roundup(bid)),d2s(roundup(drbid)),d2s(roundup(dpbid)), d2s(roundup(fuelbid)), d2s(roundup(allbid))]

                    if updatego is not None or quotbut is not None or (taskbox == 5 and updatebid is None):
                        for ix in range(len(tbox)):
                            tbox[ix] = request.values.get(f'tbox{str(ix)}')
                        if tbox[12]: bidthis[0] = d2s(roundup(bid))
                        if tbox[13]: bidthis[1] = d2s(roundup(drbid))
                        if tbox[14]: bidthis[2] = d2s(roundup(dpbid))
                        if tbox[16]: bidthis[3] = d2s(roundup(fuelbid))
                        if tbox[15]: bidthis[4] = d2s(roundup(allbid))
                except:
                    timedata = []
                    distdata = []
                    costdata = []
                    biddata = []
                    newdirdata = []

                # Set checkbox defaults if first time through
                #print(updatebid, updatego, updateE,emailgo)
                if updatebid is None and updatego is None and updateE is None:
                    tbox = [0] * 24
                    tbox[0] = 'on'
                    tbox[12] = 'on'
                    if biddata:
                        if len(biddata)>0:
                            bidthis[0] = biddata[0]
                    takedef = 1
                else:
                    takedef = 0

                if quotbut is not None:
                    #Set the email data:
                    etitle = f'{cdata[0]} Quote to {locto} from {locfrom}'
                    if qdat is not None:
                        customer = qdat.Person
                        if customer is None:
                            customer = friendly(emailto)
                    else:
                        customer = friendly(emailto)
                    qdat.Person = customer
                    #Try to use just first name as default
                    try:
                        bidnamelist = customer.split()
                        #print(bidnamelist)
                        bidname = bidnamelist[0]
                    except:
                        bidname = ''
                    db.session.commit()
                    ebody, tbox, etitle = bodymaker(bidname,cdata,bidthis,locto,tbox,expdata,takedef,distdata,multibid, etitle)
                    ebody = ebody + maketable(expdata)
                    emailin1 = request.values.get('edat2')
                    if updatego is None:
                        emailin1 = emailonly(emailto)
                    emailin2 = ''
                    emailcc1 = usernames['info']
                    emailcc2 = usernames['serv']
                    emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2]
                else:
                    #Set the email data:
                    if updatebid is not None or updatego is not None:
                        for ix in range(len(tbox)):
                            tbox[ix] = request.values.get(f'tbox{str(ix)}')
                        etitle = f'{cdata[0]} Quote to {locto} from {locfrom}'
                        ebody, tbox, etitle = bodymaker(bidname,cdata,bidthis,locto,tbox,expdata, takedef,distdata, multibid, etitle)
                        ebody = ebody + maketable(expdata)
                    else:
                        etitle = request.values.get('edat0')
                        ebody = request.values.get('edat1')
                    emailin1 = request.values.get('edat2')
                    emailin2 = request.values.get('edat3')
                    emailcc1 = request.values.get('edat4')
                    emailcc2 = request.values.get('edat5')
                    emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2]
                    #qdat.Response = ebody
                    db.session.commit()


        else:
            qdata = dataget_Q(thismuch)
            quot = request.values.get('optradio')
            if quot is not None:
                qdat = Quotes.query.get(quot)
                print(f'Getting body_text because this is not a post so we are getting new values')
                plaintext, htmltext = get_body_text(qdat)
                if htmltext is None:
                    showtext = plaintext
                else:
                    showtext = htmltext
            else:
                showtext = ''
            locto = 'Capitol Heights, MD  20743'
            locfrom = 'Baltimore Seagirt'
            etitle = f'{cdata[0]} Quote for Drayage to {locto} from {locfrom}'
            efrom = usernames['quot']
            eto1 = 'unknown'
            eto2 = ''
            ecc1 = usernames['serv']
            ecc2 = usernames['info']
            emaildata = [etitle, showtext, eto1, eto2, ecc1, ecc2, efrom]
            costdata = None
            biddata = None
            newdirdata = None
            bidthis = None
            bidname = None


            # Get and update the cost data
            timedata = []
            distdata = []


    else:
        iter = 1
        os.environ['MID'] = 'None Selected'
        print('This is NOT a Post')
        ebodytxt = ''
        #print('Entering Quotes1',flush=True)
        username = session['username'].capitalize()
        tbox = [0] * 27
        tbox[0] = 'on'
        tbox[12] = 'on'
        qdat=None
        locto = 'Upper Marlboro, MD  20772'
        locfrom = 'Baltimore Seagirt'
        etitle = f'{cdata[0]} Quote for Drayage to {locto} from {locfrom}'
        ebody = f'Regirgitation from the input'
        efrom = usernames['quot']
        eto1 = 'unknown'
        eto2 = ''
        ecc1 = usernames['expo']
        ecc2 = usernames['info']
        emaildata = [etitle, ebody, eto1, eto2, ecc1, ecc2, efrom]
        costdata = None
        biddata = None
        newdirdata = None
        bidthis = None
        bidname = None
        timedata = []
        distdata = []
        quot=0
        # Set quotes to top of the table:
        qdat = Quotes.query.filter(Quotes.Status == 0).order_by(Quotes.id.desc()).first()
        if qdat is not None:
            quot = qdat.id
            quotbut = qdat.id
            print(f'Getting body_text because this is not a post and we set pointer to top of table')
            plaintext, htmltext = get_body_text(qdat)
        else:
            add_quote_emails()
        thismuch = '6'
        taskbox = 0


    qdata = dataget_Q(thismuch)
    if htmltext is None:
        showtext = plaintext
    else:
        showtext = htmltext
    print(f'Got qdata for thismuch={thismuch}, quot={quot}, lengthofqdata={len(qdata)}', flush=True)
    print(f'mutlibid on exit is {multibid[0]} and {multibid[1]}')
    #Save all the session variables that may have been updated...
    iter = iter + 1
    os.environ[uiter] = str(iter)
    if plaintext is None: plaintext = ''
    if htmltext is None: htmltext = ''
    os.environ[utext] = plaintext
    os.environ[uhtml] = htmltext
    os.environ[umid] = mid
    print(f'Exiting with iter = {iter} and mid: {mid}')
    return bidname, costdata, biddata, expdata, timedata, distdata, emaildata, locto, locfrom, newdirdata, qdata, bidthis, taskbox, thismuch, quot, qdat, tbox, showtext, multibid
import requests

from webapp import db
from flask import render_template, flash, redirect, url_for, session, logging, request
from requests import get
from webapp.CCC_system_setup import apikeys
from webapp.CCC_system_setup import myoslist, addpath, tpath, companydata, usernames, passwords, scac, imap_url, accessorials, signoff
from webapp.viewfuncs import d2s, stat_update, hasinput, d1s
#from viewfuncs import d2s, d1s
import imaplib, email
import math
import re
from email.header import decode_header
import webbrowser
import os
from email.utils import parsedate_tz, mktime_tz
from email.utils import parsedate_to_datetime, parseaddr
from bs4 import BeautifulSoup

import datetime
from webapp.models import Quotes, Quoteinput, Terminals
from webapp.send_mimemail import send_replymail
from pyzipcode import ZipCodeDatabase
zcdb = ZipCodeDatabase()

from viewfuncs import dataget_Q, nonone, numcheck
try:
    from zoneinfo import ZoneInfo
except:
    from backports.zoneinfo import ZoneInfo
import time
from contextlib import contextmanager
from tzlocal import get_localzone

from html import escape

API_KEY_GEO = apikeys['gkey']
API_KEY_DIS = apikeys['dkey']
cdata = companydata()

date_y4=re.compile(r'([1-9]|0[1-9]|[12][0-9]|3[01]) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4})')

today_now = datetime.datetime.now()
today = today_now.date()
timenow = today_now.time()
include_text = ''
EMAIL_BODY_CACHE = {}
EMAIL_BODY_CACHE_MAX = 50

# Adding helper functions to cache the email text
def get_cache_key_for_qdat(qdat):
    if qdat is None:
        return None
    return str(qdat.id)


def get_cached_body_text(qdat, force_refresh=False):
    """
    Server-side in-memory cache.
    Avoids storing large email bodies in Flask session cookies.
    """
    global EMAIL_BODY_CACHE

    if qdat is None:
        return '', None

    cache_key = get_cache_key_for_qdat(qdat)
    if cache_key is None:
        return '', None

    if not force_refresh and cache_key in EMAIL_BODY_CACHE:
        print(f"[CACHE HIT] body text for qdat {qdat.id}", flush=True)
        item = EMAIL_BODY_CACHE[cache_key]
        return item.get('plaintext', ''), item.get('htmltext')

    print(f"[CACHE MISS] body text for qdat {qdat.id}", flush=True)
    plaintext, htmltext = get_body_text(qdat)

    EMAIL_BODY_CACHE[cache_key] = {
        'plaintext': plaintext,
        'htmltext': htmltext,
    }

    # trim cache if too large
    if len(EMAIL_BODY_CACHE) > EMAIL_BODY_CACHE_MAX:
        first_key = next(iter(EMAIL_BODY_CACHE))
        EMAIL_BODY_CACHE.pop(first_key, None)

    return plaintext, htmltext


def clear_cached_body_text(qdat=None):
    global EMAIL_BODY_CACHE

    if qdat is None:
        EMAIL_BODY_CACHE.clear()
        return

    cache_key = get_cache_key_for_qdat(qdat)
    if cache_key in EMAIL_BODY_CACHE:
        EMAIL_BODY_CACHE.pop(cache_key, None)

#Helper function for the equipment:
def get_equipment_text():
    text = ''
    def to_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0
    num40 = to_int(request.values.get('num40'))
    num20 = to_int(request.values.get('num20'))
    num45 = to_int(request.values.get('num45'))
    num40s = to_int(request.values.get('num40s'))
    if num40>0: text = f'{text} {num40} x 40HC,'
    if num20>0: text = f'{text} {num20} x 20ST,'
    if num45>0: text = f'{text} {num45} x 45HC,'
    if num40s>0: text = f'{text} {num40s} x 40ST,'
    #Remove trailing comma
    text = text.rstrip(',')
    if text == '': text = '1 x 40HC'
    return text

#Adding helper function to test time to perform various tasks
@contextmanager
def step_timer(label):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = time.perf_counter() - t0
        print(f"[TIMING] {label}: {dt:.3f}s", flush=True)


# Helper functions to avoid calling google api every update unless the locfrom or locto changes
def normalize_loc(s):
    return (s or '').strip().lower()

def make_route_key(locfrom, locto):
    return f"{normalize_loc(locfrom)}|||{normalize_loc(locto)}"



# Define new helper functions for conversion to send emails as replys
def html_to_text_for_preview(htmltext):
    """
    Convert HTML to readable plain text for safe in-page preview.
    """
    if not htmltext:
        return ''

    try:
        soup = BeautifulSoup(htmltext, 'html.parser')
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()
        text = soup.get_text('\n')
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    except Exception:
        return htmltext


def normalize_send_options(req):
    """
    Read new send controls from Aquotemaker.html.
    """
    send_mode = req.values.get('send_mode', 'reply')
    if send_mode not in ('direct', 'reply'):
        send_mode = 'reply'

    reply_style = req.values.get('reply_style', 'quoted')
    if reply_style not in ('clean', 'quoted'):
        reply_style = 'quoted'

    save_sent = req.values.get('save_sent') == 'on'

    return send_mode, reply_style, save_sent


def get_original_message_meta(qdat):
    """
    Reload the original message by Message-ID and pull headers needed for reply threading.
    """
    if qdat is None or not qdat.Mid:
        return {}

    username = usernames['quot']
    password = passwords['quot']
    mid = qdat.Mid.strip()

    imap = imaplib.IMAP4_SSL(imap_url)
    imap.login(username, password)

    try:
        imap.select('INBOX')
        result, data = imap.search(None, f'HEADER Message-ID "{mid}"')
        if result != 'OK' or not data or not data[0]:
            return {}

        msg_ids = data[0].split()
        if not msg_ids:
            return {}

        result, fetched = imap.fetch(msg_ids[0], '(RFC822)')
        if result != 'OK':
            return {}

        email_message = email.message_from_bytes(fetched[0][1])

        from_header = email_message.get('From', '')
        reply_to_header = email_message.get('Reply-To', '')
        reply_to_email = parseaddr(reply_to_header)[1] or parseaddr(from_header)[1]

        return {
            'message_id': email_message.get('Message-ID', ''),
            'references': email_message.get('References', ''),
            'subject': email_message.get('Subject', qdat.Subject or ''),
            'from': from_header,
            'date': email_message.get('Date', ''),
            'reply_to_email': reply_to_email,
        }
    finally:
        try:
            imap.close()
        except Exception:
            pass
        imap.logout()


def build_quoted_reply_html(new_html, original_meta, original_html=None, original_text=None):
    """
    Build a reply body that includes the original message below the new quote.
    """
    header = (
        '<br><br><hr>'
        f'<div style="font-family:Arial,sans-serif;font-size:13px;color:#555;">'
        f'<b>From:</b> {escape(original_meta.get("from", ""))}<br>'
        f'<b>Date:</b> {escape(original_meta.get("date", ""))}<br>'
        f'<b>Subject:</b> {escape(original_meta.get("subject", ""))}'
        f'</div><br>'
    )

    if original_html:
        quoted = (
            '<blockquote style="margin:0;padding-left:12px;border-left:3px solid #ccc;">'
            f'{original_html}'
            '</blockquote>'
        )
    else:
        safe_text = escape(original_text or '').replace('\n', '<br>')
        quoted = (
            '<blockquote style="margin:0;padding-left:12px;border-left:3px solid #ccc;'
            'font-family:Arial,sans-serif;font-size:14px;">'
            f'{safe_text}'
            '</blockquote>'
        )

    return f'{new_html}{header}{quoted}'

# Begin new functions to support conveting webapp to api also

def default_tbox():
    """
    Default quote screen / pricing flags.
    Matches current first-pass behavior:
    - standard chassis on
    - live load on
    """
    tbox = [0] * 27
    tbox[0] = 'on'
    tbox[17] = 'on'
    return tbox


def copy_tbox(tbox):
    """
    Return a safe 27-slot copy so pricing functions do not mutate caller state.
    """
    if tbox is None:
        return default_tbox()

    out = [0] * 27
    for ix in range(min(len(tbox), 27)):
        out[ix] = tbox[ix]
    return out


def tbox_from_request(req, base_tbox=None):
    """
    Web helper: overlay request checkbox values onto an existing/default tbox.
    Any checkbox not present in request stays false/0.
    """
    tbox = copy_tbox(base_tbox)

    for ix in range(27):
        val = req.values.get(f'tbox{ix}')
        tbox[ix] = val if val is not None else 0

    return tbox


def tbox_from_flags(flags=None, base_tbox=None):
    """
    API/helper version. Accepts named booleans and converts them into the
    old 27-slot tbox structure.
    """
    flags = flags or {}
    tbox = copy_tbox(base_tbox)

    mapping = {
        'standard_chassis': 0,
        'triax_chassis': 1,
        'prepull': 2,
        'yard_storage': 3,
        'overweight': 4,
        'permits': 5,
        'extra_stop': 6,
        'reefer': 7,
        'scale_tickets': 8,
        'residential': 9,
        'urban': 10,
        'port_congestion': 11,
        'chassis_split': 12,
        'subtract_temp_fsc': 13,
        'is_45hc': 14,
        'is_20std': 15,
        'show_commodity': 16,
        'live': 17,
        'dr': 18,
        'dp': 19,
        'all_in_1d': 20,
        'all_in_2d': 21,
        'fsc': 22,
        'multi_load': 23,
        'mixed_20_40': 24,
        'immediate_capacity': 25,
        'future_capacity': 26,
    }

    for key, idx in mapping.items():
        if flags.get(key):
            tbox[idx] = 'on'
        else:
            tbox[idx] = 0

    return tbox


def normalize_markup(newmarkup, qidat):
    """
    Returns:
        markupx   -> float multiplier used in pricing
        newmarkup -> string version suitable for web/db reuse
    """
    default_markup = float(qidat.markup) / 100

    if newmarkup is None or str(newmarkup).strip() == '':
        return default_markup, str(default_markup)

    try:
        markupx = float(newmarkup)
        return markupx, str(newmarkup)
    except Exception:
        return default_markup, str(default_markup)

################end of api helper functions

def make_reply_subject(original_subject):
    subject = (original_subject or '').strip()
    if not subject:
        return 'Re:'
    if subject.lower().startswith('re:'):
        return subject
    return f'Re: {subject}'

def safe_db_text(val):
    if val is None:
        return ''
    return ''.join(ch for ch in val if ord(ch) <= 0xFFFF)

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
            try:
                part = response_part[1].decode('utf-8')
                msg = email.message_from_string(part)
                subject=msg['Subject']
                mid = msg['Message-ID']
            except:
                subject='Cannot Parse'
                mid=None
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
            if not 'Forwarded Message' in line or 'Subject:' in line or 'Date:' in line or 'To:' in line or 'CC:' in line or 'From:' in line or 'Content-Type' in line or 'Content-Transfer' in line:
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
            #print(f'Subject:{subject}')
        if 'Message-ID' in line:
            mid = line.split('Message-ID:')[1]
            mid = mid.replace('Fwd:', '')
            mid = mid.strip()
            #print(f'MID:{mid}')
        if 'From' in test and '@' in line and 'firsteagle' not in line and 'onestop' not in line:
            #print('efrom',line)
            efrom = line.split('From:')[1]
            efrom = efrom.strip()
            #print(f'From:{efrom}')
        if 'Date' in test:
            edate = line.split('Date:')[1]
            edate = edate.strip()
            #print(f'Date:{edate}')
        if 'Content-Type:' in line and 'plain' in line:
            #print(f'BodyStart:{line}')
            appendit = 1
        if 'Content-Type:' in line and 'html' in line:
            #print(f'BodyStop:{line}')
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
    try:
        text, encoding = decode_header(data)[0]
    except:
        text = 'No Decode Available'
        encoding = None
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
    imessages = int(messages[0])
    #print(f'Total number of messages in inbox is {imessages}')
    #print(f'username is {username}, password is {password}')
    #print(f'imap_url is {imap_url}')
    #print(f'status is {status}')

    if imessages >= 50:
        N = 50
    else:
        N = imessages - 1
    #for i in range(messages, messages - N, -1):
    for i in range(imessages - N , imessages + 1):
        decode_error = 0
        # fetch the email message by ID
        #res, msg = imap.fetch(str(i), "(RFC822)")
        # Insert the GPTChat solution
        #print(f'Attempting to get message {i}')
        result, email_data = imap.fetch(str(i), "(RFC822)")
        # convert the email message data into an email object
        #print(f'Result for email {i} is {result}')
        if result == 'OK':
            email_message = email.message_from_bytes(email_data[0][1])
            try:
                # extract the subject of the email
                subject = extract_for_code(email_message["Subject"])
                if('re:' in subject.lower()): skip = True
                else: skip = False
                #print(f'For message number {i} th Subject is {subject}')
                mid = extract_for_code(email_message["Message-ID"])
                mid = mid.strip()
            except:
                subject = 'Could not Decode Message'
                decode_error = 1
            try:
                fromp = extract_for_code(email_message["From"])
            except:
                fromp = 'Invalid Email'
            #print(fromp)
            try:
                if '@' not in fromp: fromp = 'Invalid Email'
            except:
                fromp = 'Invalid Email'

            #print(f'Message ID: {mid}')
            #print(f'Subject: {subject}')
            #print(f'From: {fromp}')

            # extract the date and time the email was sent
            try:
                date_time_str = email_message["Date"]
                date_time = parsedate_to_datetime(date_time_str)
                #utc_offset = date_time.utcoffset()
                ny_tz = ZoneInfo("America/New_York")
                #utc_dt = date_time.astimezone(ZoneInfo("UTC"))
                #local_tz = get_localzone()
                #local_dt = utc_dt.astimezone(local_tz)
                local_dt = date_time.astimezone(ny_tz)
                #print(f'DateTime: {date_time}')
                #print(f'UTC Time: {utc_dt}')
                #print(f'Local Time: {local_dt}')
                #print(f'Date: {thisdate}')
                #print(f'Time: {thistime}')
                #local_tz = ZoneInfo(time.tzname[0])
                #local_dt = utc_dt.astimezone(local_tz)
                #print(f'Local Date Time: {local_dt}')
            except:
                #print('Failed to get the email date-time string')
                date_time = today_now
                #thisdate = today
                #thistime = timenow
                #utc_dt = date_time.astimezone(ZoneInfo("UTC"))
                #local_tz = get_localzone()
                ny_tz = ZoneInfo("America/New_York")
                local_dt = date_time.astimezone(ny_tz)
                #local_dt = utc_dt.astimezone(local_tz)
                #print(f'Date Time extraction failed using {str(thisdate)} and {str(thistime)}')

            if not decode_error and not skip:
                qdat = Quotes.query.filter(Quotes.Mid == mid).first()
                if qdat is None:
                    try:
                        input = Quotes(Date=local_dt, From=fromp, Subject=subject, Mid=mid, Person=None, Emailto=None, Subjectsend=None,
                                       Response=None, Amount=None, Location=None, Status=0, Responder=None, RespDate=None, Start='Seagirt Marine Terminal, Baltimore, MD', Markup=None)
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
    #print(json['routes'])
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
        #print('Toll by latitude Method 2')
    if (lo_last<lom and lo>lom) or (lo_last>lom and lo<lom):
        locross = 1
        #print('Toll by longitude Method 2')
    return lacross, locross

def checkcross2(la_last, la, lo_last, lo, xmin, ymin, xmax, ymax):

    lanow = la_last
    lonow = lo_last
    lastep = (la - la_last)/100
    lostep = (lo - lo_last)/100

    for step in range(100):
        lanow = lanow+lastep
        lonow = lonow+lostep

        if lanow > ymin and lanow < ymax and lonow > xmin and lonow < xmax:
            return 1

    return 0


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

def make_emaildata_list(subject, body_html, to_1, to_2, cc_1, cc_2, from_addr=None):
    return [
        subject or '',
        body_html or '',
        to_1 or '',
        to_2 or '',
        cc_1 or '',
        cc_2 or '',
        from_addr or usernames['quot'],
    ]


def sendquote():
    """
    Send either:
      - direct standalone email
      - threaded reply to original email

    Requires the updated Aquotemaker.html fields:
      qid, mid, send_mode, reply_style, save_sent
    """

    error = 0

    qid = request.values.get('qid')
    send_mode, reply_style, save_sent = normalize_send_options(request)

    etitle = request.values.get('edat0')
    ebody = request.values.get('edat1')
    emailin1 = request.values.get('edat2')
    emailin2 = request.values.get('edat3')
    emailcc1 = request.values.get('edat4')
    emailcc2 = request.values.get('edat5')
    preview_subject = etitle

    qdat = None
    if qid:
        try:
            qdat = Quotes.query.get(int(qid))
        except Exception:
            qdat = None

    original_meta = {}
    original_plaintext = ''
    original_html = ''
    preview_subject = etitle

    if send_mode == 'reply' and qdat is not None:
        original_meta = get_original_message_meta(qdat)
        preview_subject = make_reply_subject(original_meta.get('subject') or qdat.Subject)
        try:
            with step_timer("get_body_text at top of sendquote"):
                original_plaintext, original_html = get_cached_body_text(qdat)
        except Exception:
            original_plaintext, original_html = '', ''

        # If no explicit To entered, default to reply-to / from
        if (not emailin1 or '@' not in emailin1) and original_meta.get('reply_to_email'):
            emailin1 = original_meta['reply_to_email']

        etitle = make_reply_subject(original_meta.get('subject') or qdat.Subject)

        if reply_style == 'quoted':
            ebody = build_quoted_reply_html(
                new_html=ebody,
                original_meta=original_meta,
                original_html=original_html,
                original_text=original_plaintext
            )

    if '@' not in (emailin1 or ''):
        error = 1

    emaildata = {
        'subject': etitle,
        'body_html': ebody,
        'to_1': emailin1,
        'to_2': emailin2,
        'cc_1': emailcc1,
        'cc_2': emailcc2,
        'from_addr': usernames['quot'],
        'send_mode': send_mode,
        'reply_style': reply_style,
        'save_sent': save_sent,
        'quote_id': qid,
        'original_message_id': original_meta.get('message_id', ''),
        'references': original_meta.get('references', ''),
        'original_subject': original_meta.get('subject', ''),
        'original_from': original_meta.get('from', ''),
        'original_date': original_meta.get('date', ''),
    }

    if error == 0:
        #send_result = send_mimemail(emaildata, 'qsnd')
        with step_timer("send_result"):
            send_result = send_replymail(emaildata, 'qsnd')

        # Optional bookkeeping
        if qdat is not None:
            try:
                qdat.Emailto = emailin1
                qdat.Subjectsend = etitle
                qdat.Response = safe_db_text(ebody)
                qdat.Responder = session.get('username')
                qdat.RespDate = datetime.datetime.now(ZoneInfo("America/New_York"))
                db.session.commit()
            except Exception:
                db.session.rollback()

        return emaildata, send_result

    return emaildata, None




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
    #print(f'url:{url}')
    response = get(url)
    #print(response.json())
    dis, dus, hts, las, los  = direct_resolver(response.json())

    #Convert all mixed units to miles, hours and convert from text to floats
    for di in dis:
        if 'mi' in di:
            #nu = float(di.replace('mi',''))
            nu = float(di.replace('mi', '').replace(',', ''))
        elif 'ft' in di:
            nu = float(di.replace('ft','').replace(',', ''))/5280.0
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

    #print(f'dists:{dists} duras:{duras} tot_dist:{tot_dist}')

    return dists, duras, lats, lons, hts, tot_dist, tot_dura

def get_place(subject, body, multibid):
    loci = []
    location = 'No Location Found'
    zip_c = re.compile(r'\w+[,.]?\s+\w+[,.]?\s+[0-9]{5}')
    zip_p = re.compile(r'[\s,]\d{5}(?:[-\s]\d{4})?')
    nozip = re.compile(r'\w+[,.]?\s+(MD|PA|VA|DE|NJ|OH|NC)')
    testp = zip_p.findall(subject)
    testp2 = zip_c.findall(subject)
    testq = zip_p.findall(body)
    testq2 = zip_c.findall(body)
    testp3 = nozip.match(subject)
    testq3 = nozip.match(body)
    #print(f'the subject has these zipcodes {testp}')
    #print(f'the body has these zipcodes {testq}')
    #print(f'the subject has these city-zips {testp2}')
    #print(f'the body has these city-zips {testq2}')
    #print(f'the subject has these city-states {testp3}')
    #print(f'the body has these city-states {testq3}')
    #print('The body is:',body)
    #print(f'the address is {testp}, {testq}, {testq2}, {testq3}')
    for test in testp:
        ziptest = test.strip()
        #print(f'this zip is: {ziptest}')
        try:
            zb = zcdb[ziptest]
            location = f'{zb.city}, {zb.state}  {ziptest}'
            # print(zcdb[location])
            # print(f'zb is {zb} {zb.city}')
            #print(f'In subject: test is {test} and location is **{location}**')
        except:
            #print(f'{ziptest} does not work')
            location = 'nogood'

        if location != 'nogood' and multibid[0]=='off': loci.append(location)

    for test in testq:
        ziptest = test.strip()
        #print(f'this zip is: {ziptest}')
        if zip != '21224':
            try:
                zb = zcdb[ziptest]
                location = f'{zb.city}, {zb.state}  {ziptest}'
                #print(f'In body: test is {test} and location is **{location}**')
            except:
                #print(f'{ziptest} does not work')
                location = 'nogood'
        else:
            location = 'nogood'

        if location != 'nogood': loci.append(location)


    if (len(testp)==0 and len(testq)==0) or len(loci)==0:
        location = 'No Location Found'
        #print(f'Both subject and body failed to find a location')
    else:
        #Find best and most likely loci
        #print('loci is:', loci)
        location = loci[0]

    if len(location) > 199: location = location[0:199]

    # if multibid is on need to make sure loci has same number of locations as multibid request
    requested = multibid[1]
    if len(loci) < requested:
        while len(loci) < requested:
            loci.append('No Location Found')
    if len(loci) > requested:
        loci = loci[0:requested]
    #print(f'returning location {location} loci {loci}')
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

def surcharge_bid(doit, sc, oldbid):
    if doit:
        bid = d2s(float(oldbid) - float(sc))
    else:
        bid = oldbid
    return bid

def bodymaker_direct(customer, cdata, bidthis, locto, tbox, expdata, distdata, multibid, etitle, port, include_text, whouse, wareBB, wareUD, mdistdata, costdata, sboxes):
    # Get the costs of the additional boxes checked
    if multibid[0] != 'on':
        sen, tbox, btype, stype, mixtype, ow = direct_insert_adds(tbox,expdata,distdata,multibid,mdistdata, 0, costdata)
    else:
        btype = []
        if tbox[17]: btype.append('live')
        if tbox[18]: btype.append('dr')
        if tbox[19]: btype.append('dp')
        if tbox[22]: btype.append('fsc')
        if tbox[20]: btype.append('all-in-1d')
        if tbox[21]: btype.append('all-in-2d')

    #print(f'btype is {btype} and wareBB is {wareBB}')
    tabover = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
    smallto = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\u2022'
    ebody = ''


    if wareBB is not None or wareUD is not None:
        #print('Running the warehouse wareBB section')
        sdray = f'Drayage from {port} to {cdata[0]} warehouse: <b>${expdata[29]}</b>'
        spallet1 = f'Pallets off-loaded at warehouse: <b>${expdata[30]} per pallet</b>'
        spallet2 = f'Pallets on-loaded from warehouse: <b>${expdata[30]} per pallet</b>'
        sstopallet = f'Storage in warehouse: <b>${expdata[31]} per pallet per day</b>'
        if wareBB is not None:
            ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote to dray and transload your container load from {port} to our warehouse in {cdata[6]}.<br><br>'
            ebody = ebody + f'\n{tabover}{sdray}<br>'
            ebody = ebody + f'\n{tabover}{spallet1}<br>'
            ebody = ebody + f'\n{tabover}{spallet2}<br>'
            ebody = ebody + f'\n{tabover}{sstopallet}<br>'

            bidtypeamount = [None, None]
            return ebody, tbox, etitle, bidtypeamount

        if wareUD is not None:
            if whouse[3]:
                ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote to dray and transload your container load from {port} to our warehouse in {cdata[6]}.<br><br>'
            else:
                ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote to transload your load at our warehouse in {cdata[6]}.<br><br>'
            if whouse[3]:
                ebody = ebody + f'\n{tabover}{sdray}<br>'
            if whouse[4]:
                ebody = ebody + f'\n{tabover}{spallet1}<br>'
                ebody = ebody + f'\n{tabover}{spallet2}<br>'
            if whouse [5]:
                ebody = ebody + f'\n{tabover}{sstopallet}<br>'
            if whouse [6]:
                ebody = ebody + f'\n{tabover}Unload each floor loaded container or dry van at a cost of <b>${expdata[32]}</b><br>'
            if whouse [7]:
                ebody = ebody + f'\n{tabover}Palletize the product at a cost of <b>${expdata[33]}</b> per pallet<br>'
            if whouse [8]:
                ebody = ebody + f'\n{tabover}Provide pallets for palletization at a cost of <b>${expdata[34]}</b> per pallet<br>'
            bidtypeamount = [None, None]
            return ebody, tbox, etitle, bidtypeamount


    bidtypeamount = [None, None]
    #print(f'the multibid is: {multibid}')

    # This section is active only if multiple locations is active, not if multiple bid types are needed for same location
    if multibid[0] == 'on':
        loci = multibid[2]
        bids = multibid[3]
        etitle = f'{cdata[0]} (MC#{cdata[12]}) Quotes to'
        for kx, loc in enumerate(loci):
            if hasinput(loc):
                etitle = etitle + f' {loc};'

        etitle = etitle[:-1]
        if 'all-in-1d' in btype:
            ebody = f'Hello {customer}, <br><br>We can cover this move. <br<br>Rate:'
            for ix, loc in enumerate(loci):
                sen, tbox, btype, stype, mixtype, ow = direct_insert_adds(tbox, expdata, distdata, multibid, mdistdata, ix, costdata)
                if ow:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> plus an OW fee of <b>${d2s(ow)}</b> to {loc}<br>'
                else:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'

            if sboxes[1] == 'include':
                ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
            else:
                ebody = ebody + f'{sen}'
            bidtypeamount[0] = 'all-in-1d'
            bidtypeamount[1] = bids[0]

        elif 'live' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>Live-Load</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                sen, tbox, btype, stype, mixtype, ow = direct_insert_adds(tbox, expdata, distdata, multibid, mdistdata, ix, costdata)
                #print(f'sen is {sen} for loc {loc}')
                if ow:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> plus an OW fee of <b>${d2s(ow)}</b> to {loc}<br>'
                else:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'
            ebody = ebody + f'<br>These quotes are inclusive of tolls, fuel, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'
            if sboxes[1] == 'include':
                ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
            else:
                ebody = ebody + f'{sen}'
            bidtypeamount[0] = 'live'
            bidtypeamount[1] = bids[0]

        elif 'dr' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>Drop-Pick</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                sen, tbox, btype, stype, mixtype, ow = direct_insert_adds(tbox, expdata, distdata, multibid, mdistdata, ix, costdata)
                if ow:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> plus an OW fee of <b>${d2s(ow)}</b> to {loc}<br>'
                else:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'

            ebody = ebody + f'<br>These quotes are inclusive of tolls and fuel.'
            if sboxes[1] == 'include':
                ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
            else:
                ebody = ebody + f'{sen}'
            bidtypeamount[0] = 'dr'
            bidtypeamount[1] = bids[0]

        elif 'dp' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>Drop-Hook</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                sen, tbox, btype, stype, mixtype, ow = direct_insert_adds(tbox, expdata, distdata, multibid, mdistdata, ix, costdata)
                if ow:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> plus an OW fee of <b>${d2s(ow)}</b> to {loc}<br>'
                else:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'

            ebody = ebody + f'<br>These quotes are inclusive of tolls and fuel.  A return container must be available and ready upon delivery or bobtail charges may apply.'
            if sboxes[1] == 'include':
                ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
            else:
                ebody = ebody + f'{sen}'
            bidtypeamount[0] = 'dp'
            bidtypeamount[1] = bids[0]

        elif 'fsc' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>Live-Load</b> quotes:<br><br>'

            for ix, loc in enumerate(loci):
                sen, tbox, btype, stype, mixtype, ow = direct_insert_adds(tbox, expdata, distdata, multibid, mdistdata, ix, costdata)
                if ow:
                    ebody = ebody + f'{tabover}<b>{bids[ix]} plus {d1s(expdata[14])}% FSC</b> plus an OW fee of <b>${d2s(ow)}</b> to {loc}<br>'
                else:
                    ebody = ebody + f'{tabover}<b>{bids[ix]} plus {d1s(expdata[14])}% FSC</b> to {loc}<br>'

            ebody = ebody + f'<br>These quotes are inclusive of tolls, fuel, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'
            if sboxes[1] == 'include':
                ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
            else:
                ebody = ebody + f'{sen}'
            bidtypeamount[0] = 'fsc'
            bidtypeamount[1] = bids[0]

    else:
        if locto is None or locto == 'No Location Found':
            ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> has no quote due to location not found.'
            bidtypeamount[0] = 'live'
            bidtypeamount[1] = 0.00
        else:
            equip = get_equipment_text()
            if tbox[24]: equip = '40HC and 20STD'
            com = 'General Freight'
            if sboxes[2] == 'com1':
                com = 'General Non-Haz'
            if sboxes[2] == 'com2':
                com = 'Unspecified Non-Haz'
            if sboxes[2] == 'com3':
                com = 'Wine'
            if sboxes[2] == 'com4':
                com = sboxes[3]
            if sboxes[2] == 'com5':
                com = 'General Freight Legal Weight'
                equip = sboxes[3]

            if 'all-in-1d' in btype:
                chassis = ''
                if tbox[0]: chassis = f'(Additional days <b>${expdata[15]}/day</b>)'
                if tbox[1]: chassis = f'(Additional days of triax <b>${expdata[16]}/day</b>)'
                ebody = f'Hello {customer}, '
                if tbox[25]: ebody = ebody + f'\n\n<br><br>We have immediate capacity to execute this move.'
                ebody = ebody + f'<br><br>Rate: <b>${bidthis[5]}</b> All-In\n<br>Lane: {port} to {locto}\n<br>Equipment: {equip}'
                if tbox[16]: ebody = ebody + f'\n<br>Commodity: {com}'
                ebody = ebody + f'\n\n<br><br>The rate includes:\n<br>{smallto}Tolls\n<br>{smallto}Fuel\n<br>{smallto}1 Day of Chassis {chassis}\n<br>{smallto}2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter)'
                if tbox[2]: ebody = ebody + f'\n<br>{smallto}Prepull'
                if tbox[3]: ebody = ebody + f'\n<br>{smallto}1 Day of Yard Storage (Additional Day {expdata[18]}/day)'
                if tbox[4]: ebody = ebody + f'\n<br>{smallto}Overweight Fees'
                if tbox[5]: ebody = ebody + f'\n<br>{smallto}Permits'
                if tbox[6]: ebody = ebody + f'\n<br>{smallto}Extra Stop'
                if tbox[7]: ebody = ebody + f'\n<br>{smallto}Reefer Fees'
                if tbox[8]: ebody = ebody + f'\n<br>{smallto}Scale Tickets'
                if tbox[9]: ebody = ebody + f'\n<br>{smallto}Residential Fees'
                if tbox[10]: ebody = ebody + f'\n<br>{smallto}Urban Fees'
                if tbox[11]: ebody = ebody + f'\n<br>{smallto}Congestion Fees'
                if tbox[12]: ebody = ebody + f'\n<br>{smallto}Chassis Split'


                if sboxes[1] == 'include':
                    ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
                else:
                    ebody = ebody + f'{sen}'

                bidtypeamount[0] = 'all-in-1d'
                bidtypeamount[1] = bidthis[5]

            elif 'all-in-2d' in btype:
                chassis = ''
                if tbox[0]: chassis = f'(Additional days <b>${expdata[15]}/day</b>)'
                if tbox[1]: chassis = f'(Additional days of triax <b>${expdata[16]}/day</b>)'
                ebody = f'Hello {customer}, '
                if tbox[25]: ebody = ebody + f'\n\n<br><br>We have immediate capacity to execute this move.'
                ebody = ebody + f'<br><br>Rate: <b>${bidthis[4]}</b> All-In\n<br>Lane: {port} to {locto}\n<br>Equipment: {equip}'
                if tbox[16]: ebody = ebody + f'\n<br>Commodity: {com}'
                ebody = ebody + f'\n\n<br><br>The rate includes:\n<br>{smallto}Tolls\n<br>{smallto}Fuel\n<br>{smallto}2 Days of Chassis {chassis}\n<br>{smallto}2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter)'

                if tbox[2]: ebody = ebody + f'\n<br>{smallto}Prepull'
                if tbox[3]: ebody = ebody + f'\n<br>{smallto}1 Day of Yard Storage (Additional Day {expdata[18]}/day)'
                if tbox[4]: ebody = ebody + f'\n<br>{smallto}Overweight Fees'
                if tbox[5]: ebody = ebody + f'\n<br>{smallto}Permits'
                if tbox[6]: ebody = ebody + f'\n<br>{smallto}Extra Stop'
                if tbox[7]: ebody = ebody + f'\n<br>{smallto}Reefer Fees'
                if tbox[8]: ebody = ebody + f'\n<br>{smallto}Scale Tickets'
                if tbox[9]: ebody = ebody + f'\n<br>{smallto}Residential Fees'
                if tbox[10]: ebody = ebody + f'\n<br>{smallto}Urban Fees'
                if tbox[11]: ebody = ebody + f'\n<br>{smallto}Congestion Fees'
                if tbox[12]: ebody = ebody + f'\n<br>{smallto}Chassis Split'

                if sboxes[1] == 'include':
                    ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
                else:
                    ebody = ebody + f'{sen}'

                bidtypeamount[0] = 'all-in-2d'
                bidtypeamount[1] = bidthis[4]

            elif len(btype) == 1: #This the one bid only section###################################################################################################

                if 'live' in btype:
                    bid = surcharge_bid(tbox[13], costdata[7], bidthis[0])
                    bidtype = 'Live-Load'
                    bidtypeamount[0] = 'live'
                    bidtypeamount[1] = bidthis[0]
                if 'dr' in btype:
                    bid = surcharge_bid(tbox[13], costdata[7], bidthis[1])
                    bidtype = 'Drop-Pick'
                    bidtypeamount[0] = 'dr'
                    bidtypeamount[1] = bidthis[1]
                if 'dp' in btype:
                    bid = surcharge_bid(tbox[13], costdata[7], bidthis[2])
                    bidtype = 'Drop-Hook'
                    bidtypeamount[0] = 'dp'
                    bidtypeamount[1] = bidthis[2]
                if 'fsc' in btype:
                    bid = surcharge_bid(tbox[13], costdata[7], bidthis[3])
                    bidtype = f'plus {d1s(expdata[14])}% FSC</b>'
                    bidtypeamount[0] = 'fsc'
                    bidtypeamount[1] = bidthis[3]

                ebody = f'Hello {customer}, '

                if tbox[25]: ebody = ebody + f'\n\n<br><br>We have immediate capacity to execute this move.'

                if tbox[0]: ebody = ebody + f'<br><br>Rate: <b>${bid}</b> {bidtype} + chassis <b>${expdata[15]}/day</b>'
                elif tbox[1]: ebody = ebody + f'<br><br>Rate: <b>${bid}</b> {bidtype} + triax chassis <b>${expdata[16]}/day</b>'
                else: ebody = ebody + f'<br><br>Rate: <b>${bid}</b> {bidtype}'

                ebody = ebody + f'\n<br>Lane: {port} to {locto}\n<br>Equipment: {equip}'
                if tbox[16]: ebody = ebody + f'\n<br>Commodity: {com}'

                ebody = ebody + f'\n\n<br><br>The rate includes:\n<br>{smallto}Tolls and Fuel'
                if bidtypeamount[0] == 'live' or bidtypeamount[0] == 'fsc':
                    ebody = ebody + f'\n<br>{smallto}2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter)'
                if not tbox[2]: ebody = ebody + f'\n<br>{smallto}Prepull and Storage for next day delivery'

                if sboxes[1] == 'include':
                    ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
                else:
                    ebody = ebody + f'{sen}'

            # This is the section for one location, but several bid types on same quote
            elif len(btype) > 1:
                ebody = f'Hello {customer}, '

                if tbox[25]: ebody = ebody + f'\n\n<br><br>We have immediate capacity to execute this move.'

                ebody = ebody + f'<br><br>Here are rate options for {port}->{locto}\n<br>Equipment: {equip}'
                if tbox[16]: ebody = ebody + f'\n<br>Commodity: {com}'
                ebody = ebody + '<br><br>'

                if 'live' in btype:
                    ebody =  ebody + f'<b>${bidthis[0]}</b> for a live load which includes 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).<br>'

                if 'dr' in btype:
                    ebody = ebody + f'<b>${bidthis[1]}</b> for a drop-pick (two bobtails included).<br>'

                if 'dp' in btype:
                    ebody = ebody + f'<b>${bidthis[2]}</b> for a drop-hook (no bobtailing).<br>'

                if 'fsc' in btype:
                    ebody = ebody + f'<b>${bidthis[3]} plus {d1s(expdata[14])}% FSC</b> for a live load which includes 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).<br>'

                ebody = ebody + f'<br>The quotes are inclusive of all tolls and fuel costs.  No pre-pull or storage for next day delivery.<br>'

                if tbox[0]:
                    ebody = ebody + f'Add Chassis <b>${expdata[15]}/day</b>'
                elif tbox[1]:
                    ebody = ebody + f'Add Triax Chassis <b>${expdata[16]}/day</b>'

    if len(btype) == 1 and stype == 'ml':
        ebody = ebody.replace('this','each of these').replace('load', 'loads').replace('move','moves')
        ebody = ebody.replace('these quote', 'this quote').replace('All-In', 'All-In, Each').replace('Drop-Pick', 'Drop-Pick, Each')

    if len(btype) == 1 and mixtype == 'mix':
        ebody = ebody.replace('is inclusive','is valid for either 20ft or 40ft containers and is inclusive')

    if len(btype) > 1 and mixtype == 'mix':
        ebody = ebody.replace('is inclusive','is valid for either 20ft or 40ft containers and is inclusive')

    return ebody, tbox, etitle, bidtypeamount

def direct_insert_adds(tbox, expdata, distdata, multibid, mdistdata, kx, costdata):
    sen = ''
    adds = []
    btype = []
    owfeetot = 0
    smallto = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\u2022'

    if tbox[17]: btype.append('live')
    if tbox[18]: btype.append('dr')
    if tbox[19]: btype.append('dp')
    if tbox[22]: btype.append('fsc')
    if tbox[20]: btype.append('all-in-1d')
    if tbox[21]: btype.append('all-in-2d')

    if 'all-in-1d' not in btype and 'all-in-2d' not in btype:

        if multibid[0] == 'on':
            distdata = mdistdata[kx]
            if tbox[0]: adds.append(f'Standard Chassis: <b>${expdata[15]}/day</b>')
            if tbox[1]: adds.append(f'Triax Chassis: <b>${expdata[16]}/day</b>')

        if tbox[2]:
            adds.append(f'Pre-pull Fee: <b>${expdata[17]}</b> (includes one day of yard storage)')
        if tbox[3]:
            adds.append(f'Yard Storage: <b>${expdata[18]}/day</b>')
        if tbox[4]:
            owfee1 = round(int(float(expdata[21])))
            try:
                distloaded = float(distdata[0]) / 2
                owfee2 = round(int(float(expdata[22]) * float(distdata[0]) / 2) / 10) * 10
                owfeetot = owfee1+owfee2
            except:
                distloaded = 0
                owfee1=0
                owfee2=0
                owfeetot=0
            if multibid[0] != 'on': adds.append(f'Overweight Fee:  <b>${d2s(owfeetot)}</b>')
        if tbox[5]:
            permitfee = 90.00
            adds.append(f'Permits Fee:  <b>${d2s(expdata[28])}</b>')
        if tbox[6]:
            adds.append(f'Extra Stop Fee: <b>${expdata[20]}</b>')
        if tbox[7]:
            adds.append(f'Reefer Fee:  <b>${expdata[23]}</b>')
        if tbox[8]:
            adds.append(f'Scale Ticket Set:  <b>${expdata[24]}</b>')
        if tbox[9]:
            adds.append(f'Residential Fee:  <b>${expdata[25]}</b>')
        if tbox[10]:
            adds.append(f'Urban Fee:  <b>${expdata[25]}</b>')
        if tbox[11]:
            adds.append(f'Port Congestion:  <b>${expdata[26]}$/hr over 2 hrs</b>')
        if tbox[12]:
            adds.append(f'Chassis Split:  <b>${expdata[27]}</b>')
        if tbox[13]:
            adds.append(f'Fuel Surcharge:  <b>${costdata[7]}</b>')
    num_items = len(adds)

    #print(f'bype:{btype}, multibid:{multibid}')
    if len(btype) == 1:
        if multibid[0] == 'on':
            if num_items == 1:
                sen = '<br><br>Required addition: '
            elif num_items > 1:
                sen = '<br><br>Required additions: '
        else:
            if num_items == 1: sen = '<br><br>Other charges that apply for this move: '
            if num_items > 1: sen = '<br><br>Other charges that apply for this move: '
    if len(btype) > 1:
        if num_items == 1: sen = '<br><br>'
        elif num_items > 1: sen = '<br><br>Added charges to these quotes will include: '
    for ix, add in enumerate(adds):
        if ix == 0: sen = sen + f'<br>{smallto}' + add
        elif ix == num_items-1: sen = sen + f'<br>{smallto}' + add
        else: sen = sen + f'<br>{smallto}' + add
    if num_items>0: sen = sen + '.  '
    stype = 'reg'
    mixtype = 'none'
    if tbox[23]: stype = 'ml'
    if tbox[24]:
        mixtype = 'mix'
        stype = 'ml'

    #if tbox[25] and tbox[26]:  sen = sen + f'<br><br>We have immediate capacity and capacity into next week to execute the job quoted. '
    #elif tbox[25]: sen = sen + f'<br><br>We have immediate capacity to execute the job quoted. '
    #elif tbox[26]: sen = sen + f'<br><br>We have capacity for next week and beyond to execute the job quoted. '

    return sen, tbox, btype, stype, mixtype, owfeetot

def build_quote_email_direct_api(
        customer,
        cdata,
        bidthis,
        locto,
        tbox,
        expdata,
        distdata,
        multibid,
        etitle,
        port,
        include_text,
        whouse,
        wareBB,
        wareUD,
        mdistdata,
        costdata,
        sboxes,
        include_accessorial_table=False):
    """
    API-safe wrapper around bodymaker_direct().
    """

    ebody, tbox, etitle, bidtypeamount = bodymaker_direct(
        customer,
        cdata,
        bidthis,
        locto,
        tbox,
        expdata,
        distdata,
        multibid,
        etitle,
        port,
        include_text,
        whouse,
        wareBB,
        wareUD,
        mdistdata,
        costdata,
        sboxes
    )

    if wareBB is not None or wareUD is not None:
        ebody = ebody + f'<br><br><em>{signoff}</em>'
    else:
        if include_accessorial_table:
            ebody = ebody + maketable(expdata)
        else:
            ebody = ebody + f'<br><br><em>{signoff}</em>'

    return {
        'body_html': ebody,
        'subject': etitle,
        'reply_preferred': True,
        'bidtypeamount': bidtypeamount,
        'tbox': tbox
    }

def bodymaker_classic(customer, cdata, bidthis, locto, tbox, expdata, takedef, distdata, multibid, etitle, port, include_text, whouse, wareBB, wareUD, mdistdata, costdata, sboxes):
    # Get the costs of the additional boxes checked
    if multibid[0] != 'on':
        sen, tbox, btype, stype, mixtype, ow = classic_insert_adds(tbox,expdata,takedef,distdata,multibid,mdistdata, 0, costdata)
    else:
        btype = []
        if tbox[17]: btype.append('live')
        if tbox[18]: btype.append('dr')
        if tbox[19]: btype.append('dp')
        if tbox[22]: btype.append('fsc')
        if tbox[20]: btype.append('all-in-1d')
        if tbox[21]: btype.append('all-in-2d')

    #print(f'btype is {btype} and wareBB is {wareBB}')
    tabover = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
    smallto = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp'
    ebody = ''

    if wareBB is not None or wareUD is not None:
        #print('Running the warehouse wareBB section')
        sdray = f'Drayage from {port} to {cdata[0]} warehouse: <b>${expdata[29]}</b>'
        spallet1 = f'Pallets off-loaded at warehouse: <b>${expdata[30]} per pallet</b>'
        spallet2 = f'Pallets on-loaded from warehouse: <b>${expdata[30]} per pallet</b>'
        sstopallet = f'Storage in warehouse: <b>${expdata[31]} per pallet per day</b>'
        if wareBB is not None:
            ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote to dray and transload your container load from {port} to our warehouse in {cdata[6]}.<br><br>'
            ebody = ebody + f'\n{tabover}{sdray}<br>'
            ebody = ebody + f'\n{tabover}{spallet1}<br>'
            ebody = ebody + f'\n{tabover}{spallet2}<br>'
            ebody = ebody + f'\n{tabover}{sstopallet}<br>'

            bidtypeamount = [None, None]
            return ebody, tbox, etitle, bidtypeamount

        if wareUD is not None:
            if whouse[3]:
                ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote to dray and transload your container load from {port} to our warehouse in {cdata[6]}.<br><br>'
            else:
                ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote to transload your load at our warehouse in {cdata[6]}.<br><br>'
            if whouse[3]:
                ebody = ebody + f'\n{tabover}{sdray}<br>'
            if whouse[4]:
                ebody = ebody + f'\n{tabover}{spallet1}<br>'
                ebody = ebody + f'\n{tabover}{spallet2}<br>'
            if whouse [5]:
                ebody = ebody + f'\n{tabover}{sstopallet}<br>'
            if whouse [6]:
                ebody = ebody + f'\n{tabover}Unload each floor loaded container or dry van at a cost of <b>${expdata[32]}</b><br>'
            if whouse [7]:
                ebody = ebody + f'\n{tabover}Palletize the product at a cost of <b>${expdata[33]}</b> per pallet<br>'
            if whouse [8]:
                ebody = ebody + f'\n{tabover}Provide pallets for palletization at a cost of <b>${expdata[34]}</b> per pallet<br>'
            bidtypeamount = [None, None]
            return ebody, tbox, etitle, bidtypeamount


    bidtypeamount = [None, None]
    #print(f'the multibid is: {multibid}')
    if multibid[0] == 'on':
        loci = multibid[2]
        bids = multibid[3]
        etitle = f'{cdata[0]} (MC#{cdata[12]}) Quotes to'
        for kx, loc in enumerate(loci):
            if hasinput(loc):
                etitle = etitle + f' {loc};'

        etitle = etitle[:-1]
        if 'all-in-1d' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>All-In</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                sen, tbox, btype, stype, mixtype, ow = classic_insert_adds(tbox, expdata, takedef, distdata, multibid, mdistdata, ix, costdata)
                if ow:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> plus an OW fee of <b>${d2s(ow)}</b> to {loc}<br>'
                else:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'

            if sboxes[1] == 'include':
                ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
            else:
                ebody = ebody + f'{sen}'
            bidtypeamount[0] = 'all-in-1d'
            bidtypeamount[1] = bids[0]

        elif 'live' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>Live-Load</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                sen, tbox, btype, stype, mixtype, ow = classic_insert_adds(tbox, expdata, takedef, distdata, multibid, mdistdata, ix, costdata)
                if ow:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> plus an OW fee of <b>${d2s(ow)}</b> to {loc}<br>'
                else:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'
            ebody = ebody + f'<br>These quotes are inclusive of tolls, fuel, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'
            if sboxes[1] == 'include':
                ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
            else:
                ebody = ebody + f'{sen}'
            bidtypeamount[0] = 'live'
            bidtypeamount[1] = bids[0]

        elif 'dr' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>Drop-Pick</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                sen, tbox, btype, stype, mixtype, ow = classic_insert_adds(tbox, expdata, takedef, distdata, multibid, mdistdata, ix, costdata)
                if ow:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> plus an OW fee of <b>${d2s(ow)}</b> to {loc}<br>'
                else:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'

            ebody = ebody + f'<br>These quotes are inclusive of tolls and fuel.'
            if sboxes[1] == 'include':
                ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
            else:
                ebody = ebody + f'{sen}'
            bidtypeamount[0] = 'dr'
            bidtypeamount[1] = bids[0]

        elif 'dp' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>Drop-Hook</b> quotes:<br><br>'
            for ix, loc in enumerate(loci):
                sen, tbox, btype, stype, mixtype, ow = classic_insert_adds(tbox, expdata, takedef, distdata, multibid, mdistdata, ix, costdata)
                if ow:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> plus an OW fee of <b>${d2s(ow)}</b> to {loc}<br>'
                else:
                    ebody = ebody + f'{tabover}<b>{bids[ix]}</b> to {loc}<br>'

            ebody = ebody + f'<br>These quotes are inclusive of tolls and fuel.  A return container must be available and ready upon delivery or bobtail charges may apply.'
            if sboxes[1] == 'include':
                ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
            else:
                ebody = ebody + f'{sen}'
            bidtypeamount[0] = 'dp'
            bidtypeamount[1] = bids[0]

        elif 'fsc' in btype:
            ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer the following <b>Live-Load</b> quotes:<br><br>'

            for ix, loc in enumerate(loci):
                sen, tbox, btype, stype, mixtype, ow = classic_insert_adds(tbox, expdata, takedef, distdata, multibid, mdistdata, ix, costdata)
                if ow:
                    ebody = ebody + f'{tabover}<b>{bids[ix]} plus {d1s(expdata[14])}% FSC</b> plus an OW fee of <b>${d2s(ow)}</b> to {loc}<br>'
                else:
                    ebody = ebody + f'{tabover}<b>{bids[ix]} plus {d1s(expdata[14])}% FSC</b> to {loc}<br>'

            ebody = ebody + f'<br>These quotes are inclusive of tolls, fuel, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'
            if sboxes[1] == 'include':
                ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
            else:
                ebody = ebody + f'{sen}'
            bidtypeamount[0] = 'fsc'
            bidtypeamount[1] = bids[0]

    else:
        if locto is None or locto == 'No Location Found':
            ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> has no quote due to location not found.'
            bidtypeamount[0] = 'live'
            bidtypeamount[1] = 0.00
        else:
            if 'all-in-1d' in btype:
                include_text = include_text.replace('2-days', '1-day')
                ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote of <b>${bidthis[5]} All-In</b> for this load to {locto} from {port}.' \
                        f'\nThe quote is inclusive of {include_text}, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'
                if sboxes[1] == 'include':
                    ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
                else:
                    ebody = ebody + f'{sen}'
                bidtypeamount[0] = 'all-in-1d'
                bidtypeamount[1] = bidthis[5]

            elif 'all-in-2d' in btype:
                ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote of <b>${bidthis[4]} All-In</b> for this load to {locto} from {port}.' \
                        f'\nThe quote is inclusive of {include_text}, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'
                if sboxes[1] == 'include':
                    ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
                else:
                    ebody = ebody + f'{sen}'
                bidtypeamount[0] = 'all-in-2d'
                bidtypeamount[1] = bidthis[4]

            elif len(btype) == 1:

                if 'live' in btype:
                    bid = surcharge_bid(tbox[13], costdata[7], bidthis[0])
                    ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote of <b>${bid}</b> for this live load to {locto} from {port}.' \
                            f'\nThe quote is inclusive of tolls, fuel, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'
                    bidtypeamount[0] = 'live'
                    bidtypeamount[1] = bidthis[0]

                if 'dr' in btype:
                    bid = surcharge_bid(tbox[13], costdata[7], bidthis[1])
                    ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote of <b>${bid}</b> for this drop-pick load at {locto} from {port}.' \
                            f'\nThe quote is inclusive of tolls and fuel and two bobtails to load site.'
                    bidtypeamount[0] = 'dr'
                    bidtypeamount[1] = bidthis[1]

                if 'dp' in btype:
                    bid = surcharge_bid(tbox[13], costdata[7], bidthis[2])
                    ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote of <b>${bid}</b> for this drop-hook load to {locto} from {port}.' \
                            f'\nThe quote is inclusive of tolls, fuel, and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).  No bobtailing included for drop-hook.'
                    bidtypeamount[0] = 'dp'
                    bidtypeamount[1] = bidthis[2]

                if 'fsc' in btype:
                    ebody = f'Hello {customer}, \n\n<br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer a quote of <b>${bidthis[3]} plus {d1s(expdata[14])}% FSC</b> for this load to {locto} from {port}.' \
                            f'\nThe quote is inclusive of tolls and 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).'
                    bidtypeamount[0] = 'fsc'
                    bidtypeamount[1] = bidthis[3]

                if sboxes[1] == 'include':
                    ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
                else:
                    ebody = ebody + f'{sen}'

            elif len(btype) > 1:
                if mixtype == 'mix':
                    ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer these quotes for loads to {locto} from {port}, which apply to both 20ft and 40ft containers.<br><br>'
                else:
                    ebody = f'Hello {customer}, <br><br>{cdata[0]} <b>(MC#{cdata[12]})</b> is pleased to offer these quotes for loads to {locto} from {port}.<br><br>'

                if 'live' in btype:
                    ebody =  ebody + f'<b>${bidthis[0]}</b> for a live load which includes 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).<br>'

                if 'dr' in btype:
                    ebody = ebody + f'<b>${bidthis[1]}</b> for a drop-pick (two bobtails included).<br>'

                if 'dp' in btype:
                    ebody = ebody + f'<b>${bidthis[2]}</b> for a drop-hook (no bobtailing).<br>'

                if 'fsc' in btype:
                    ebody = ebody + f'<b>${bidthis[3]} plus {d1s(expdata[14])}% FSC</b> for a live load which includes 2 hrs free load time (<b>${expdata[19]}/hr</b> thereafter).<br>'


                ebody = ebody + f'<br>The quotes are inclusive of all tolls and fuel costs.'
                if sboxes[1] == 'include':
                    ebody = ebody + f'{sen}<br><br>The following accessorial table is provided for information purposes only.'
                else:
                    ebody = ebody + f'{sen}'

    if len(btype) == 1 and stype == 'ml':
        ebody = ebody.replace('this','each of these').replace('load', 'loads')
        ebody = ebody.replace('these quote', 'this quote')

    if len(btype) == 1 and mixtype == 'mix':
        ebody = ebody.replace('is inclusive','is valid for either 20ft or 40ft containers and is inclusive')

    if len(btype) > 1 and mixtype == 'mix':
        ebody = ebody.replace('is inclusive','is valid for either 20ft or 40ft containers and is inclusive')

    return ebody, tbox, etitle, bidtypeamount



def classic_insert_adds(tbox, expdata, takedef, distdata, multibid, mdistdata, kx, costdata):
    sen = ''
    adds = []
    btype = []
    owfeetot = 0
    smallto = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\u2022'

    if tbox[17]: btype.append('live')
    if tbox[18]: btype.append('dr')
    if tbox[19]: btype.append('dp')
    if tbox[22]: btype.append('fsc')
    if tbox[20]: btype.append('all-in-1d')
    if tbox[21]: btype.append('all-in-2d')
    if not takedef:
        tbox = tbox_from_request(request, tbox)

    if 'all-in-1d' not in btype and 'all-in-2d' not in btype:

        if multibid[0] == 'on':
            distdata = mdistdata[kx]

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
            try:
                distloaded = float(distdata[0]) / 2
                owfee2 = round(int(float(expdata[22]) * float(distdata[0]) / 2) / 10) * 10
                owfeetot = owfee1+owfee2
            except:
                distloaded = 0
                owfee1=0
                owfee2=0
                owfeetot=0
            if multibid[0] != 'on': adds.append(f'Overweight Fee:  <b>${d2s(owfeetot)}</b>')
        if tbox[5]:
            permitfee = 90.00
            adds.append(f'Permits Fee:  <b>${d2s(expdata[28])}</b>')
        if tbox[6]:
            adds.append(f'Extra Stop Fee: <b>${expdata[20]}</b>')
        if tbox[7]:
            adds.append(f'Reefer Fee:  <b>${expdata[23]}</b>')
        if tbox[8]:
            adds.append(f'Scale Ticket Set:  <b>${expdata[24]}</b>')
        if tbox[9]:
            adds.append(f'Residential Fee:  <b>${expdata[25]}</b>')
        if tbox[10]:
            adds.append(f'Urban Fee:  <b>${expdata[25]}</b>')
        if tbox[11]:
            adds.append(f'Port Congestion:  <b>${expdata[26]}$/hr over 2 hrs</b>')
        if tbox[12]:
            adds.append(f'Chassis Split:  <b>${expdata[27]}</b>')
        if tbox[13]:
            adds.append(f'Fuel Surcharge:  <b>${costdata[7]}</b>')
    num_items = len(adds)
    tabover = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
    if len(btype) == 1:
        if multibid[0] == 'on':
            if num_items == 1:
                sen = '<br><br>Required addition: '
            elif num_items > 1:
                sen = '<br><br>Required additions: '
        else:
            if num_items == 1: sen = '<br><br>Also required for this move: '
            if num_items > 1: sen = '<br><br>Also required for this move: '
    if len(btype) > 1:
        if num_items == 1: sen = '<br><br>'
        elif num_items > 1: sen = '<br><br>Added charges to these quotes will include: '
    for ix, add in enumerate(adds):
        if ix == 0: sen = sen + f'<br>{smallto}' + add
        elif ix == num_items-1: sen = sen + f'<br>{smallto}' + add
        else: sen = sen + f'<br>{smallto}' + add
    if num_items>0: sen = sen + '.  '
    stype = 'reg'
    mixtype = 'none'
    if tbox[23]: stype = 'ml'
    if tbox[24]:
        mixtype = 'mix'
        stype = 'ml'

    #if tbox[25] and tbox[26]:  sen = sen + f'<br><br>We have immediate capacity and capacity into next week to execute the job quoted. '
    #elif tbox[25]: sen = sen + f'<br><br>We have immediate capacity to execute the job quoted. '
    #elif tbox[26]: sen = sen + f'<br><br>We have capacity for next week and beyond to execute the job quoted. '

    return sen, tbox, btype, stype, mixtype, owfeetot


def get_costs(
        miles,
        hours,
        lats,
        lons,
        dirdata,
        tot_dist,
        tot_dura,
        qidat,
        tbox,
        expdata,
        newmarkup=None
):
    """
    Pricing engine that works for both:
      - web form flow
      - API / bot flow

    Inputs:
      tbox       -> already prepared 27-slot checkbox vector
      newmarkup  -> optional markup override from web/API

    Returns unchanged:
      timedata, distdata, costdata, biddata, newdirdata, include_text
    """

    # Work on a local copy so caller state is not mutated
    tbox = copy_tbox(tbox)

    # Get the base input costs
    ph_driver = float(qidat.ph_driver) / 100
    fuel = float(qidat.fuelpergal) / 100
    mpg = float(qidat.mpg) / 100
    pm_fuel = fuel / mpg
    ins = float(qidat.insurance_annual_truck) / 100
    ph_insurance = ins / 1992  # based on 249 work days 8 hrs per day
    md_toll = float(qidat.toll) / 100
    gapct = float(qidat.ga) / 100
    pm_repairs = float(qidat.pm_repairs) / 100
    pm_fees = float(qidat.pm_fees) / 100
    pm_other = float(qidat.pm_other) / 100
    pmc = pm_fuel + pm_repairs + pm_fees + pm_other
    phc = ph_driver + ph_insurance
    fsc = float(qidat.FSC) / 100

    idlefuel = float(qidat.idlefuel) / 100
    fuel2 = float(qidat.fuel2) / 100   # used to calculate fuel surcharge
    porttime = float(qidat.avgporttime) / 100
    portmiles = float(qidat.avgportdist) / 100
    deviation = qidat.deviation
    pm_fuel2 = fuel2 / mpg

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

    markupx, newmarkup = normalize_markup(newmarkup, qidat)

    # Calculate road tolls
    tollroadlist = ['I-76', 'NJ Tpke', 'MD-200']
    tollroadcpm = [.784, .275, .35]
    legtolls = len(dirdata) * [0.0]
    legcodes = len(dirdata) * ['None']

    for lx, mi in enumerate(miles):
        for nx, tollrd in enumerate(tollroadlist):
            if tollrd in dirdata[lx]:
                legtolls[lx] = tollroadcpm[nx] * mi
                legcodes[lx] = tollrd

    # Calculate plaza tolls
    fm_tollbox = [39.267757, -76.610192, 39.261248, -76.563158]
    bht_tollbox = [39.269962, -76.566240, 39.239063, -76.58]
    fsk_tollbox = [39.232770, -76.502453, 39.202279, -76.569906]
    bay_tollbox = [39.026893, -76.417512, 38.964938, -76.290104]
    sus_tollbox = [39.478100, -76.112203, 39.608403, -76.062308]
    new_tollbox = [39.634568, -75.773041, 39.657970, -75.754566]
    dmb_tollbox = [39.644216, -75.570003, 39.721472, -75.465073]
    dtr_tollbox = [38.932101, -77.243797, 38.942280, -77.230473]

    tollcodes = ['FM', 'BHT', 'FSK', 'BAY', 'SUS', 'NEW', 'DMB', 'DTR']
    tollboxes = [fm_tollbox, bht_tollbox, fsk_tollbox, bay_tollbox, sus_tollbox, new_tollbox, dmb_tollbox, dtr_tollbox]
    onceonly = []

    for jx, lat in enumerate(lats):
        la = float(lat)
        lo = float(lons[jx])

        if jx > 0:
            la_last = float(lats[jx - 1])
            lo_last = float(lons[jx - 1])

            for kx, tollbox in enumerate(tollboxes):
                lah = max([tollbox[0], tollbox[2]])
                lal = min([tollbox[0], tollbox[2]])
                loh = max([tollbox[1], tollbox[3]])
                lol = min([tollbox[1], tollbox[3]])

                tollpass = checkcross2(la_last, la, lo_last, lo, lol, lal, loh, lah)

                if tollpass:
                    tollcode = tollcodes[kx]
                    if tollcode not in onceonly:
                        onceonly.append(tollcode)
                        if tollcode == 'DTR':
                            legtolls[jx] = 10.50
                        else:
                            legtolls[jx] = md_toll
                        legcodes[jx] = tollcode

    # Time and distance
    tot_tolls = 0.00
    loadtime = 2.0
    triptime = tot_dura * 2.0
    handling = .5 + triptime * .01
    dphandling = .75 + triptime * .05
    tottime = porttime + loadtime + triptime + handling
    dptime = porttime + triptime + dphandling
    idletime = porttime + .5 * loadtime + handling
    timedata = [d1s(triptime), d1s(porttime), d1s(loadtime), d1s(handling), d1s(tottime)]

    tripmiles = tot_dist * 2.0
    devtext = qidat.deviation
    parts = devtext.split('+')
    dev0 = float(parts[0])
    dev1 = float(parts[1])
    glidemiles = dev0 + dev1 * tripmiles
    totmiles = tripmiles + portmiles + glidemiles
    distdata = [d1s(tripmiles), d1s(portmiles), '0.0', d1s(glidemiles), d1s(totmiles)]

    newdirdata = []
    for lx, aline in enumerate(dirdata):
        tot_tolls += legtolls[lx]
        aline = aline.replace('<div style="font-size:0.9em">Toll road</div>', '')
        aline = aline.strip()

        if legtolls[lx] < .000001:
            newdirdata.append(f'{d1s(miles[lx])} MI {d2s(hours[lx])} HRS {aline}')
        else:
            newdirdata.append(
                f'{d1s(miles[lx])} MI {d2s(hours[lx])} HRS {aline} '
                f'Tolls:${d2s(legtolls[lx])}, TollCode:{legcodes[lx]}'
            )

    # Cost analysis
    cost_drv = tottime * ph_driver
    cost_fuel = totmiles * pm_fuel + idletime * idlefuel * fuel
    cost_fuel2 = totmiles * pm_fuel2 + idletime * idlefuel * fuel2
    fuel_surcharge = roundup(cost_fuel - cost_fuel2)
    cost_tolls = 2.0 * tot_tolls

    cost_insur = tottime * ph_insurance
    cost_rm = totmiles * pm_repairs
    cost_misc = totmiles * (pm_fees + pm_other)

    cost_direct = cost_drv + cost_fuel + cost_tolls + cost_insur + cost_rm + cost_misc
    cost_ga = cost_direct * gapct / 100.0
    cost_total = cost_direct + cost_ga

    costdata = [
        d2s(cost_drv),
        d2s(cost_fuel),
        d2s(cost_tolls),
        d2s(cost_insur),
        d2s(cost_rm),
        d2s(cost_misc),
        d2s(cost_ga),
        d2s(fuel_surcharge),
        d2s(cost_direct),
        d2s(cost_total)
    ]

    # Base bids
    bid = cost_total * markupx
    dpcost = (
        dptime * (ph_driver + ph_insurance)
        + totmiles * (pm_fuel + pm_repairs + pm_fees + pm_other)
        + cost_tolls
    ) * (1 + gapct / 100)

    dpbid = dpcost * markupx

    bobtailcost = (
        ((dptime - .25) * (ph_driver + ph_insurance))
        + ((totmiles - 8) * (pm_fuel + pm_repairs + pm_fees + pm_other))
    ) * (1 + gapct / 100)

    drbid = dpbid + bobtailcost * markupx
    fuelbid = bid / (1 + fsc / 100)

    # All-in/accessorial additions
    allbid1 = bid
    allbid2 = bid
    include_text = 'tolls, fuel'

    if tbox[0]:
        allbid1 += 2 * chassis2
        allbid2 += chassis2
        include_text = f'{include_text}, 2-days chassis'

    if tbox[1]:
        allbid1 += 2 * chassis3
        allbid2 += chassis3
        include_text = f'{include_text}, 2-days triax chassis'

    if tbox[2]:
        allbid1 += prepull
        allbid2 += prepull
        include_text = f'{include_text}, prepull'

    if tbox[3]:
        allbid1 += store
        allbid2 += store
        include_text = f'{include_text}, 1-day storage'

    if tbox[4]:
        owfee1 = round(int(float(expdata[21])))
        owfee2 = round(int(float(expdata[22]) * float(distdata[0]) / 2) / 10) * 10
        owfeetot = owfee1 + owfee2
        allbid1 += owfeetot
        allbid2 += owfeetot
        include_text = f'{include_text}, overweight fees'

    if tbox[5]:
        allbid1 += float(expdata[28])
        allbid2 += float(expdata[28])
        include_text = f'{include_text}, permits'

    if tbox[6]:
        allbid1 += float(expdata[20])
        allbid2 += float(expdata[20])
        include_text = f'{include_text}, extra stops'

    if tbox[7]:
        allbid1 += float(expdata[23])
        allbid2 += float(expdata[23])
        include_text = f'{include_text}, reefer fees'

    if tbox[8]:
        allbid1 += float(expdata[24])
        allbid2 += float(expdata[24])
        include_text = f'{include_text}, scale tickets'

    if tbox[9]:
        allbid1 += float(expdata[25])
        allbid2 += float(expdata[25])
        include_text = f'{include_text}, residential fees'

    if tbox[11]:
        allbid1 += float(expdata[26])
        allbid2 += float(expdata[26])
        include_text = f'{include_text}, urban fees'

    biddata = [
        d2s(roundup(bid)),      # live
        d2s(roundup(drbid)),    # drop-pick
        d2s(roundup(dpbid)),    # drop-hook
        d2s(roundup(fuelbid)),  # FSC style
        d2s(roundup(allbid1)),  # all-in 2-day chassis
        d2s(roundup(allbid2)),  # all-in 1-day chassis
    ]

    return timedata, distdata, costdata, biddata, newdirdata, include_text

#######################################Additional API/Service Handlers:
def get_quoteinput_for_api():
    qidat = Quoteinput.query.order_by(Quoteinput.id.desc()).first()
    if qidat is None:
        raise ValueError("No Quoteinput pricing row found")
    return qidat

def build_expdata_from_qidat(qidat):
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
    congest = float(qidat.congestion) / 100
    chassplit = float(qidat.chassplit) / 100
    owmile = float(qidat.owmile) / 100
    try:
        permits = float(qidat.permits) / 100
    except:
        permits = 0.00

    # Wahrehouse costs
    xdray = float(qidat.xdray) / 100
    xpalletxfer = float(qidat.xpalletxfer) / 100
    xstopallet = float(qidat.xstopallet) / 100
    xfloorunload = float(qidat.xfloorunload) / 100
    xpalletization = float(qidat.xpalletization) / 100
    xpalletcost = float(qidat.xpalletcost) / 100

    # Newly added cost parameters:
    idlefuel = float(qidat.idlefuel) / 100
    fuel2 = float(qidat.fuel2) / 100
    avgporttime = float(qidat.avgporttime) / 100
    avgportdist = float(qidat.avgportdist) / 100
    # Split the curve fit data for deviation miles:

    expdata = [d2s(ph_driver), d2s(fuel), d2s(mpg), d2s(ins), d2s(markup), d2s(toll), d2s(gapct),
               d2s(pm_repairs), d2s(pm_fees), d2s(pm_other), d2s(pm_fuel), d2s(ph_insurance), d2s(pmc), d2s(phc),
               d1s(fsc), d2s(chassis2), d2s(chassis3), d2s(prepull), d2s(store), d2s(detention), d2s(extrastop),
               d2s(overweight), d2s(owmile), d2s(reefer), d2s(scale), d2s(resid), d2s(congest), d2s(chassplit),
               d2s(permits),
               d2s(xdray), d2s(xpalletxfer), d2s(xstopallet), d2s(xfloorunload), d2s(xpalletization), d2s(xpalletcost),
               d2s(idlefuel), d2s(fuel2), d2s(avgporttime), d2s(avgportdist), qidat.deviation]

    return expdata

def select_bid_from_tbox(tbox, biddata):
    """
    Returns the selected bid based on tbox flags.

    biddata index meaning:
        0 = live
        1 = drop-pick (dr)
        2 = drop-hook (dp)
        3 = fsc
        4 = all-in-2d
        5 = all-in-1d
    """

    # Priority order (matches your UI behavior)
    if tbox[20]:   # all-in-1d
        return 'all_in_1d', biddata[5]

    if tbox[21]:   # all-in-2d
        return 'all_in_2d', biddata[4]

    if tbox[17]:   # live
        return 'live', biddata[0]

    if tbox[18]:   # drop-pick
        return 'dr', biddata[1]

    if tbox[19]:   # drop-hook
        return 'dp', biddata[2]

    if tbox[22]:   # fsc
        return 'fsc', biddata[3]

    # fallback (should not happen, but safe default)
    return 'live', biddata[0]

def calculate_quote_api(
        locto,
        term=None,
        start_address=None,
        tbox=None,
        newmarkup=None,
        qidat=None,
        expdata=None):

    # 1. Ensure required inputs
    if locto is None:
        raise ValueError("locto (delivery location) is required")

    # 2. Get pricing profile if not provided
    if qidat is None:
        qidat = get_quoteinput_for_api()

    if expdata is None:
        expdata = build_expdata_from_qidat(qidat)

    # 3. Ensure tbox exists
    if tbox is None:
        tbox = default_tbox()

    # 4. Resolve terminal / start location
    term, locfrom, locto, port = get_terminal(
        locto=locto,
        term=term
    )

    # Override start address if explicitly passed
    if start_address:
        locfrom = start_address

    # 5. Get directions
    miles, hours, lats, lons, dirdata, tot_dist, tot_dura = get_directions(locfrom, locto)

    # 6. Run pricing
    timedata, distdata, costdata, biddata, newdirdata, include_text = get_costs(
        miles,
        hours,
        lats,
        lons,
        dirdata,
        tot_dist,
        tot_dura,
        qidat,
        tbox,
        expdata,
        newmarkup=newmarkup
    )

    bid_type, selected_bid = select_bid_from_tbox(tbox, biddata)

    # 7. Return structured result
    return {
        "term": term,
        "locfrom": locfrom,
        "locto": locto,
        "port": port,
        "timedata": timedata,
        "distdata": distdata,
        "costdata": costdata,
        "biddata": biddata,
        "selected_bid_type": bid_type,
        "selected_bid": selected_bid,
        "include_text": include_text,
    }

def calculate_and_build_quote_api(
        locto,
        customer,
        cdata,
        term=None,
        start_address=None,
        tbox=None,
        newmarkup=None,
        qidat=None,
        expdata=None,
        email_style='direct',
        include_accessorial_table=False,
        sboxes=None,
        multibid=None,
        whouse=None,
        wareBB=None,
        wareUD=None,
        etitle=None):
    """
    Top-level API helper:
      1) calculate pricing
      2) build the direct-format email

    Returns one combined dict with:
      - quote data
      - email subject/body
    """

    if email_style != 'direct':
        raise ValueError("Only direct email style is supported in calculate_and_build_quote_api().")

    # Defaults that bodymaker_direct expects
    if tbox is None:
        tbox = default_tbox()

    if qidat is None:
        qidat = get_quoteinput_for_api()

    if expdata is None:
        expdata = build_expdata_from_qidat(qidat)

    # sboxes[0] = style, sboxes[1] = include table or not
    # Keep only the values bodymaker_direct actually relies on.
    if sboxes is None:
        sboxes = ['direct', 'exclude', '', '']
    else:
        sboxes = list(sboxes)
        while len(sboxes) < 4:
            sboxes.append('')
        sboxes[0] = 'direct'
        sboxes[1] = 'include' if include_accessorial_table else 'exclude'

    if multibid is None:
        multibid = ['off', 1, [], []]

    if whouse is None:
        whouse = [0] * 9

    # ------------------------------------------------------------
    # Step 1: run pricing wrapper
    # ------------------------------------------------------------
    quote_result = calculate_quote_api(
        locto=locto,
        term=term,
        start_address=start_address,
        tbox=tbox,
        newmarkup=newmarkup,
        qidat=qidat,
        expdata=expdata
    )

    # ------------------------------------------------------------
    # Step 2: build bidthis the same way the web route does
    # ------------------------------------------------------------
    biddata = quote_result['biddata']
    #tbox_used = quote_result['tbox']
    tbox_used = copy_tbox(tbox)

    bidthis = ['0.00'] * 6
    if tbox_used[17]:
        bidthis[0] = biddata[0]   # live
    if tbox_used[18]:
        bidthis[1] = biddata[1]   # dr
    if tbox_used[19]:
        bidthis[2] = biddata[2]   # dp
    if tbox_used[22]:
        bidthis[3] = biddata[3]   # fsc
    if tbox_used[21]:
        bidthis[4] = biddata[4]   # all-in-2d
    if tbox_used[20]:
        bidthis[5] = biddata[5]   # all-in-1d

    # If nothing was selected, fall back to live
    if bidthis == ['0.00'] * 6:
        bidthis[0] = biddata[0]

    # ------------------------------------------------------------
    # Step 3: subject default
    # ------------------------------------------------------------
    port = quote_result['port']
    locto_resolved = quote_result['locto']

    if etitle is None:
        if wareBB or wareUD:
            etitle = f'{cdata[0]} (MC#{cdata[12]}) Quote for Warehouse Services from {port}'
        else:
            etitle = f'{cdata[0]} (MC#{cdata[12]}) Quote to {locto_resolved} from {port}'

    # ------------------------------------------------------------
    # Step 4: mdistdata for multibid mode
    # For normal API use this will usually be empty.
    # ------------------------------------------------------------
    mdistdata = []
    if multibid[0] == 'on':
        # If caller did not prebuild mdistdata, use current distdata for each location slot
        requested = multibid[1] if len(multibid) > 1 and multibid[1] else 1
        mdistdata = [quote_result['distdata']] * requested

        # If caller did not prebuild multibid bids, map selected quote type over locations
        if len(multibid) < 4:
            while len(multibid) < 4:
                multibid.append([])

        if not multibid[3]:
            bid_type, selected_bid = select_bid_from_tbox(tbox_used, biddata)
            loci = multibid[2] if len(multibid) > 2 else []
            multibid[3] = [selected_bid for _ in loci]
    else:
        mdistdata = []

    # ------------------------------------------------------------
    # Step 5: build direct email
    # ------------------------------------------------------------
    email_result = build_quote_email_direct_api(
        customer=customer,
        cdata=cdata,
        bidthis=bidthis,
        locto=locto_resolved,
        tbox=tbox_used,
        expdata=expdata,
        distdata=quote_result['distdata'],
        multibid=multibid,
        etitle=etitle,
        port=port,
        include_text=quote_result['include_text'],
        whouse=whouse,
        wareBB=wareBB,
        wareUD=wareUD,
        mdistdata=mdistdata,
        costdata=quote_result['costdata'],
        sboxes=sboxes,
        include_accessorial_table=include_accessorial_table
    )

    # ------------------------------------------------------------
    # Step 6: combined return
    # ------------------------------------------------------------
    with open("debug_email.html", "w") as f:
        f.write(f"<html><body>{email_result.get('body_html')}</body></html>")

    return {
        'quote': {
            'selected_bid_type': quote_result.get('selected_bid_type'),
            'selected_bid': quote_result.get('selected_bid'),
            'biddata': quote_result.get('biddata'),
            'costdata': quote_result.get('costdata'),
            'distdata': quote_result.get('distdata'),
            'timedata': quote_result.get('timedata'),
            'include_text': quote_result.get('include_text'),
            'port': quote_result.get('port'),
            'locfrom': quote_result.get('locfrom'),
            'locto': quote_result.get('locto'),
            'newdirdata': quote_result.get('newdirdata'),
        },
        'reply': {
            'body_html': email_result.get('body_html'),
            'subject': email_result.get('subject'),
            'reply_preferred': True,
        },
        'meta': {
            'bidthis': bidthis,
            'selected_bid_type': quote_result.get('selected_bid_type'),
            'generated_at': datetime.datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0).isoformat()
        }
    }


def get_body_text(qdat):
    """
    Reload original email by Message-ID.
    Returns:
        plaintext_for_page_preview
        htmltext_for_iframe_preview
    """
    if qdat is None or not qdat.Mid:
        return '', ''

    username = usernames['quot']
    password = passwords['quot']
    mid = qdat.Mid.strip()

    imap = imaplib.IMAP4_SSL(imap_url)
    imap.login(username, password)

    plaintext = ''
    htmltext = ''

    try:
        imap.select('INBOX')
        result, data = imap.search(None, f'HEADER Message-ID "{mid}"')
        if result != 'OK' or not data or not data[0]:
            return '', ''

        msg_ids = data[0].split()
        if not msg_ids:
            return '', ''

        result, fetched = imap.fetch(msg_ids[0], '(RFC822)')
        if result != 'OK':
            return '', ''

        email_message = email.message_from_bytes(fetched[0][1])

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in disposition.lower():
                    continue

                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    decoded = payload.decode(charset, errors='replace') if payload else ''
                except Exception:
                    decoded = ''

                if content_type == "text/plain" and not plaintext:
                    plaintext = decoded

                if content_type == "text/html" and not htmltext:
                    htmltext = decoded
        else:
            content_type = email_message.get_content_type()
            payload = email_message.get_payload(decode=True)
            charset = email_message.get_content_charset() or 'utf-8'
            decoded = payload.decode(charset, errors='replace') if payload else ''

            if content_type == 'text/html':
                htmltext = decoded
            else:
                plaintext = decoded

        # Safe page preview should be text, not raw HTML
        if not plaintext and htmltext:
            plaintext = html_to_text_for_preview(htmltext)

        return plaintext.strip(), htmltext.strip()

    finally:
        try:
            imap.close()
        except Exception:
            pass
        imap.logout()

def go_to_next(mid, taskbox):
    #Loads in the next email off of a remove and go....
    with step_timer("getting the data from the table with status 0"):
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
            # print(f'comparing {datethis} to {datelast}')
            if datethis == datelast:
                # print(f'Getting body_text because it is a successful remove and go')
                # Change from lower section### gets the email data since below where we get email data
                taskbox = 5
                with step_timer("get_body_text for next email"):
                    plaintext, htmltext = get_cached_body_text(qdat)
                mid = qdat.Mid
                emailto = qdat.From
                #if emailto is None:
                    #emailto = qdat.From
                    #qdat.From = emailto
                    #db.session.commit()
                multibid = ['off', 1, 0, 0]
                with step_timer("get_places for next email"):
                    locto, loci = get_place(qdat.Subject, plaintext, multibid)
                qdat.Location = locto
                db.session.commit()
                qdat = Quotes.query.get(quot)
                #####################################

            else:
                multibid = ['off', 1, 0, 0]
                plaintext, htmltext = None, None
                taskbox = 0
                quot = 0
                emailto = None
                locto = None
                loci = None
        else:
            multibid = ['off', 1, 0, 0]
            taskbox = 0
            quot = 0
            return None, quot, None, None, None, None, None, None, None, taskbox, None, None, None, None

        return qdat, quot, quotbut, datethis, datelast, plaintext, htmltext, mid, taskbox, multibid, emailto, locto, loci

    else:
        taskbox = 0
        quot = 0
        return None, quot, None, None, None, None, None, None, None, taskbox, None, None, None, None

def get_terminal(locto=None, term=None, req=None):
    """
    Works for both web and API use.

    Web usage:
        get_terminal(locto, req=request)

    API usage:
        get_terminal(locto='Glen Burnie, MD 21060', term='Seagirt Marine Terminal')
    """
    if req is not None:
        if term is None:
            term = req.values.get('terminal')

        if locto is None:
            locto_update = req.values.get('locto')
            if locto_update is not None and locto_update != 'None':
                locto = locto_update

    if term is None:
        locfrom = '2600 Broening Hwy, Baltimore, MD 21224'
        thisterm = 'BAL'
        port = 'Baltimore Seagirt'
    else:
        tdat = Terminals.query.filter(Terminals.Name == term).first()
        if tdat is not None:
            thisterm = tdat.Name
            locfrom = tdat.Address
            locfrom = locfrom.replace(thisterm, '')
            locfrom = locfrom.strip()
            port = tdat.Name
        else:
            locfrom = '2600 Broening Hwy, Baltimore, MD 21224'
            thisterm = 'BAL'
            port = 'Baltimore Seagirt'

    return thisterm, locfrom, locto, port

def old_get_terminal(locto):
    term = request.values.get('terminal')
    if locto is None:
        locto_update = request.values.get('locto')
        #print(f'locto update is {locto_update}')
        if locto_update is not None and locto_update != 'None': locto = locto_update

    if term is None:
        locfrom = '2600 Broening Hwy, Baltimore, MD 21224'
        thisterm = 'BAL'
        port = 'Baltimore Seagirt'
    else:
        tdat = Terminals.query.filter(Terminals.Name == term).first()
        if tdat is not None:
            thisterm = tdat.Name
            locfrom = tdat.Address
            locfrom = locfrom.replace(thisterm, '')
            locfrom = locfrom.strip()
            port = tdat.Name
        else:
            locfrom = '2600 Broening Hwy, Baltimore, MD 21224'
            thisterm = 'BAL'
            port = 'Baltimore Seagirt'
    #print(thisterm, locfrom, port)
    return thisterm, locfrom, locto, port

def get_whouse_values(iter, whouse):
    showcosts = request.values.get('showcosts')
    showfees = request.values.get('showfees')
    showhouse = request.values.get('showhouse')
    wdray = request.values.get('wdray')
    palletxfer = request.values.get('palletxfer')
    stopallet = request.values.get('stopallet')
    floorunload = request.values.get('floorunload')
    palletization = request.values.get('palletization')
    palletcost = request.values.get('palletcost')
    setquotehouse = request.values.get('setquotehouse')
    whouse = [showcosts, showfees, showhouse, wdray, palletxfer, stopallet, floorunload, palletization, palletcost, setquotehouse, 0, 0, 0, 0, 0]
    return whouse

def get_new_fees():

    qidat = Quoteinput.query.order_by(Quoteinput.id.desc()).first()
    alist = []
    blist = [int(float(a) * 100) for a in alist]

    anames = ['driver', 'fuel', 'mpg', 'insurance', 'markup', 'toll', 'gapct', 'rm', 'fees', 'other', 'fsc', 'chassis2', 'chassis3',
              'prepull', 'store', 'detention', 'extrastop', 'overweight', 'reefer', 'scale', 'residential', 'congestion', 'chassplit',
              'owmiles', 'permits', 'xdray', 'xpalletxfer', 'xstopallet', 'xfloorunload', 'xpalletization', 'xpalletcost', 'idlefuel','fuel2', 'avgporttime', 'avgportdist', 'deviation']

    dnames = ['ph_driver', 'fuelpergal', 'mpg', 'insurance_annual_truck', 'markup', 'toll', 'ga', 'pm_repairs', 'pm_fees', 'pm_other',
                'FSC', 'chassis2', 'chassis3', 'prepull', 'store', 'detention', 'extrastop', 'overweight', 'reefer', 'scale', 'residential', 'congestion', 'chassplit', 'owmile', 'permits',
                'xdray', 'xpalletxfer', 'xstopallet', 'xfloorunload', 'xpalletization', 'xpalletcost', 'idlefuel','fuel2', 'avgporttime', 'avgportdist', 'deviation']

    for ix, a in enumerate(anames):
        aval = request.values.get(a)
        try:
            aval = float(aval)
        except:
            print(f'This one not float:{aval}')
        if aval is None:
            d = dnames[ix]
            astr = f'qidat.{d}'
            aval = eval(astr)
            if isinstance(aval, (int, float)):
                aval = float(aval / 100)
            else:
                # handle text case here
                aval = str(aval)
        alist.append(aval)

    #for anow in alist: print(anow)

    return alist


def isoQuote():
    username = session['username'].capitalize()
    #define User variables
    # Qote being worked
    uquot = f'{username}_quot'
    uiter = f'{username}_iter'

    quot=0
    tbox = [0]*27
    bidthis = [0]*6
    expdata=[]
    costdata=[]
    multibid=['off', 1, 0, 0]
    locs = []
    sboxes = ['direct', 'exclude', 'com1', 'General Freight']
    ebodytxt=''
    qdat = None
    htmltext = None
    plaintext = None
    mid = ''
    locto = None
    include_text = ''
    whouse = [0]*15
    mdistdata = []
    send_mode = 'reply'
    reply_style = 'quoted'
    save_sent = 'on'

    def to_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0

    equip = [
        to_int(request.values.get('num40')),
        to_int(request.values.get('num20')),
        to_int(request.values.get('num45')),
        to_int(request.values.get('num40s')),
    ]

    if request.method == 'POST':
        try:
            iter = int(os.environ[uiter])
        except:
            iter = 1
        #plaintext = ''
        #htmltext = ''
        print(f'This is a POST with iter {iter} plaintext is {plaintext}')
        emailgo = request.values.get('Email')
        updatego = request.values.get('GetQuote')
        updatebid = request.values.get('Update')
        updateE = request.values.get('UpdateE')
        returnhit = request.values.get('Return')
        removego = request.values.get('RemoveGo')
        bidname = request.values.get('bidname')
        ware = request.values.get('Ware')
        exitnow = request.values.get('exitquotes')

        wareBB = request.values.get('WareBB')
        wareUD = request.values.get('WareUD')
        whouse = get_whouse_values(iter, whouse)

        send_mode = request.values.get('send_mode', 'reply')
        reply_style = request.values.get('reply_style', 'quoted')
        save_sent = 'on' if request.values.get('save_sent', 'on') == 'on' else 'off'


        if exitnow is not None:
            #print('Exiting quotes')
            return 'exitnow', costdata, None, expdata, None, None, None, locto, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None


        for jx in range(6):
            bidthis[jx] = request.values.get(f'bidthis{jx}')
            bidthis[jx] = d2s(bidthis[jx])

        newmarkup = request.values.get('optmarkup')
        tbox = tbox_from_request(request, tbox)

        # locto = request.values.get('locto')
        term, locfrom, locto, port = get_terminal(locto=locto, req=request)

        #locto = request.values.get('locto')
        #term, locfrom, locto, port = get_terminal(locto)
        thismuch = request.values.get('thismuch')
        taskbox = request.values.get('taskbox')
        taskbox = nonone(taskbox)
        qbid = request.values.get('quickbid')
        qdel = request.values.get('quickdel')
        getnumq = request.values.get('numcit')
        #print(f'Here, locfrom is: {locfrom}')
        if getnumq is not None:
            if 1 == 1:
                try: multibid[1] = int(getnumq)
                except: multibid[1] = 1
                if multibid[1] > 1:
                    multibid[0] = 'on'
                    for ix in range(multibid[1]):
                        locs.append(request.values.get(f'locto{ix}'))
                    multibid[2] = locs
                else:
                    multibid[0] = 'off'
                    locs.append(request.values.get(f'locto'))
            elif 1 == 2:
                multibid[0] = 'off'
                multibid[1] = 1
        else:
            multibid[0] = 'off'
            multibid[1] = 1
        #print(f'mutlibid is {multibid[0]} and {multibid[1]} locs are {locs}')


        if qbid is not None: taskbox = 1
        if qdel is not None: taskbox = 2
        refresh = request.values.get('refresh')
        if refresh is not None: taskbox = 6
        quotbut = request.values.get('optradio')
        updatecosts = request.values.get('newcosts')
        def_costs = request.values.get('oldcosts')
        updatefees = request.values.get('newfees')
        updatehousefees = request.values.get('updatehousefees')


        if updatecosts is not None or updatefees is not None or updatehousefees is not None:

            alist = get_new_fees()
            print(alist)
            #blist = [int(float(a)*100) for a in alist]
            blist = [int(float(a) * 100) for a in alist if isinstance(a, (int, float))]
            blist.append(alist[35])
            pmf=int(100*float(alist[1])/float(alist[2]))
            phi=int(100*float(alist[3])/1992)
            #print(f'pmf={pmf} and phi={phi}')
            pmt = pmf+blist[7]+blist[8]+blist[9]
            pht = blist[0] + phi
            input = Quoteinput(ph_driver=blist[0],fuelpergal=blist[1],mpg=blist[2],insurance_annual_truck=blist[3],markup=blist[4],toll=blist[5],ga=blist[6],pm_repairs=blist[7],pm_fees=blist[8],
                               pm_other=blist[9],pm_fuel=pmf,ph_insurance=phi,pm_total=pmt,ph_total=pht,FSC=blist[10],
                               chassis2=blist[11], chassis3=blist[12], prepull=blist[13], store=blist[14], detention=blist[15], extrastop=blist[16], overweight=blist[17],
                               reefer=blist[18], scale=blist[19], residential=blist[20], congestion=blist[21], chassplit=blist[22], owmile=blist[23], permits=blist[24],
                               xdray=blist[25], xpalletxfer=blist[26], xstopallet=blist[27], xfloorunload=blist[28], xpalletization=blist[29], xpalletcost=blist[30],
                               idlefuel=blist[31], fuel2=blist[32], avgporttime=blist[33], avgportdist=blist[34], deviation=blist[35])
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
                               reefer=qfdat.reefer, scale=qfdat.scale, residential=qfdat.residential, congestion=qfdat.congestion, chassplit=qfdat.chassplit, owmile=qfdat.owmile, permits=qfdat.permits)
            db.session.add(input)
            db.session.commit()
            #This makes first and last records the same so from now on will get original values until a change is made
        else:
            with step_timer("getting qidat, the next table email"):
                qidat = Quoteinput.query.order_by(Quoteinput.id.desc()).first()

        print(f'this data for qidat: {qidat.id}')
        ph_driver = float(qidat.ph_driver) / 100
        fuel = float(qidat.fuelpergal) / 100
        mpg = float(qidat.mpg) / 100
        pm_fuel = fuel / mpg
        ins = float(qidat.insurance_annual_truck) / 100
        ph_insurance = ins / 1992  # based on 249 work days 8 hrs per day
        markup = float(qidat.markup) / 100

        newmarkup = request.values.get('optmarkup')
        if newmarkup is not None:
            try:
                markupx = float(newmarkup)
            except:
                #print(f'Could not float convert {newmarkup}')
                markupx = float(qidat.markup) / 100
        else:
            markupx = float(qidat.markup)/100
            newmarkup = str(markupx)
        #print(f'The markup and newmarkup are {markup} and {newmarkup}')
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
        try: permits = float(qidat.permits) / 100
        except: permits = 0.00

        #Wahrehouse costs
        xdray = float(qidat.xdray) / 100
        xpalletxfer = float(qidat.xpalletxfer) / 100
        xstopallet = float(qidat.xstopallet) / 100
        xfloorunload = float(qidat.xfloorunload) / 100
        xpalletization = float(qidat.xpalletization) / 100
        xpalletcost = float(qidat.xpalletcost) / 100

        #Newly added cost parameters:
        idlefuel = float(qidat.idlefuel) / 100
        fuel2 = float(qidat.fuel2) / 100
        avgporttime = float(qidat.avgporttime) / 100
        avgportdist = float(qidat.avgportdist) / 100
        #Split the curve fit data for deviation miles:

        #print(f'ph_driver is {ph_driver} and d2s gives {d2s(ph_driver)}')
        expdata = [d2s(ph_driver), d2s(fuel), d2s(mpg), d2s(ins), d2s(markup), d2s(toll), d2s(gapct),
                   d2s(pm_repairs), d2s(pm_fees), d2s(pm_other), d2s(pm_fuel), d2s(ph_insurance), d2s(pmc), d2s(phc),
                   d1s(fsc), d2s(chassis2), d2s(chassis3), d2s(prepull), d2s(store), d2s(detention), d2s(extrastop),
                   d2s(overweight), d2s(owmile), d2s(reefer), d2s(scale), d2s(resid), d2s(congest), d2s(chassplit), d2s(permits),
                   d2s(xdray), d2s(xpalletxfer), d2s(xstopallet), d2s(xfloorunload), d2s(xpalletization), d2s(xpalletcost),
                   d2s(idlefuel), d2s(fuel2), d2s(avgporttime), d2s(avgportdist), qidat.deviation]
                    #35              36                 37              38              39

        if quotbut is not None:
            quot=nonone(quotbut)
        if quot == 0:
            quot = request.values.get('quotpass')
            quot = nonone(quot)

        qdat = Quotes.query.get(quot)
        print(f'Got qdat for quot:{quot} quotbut:{quotbut} username:{username} taskbox:{taskbox}')
        if qdat is not None:
            with step_timer("get_body_text for qdat 2890"):
                plaintext, htmltext = get_cached_body_text(qdat)
                print(f'Plaintext for qdat {qdat.id}: {plaintext}')

        if returnhit is not None:
            taskbox = 0
            quot = 0
            print('clearing body text cache')
            clear_cached_body_text()


        #If choose exit or assign as a warehouse job (status 7)...
        if removego is not None or ware is not None:
            if removego is not None:  qdat.Status = -1
            else: qdat.Status = 7
            db.session.commit()
            #Now moving to the next email on the list.....
            with step_timer("go_to_next"):
                qdat, quot, quotbut, datethis, datelast, plaintext, htmltext, mid, taskbox, multibid, emailto, locto, loci = go_to_next(mid, taskbox)
            equip = [1, 0, 0, 0]
            #print(f'locto from email is {locto}')
            #print(f'1479 plaintext: {plaintext}')


        #If no radio button selected then go with generic
        if taskbox == 1 and quot == 0: taskbox = 5

        if taskbox == 2:
            if qdat is not None:
                #print(f'quot is {quot}')
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
                with step_timer("get_body_text after refreshing email"):
                    plaintext, htmltext = get_cached_body_text(qdat)

        if taskbox == 1 or taskbox == 5:
            if qdat is None:
                qdat = Quotes.query.filter(Quotes.Status==0).order_by(Quotes.id.desc()).first()
                if qdat is not None:
                    quot = qdat.id
                    quotbut = qdat.id
                    locto = qdat.Location
            if quot>0 and qdat is not None:
                plaintext, htmltext = get_cached_body_text(qdat)
                if multibid[0] == 'off' and locto is None:
                    #print('Getting new locations because multibid is off and locto is None ')
                    locto, loci = get_place(qdat.Subject, plaintext, multibid)
                    qdat.Location = locto
                    multibid[2] = loci
                    db.session.commit()
                    qdat = Quotes.query.get(quot)
                if multibid[0] == 'on':
                    # Test if all locs are None then try to extract from email:
                    testloc, testloci = get_place(qdat.Subject, plaintext, multibid)
                    locs = multibid[2]
                    #print(f'Here is multibid[1]:{multibid[1]} and here is multibid[2]: {multibid[2]}')
                    #print(f'Here is locs:{locs} and here is testloci:{testloci}')
                    for ix in range(multibid[1]):
                        if not hasinput(locs[ix]): locs[ix] = testloci[ix]

                emailto = qdat.From
                if emailto is None:
                    emailto = qdat.From
                    qdat.From = emailto
                    db.session.commit()
                    qdat = Quotes.query.get(quot)
            else:
                #print('No radio button selected, default is top of the current list')
                comdata = companydata()
                locto = comdata[6]
                emailto = usernames['serv']

            if quot > 0 or taskbox == 5:
                #print(f'Here2a, locfrom is: {locfrom} and locto is {locto}')
                if qdat is not None:
                    locfrom1 = qdat.Start
                    term, locfrom2, locto, port = get_terminal(locto=locto, req=request)
                    if locfrom2 is not None:
                        if locfrom1 == locfrom2:
                            locfrom = locfrom1
                        else:
                            #update qdat
                            qdat.Start = locfrom2
                            locfrom = locfrom2
                    #print(f'Here, locfrom is: {locfrom} and locto is {locto}')
                    if locfrom is None:
                        term, locfrom, locto, port = get_terminal(locto=locto, req=request)
                else:
                    term, locfrom, locto, port = get_terminal(locto=locto, req=request)


                if updatego is not None or updatebid is not None or emailgo is not None or updateE is not None:
                    if multibid[0] == 'on':
                        # Get the bids for each location....
                        mbids = []
                        mdistdata = []
                        #for ix in range(len(tbox)):
                            #tbox[ix] = request.values.get(f'tbox{str(ix)}')
                        tbox = tbox_from_request(request, tbox)
                        for locto in locs:
                            #print(f'Getting data for going to location {locto}')
                            if hasinput(locto) and locto != 'No Location Found':
                                with step_timer("get_directions on update"):
                                    miles, hours, lats, lons, dirdata, tot_dist, tot_dura = get_directions(locfrom, locto)
                                timedata, distdata, costdata, biddata, newdirdata, include_text = get_costs(miles, hours, lats, lons, dirdata, tot_dist, tot_dura, qidat, tbox, expdata, newmarkup=newmarkup)
                                #print(f'1659 distdata is {distdata}')
                                mdistdata.append(distdata)
                                #print(biddata)
                                if tbox[17]: mbids.append(biddata[0])
                                elif tbox[18]: mbids.append(biddata[1])
                                elif tbox[19]: mbids.append(biddata[2])
                                elif tbox[20]: mbids.append(biddata[5])
                                elif tbox[21]: mbids.append(biddata[4])
                                elif tbox[22]: mbids.append(biddata[3])
                            else:
                                mbids.append('0.00')
                        #print(mbids)
                        multibid[3] = mbids

                    # Get the email parameters and box information
                    locto = request.values.get('locto')
                    if locto is None:
                        locto = 'No Location Found'
                    locfrom = request.values.get('locfrom')
                    emailto = request.values.get('edat2')
                    respondnow = datetime.datetime.now()

                    #respond_utc_dt = respondnow.astimezone(ZoneInfo("UTC"))
                    #local_tz = get_localzone()
                    #respond_local_dt = respond_utc_dt.astimezone(local_tz)
                    ny_tz = ZoneInfo("America/New_York")
                    respond_local_dt = respondnow.astimezone(ny_tz)

                    if taskbox == 1 or taskbox == 5:
                        print(f'Here setting qdat.start with, locfrom is: {locfrom}')
                        qdat.Start = locfrom
                        qdat.Location = locto
                        qdat.From = emailto
                        qdat.Markkup = newmarkup
                        qdat.Person = bidname
                        qdat.Responder = username
                        qdat.RespDate = respond_local_dt
                        qdat.Status = 1
                        db.session.commit()
                        qdat = Quotes.query.get(quot)

                if emailgo is not None:
                    #print(f'The task box is {taskbox}')
                    #Email the quote based on the currently loaded email parameters from the html
                    with step_timer("sendquote following emailgo"):
                        emaildata, send_result = sendquote()

                    if taskbox == 1 or taskbox == 5:
                        qdat.Status = 2
                        qdat.Subjectsend = emaildata.get('subject', '')
                        qdat.Response = safe_db_text(emaildata.get('body_html', ''))
                        qdat.Emailto = emaildata.get('to_1', '')
                        qdat.Markup = newmarkup
                        db.session.commit()
                    # Now moving to the next email on the list.....
                    with step_timer("going to next email"):
                        qdat, quot, quotbut, datethis, datelast, plaintext, htmltext, mid, taskbox, multibid, emailto, locto, loci = go_to_next(mid, taskbox)
                    ebodytxt = plaintext
                    #print(f'1645 plaintext: {plaintext}')
                    equip = [1, 0, 0, 0]


                #print('Running Directions:',locfrom,locto,bidthis[0],bidname,taskbox,quot)
                if 1 == 1:
                    if locfrom is not None and locto is not None and locto != 'No Location Found':
                        ####################################  Directions Section  ######################################
                        #Save session variables so we dont call get directions every update unless locfrom or locto change
                        route_key = make_route_key(locfrom, locto)
                        cached_route_key = session.get('route_key')
                        cached_route = session.get('route_data')

                        if cached_route_key == route_key and cached_route:
                            print("[TIMING] get_directions: cache hit", flush=True)
                            miles = cached_route['miles']
                            hours = cached_route['hours']
                            lats = cached_route['lats']
                            lons = cached_route['lons']
                            dirdata = cached_route['dirdata']
                            tot_dist = cached_route['tot_dist']
                            tot_dura = cached_route['tot_dura']
                        else:
                            with step_timer("get_directions"):
                                miles, hours, lats, lons, dirdata, tot_dist, tot_dura = get_directions(locfrom, locto)

                            session['route_key'] = route_key
                            session['route_data'] = {
                                'miles': miles,
                                'hours': hours,
                                'lats': lats,
                                'lons': lons,
                                'dirdata': dirdata,
                                'tot_dist': tot_dist,
                                'tot_dura': tot_dura,
                            }

                        ####################################  Cost & Bid Section  ######################################
                        tbox = tbox_from_request(request, tbox)

                        with step_timer("get_costs"):
                            timedata, distdata, costdata, biddata, newdirdata, include_text = get_costs(miles, hours, lats, lons, dirdata, tot_dist, tot_dura, qidat, tbox, expdata,newmarkup=newmarkup)
                        #print(f'1724 ran the get costs section and distdata is {distdata}')
                        if updatego is not None or quotbut is not None or (taskbox == 5 and updatebid is None):
                            #for ix in range(len(tbox)):
                               # tbox[ix] = request.values.get(f'tbox{str(ix)}')
                            tbox = tbox_from_request(request, tbox)
                            if tbox[17]: bidthis[0] = biddata[0]
                            if tbox[18]: bidthis[1] = biddata[1]
                            if tbox[19]: bidthis[2] = biddata[2]
                            if tbox[22]: bidthis[3] = biddata[3]
                            if tbox[20]: bidthis[5] = biddata[5]
                            if tbox[21]: bidthis[4] = biddata[4]
                    else:
                        timedata = []
                        distdata = []
                        costdata = []
                        biddata = []
                        newdirdata = []
                if 1 == 2:
                    timedata = []
                    distdata = []
                    costdata = []
                    biddata = []
                    newdirdata = []

                # Set checkbox defaults if first time through
                #print(updatebid, updatego, updateE,emailgo)
                if updatebid is None and updatego is None and updateE is None:
                    tbox = [0] * 27
                    tbox[0] = 'on'
                    tbox[17] = 'on'
                    if biddata:
                        if len(biddata)>0:
                            bidthis[0] = biddata[0]
                    takedef = 1
                else:
                    takedef = 0

                if quotbut is not None:
                    # This section sets everything up on first pass thru
                    if wareBB or wareUD:
                        etitle = f'{cdata[0]} (MC#{cdata[12]}) Quote for Warehouse Services from {port}'
                    else:
                        etitle = f'{cdata[0]} (MC#{cdata[12]}) Quote to {locto} from {port}'

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
                    if sboxes[0] == 'direct':
                        with step_timer("bodymaker_direct"):
                            ebody, tbox, etitle, bidtypeamount = bodymaker_direct(bidname,cdata,bidthis,locto,tbox,expdata,distdata,multibid, etitle, port, include_text, whouse, wareBB, wareUD, mdistdata, costdata, sboxes)
                    elif sboxes[0] == 'classic':
                        ebody, tbox, etitle, bidtypeamount = bodymaker_classic(bidname,cdata,bidthis,locto,tbox,expdata,distdata,multibid, etitle, port, include_text, whouse, wareBB, wareUD, mdistdata, costdata, sboxes)
                    #print(f'The bidtypeamount here after call is {bidtypeamount} and amount in database is {qdat.Amount} for {quot}')
                    if wareBB is not None or wareUD is not None:
                        ebody = ebody + f'<br><br><em>{signoff}</em>'
                    else:
                        if sboxes[1] == 'include':
                            ebody = ebody + maketable(expdata)
                        else:
                            ebody = ebody + f'<br><br><em>{signoff}</em>'

                    emailin1 = request.values.get('edat2')
                    if updatego is None:
                        emailin1 = emailonly(emailto)
                    emailin2 = ''
                    emailcc1 = usernames['info']
                    emailcc2 = usernames['serv']

                    #Preview Builder
                    preview_subject = etitle
                    if send_mode == 'reply' and qdat is not None:
                        original_meta = get_original_message_meta(qdat)
                        preview_subject = make_reply_subject(original_meta.get('subject') or qdat.Subject)

                    emaildata = make_emaildata_list(
                        preview_subject,
                        ebody,
                        emailin1,
                        emailin2,
                        emailcc1,
                        emailcc2,
                        usernames['quot']
                    )
                    qdat.Amount = bidtypeamount[1]
                    db.session.commit()
                    qdat = Quotes.query.get(quot)
                else:
                    #This for recycles in the quote...
                    if updatebid is not None or updatego is not None or wareBB is not None or wareUD is not None:
                        #for ix in range(len(tbox)):
                            #tbox[ix] = request.values.get(f'tbox{str(ix)}')
                        tbox = tbox_from_request(request, tbox)

                        quotestyle = request.values.get('quotestyle')
                        atable = request.values.get('atable')
                        commodity = request.values.get('commodity')
                        comtext = request.values.get('comtext')
                        print(quotestyle, atable, commodity, comtext)
                        if quotestyle is None: quotestyle = 'direct'
                        if atable is None: atable = 'exclude'
                        if commodity is None: commodity = 'com1'
                        if comtext is None: comtext = 'General Freight'
                        sboxes = [quotestyle, atable, commodity, comtext]

                        if wareBB is not None or wareUD is not None:
                            etitle = f'{cdata[0]} (MC#{cdata[12]}) Quote for Warehouse Services from {port}'
                        else:
                            etitle = f'{cdata[0]} (MC#{cdata[12]}) Quote to {locto} from {port}'

                        if sboxes[0] == 'direct':
                            ebody, tbox, etitle, bidtypeamount = bodymaker_direct(bidname, cdata, bidthis, locto, tbox,
                                                                                  expdata, distdata, multibid,
                                                                                  etitle, port, include_text, whouse,
                                                                                  wareBB, wareUD, mdistdata, costdata,
                                                                                  sboxes)
                        elif sboxes[0] == 'classic':
                            ebody, tbox, etitle, bidtypeamount = bodymaker_classic(bidname, cdata, bidthis, locto, tbox,
                                                                                   expdata, takedef, distdata, multibid,
                                                                                   etitle, port, include_text, whouse,
                                                                                   wareBB, wareUD, mdistdata, costdata,
                                                                                   sboxes)

                        if wareBB is not None or wareUD is not None:
                            ebody = ebody + f'<br><br><em>{signoff}</em>'
                        else:
                            if sboxes[1] == 'include':
                                ebody = ebody + maketable(expdata)
                            else:
                                ebody = ebody + f'<br><br><em>{signoff}</em>'


                        #print(f'The bidtypeamount here after 2nd lower call is {bidtypeamount} and amount in database is {qdat.Amount}')
                        qdat.Amount = bidtypeamount[1]
                    else:
                        etitle = request.values.get('edat0')
                        ebody = request.values.get('edat1')

                    emailin1 = request.values.get('edat2')
                    emailin2 = request.values.get('edat3')
                    emailcc1 = request.values.get('edat4')
                    emailcc2 = request.values.get('edat5')

                    preview_subject = etitle
                    if send_mode == 'reply' and qdat is not None:
                        original_meta = get_original_message_meta(qdat)
                        preview_subject = make_reply_subject(original_meta.get('subject') or qdat.Subject)

                    emaildata = make_emaildata_list(
                        preview_subject,
                        ebody,
                        emailin1,
                        emailin2,
                        emailcc1,
                        emailcc2,
                        usernames['quot']
                    )

                    with step_timer("db_commit 3247"):
                        db.session.commit()
                    qdat = Quotes.query.get(quot)


        else:
            qdata = dataget_Q(thismuch)
            quot = request.values.get('optradio')
            if quot is not None:
                qdat = Quotes.query.get(quot)
                #print(f'Getting body_text because this is not a post so we are getting new values')
                with step_timer("get_body_text for opt radio selection"):
                    plaintext, htmltext = get_cached_body_text(qdat)
                #print(f'1766 plaintext: {plaintext}')
                showtext = plaintext
            else:
                showtext = ''
            term, locfrom, locto, port = get_terminal(locto=locto, req=request)
            if locto is None: locto = 'Capitol Heights, MD  20743'
            etitle = f'{cdata[0]} Quote for Drayage to {locto} from {port}'
            efrom = usernames['quot']
            eto1 = 'unknown'
            eto2 = ''
            ecc1 = usernames['serv']
            ecc2 = usernames['info']

            preview_subject = etitle
            if send_mode == 'reply' and qdat is not None:
                original_meta = get_original_message_meta(qdat)
                preview_subject = make_reply_subject(original_meta.get('subject') or qdat.Subject)

            emaildata = make_emaildata_list(
                preview_subject,
                showtext,
                eto1,
                eto2,
                ecc1,
                ecc2,
                efrom
            )

            costdata = None
            biddata = None
            newdirdata = None
            bidthis = None
            bidname = None


            # Get and update the cost data
            timedata = []
            distdata = []
            mdistdata = []


    else:
        iter = 1
        #print('This is NOT a Post')
        ebodytxt = ''
        #print('Entering Quotes1',flush=True)
        username = session['username'].capitalize()
        tbox = [0] * 27
        tbox[0] = 'on'
        tbox[17] = 'on'
        qdat=None
        term, locfrom, locto, port = get_terminal(locto=locto, req=request)
        locto = 'No Location Found'
        etitle = f'{cdata[0]} Quote for Drayage to {locto} from {port}'
        ebody = f'Regirgitation from the input'
        efrom = usernames['quot']
        eto1 = 'unknown'
        eto2 = ''
        ecc1 = usernames['expo']
        ecc2 = usernames['info']

        preview_subject = etitle
        if send_mode == 'reply' and qdat is not None:
            original_meta = get_original_message_meta(qdat)
            preview_subject = make_reply_subject(original_meta.get('subject') or qdat.Subject)

        emaildata = make_emaildata_list(
            preview_subject,
            ebody,
            eto1,
            eto2,
            ecc1,
            ecc2,
            efrom
        )

        costdata = None
        biddata = None
        newdirdata = None
        bidthis = None
        bidname = None
        timedata = []
        distdata = []
        mdistdata = []
        quot=0
        # Set quotes to top of the table:
        qdat = Quotes.query.filter(Quotes.Status == 0).order_by(Quotes.id.desc()).first()
        if qdat is not None:
            quot = qdat.id
            quotbut = qdat.id
            #print(f'Getting body_text because this is not a post and we set pointer to top of table')
            with step_timer("get_body_text for all else"):
                plaintext, htmltext = get_cached_body_text(qdat)
            #print(f'1832 plaintext: {plaintext}')
        else:
            add_quote_emails()
        thismuch = '6'
        taskbox = 0
        newmarkup = None


    qdata = dataget_Q(thismuch)
    showtext = plaintext
    print(f'Got qdata for thismuch={thismuch}, quot={quot}, lengthofqdata={len(qdata)}', flush=True)
    print(f'mutlibid on exit is {multibid[0]} and {multibid[1]} and uiter is {uiter} and iter is {iter}')
    #Save all the session variables that may have been updated...
    iter = iter + 1
    os.environ[uiter] = str(iter)


    if multibid[0] == 'on':
        loci = multibid[2]
        locto = 'OK'
        for loctest in loci:
            if loctest == 'No Location Found': locto = 'No Location Found'

    #print(f'Here at end, locfrom is: {locfrom}')
    multibid.append(term)
    terminals = Terminals.query.all()
    multibid.append(terminals)
    #print(multibid)
    #print(f'Exiting with iter = {iter} and mid: {mid} for umid: {umid} and osenv for uiter: {os.environ[uiter]}')
    #print(f'On exit emaildata is: {emaildata}')
    return (bidname, costdata, biddata, expdata, timedata, distdata, emaildata, locto, locfrom, newdirdata,
            qdata, bidthis, taskbox, thismuch, quot, qdat, tbox, showtext, multibid, newmarkup, whouse, sboxes, htmltext, send_mode, reply_style, save_sent, equip)
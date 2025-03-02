from webapp import db
from flask import render_template, flash, redirect, url_for, session, logging, request
from requests import get
from CCC_system_setup import apikeys
from CCC_system_setup import myoslist, addpath, tpath, companydata, usernames, passwords, scac, imap_url, accessorials, signoff
from webapp.viewfuncs import d2s, stat_update, hasinput, d1s
#from viewfuncs import d2s, d1s
import imaplib, email
import math

import webbrowser
import os
from email.utils import parsedate_tz, mktime_tz
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from sqlalchemy.sql import desc
import ast

import datetime
from webapp.models import Orders, Gledger, PaymentsRec

cdata = companydata()

today_now = datetime.datetime.now()
today = today_now.date()
timenow = today_now.time()

def isoPay():
    username = session['username'].capitalize()
    exitnow = request.values.get('exitPay')
    active_task = request.values.get('active_task')
    redirect = request.values.get('exitAR2')
    uiter = f'{username}_iter'

    if request.method == 'POST':
        try:
            iter = int(os.environ[uiter])
        except:
            iter = 1

        if exitnow is not None:
            #status, this_id, odata, pdata= isoPay()
            return  'exitnow', None, None, None, None

        elif redirect is not None:
            this_id = request.values.get('optradio')
            task = 'include details'

        # Not exiting after a Post
        else:
            this_id = request.values.get('optradio')
            print(f'The payment id of interest is {this_id}')
            task = 'include details'
            pdata = PaymentsRec.query.all()
            odata = Orders.query.filter(Orders.QBi == this_id).all()
            tot = 0.00
            for odat in odata:
                tot = tot + float(odat.PaidAmt)

    else:
        iter = 1
        username = session['username'].capitalize()
        this_id = 0
        task = 'payments'
        pdata = PaymentsRec.query.all()
        odata = None

    if this_id == 0:
        plen = len(pdata)
        pdat = pdata[plen-1]
        this_id = pdat.id
        odata = Orders.query.filter(Orders.QBi == this_id).all()
        tot = 0.00
        for odat in odata:
            tot = tot + float(odat.PaidAmt)

    #Save all the session variables that may have been updated...
    iter = iter + 1
    os.environ[uiter] = str(iter)

    return 'keepgoing', this_id, odata, pdata, tot
from webapp import db
from webapp.models import Income, Openi, Orders

import datetime
from datetime import timedelta
from flask import render_template, flash, redirect, url_for, session, logging, request


from webapp.viewfuncs import d2s

today = datetime.datetime.today()
today_str = today.strftime("%m/%d/%Y")
d = today.strftime("%B %d, %Y")

#Calc days back desered to go back to last date of year two years prior
tyear = today.year - 2
last_day_back = datetime.date(tyear, 1, 1)
daysback = today.date() - last_day_back
days_far_back = daysback.days
cutoff = datetime.datetime.now() - timedelta(days_far_back)
cutoff = cutoff.date()
over30 = datetime.datetime.now() - timedelta(30)
over30 = over30.date()
todaydate = today.date()

def intdol(int):
    if int is not None:
        fd = int/100
        return "${:0,.2f}".format(fd)
    else:
        return ''

def get_revenues():
    #title1,col1,data1,title2,col2,data2 = revenues()
    data1 = []
    data2 = []
    data3 = []
    idata = Income.query.filter(Income.Type == 'MR').all()
    odata = Openi.query.order_by(Openi.Open.desc()).all()

    title1 = idata[0].Description
    title2 = odata[0].Description
    exclude_these = ['FEL Ocean Div', 'First Eagle Logistics', 'One Stop Logistics', 'Nello Enterprise LLC',
                     'Jays Auto Service']


    tab1 = request.values.get('mireport')
    tab2 = request.values.get('obreport')
    tab3 = request.values.get('oireport')
    tab4 = request.values.get('bireport')
    if tab4 is not None:
        tabon = [tab1, tab2, 0, 'on']
    else:
        tabon = [tab1, tab2, tab3, 0]
    if tabon == [None, None, None, 0]:
        tabon = ['on', 'on', 'on', 0]

    lastitem = None
    col1 = ['Month', 'Revenues', 'Collected', 'Over120', 'Over90', 'Over60', 'Over30', 'Under30', 'All Open']
    col2 = ['Company', 'Total Revenues', 'Collected', 'Over120', 'Over90', 'Over60', 'Over30', 'Under30', 'All Open']

    for idat in idata:
        data1.append([idat.Period, intdol(idat.Mrev), intdol(idat.Mpaid), intdol(idat.O120), intdol(idat.O90), intdol(idat.O60), intdol(idat.O30), intdol(idat.U30), intdol(idat.Open)])
    for odat in odata:
        if odat.Company == 'TOTAL':
            lastitem = [odat.Company, intdol(odat.Mrev), intdol(odat.Mpaid), intdol(odat.O120), intdol(odat.O90), intdol(odat.O60), intdol(odat.O30), intdol(odat.U30), intdol(odat.Open)]
        else:
            data2.append([odat.Company, intdol(odat.Mrev), intdol(odat.Mpaid), intdol(odat.O120), intdol(odat.O90), intdol(odat.O60), intdol(odat.O30), intdol(odat.U30), intdol(odat.Open)])
    if lastitem is not None:
        data2.append(lastitem)


    if tabon[3] == 'on':
        col3 = ['Period', 'Revenues']
        adata = Income.query.filter(Income.Type == 'BI').all()
        title3 = adata[0].Description
        for adat in adata:
            data3.append([adat.Period, intdol(adat.Mrev)])

    else:
        col3 = ['Jo', 'Company', 'Container', 'Invoice Date', 'Total Amount']
        adata = Orders.query.filter(
            (Orders.Istat > 0) & (Orders.Istat != 5) & (Orders.Istat != 8) & (Orders.InvoDate > cutoff)).order_by(
            Orders.InvoDate).all()
        title3 = adata[0].Description
        for adat in adata:
            try: amt = float(adat.InvoTotal)
            except: amt = 0.00
            ship = adat.Shipper
            if ship not in exclude_these:
                status = adat.Seal
                if status != 'Uncollectable':
                    data3.append([adat.Jo, adat.Shipper, adat.Container, adat.InvoDate, d2s(amt)])



    return title1, col1, data1, title2, col2, data2, title3, col3, data3, tabon
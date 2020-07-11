from webapp import db
from webapp.models import General, users, OverSeas, Orders, IEroll, Broll
from flask import session, logging, request
import datetime
import calendar
import re
import os
import shutil
import subprocess
from webapp.report_maker import reportmaker

def isoR():

    if request.method == 'POST':
# ____________________________________________________________________________________________________________________B.FormVariables.General

        from viewfuncs import parseline, popjo, jovec, newjo, timedata, nonone, nononef
        from viewfuncs import numcheck, numcheckv, viewbuttons, get_ints, numcheckvec, erud

        #Zero and blank items for default
        username = session['username'].capitalize()
        cache= request.values.get('cache')
        err=[]
        docref=''
        doctxt=''
        fyear=2019
        oceantype=request.values.get('dt1')
        trucktype=request.values.get('dt2')
        detailtype=request.values.get('dt3')
        c1=request.values.get('dc1')
        c2=request.values.get('dc2')
        c3=request.values.get('dc3')
        c4=request.values.get('dc4')
        c5=request.values.get('dc5')
        c6=request.values.get('dc6')
        c7=request.values.get('dc7')
        clist=[oceantype,trucktype,detailtype,c1,c2,c3,c4,c5,c6,c7]

        today = datetime.date.today()
        now = datetime.datetime.now().strftime('%I:%M %p')

        leftsize=8
        leftscreen=0

        interreport =  request.values.get('mtick')
        jayreport   =  request.values.get('jaystuff')
        increport   =  request.values.get('income')
        custreport  =  request.values.get('customer')
        thiscomp    =  request.values.get('thiscompany')
        PLreport    =  request.values.get('PL')

        sdate=request.values.get('start')
        fdate=request.values.get('finish')

        #This sequence will reset hv while collecting the new plot accounts
        # hv[0] and hv[11] store the number of bars and their labels of the plot
        # This provide hv[1-10] as the bar chart data available
        hv = [request.values.get(f'act{ix}') for ix in range(0,13)]
        for ix, est in enumerate(hv):
            if est is None: hv[ix] = '0'

        #If the first 3 selections are all '0' make sure remaining are turned off:
        if hv[1] == '0' and hv[2] == '0' and hv[3] == '0' and hv[4] == '0': hv = ['0']*13

        # If no accts selected to plot then switch off the plot section of page
        if all(h=='0' for h in hv):
            plotswitch = 0
            plotthese = []
        else:
            plotswitch=1
            plotthese = [h for h in hv if h != '0' ]
        hv[0] = len(plotthese)
        hv[11] = plotthese
        hv[12] = request.values.get('timestyle')
        if hv[12] is None:
            hv[12] = '12'

        print('plotstuff',plotswitch,plotthese)

        monvec=['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        for j, mon in enumerate(monvec):
            a=request.values.get(mon)
            if a is not None:
                b=request.values.get('focusyear')
                if b is not None:
                    fyear=2018
                jmonth=j+1
                leapyears=[2020,2024,2028,2032,2036]
                if fyear in leapyears:
                    enddays = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                else:
                    enddays = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                endday=enddays[j]
                start= datetime.date(fyear, jmonth, 1)
                end= datetime.date(fyear, jmonth, endday)
                sdate=start.strftime('%Y-%m-%d')
                fdate=end.strftime('%Y-%m-%d')

        if interreport is not None:
            cache,docref=reportmaker('mtick','')

        if jayreport is not None:
            cache,docref=reportmaker('jay','')

        if increport is not None:
            cache,docref=reportmaker('income','')

        if custreport is not None and thiscomp != '1':
            cache,docref=reportmaker('customer',thiscomp)

        if PLreport is not None:
            cache,docref=reportmaker('pl','')


        if cache is not None:
            #Save the current cache so we do not start from bad place in future
            udat=users.query.filter(users.name=='cache').first()
            udat.username=str(cache)
            db.session.commit()


    else:
        from viewfuncs import popjo, jovec, timedata, nonone, nononef, init_truck_zero, erud
        today = datetime.date.today()
        err=[]
        hv = ['0'] * 12
        hv[0] = 0
        #today = datetime.datetime.today().strftime('%Y-%m-%d')
        now = datetime.datetime.now().strftime('%I:%M %p')
        docref=''
        doctxt=''
        thiscomp=''
        leftscreen=0
        leftsize=8
        udat=users.query.filter(users.name=='Cache').first()
        cache=udat.username
        cache=nonone(cache)
        sdate=today
        fdate=today
        fyear=2020
        clist=['off']*12
        clist[1] = 'on'

    customerlist=[]
    if clist[0]=='on':
        odata=OverSeas.query.all()
        for odat in odata:
            cust=odat.BillTo
            if cust not in customerlist:
                customerlist.append(cust)
    if clist[1]=='on':
        odata=Orders.query.all()
        for odat in odata:
            cust=odat.Shipper
            if cust not in customerlist:
                customerlist.append(cust)

    customerlist.sort()
    idata1 = IEroll.query.filter(IEroll.Name.contains('Totals')).order_by(IEroll.Name).all()
    idata2 = IEroll.query.filter(~(IEroll.Name.contains('Totals')) & (IEroll.Type == 'Expense')).order_by(IEroll.Name).all()
    idata3 = IEroll.query.filter(~(IEroll.Name.contains('Totals')) & (IEroll.Type == 'Income')).order_by(IEroll.Name).all()
    idata4 = Broll.query.filter(Broll.Type == 'Expense-B').order_by(Broll.Tot.desc()).all()
    err = erud(err)


    return idata1, idata2, idata3, idata4, hv, cache, err, leftscreen, docref, leftsize, today, now, doctxt, sdate, fdate, fyear, customerlist, thiscomp, clist

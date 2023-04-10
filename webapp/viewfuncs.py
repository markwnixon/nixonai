from webapp import db
from webapp.models import Trucklog, DriverAssign, Invoices, JO, Income, Bills, Accounts, Bookings, OverSeas, Autos, People, Interchange, Drivers, ChalkBoard, Orders, Drops, Services, Quotes, Divisions
from webapp.models import Taxmap, QBaccounts, Accttypes, IEroll, Broll, StreetTurns, Gledger, Adjusting
from flask import session, logging, request
import datetime
import calendar
import re
import os
import shutil
import subprocess
import img2pdf
import json
from webapp.CCC_system_setup import addpath, scac, tpath, companydata

today=datetime.date.today()
today_str = today.strftime('%Y-%m-%d')
cdata = companydata()
jbcode = cdata[10]+'T'

def last_day_of_month(any_day):
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
    return next_month - datetime.timedelta(days=next_month.day)

def nodollar(infloat):
    outstr="%0.2f" % infloat
    return outstr

def dollar(infloat):
    outstr='$'+"%0.2f" % infloat
    return outstr

def avg(in1,in2):
    out=(in1+in2)/2
    return out

def stat_update(status,newval,i):
    a=list(status)
    a[i]=newval
    b=''.join(a)
    return b

def d2s(instr):
    try:
        instr=instr.replace('$','').replace(',','')
    except:
        instr=str(instr)
    try:
        infloat=float(instr)
        outstr="%0.2f" % infloat
    except:
        outstr=instr
    return outstr

def d2sa(instr):
    try:
        instr=instr.replace('$','').replace(',','')
    except:
        instr=str(instr)
    try:
        infloat=float(instr)
        outstr="%0.2f" % infloat
    except:
        outstr='0.00'
    return outstr

def d1s(instr):
    try:
        instr=instr.replace('$','').replace(',','')
    except:
        instr=str(instr)
    try:
        infloat=float(instr)
        outstr="%0.1f" % infloat
    except:
        outstr=instr
    return outstr

def stripper(input):
    try:
        new = input.strip()
    except:
        new = ''
    return new

def hasinput(input):
    if input is None:
        return 0
    elif isinstance(input,str):
        input = input.strip()
        if input == '' or input == 'None' or input == 'none' or input=='0' or input == 'Choose Later':
            return 0
        else:
            return 1
    elif isinstance(input,int):
        if input == 0:
            return 0
        else:
            return 1
    else:
        return 1

def container_types():
    return ['''40' GP 9'6"''', '''40' GP 8'6"''', '''45' GP 9'6"''', '''20' GP 8'6"''', '''45' VH 9'6"''',
            '''20' VH 8'6"''', '53FT Dry', 'LCL', 'RORO']

def testdrop(dblock):
    idret = 0
    xtest = 'xxx'
    newdrop = dblock
    company = 'None'
    dblock2 = dblock.strip()
    ltest = len(dblock2)
    print('ltest=',ltest)
    if ltest == 3:
        sfind = dblock2.lower()
        if sfind == 'bal':
            xtest = 'sea'
        ddata = Drops.query.all()
        for ddat in ddata:
            entity = stripper(ddat.Entity)
            scomp = entity[0:3]
            scomp = scomp.lower()
            print(sfind,scomp)
            if sfind == scomp or xtest == scomp:
                idret = ddat.id
                a1 = stripper(ddat.Entity)
                a2 = stripper(ddat.Addr1)
                a3 = stripper(ddat.Addr2)
                a4 = stripper(ddat.Phone)
                a5 = stripper(ddat.Email)
                newdrop = a1 + '\n' + a2 + '\n' + a3 + '\n' + a4 + '\n' + a5
                company = a1
                print('Found:',a1,a2,a3,a4,a5)
                break
    return idret, newdrop, company

def dropupdate(dropblock):
    droplist=dropblock.splitlines()
    avec=['']*5
    for j,drop in enumerate(droplist):
        avec[j]=stripper(drop)
    entity=avec[0]
    addr1=avec[1]
    edat=Drops.query.filter((Drops.Entity==entity) & (Drops.Addr1==addr1)).first()
    if edat is None:
        input = Drops(Entity=entity,Addr1=addr1,Addr2=avec[2],Phone=avec[3],Email=avec[4])
        db.session.add(input)
        db.session.commit()
    return entity

def dropupdate2(bid):
    pdat = People.query.filter(People.id == bid).first()
    if pdat is not None:
        droplist = [pdat.Company,pdat.Addr1,pdat.Addr2,pdat.Email,pdat.Telephone]
        avec=['']*5
        for j,drop in enumerate(droplist):
            avec[j]=stripper(drop)
        entity=avec[0]
        addr1=avec[1]
        edat=Drops.query.filter((Drops.Entity==entity) & (Drops.Addr1==addr1)).first()
        if edat is None:
            input = Drops(Entity=entity,Addr1=addr1,Addr2=avec[2],Phone=avec[3],Email=avec[4])
            db.session.add(input)
            db.session.commit()

        edatnew = Drops.query.filter((Drops.Entity==entity) & (Drops.Addr1==addr1)).first()
        return edatnew.id
    else:
        return 0



def getexpimp(con):
    idata = Interchange.query.filter(Interchange.Container == con).all()
    for idat in idata:
        ctype = idat.Type
        if ctype == 'Load Out':
            return 'Import'
        if ctype == 'Load In':
            return 'Export'
    return 'No Info'

def dropupdate3(txt):
    edat = Drops.query.filter(Drops.Entity == 'Baltimore Seagirt').first()
    return edat.id

def txtfile(infile):
    base=os.path.splitext(infile)[0]
    tf=base+'.txt'
    return tf

def doctransfer(d1,d2,filesel):
    if filesel != '1':
        docold=f'tmp/{scac}/processing/'+d1+'/'+filesel
        docref=f'tmp/{scac}/data/'+d2+'/'+filesel
        oldtxt=docold.split('.',1)[0]+'.txt'
        doctxt=docref.split('.',1)[0]+'.txt'
        try:
            shutil.move(addpath(docold),addpath(docref))
            shutil.move(addpath(oldtxt),addpath(doctxt))
        except OSError:
            print('File has been moved already')
    else:
        docref=''
        doctxt=''
    return docref,doctxt


def commaguard(instring):
    sandwich=re.compile(r',[A-Za-z]')
    t1=sandwich.findall(instring)
    for t in t1:
        l=t[1]
        instring=instring.replace(t,', '+l)
    return instring

def parseline(line,j):
    line=commaguard(line)
    splitline=line.upper().split()
    outline=[]
    newline=''
    for word in splitline:
        if len(newline)<j-7:
            newline=newline+word+' '
        else:
            outline.append(newline)
            newline=word+' '
    outline.append(newline)
    return outline

def parselinenoupper(line,j):
    line=commaguard(line)
    splitline=line.split()
    outline=[]
    newline=''
    for word in splitline:
        if len(newline)<j-7:
            newline=newline+word+' '
        else:
            outline.append(newline)
            newline=word+' '
    outline.append(newline)
    return outline

def nonone(input):
    try:
        output=int(input)
    except:
        output=0
    return output

def nons(input):
    if input is None or input == 'None':
        input=''
    return input

def nononef(input):
    if input is None:
        output = 0.00
    elif input=='' or input==' ' or input=='None':
        output=0.00
    else:
        input=input.replace('$','').replace(',','')
        output=float(input)
    return output

def GetCo(dtype,lpt):
    if dtype=='Jays':
        if lpt=='All':
            data=People.query.filter( (People.Ptype=='Jays') | (People.Ptype== 'TowCo') ).all()
        if lpt=='Jays':
            data=People.query.filter(People.Ptype=='Jays').all()
        if lpt=='TowCo':
            data=People.query.filter(People.Ptype=='TowCo').all()
        if lpt=='TowPu':
            data=People.query.filter(People.Ptype=='TowPu').all()
        if lpt=='TowDel':
            data=People.query.filter(People.Ptype=='TowDel').all()
    return data

def GetCo3(dtype):
    if dtype=='JaysAuto':
        pdata1=People.query.filter(People.Ptype=='TowCo').order_by(People.Company).all()
        pdata2=People.query.filter(People.Ptype=='TowPu').order_by(People.Company).all()
        pdata3=People.query.filter(People.Ptype=='TowDel').order_by(People.Company).all()
    return pdata1,pdata2,pdata3

def popjo(oder,monsel):
    m=Storage.query.get(oder)
    headjo=m.Jo
    if monsel is None or monsel==0:
        char3=headjo[2]
    else:
        char3=str(monsel)
        char3=char3.replace('10','X').replace('11','Y').replace('12','Z')
    thisjo='FS'+char3+'01'+headjo[5:8]
    return thisjo


def jovec(jo):
    jolist=['']*12
    char3=['1', '2', '3', '4', '5', '6', '7', '8', '9', 'X', 'Y', 'Z']
    k=0
    for i in char3:
        jolist[k]='FS'+i+'01'+jo[5:8]
        k=k+1
    return jolist

def newjo(jtype,sdate):
    dt = datetime.datetime.strptime(sdate, '%Y-%m-%d')
    year= str(dt.year)
    day=str(dt.day)
    month=str(dt.month)
    lv=JO.query.get(1)
    nextid=lv.nextid
    eval=str(nextid%100).zfill(2)
    day2="{0:0=2d}".format(int(day))
    if month=='10':
        month='X'
    if month=='11':
        month='Y'
    if month=='12':
        month='Z'

    nextjo = jtype+month+day2+year[3]+eval
    input2 = JO(jo=nextjo, nextid=0, date=sdate, status=1)
    db.session.add(input2)
    lv.nextid=nextid+1
    db.session.commit()
    return nextjo


def numcheckv(a1):
    numchecked=0
    avec=[]
    for a in a1:
        testone = request.values.get('oder'+str(a.id))
        if testone:
            numchecked=numchecked+1
            avec.append(int(testone))
    return avec

def numcheckvec(a1,a2):
    numchecked=0
    avec=[]
    for a in a1:
        testone = request.values.get(a2+str(a.id))
        if testone:
            numchecked=numchecked+1
            avec.append(int(testone))
    return avec

def numcheck(ntab, a1, a2, a3, a4, a5, textdat):
    out=[0]*ntab
    numchecked=0
    bigdata=[a1,a2,a3,a4,a5]
    for i in range(ntab):
        if bigdata[i] != 0:
            for data in bigdata[i]:
                testone = request.values.get(textdat[i]+str(data.id))
                if testone:
                    numchecked=numchecked+1
                    out[i]=int(testone)
    if ntab==1:
        return out[0],numchecked
    if ntab==2:
        return out[0],out[1],numchecked
    if ntab==3:
        return out[0],out[1],out[2],numchecked
    if ntab==4:
        return out[0],out[1],out[2],out[3],numchecked
    if ntab==5:
        return out[0],out[1],out[2],out[3],out[4],numchecked


def sdiff(a,b):
    try:
        af=nononef(a)
    except:
        af=0.0
    try:
        bf=nononef(b)
    except:
        bf=0.0
    sf=af-bf
    nsf="{:.2f}".format(sf)
    return nsf

def sadd(a,b):
    try:
        af=nononef(a)
    except:
        af=0.0
    try:
        bf=nononef(b)
    except:
        bf=0.0
    sf=af+bf
    nsf="{:.2f}".format(sf)
    return nsf

def timedata(subdata1):
    k=0
    bm=['']*len(subdata1)
    cm=['']*len(subdata1)
    for data in subdata1:
        mdata=['']*12
        ndata=['']*12
        jo=data.Jo
        jol=jovec(jo)
        m=0
        for j in jol:
            idat=Invoices.query.filter(Invoices.Subjo==j).first()
            if idat is not None:
                if idat.Total is not None:
                    mdata[m]=str(idat.Total)
                    ndata[m]=idat.Status
            m=m+1
        bm[k]=mdata
        cm[k]=ndata
        k=k+1
    return bm, cm

def init_storage_zero():
    monsel=0
    oder=0
    peep=0
    serv=0
    invo=0
    inco=0
    cache=0
    modata=0
    modlink=0
    fdata=0
    invooder=0
    return monsel,oder,peep,serv,invo,inco,cache,modata,modlink,fdata,invooder

def init_truck_zero():
    oder=0
    poof=0
    tick=0
    serv=0
    peep=0
    invo=0
    cache=0
    modata=0
    modlink=0
    stayslim=0
    invooder=0
    stamp=0
    fdata=0
    csize=0
    invodate=0
    inco=0
    cdat=0
    pb=0
    passdata=0
    vdata=0
    caldays=0
    daylist=0
    weeksum=0
    nweeks=0
    return oder, poof, tick, serv, peep, invo, cache, modata, modlink, stayslim, invooder, stamp, fdata, csize, invodate, inco, cdat,pb,passdata,vdata,caldays,daylist,weeksum,nweeks

def init_ocean_zero():
    ship=0
    book=0
    auto=0
    peep=0
    comm=0
    invo=0
    cache=0
    modata=0
    modlink=0
    stayslim=0
    invooder=0
    stamp=0
    fdata=0
    csize=0
    invodate=0
    inco=0
    cdat=0
    pb=0
    passdata=0
    vdata=0
    caldays=0
    daylist=0
    weeksum=0
    nweeks=0
    return ship,book,auto,peep,comm,invo,cache,modata,modlink,stayslim,invooder,stamp,fdata,csize,invodate,inco,cdat,pb,passdata,vdata,caldays,daylist,weeksum,nweeks


def init_horizon_zero():
    cars=0
    auto=0
    peep=0
    invo=0
    cache=0
    modata=0
    modlink=0
    invooder=0
    stamp=0
    fdata=0
    csize=0
    invodate=0
    inco=0
    cdat=0
    pb=0
    passdata=0
    vdata=0
    caldays=0
    daylist=0
    weeksum=0
    nweeks=0
    return cars,auto,peep,invo,cache,modata,modlink,invooder,stamp,fdata,csize,invodate,inco,cdat,pb,passdata,vdata,caldays,daylist,weeksum,nweeks




def init_horizon_blank():
    filesel=''
    docref=''
    search11=''
    search12=''
    search21=''
    search22=''
    search31=''
    search32=''
    return filesel, docref, search11, search12, search21, search22, search31, search32

def init_billing_blank():
    filesel=''
    docref='',
    search11=''
    search12=''
    search13=''
    search14=''
    search21=''
    search22=''
    bType=''
    bClass=''
    return filesel,docref,search11,search12,search13,search14,search21,search22,bType,bClass

def init_storage_blank():
    invojo=''
    filesel=''
    docref='',
    search11=''
    search12=''
    search21=''
    search31=''
    return invojo, filesel,docref,search11,search12,search21,search31


def init_ocean_blank():
    filesel=''
    docref=''
    josearch1=''
    booksearch1=''
    josearch2=''
    booksearch2=''
    search31=''
    search32=''
    search41=''
    search42=''
    search51=''
    search52=''
    return filesel, docref, josearch1, booksearch1, josearch2, booksearch2, search31, search32, search41, search42, search51 , search52






def money12(basejo):
    involine=['']*13
    paidline=['']*13
    refline=['']*13
    balline=['']*13
    jol=jovec(basejo)

    for m,j in enumerate(jol):
        idat=Invoices.query.filter(Invoices.SubJo==j).first()
        pdat=Income.query.filter(Income.Account==j).first()
        invoamt=0.00
        incoamt=0.00
        if idat is not None:
            if idat.Total is not None:
                involine[m]=str(idat.Total)
                invoamt=float(idat.Total)
        if pdat is not None:
            if pdat.Amount is not None:
                paidline[m]=str(pdat.Amount)
                refline[m]=pdat.Ref
                incoamt=float(pdat.Amount)
        if idat is not None and pdat is not None:
            #balline[m]=sdiff(idat.Total,pdat.Amount)
            diffamt=invoamt-incoamt
            balline[m]=str(diffamt)
        elif idat is not None:
            balline[m]=str(idat.Total)
        elif pdat is not None:
            balline[m]=str(pdat.Amount)

    return involine,paidline,refline,balline

def calendar_calcs(thistype):
    today = datetime.datetime.today()
    ndays=18
    day=today.day
    d = today
    nlist=ndays*4
    caldays=list(range(ndays))
    caldt=list(range(ndays))
    daylist=list(range(nlist))
    for i in range(ndays):
        for j in range(4):
            k=4*i+j
            daylist[k]=0
    for i in range(6):
        days_ahead1 = i - 7 - d.weekday()
        if days_ahead1 <= 0:
            days_ahead1 += 7
        days_ahead2 = days_ahead1 + 7
        days_ahead0 = days_ahead1 - 7
        next_weekday0= d + datetime.timedelta(days_ahead0)
        next_weekday1= d + datetime.timedelta(days_ahead1)
        next_weekday2= d + datetime.timedelta(days_ahead2)
        calmon0=str(next_weekday0.month)
        calmon1=str(next_weekday1.month)
        calmon2=str(next_weekday2.month)
        caldays[i+12]= calendar.day_abbr[i] + ' ' + calendar.month_abbr[int(calmon2)] + ' ' + str(next_weekday2.day)
        if next_weekday1.day==day:
            caldays[i+6]=   'X' + calendar.day_abbr[i] + ' ' + calendar.month_abbr[int(calmon1)] + ' ' + str(next_weekday1.day)
        else:
            caldays[i+6]=   calendar.day_abbr[i] + ' ' + calendar.month_abbr[int(calmon1)] + ' ' + str(next_weekday1.day)
        caldays[i]=   calendar.day_abbr[i] + ' ' + calendar.month_abbr[int(calmon0)] + ' ' + str(next_weekday0.day)
    # Create DateTime obj while we are here:
        datestr2=str(next_weekday2.month) + '/' + str(next_weekday2.day) + '/' + str(next_weekday2.year)
        datestr1=str(next_weekday1.month) + '/' + str(next_weekday1.day) + '/' + str(next_weekday1.year)
        datestr0=str(next_weekday0.month) + '/' + str(next_weekday0.day) + '/' + str(next_weekday0.year)
        caldt[i] = datetime.datetime.strptime(datestr0, '%m/%d/%Y')
        caldt[i+6] = datetime.datetime.strptime(datestr1, '%m/%d/%Y')
        caldt[i+12] = datetime.datetime.strptime(datestr2, '%m/%d/%Y')
    if thistype=='Trucking':
        for i in range(ndays):
            dloc=caldt[i]
            odata = Orders.query.filter(Orders.Date == dloc)
            j=0
            for data in odata:
                k=4*i+j
                daylist[k]=[data.Order, data.Pickup, data.Booking, data.Driver, data.Time, data.Jo, data.Container, data.Status]
                j=j+1

    if thistype=='Billing':
        for i in range(ndays):
            dloc=caldt[i]
            odata = Bills.query.filter(Bills.bDate == dloc)
            j=0
            for data in odata:
                k=4*i+j
                daylist[k]=[data.Company, data.bAmount, data.Account, data.Status]
                j=j+1

    return caldays,daylist


def calendar7_weeks(thistype,lweeks):
    today = datetime.datetime.today()
    nweeks=lweeks[0]+lweeks[1]
    ndays=nweeks*7
    day=today.day
    d = today
    nlist=ndays*4
    caldays=list(range(ndays))
    caldt=list(range(ndays))
    daylist=list(range(nlist))
    days_ahead=[0]*nweeks
    calmon=[0]*nweeks
    next_weekday=[0]*nweeks
    datestr=[0]*nweeks

    for i in range(ndays):
        for j in range(4):
            k=4*i+j
            daylist[k]=0

    for i in range(7):
        days_ahead1 = i - 7 - d.weekday()
        if days_ahead1 <= 0:
            days_ahead1 += 7
        day0=days_ahead1-7*lweeks[0]
        for m in range(nweeks):
            days_ahead[m]=day0+7*m
            next_weekday[m] = d + datetime.timedelta(days_ahead[m])
            calmon[m]=str(next_weekday[m].month)
            caldays[i+7*m]=   calendar.day_abbr[i] + ' ' + calendar.month_abbr[int(calmon[m])] + ' ' + str(next_weekday[m].day)
            datestr[m]=str(next_weekday[m].month) + '/' + str(next_weekday[m].day) + '/' + str(next_weekday[m].year)
            caldt[i+7*m] = datetime.datetime.strptime(datestr[m], '%m/%d/%Y')

        if next_weekday[lweeks[0]].day==day:
            caldays[i+7*lweeks[0]]=   'X' + calendar.day_abbr[i] + ' ' + calendar.month_abbr[int(calmon[lweeks[0]])] + ' ' + str(next_weekday[lweeks[0]].day)

    if thistype=='Trucking':
        weeksum=0
        for i in range(ndays):
            dloc=caldt[i]
            odata = Orders.query.filter(Orders.Date == dloc).all()
            for j,data in enumerate(odata):
                k=4*i+j
                shipper=data.Shipper
                if len(shipper)>8:
                    shipper=re.match(r'\W*(\w[^,. !?"]*)', shipper).groups()[0]
                loc1=Drops.query.filter(Drops.Entity==data.Company).first()
                loc2=Drops.query.filter(Drops.Entity==data.Company2).first()
                drv=Drivers.query.filter(Drivers.Name==data.Driver).first()

                if loc1 is not None:
                    addr11=loc1.Addr1
                    addr21=loc1.Addr2
                else:
                    addr11=''
                    addr21=''
                if loc2 is not None:
                    addr12=loc2.Addr1
                    addr22=loc2.Addr2
                else:
                    addr12=''
                    addr22=''
                if drv is not None:
                    phone=drv.Phone
                    trk=drv.Truck
                    plate=drv.Tag
                else:
                    phone=''
                    trk=''
                    plate=''

                cb=[]
                comlist=ChalkBoard.query.filter(ChalkBoard.Jo==data.Jo).all()
                for c in comlist:
                    addline=c.register_date.strftime('%m/%d/%Y')+' by '+c.creator+' at '+c.register_date.strftime('%H:%M')+': '+c.comments
                    addline=parselinenoupper(addline,85)
                    for a in addline:
                        cb.append(a)

                daylist[k]=[data.Order, data.Pickup, data.Booking, data.Driver, data.Time, data.Jo, data.Container, data.Status, shipper, data.id, data.Company, addr11, addr21, data.Company2, addr12, addr22, phone, trk, plate, cb]

    if thistype=='Moving':
        weeksum=0
        for i in range(ndays):
            dloc=caldt[i]
            odata = Moving.query.filter(Moving.Date == dloc).all()
            for j,data in enumerate(odata):
                k=4*i+j
                shipper=data.Shipper
                if len(shipper)>8:
                    shipper=re.match(r'\W*(\w[^,. !?"]*)', shipper).groups()[0]
                loc1=Drops.query.filter(Drops.Entity==data.Drop1).first()
                loc2=Drops.query.filter(Drops.Entity==data.Drop2).first()
                drv=Drivers.query.filter(Drivers.Name==data.Driver).first()

                if loc1 is not None:
                    addr11=loc1.Addr1
                    addr21=loc1.Addr2
                else:
                    addr11=''
                    addr21=''
                if loc2 is not None:
                    addr12=loc2.Addr1
                    addr22=loc2.Addr2
                else:
                    addr12='NF'
                    addr22='NF'
                if drv is not None:
                    phone=drv.Phone
                    trk=drv.Truck
                    plate=drv.Tag
                else:
                    phone=''
                    trk=''
                    plate=''

                cb=[]
                comlist=ChalkBoard.query.filter(ChalkBoard.Jo==data.Jo).all()
                for c in comlist:
                    addline=c.register_date.strftime('%m/%d/%Y')+' by '+c.creator+' at '+c.register_date.strftime('%H:%M')+': '+c.comments
                    addline=parselinenoupper(addline,85)
                    for a in addline:
                        cb.append(a)

                daylist[k]=[data.id, data.Jo, shipper, data.Drop1, addr11, addr21, data.Time, data.Drop2, addr12, addr22, data.Time2, data.Container, data.Driver, data.Status, phone, trk, plate, cb]




    if thistype=='Overseas':
        weeksum=0
        for i in range(ndays):
            dloc=caldt[i]
            odata = OverSeas.query.filter(OverSeas.PuDate==dloc).all()
            for j,data in enumerate(odata):
                k=4*i+j
                shipper=data.BillTo
                if len(shipper)>8:
                    shipper=re.match(r'\W*(\w[^,. !?"]*)', shipper).groups()[0]

                pod=data.Pod
                pol=data.Pol
                if len(pod)>8:
                    pod=re.match(r'\W*(\w[^,. !?"]*)', pod).groups()[0]
                if len(pol)>8:
                    pol=re.match(r'\W*(\w[^,. !?"]*)', pol).groups()[0]

                container=data.Container
                book=data.Booking
                bdat=Bookings.query.filter(Bookings.Booking==data.Booking).first()
                if bdat is not None:
                    doccut=bdat.PortCut.strftime('%m/%d/%Y')
                else:
                    doccut=''
                cb=[]
                comlist=ChalkBoard.query.filter(ChalkBoard.Jo==data.Jo).all()
                for c in comlist:
                    addline=c.register_date.strftime('%m/%d/%Y')+' by '+c.creator+' at '+c.register_date.strftime('%H:%M')+': '+c.comments
                    addline=parselinenoupper(addline,85)
                    for a in addline:
                        cb.append(a)

                drv=Drivers.query.filter(Drivers.Name==data.Driver).first()
                if drv is not None:
                    phone=drv.Phone
                    trk=drv.Truck
                    plate=drv.Tag
                else:
                    phone=''
                    trk=''
                    plate=''

                daylist[k]=[data.id, shipper, book, container, pol, pod, data.Jo, data.Status, data.Driver, phone, trk, plate, doccut, cb]


    if thistype=='Horizon':
        weeksum=0
        for i in range(ndays):
            dloc=caldt[i]
            adata = db.session.query(Autos.Jo).distinct().filter(Autos.Date2==dloc)
            for j,data in enumerate(adata):
                cb=[]
                comlist=ChalkBoard.query.filter(ChalkBoard.Jo==data.Jo).all()
                for c in comlist:
                    addline=c.register_date.strftime('%m/%d/%Y')+' by '+c.creator+' at '+c.register_date.strftime('%H:%M')+': '+c.comments
                    addline=parselinenoupper(addline,85)
                    for a in addline:
                        cb.append(a)

                adat=Autos.query.filter(Autos.Jo==data.Jo).first()
                com=adat.TowCompany
                if com is None or com=='' or len(com)<2:
                    com='FIX'

                if adat is not None:
                    autolist=[]
                    allcars=Autos.query.filter(Autos.Jo==adat.Jo).all()
                    for car in allcars:
                        autolist.append([car.Year,car.Make,car.Model,car.VIN])


                try:
                    amt=adat.TowCost
                    amt=nononef(amt)
                    ncars=len(autolist)
                    amteach=amt/ncars
                    amteach=dollar(amteach)
                except:
                    amteach='0.00'
                    ncars=0

                k=4*i+j
                daylist[k]=[adat.id, com, adat.TowCost, adat.Status, autolist, cb, adat.Jo, amteach, ncars]

    if thistype=='Billing':
        adata= Accounts.query.all()
        sum=[0]*len(adata)
        weekly=[]
        weeksum=[0]*nweeks
        weekstop=6
        thisweek=0

        for i in range(ndays):
            dloc=caldt[i]
            odata = Bills.query.filter(Bills.bDate == dloc)
            j=0
            for data in odata:
                k=4*i+j

                billno='Bill'+str(data.id)
                cb=[]
                comlist=ChalkBoard.query.filter(ChalkBoard.Jo==billno).all()
                for c in comlist:
                    addline=c.register_date.strftime('%m/%d/%Y')+' by '+c.creator+' at '+c.register_date.strftime('%H:%M')+': '+c.comments
                    addline=parselinenoupper(addline,85)
                    for a in addline:
                        cb.append(a)

                daylist[k]=[data.id, data.Company, data.bAmount, data.pAccount, data.Status, data.bCat + ' ' + data.bType, data.bAccount, cb]
                for mm,adat in enumerate(adata):
                    if adat.Name == data.pAccount:
                        sum[mm]=sum[mm]+nononef(data.bAmount)
                j=j+1

            if i==weekstop:
                for mm,adat in enumerate(adata):
                    if sum[mm]>0:
                        weekly.append([adat.Name, sum[mm]])
                        sum[mm]=0
                weeksum[thisweek]=weekly
                weekly=[]
                thisweek=thisweek+1
                weekstop=weekstop+7

    return caldays,daylist,weeksum

#______________________________________________________________________________________________________________________________________________________________________________________________




def viewbuttons():
    match    =  request.values.get('Match')
    modify   =  request.values.get('Modify')
    vmod     =  request.values.get('Vmod')
    minvo    =  request.values.get('MakeI')
    mpack    =  request.values.get('MakeP')
    viewo     =  request.values.get('ViewO')
    viewi     =  request.values.get('ViewI')
    viewp     =  request.values.get('ViewP')
    print    =  request.values.get('Print')
    addE     = request.values.get('addentity')
    addS     = request.values.get('addservice')
    slim     = request.values.get('slim')
    stayslim = request.values.get('stayslim')
    unslim = request.values.get('unslim')
    limitptype = request.values.get('limitptype')
    returnhit = request.values.get('Return')
    deletehit = request.values.get('Delete')
    # hidden values
    update   =  request.values.get('Update')
    invoupdate = request.values.get('invoUpdate')
    emailnow = request.values.get('emailnow')
    emailinvo = request.values.get('emailInvo')
    newjob=request.values.get('NewJ')
    thisjob=request.values.get('ThisJob')
    recpay   = request.values.get('RecPay')
    hispay   = request.values.get('HisPay')
    recupdate = request.values.get('recUpdate')
    calendar=request.values.get('Calendar')
    calupdate=request.values.get('calupdate')
    return match,modify,vmod,minvo,mpack,viewo,viewi,viewp,print,addE,addS,slim,stayslim,unslim,limitptype,returnhit,deletehit,update,invoupdate,emailnow,emailinvo,newjob,thisjob,recpay,hispay,recupdate,calendar,calupdate


def get_ints():
    oder=request.values.get('oder')
    poof=request.values.get('poof')
    tick=request.values.get('tick')
    serv=request.values.get('serv')
    peep=request.values.get('peep')

    invo=request.values.get('invo')
    invooder=request.values.get('invooder')
    cache=request.values.get('cache')
    modlink =  request.values.get('passmodlink')

    oder=nonone(oder)
    poof=nonone(poof)
    tick=nonone(tick)
    serv=nonone(serv)
    peep=nonone(peep)

    invo=nonone(invo)
    invooder=nonone(invooder)
    cache=nonone(cache)
    modlink=nonone(modlink)

    return oder,poof,tick,serv,peep,invo,invooder,cache,modlink



def comporname(company,name):
    if company is None or company=='':
        nameout=name
    else:
        if len(company)<3:
            nameout=name
        else:
            nameout=company
    return nameout

def fullname(first,middle,last):
    if first is not None:
        nameout=first
    else:
        nameout=''
    if middle is not None:
        nameout=nameout+' '+middle
    if last is not None:
        nameout=nameout+' '+last
    if len(nameout)>55:
        nameout=first + ' ' + last
    return nameout

def address(addr1,addr2,addr3):
    street=addr1
    if addr3 is None or addr3=='':
        cityst=addr2
    else:
        if len(addr3)<5:
            cityst=addr2
    if addr2 is None or addr2=='':
        cityst=addr3
        if len(addr2)<3:
            cityst=addr3
    if addr2 and addr3:
        if len(addr2)>3 and len(addr3)>3:
            street=addr1 + ' ' + addr2
            cityst=addr3
    return street,cityst

def nononestr(input):
    if input is None or input =='None':
        output=''
    else:
        output=input
    return output

def containersout(datecut):
    idata=Interchange.query.filter((Interchange.Status=='Unmatched') & (Interchange.Date > datecut)).all()
    cout=[]
    for data in idata:
        cout.append(data.Container)

    return cout

def chassismatch(odat):
    con=odat.Container
    book=odat.Booking
    if 1==1:
        ticket1=Interchange.query.filter((Interchange.Release==book) | (Interchange.Container==con)).first()
        if ticket1 is not None:
            ticket2=Interchange.query.filter(((Interchange.Release==book) | (Interchange.Container==con)) & (Interchange.id != ticket1.id)).first()

        if ticket1 is not None and ticket2 is not None:
            date1=ticket1.Date
            date2=ticket2.Date
            if date1>date2:
                d1=date2
                d2=date1
            else:
                d1=date1
                d2=date2
            delta=d2-d1
            chassisdays=delta.days+1
            ticket1.Company=odat.Shipper
            ticket2.Company=odat.Shipper
            ticket1.Jo=odat.Jo
            ticket2.Jo=odat.Jo
            #Now check to see if a no-charge chassis was used...
            chas1 = ticket1.Chassis
            chas2 = ticket2.Chassis
            if chas1 == 'GBL' or chas2 == 'GBL':
                chassisdays = 0
                odat.BOL = 'GBL Chassis'
                odat.Chassis = 'GBL'
            odat.Container=ticket1.Container
            odat.Date=d1
            odat.Date2=d2
            db.session.commit()
        else:

            chassisdays=1
            d1=today
            d2=today

    return chassisdays,d1,d2




def global_inv(odata,odervec):
    #First create all the invoices for these specific jobs
    for oder in odervec:
        myo=Orders.query.get(oder)
        qty,d1,d2=chassismatch(myo)
        Invoices.query.filter(Invoices.Jo==myo.Jo).delete()
        myo.Status=stat_update(myo.Status,'1',1)
        db.session.commit()


    for oder in odervec:
        myo=Orders.query.get(oder)
        qty,d1,d2=chassismatch(myo)
        shipper=myo.Shipper
        jo=myo.Jo
        bid=myo.Bid
        lid=myo.Lid
        did=myo.Did
        cache=myo.Storage+1

        mys=Services.query.filter(Services.Service=='Chassis Fees').first()
        descript= 'Days of Chassis'
        price=float(mys.Price)
        chassis_amount=price*qty
        haul_amount=float(myo.Amount)
        total=haul_amount+chassis_amount
        input=Invoices(Jo=myo.Jo, SubJo=None, Pid=bid, Service=mys.Service, Description=descript, Ea=mys.Price, Qty=qty, Amount=chassis_amount, Total=total, Date=today, Original=None, Status='New')
        db.session.add(input)
        db.session.commit()
        descript= 'Order ' + myo.Order+ ' Line Haul '+ myo.Company + ' to ' + myo.Company2
        input=Invoices(Jo=myo.Jo, SubJo=None, Pid=bid, Service='Line Haul', Description=descript, Ea=myo.Amount, Qty=1, Amount=haul_amount, Total=total, Date=today, Original=None, Status='New')
        db.session.add(input)
        db.session.commit()
        #Now write out the invoice
        ldata=Invoices.query.filter(Invoices.Jo==myo.Jo).order_by(Invoices.Ea.desc()).all()
        pdata1=People.query.filter(People.id==myo.Bid).first()
        pdata2=Drops.query.filter(Drops.id==myo.Lid).first()
        pdata3=Drops.query.filter(Drops.id==myo.Did).first()
        import make_T_invoice
        make_T_invoice.main(myo,ldata,pdata1,pdata2,pdata3,cache,today,0)
        if cache>1:
            docref=f'tmp/{scac}/data/vInvoice/INV'+myo.Jo+'c'+str(cache)+'.pdf'
        else:
            docref=f'tmp/{scac}/data/vInvoice/INV'+myo.Jo+'.pdf'
        myo.Path=docref
        myo.Storage=cache
        db.session.commit()
# Now all the invoices are created.  Next pack them up and create a single master invoice.
    keydata=[0]*len(odervec)
    grandtotal=0
    for j, i in enumerate(odervec):
        odat=Orders.query.get(i)
        if j==0:
            pdata1=People.query.filter(People.id==odat.Bid).first()
            date1=odat.Date
            order=odat.Order
            date2=odat.Date2
        dtest1=odat.Date
        dtest2=odat.Date2
        if dtest1<date1:
            date1=dtest1
        if dtest2>date2:
            date2=dtest2
        idat=Invoices.query.filter(Invoices.Jo==odat.Jo).order_by(Invoices.Ea.desc()).first()
        keydata[j]=[odat.Jo, odat.Booking, odat.Container, idat.Total, ' For Global to Baltimore Seagirt']
        grandtotal=grandtotal+float(idat.Total)
        # put together the file paperwork

    file1=f'tmp/{scac}/data/vInvoice/P_' + 'test.pdf'
    cache2 = int(odat.Detention)
    cache2=cache2+1
    docref=f'tmp/{scac}/data/vInvoice/P_c'+str(cache2)+'_' + order + '.pdf'

    for j, i in enumerate(odervec):
        odat=Orders.query.get(i)
        odat.Location=docref
        db.session.commit()


    import make_TP_invoice
    make_TP_invoice.main(file1,keydata,grandtotal,pdata1,date1,date2)

    invooder=oder
    leftscreen=0
    leftsize=8
    modlink=0

    filegather=['pdfunite', addpath(file1)]
    for i in odervec:
        odat=Orders.query.get(i)
        filegather.append(addpath(odat.Path))

    filegather.append(addpath(docref))
    tes=subprocess.check_output(filegather)

    odat.Detention=cache2
    db.session.commit()

    return docref


def make_new_order():
    sdate = request.values.get('date')
    if sdate == '' or sdate == None:
        sdate = today.strftime('%Y-%m-%d')
    nextjo = newjo(jbcode, sdate)

    vals = ['shipper', 'order', 'bol', 'booking', 'container', 'pickup',
            'date', 'date2', 'amount', 'ctype', 'dropblock1', 'dropblock2', 'commodity', 'packing', 'seal', 'desc']
    a = list(range(len(vals)))
    for ix, vx in enumerate(vals):
        a[ix] = request.values.get(vx)

    bid = People.query.filter(People.Company == a[0]).first()
    if bid is not None:
        idb = bid.id
    else:
        idb = 0

    dropblock1 = a[10]
    dropblock2 = a[11]

    idl, newdrop1, company = testdrop(dropblock1)
    idd, newdrop2, company2 = testdrop(dropblock2)

    if idl == 0:
        company = dropupdate(dropblock1)
        newdrop1 = a[10]
        lid = Drops.query.filter(Drops.Entity == company).first()
        if lid is not None:
            idl = lid.id
        else:
            idl = 0

    if idd == 0:
        company2 = dropupdate(dropblock2)
        newdrop2 = a[11]
        did = Drops.query.filter(Drops.Entity == company2).first()
        if did is not None:
            idd = did.id
        else:
            idd = 0

    amt = d2sa(a[8])

    input = Orders(Status='00', Jo=nextjo, Load=None, Order=a[1], Company=company, Location=None, Booking=a[3],
                   BOL=a[2], Container=a[4],
                   Date=a[6], Driver=None, Company2=company2, Time=None, Date2=a[7], Time2=None, Seal=a[14],
                   Pickup=a[5], Delivery=None,
                   Amount=amt, Path=None, Original=None, Description=a[15], Chassis=None, Detention='0',
                   Storage='0', InvoTotal=amt,
                   Release=0, Shipper=a[0], Type=a[9], Time3=None, Bid=idb, Lid=idl, Did=idd, Label='FileUpload',
                   Dropblock1=newdrop1, Dropblock2=newdrop2, Commodity=a[12], Packing=a[13], Links=None, Hstat=0, Istat=0,
                   Proof=None,Invoice=None,Gate=None,Package=None,Manifest=None,Scache=0,Pcache=0,Icache=0,Mcache=0,
                   Pkcache=0, QBi=0)
    db.session.add(input)
    db.session.commit()

    odat = Orders.query.filter(Orders.Jo == nextjo).first()
    oid = odat.id
    print('madeneworder',oid,nextjo)
    return oid,nextjo


def make_new_bill():
    sdate = request.values.get('bdate')
    if sdate == '':
        sdate = today_str


    thiscomp = request.values.get('thiscomp')
    cdat = People.query.filter((People.Company == thiscomp) & (
            (People.Ptype == 'Vendor') | (People.Ptype == 'TowCo'))).first()
    if cdat is not None:
        acomp = cdat.Company
        cid = cdat.Accountid
        aid = cdat.id
        acdat = Accounts.query.filter(Accounts.id == cid).first()
        if acdat is not None:
            baccount = acdat.Name
            category = acdat.Category
            subcat = acdat.Subcategory
            descript = acdat.Description
            btype = acdat.Type
        else:
            category = 'NAY'
            subcat = 'NAY'
            descript = ''
            btype = ''
            baccount = ''
    else:
        acomp = None
        aid = None
        category = 'NAY'
        subcat = 'NAY'
        descript = ''
        btype = ''
        baccount = ''

    cco = request.values.get('ctype')
    if len(cco) != 1:
        cco = 'X'
    baccount = request.values.get('billacct')

    bamt = request.values.get('bamt')
    bamt = d2s(bamt)
    ddate = request.values.get('ddate')
    if ddate == '':
        ddate = today_str
    bdesc = request.values.get('bdesc')

    jbcode = cdata[10] + 'B'
    nextjo = newjo(jbcode, today_str)

    account = request.values.get('crataccount')

    print('sdate=',sdate)
    input = Bills(Jo=nextjo, Pid=aid, Company=acomp, Memo='', Description=bdesc, bAmount=bamt, Status='Unpaid',
                  Cache=0, Original=None,Ref='', bDate=sdate, pDate=today, pAmount='0.00', pMulti=None, pAccount=account, bAccount=baccount,
                  bType=btype,bCat=category, bSubcat=subcat, Link=None, User=None, Co=cco, Temp1=None, Temp2=None, Recurring=0,
                  dDate=ddate, pAmount2='0.00', pDate2=None, Code1=None, Code2=None, CkCache=0, QBi=0, iflag = 0, PmtList=None,
                             PacctList=None, RefList=None, MemoList=None, PdateList=None, CheckList=None, MethList=None)

    db.session.add(input)
    db.session.commit()
    bdat = Bills.query.filter(Bills.Jo == nextjo).first()

    return bdat.id, nextjo




ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def docuploader(dbase):
    err = []

    if dbase == 'bill':
        bill = request.values.get('bill')
        bill = nonone(bill)
        bdat = Bills.query.get(bill)
        if bdat is not None:
            base = bdat.Jo
            cache = bdat.Cache
        else:
            bill, jo = make_new_bill()
            bdat = Bills.query.get(bill)
            if bdat is not None:
                base = bdat.Jo
                cache = bdat.Cache

        file = request.files['sourceupload']
        if file.filename == '':
            err.append('No file selected for uploading')

        print(file.filename)

        if file and allowed_file(file.filename):
            name, ext = os.path.splitext(file.filename)
            filename1 = f'Source_{base}{ext}'
            filename2 = f'Source_{base}_c{str(cache)}.pdf'
            output1 = addpath(tpath(dbase,filename1))
            output2 = addpath(tpath(dbase,filename2))
            if ext != '.pdf':
                try:
                    file.save(output1)
                    with open(output2, "wb") as f:
                        f.write(img2pdf.convert(output1))
                    os.remove(output1)
                except:
                    filename2 = filename1
            else:
                file.save(output2)
            err.append(f'Source uploaded as {filename2}')
            bdat.Original = filename2
            bdat.cache = cache + 1
            db.session.commit()
        else:
            print('file not uploaded')
            err.append('Allowed file types are txt, pdf, png, jpg, jpeg, gif')
        return err, bill


    if dbase == 'oder':
        oder = request.values.get('passoder')
        oder = nonone(oder)
        print('docuploader oder value:',oder)
        odat = Orders.query.get(oder)
        if odat is not None:
            base = odat.Jo
            scache = odat.Scache
        else:
            oder, jo = make_new_order()
            odat = Orders.query.get(oder)
            if odat is not None:
                base = odat.Jo
                scache = odat.Scache

        file = request.files['sourceupload']
        if file.filename == '':
            err.append('No source file selected for uploading')

        if file and allowed_file(file.filename):
            name, ext = os.path.splitext(file.filename)
            filename1 = f'Source_{base}{ext}'
            filename2 = f'Source_{base}_c{str(scache)}.pdf'
            output1 = addpath(tpath(dbase,filename1))
            output2 = addpath(tpath(dbase,filename2))
            if ext != '.pdf':
                try:
                    file.save(output1)
                    with open(output2, "wb") as f:
                        f.write(img2pdf.convert(output1))
                    os.remove(output1)
                except:
                    filename2 = filename1
            else:
                file.save(output2)
            err.append(f'Source uploaded as {filename2}')
            odat.Original = filename2
            odat.Scache = scache + 1
            db.session.commit()
        else:
            err.append('Allowed file types are txt, pdf, png, jpg, jpeg, gif')

    if dbase == 'poof':
        oder = request.values.get('passoder')
        oder = nonone(oder)
        print('oder for proof upload:',oder)
        odat = Orders.query.get(oder)
        base = odat.Jo
        pcache = odat.Pcache

        file = request.files['proofupload']
        if file.filename == '':
            err.append('No file selected for uploading')

        print(file.filename)

        if file and allowed_file(file.filename):
            name, ext = os.path.splitext(file.filename)
            filename1 = f'Proof_{base}{ext}'
            filename2 = f'Proof_{base}_c{str(pcache)}.pdf'
            output1 = addpath(tpath(dbase,filename1))
            output2 = addpath(tpath(dbase,filename2))
            if ext != '.pdf':
                try:
                    file.save(output1)
                    with open(output2, "wb") as f:
                        f.write(img2pdf.convert(output1))
                    os.remove(output1)
                except:
                    filename2 = filename1
            else:
                file.save(output2)
            err.append(f'Proof uploaded as {filename2}')
            odat.Proof = filename2
            odat.Pcache = pcache + 1
            db.session.commit()
        else:
            print('file not uploaded')
            err.append('Allowed file types are txt, pdf, png, jpg, jpeg, gif')

    return err, oder

def dataget_T(thismuch, dlist, lbox):
    # 0=order,#2=interchange,#3=people/services
    today = datetime.date.today()
    stopdate = today-datetime.timedelta(days=180)
    odata = 0
    idata = 0
    fdata = 0
    if thismuch == '1':
        stopdate = today-datetime.timedelta(days=60)
        if dlist[0] == 'on':
            odata = Orders.query.filter(Orders.Date > stopdate).all()
        if dlist[2] == 'on':
            idata = Interchange.query.filter((Interchange.Date > stopdate) | (Interchange.Status == 'AAAAAA')).all()
        if lbox == 2:
            fdata = DriverAssign.query.filter((DriverAssign.Hours != None) & (DriverAssign.Date > stopdate)).all()
        elif lbox==1 or lbox==3 or lbox == 4:
            fdata = Trucklog.query.filter(Trucklog.Date > stopdate).all()
    elif thismuch == '2':
        stopdate = today-datetime.timedelta(days=120)
        if dlist[0] == 'on':
            odata = Orders.query.filter(Orders.Date > stopdate).all()
        if dlist[2] == 'on':
            idata = Interchange.query.filter((Interchange.Date > stopdate) | (Interchange.Status == 'AAAAAA')).all()
        if lbox == 2:
            fdata = DriverAssign.query.filter((DriverAssign.Hours != None) & (DriverAssign.Date > stopdate)).all()
        elif lbox==1 or lbox==3 or lbox == 4:
            fdata = Trucklog.query.filter(Trucklog.Date > stopdate).all()
    elif thismuch == '3':
        if dlist[0] == 'on':
            odata = Orders.query.filter(Orders.Istat<1).all()
        if dlist[2] == 'on':
            idata = Interchange.query.filter(
                (Interchange.Date > stopdate) | (Interchange.Status == 'AAAAAA')).all()
        if lbox == 2:
            fdata = DriverAssign.query.filter(DriverAssign.Hours != None).all()
        elif lbox==1 or lbox==3 or lbox == 4:
            fdata = Trucklog.query.all()
    elif thismuch == '4':
        if dlist[0] == 'on':
            odata = Orders.query.filter(Orders.Istat==1).all()
        if dlist[2] == 'on':
            idata = Interchange.query.filter(
                (Interchange.Date > stopdate) | (Interchange.Status == 'AAAAAA')).all()
        if lbox == 2:
            fdata = DriverAssign.query.filter(DriverAssign.Hours != None).all()
        elif lbox==1 or lbox==3 or lbox == 4:
            fdata = Trucklog.query.all()
    elif thismuch == '5':
        if dlist[0] == 'on':
            odata = Orders.query.filter( (Orders.Istat<4) & (Orders.Istat>1) ).all()
        if dlist[2] == 'on':
            idata = Interchange.query.filter(
                (Interchange.Date > stopdate) | (Interchange.Status == 'AAAAAA')).all()
        if lbox == 2:
            fdata = DriverAssign.query.filter(DriverAssign.Hours != None).all()
        elif lbox==1 or lbox==3 or lbox == 4:
            fdata = Trucklog.query.all()
    elif thismuch == '6':
        if dlist[0] == 'on':
            odata = Orders.query.filter( (Orders.Date > stopdate) & (Orders.Hstat==0) ).all()
        if dlist[2] == 'on':
            idata = Interchange.query.filter((Interchange.Date > stopdate) | (Interchange.Status != 'IO')).all()
        if lbox == 2:
            fdata = DriverAssign.query.filter(DriverAssign.Hours != None).all()
        elif lbox==1 or lbox==3 or lbox == 4:
            fdata = Trucklog.query.all()
    elif thismuch == '7':
        if dlist[0] == 'on':
            odata = Orders.query.filter( (Orders.Date > stopdate) & (Orders.Hstat==1) ).all()
        if dlist[2] == 'on':
            idata = Interchange.query.filter(
                (Interchange.Date > stopdate) | (Interchange.Status == 'AAAAAA')).all()
        if lbox == 2:
            fdata = DriverAssign.query.filter(DriverAssign.Hours != None).all()
        elif lbox==1 or lbox==3 or lbox == 4:
            fdata = Trucklog.query.all()
    else:
        if dlist[0] == 'on':
            odata = Orders.query.all()
        if dlist[2] == 'on':
            idata = Interchange.query.all()
        if lbox == 2:
            fdata = DriverAssign.query.all()
        elif lbox==1 or lbox==3 or lbox == 4:
            fdata = Trucklog.query.all()

    return odata, idata, fdata

def dataget_Q(thismuch):
    today = datetime.date.today()
    qdata = 0
    if thismuch == '1':
        stopdate = today-datetime.timedelta(days=10)
        qdata = Quotes.query.filter( (Quotes.Status != -1) & (Quotes.Date > stopdate) ).all()
    elif thismuch == '2':
        stopdate = today-datetime.timedelta(days=30)
        qdata = Quotes.query.filter( (Quotes.Status != -1) & (Quotes.Date > stopdate) ).all()
    elif thismuch == '3':
        qdata = Quotes.query.filter(Quotes.Status == 3).all()
    elif thismuch == '4':
        qdata = Quotes.query.filter(Quotes.Status == -1).all()
    elif thismuch == '5':
        qdata = Quotes.query.filter(Quotes.Status != -1).all()
    elif thismuch == '6':
        #print('thismuch6')
        qdata = Quotes.query.filter(Quotes.Status != -1).order_by(Quotes.id.desc()).limit(20).all()
    elif thismuch == '7':
        stopdate = today-datetime.timedelta(days=1)
        qdata = Quotes.query.filter( (Quotes.Status != -1) & (Quotes.Date > stopdate) ).all()
    else:
        stopdate = today - datetime.timedelta(days=10)
        qdata = Quotes.query.filter( (Quotes.Status != -1) & (Quotes.Date > stopdate) ).all()

    return qdata

def dataget_B(thismuch,co,vendmuch):
    today = datetime.date.today()
    acct = None
    if co is None:
        co = 'X'
    if thismuch is None:
        thismuch = '1'
    if vendmuch is None:
        vendmuch = 0
    if ':' in co:
        co, acct = co.split(':')
        print(co, acct)

    if co == 'X':
        if thismuch == '1':
            stopdate = today-datetime.timedelta(days=60)
            bdata = Bills.query.filter(Bills.bDate > stopdate).all()
        elif thismuch == '2':
            stopdate = today - datetime.timedelta(days=120)
            bdata = Bills.query.filter(Bills.bDate > stopdate).all()
        elif thismuch == '3':
            stopdate = today - datetime.timedelta(days=360)
            bdata = Bills.query.filter(Bills.bDate > stopdate).all()
        else:
            bdata = Bills.query.all()
    else:
        if thismuch == '1': stopdate = today-datetime.timedelta(days=60)
        elif thismuch == '2': stopdate = today-datetime.timedelta(days=120)
        elif thismuch == '3': stopdate = today - datetime.timedelta(days=360)
        else: stopdate = today - datetime.timedelta(days=700)

        if acct is None:
            bdata = Bills.query.filter((Bills.Co.contains(co)) & (Bills.bDate > stopdate)).all()
        else:
            bdata = Bills.query.filter( (Bills.Co.contains(co)) & (Bills.bDate > stopdate) & (Bills.pAccount == acct) ).all()

    if vendmuch == 0 or vendmuch == '4': vdata = People.query.filter((People.Ptype == 'Vendor') | (People.Ptype == 'TowCo') ).order_by(People.Company).all()
    if vendmuch == '1':vdata = People.query.filter(People.Ptype == 'Vendor').order_by(People.Company).all()
    if vendmuch == '2':vdata = People.query.filter(People.Ptype == 'TowCo').order_by(People.Company).all()
    if vendmuch == '3':vdata = People.query.filter(People.Ptype == 'TowCo').order_by(People.Company).all()

    return bdata,vdata


def erud(err):
    errup = ''
    for e in err:
        if len(e) > 0:
            errup = errup + e.strip() + '\n'
    if len(errup)<1:
        errup = 'All is Well'
    return errup


def getdatevec(d1, d2, driver, deftrk):
    dvec = [d1]
    d1 = datetime.datetime.strptime(d1, '%Y-%m-%d')
    dwvec = [d1.strftime('%a')]
    d2 = datetime.datetime.strptime(d2, '%Y-%m-%d')

    # Get driver data, either from past record or from default
    dat = DriverAssign.query.filter((DriverAssign.Driver == driver) & (DriverAssign.Date == d1)).first()
    tat1 = Trucklog.query.filter( (Trucklog.Date == d1) & (Trucklog.DriverStart==driver) ).first()
    tat2 = Trucklog.query.filter( (Trucklog.Date == d1) & (Trucklog.DriverEnd==driver) ).first()
    if dat is None and tat1 is None:
        if d1.strftime('%a') == 'Sat' or d1.strftime('%a') == 'Sun':
            tsvec = ['None']
            tevec = ['None']
        else:
            tsvec = [deftrk]
            tevec = [deftrk]
    else:
        if dat is not None:
            tsvec = [dat.UnitStart]
            tevec = [dat.UnitStop]
        elif tat1 is not None:
            tsvec = [tat1.Unit]
            if tat2 is not None:
                tevec = [tat2.Unit]
            else:
                tevec = [tat1.Unit]


    while d1 < d2:
        d1 = d1 + datetime.timedelta(1)
        dvec.append(d1.strftime('%Y-%m-%d'))
        dwvec.append(d1.strftime('%a'))

        dat = DriverAssign.query.filter((DriverAssign.Driver == driver) & (DriverAssign.Date == d1)).first()
        tat1 = Trucklog.query.filter((Trucklog.Date == d1) & (Trucklog.DriverStart == driver)).first()
        tat2 = Trucklog.query.filter((Trucklog.Date == d1) & (Trucklog.DriverEnd == driver)).first()
        if dat is None and tat1 is None:
            if d1.strftime('%a') == 'Sat' or d1.strftime('%a') == 'Sun':
                tsvec.append('None')
                tevec.append('None')
            else:
                tsvec.append(deftrk)
                tevec.append(deftrk)
        else:
            if dat is not None:
                tsvec.append(dat.UnitStart)
                tevec.append(dat.UnitStop)
            elif tat1 is not None:
                tsvec.append(tat1.Unit)
                if tat2 is not None:
                    tevec.append(tat2.Unit)
                else:
                    tevec.append(tat1.Unit)

    return dvec, dwvec, tsvec, tevec

def driver_assignments(lbox,holdvec):
    err=[]
    lupdate = request.values.get('LboxUpdate')

    thisdriver = request.values.get('thisdriver')
    print('thisdriver=',thisdriver)
    if thisdriver is None:
        holdvec[0] = 'Sam Ghanem'
    else:
        holdvec[0] = thisdriver

    thisdefault = request.values.get('truckdefault')
    if thisdefault is None:
        tdat = Drivers.query.filter(Drivers.Name==holdvec[0]).first()
        holdvec[1] = tdat.Truck
    else:
        tdat = Drivers.query.filter(Drivers.Name == holdvec[0]).first()
        tdat.Truck = thisdefault
        db.session.commit()
        holdvec[1] = thisdefault

    start = request.values.get('dstart')
    if isinstance(start,str):
        holdvec[2] = start
    else:
        holdvec[2] = today - datetime.timedelta(14)
        holdvec[2] = holdvec[2].strftime('%Y-%m-%d')

    stop = request.values.get('dfinish')
    if isinstance(stop,str):
        holdvec[3] = stop
    else:
        holdvec[3] = today_str

    print(start,stop)
    err.append(f'Ready to Update Logs for {holdvec[0]}')
    holdvec[4],holdvec[5],holdvec[6],holdvec[7] = getdatevec(holdvec[2],holdvec[3],holdvec[0],holdvec[1])

    #If ready to update then update the driving records:
    if lupdate is not None:
        for jx,d1 in enumerate(holdvec[4]):
            d1 = datetime.datetime.strptime(d1, '%Y-%m-%d')
            drv = holdvec[0]
            units = request.values.get('trks' + str(jx))
            unite = request.values.get('trke' + str(jx))
            tdat = DriverAssign.query.filter( (DriverAssign.Date==d1) & (DriverAssign.Driver==drv) ).first()
            if tdat is not None:
                tdat.UnitStart = units
                tdat.UnitStop = unite
                db.session.commit()
            else:
                if units is not None:
                    #Get the trucklog data for the Unit used:
                    input = DriverAssign(Date=d1,Driver=drv,UnitStart=units,UnitStop=unite,StartStamp=None,EndStamp=None,Hours=None,Miles=None,Status=0,Radius=None,Rloc=None)
                    db.session.add(input)
                    db.session.commit()

            tdat = DriverAssign.query.filter((DriverAssign.Date == d1) & (DriverAssign.Driver == drv)).first()
            tlog = Trucklog.query.filter( (Trucklog.Date == d1) & (Trucklog.Unit==units) ).first()
            if tlog is not None:
                tlog.DriverStart = drv
                tdat.StartStamp = tlog.GPSin
                tdat.Miles = tlog.Distance
                tdat.Radius = tlog.Rdist
                tdat.Rloc = tlog.Rloc
                db.session.commit()

            tlog = Trucklog.query.filter( (Trucklog.Date == d1) & (Trucklog.Unit==unite) ).first()
            if tlog is not None:
                tlog.DriverEnd = drv
                tdat.EndStamp = tlog.GPSout
                try:
                    diff = tdat.EndStamp - tdat.StartStamp
                    hours = diff.seconds/3600.0
                except:
                    hours = 0
                tdat.Hours = d2s(hours)
                db.session.commit()
        err.append(f'Successful Update for Driver {drv}')
        lbox=0
    return lbox,holdvec,err

def driver_payroll(lbox,holdvec):
    err=[]
    thispstart = 0
    thispstop = 0
    thisdriver = request.values.get('thisdriver')
    print('thisdriver=', thisdriver)
    if thisdriver is None:
        holdvec[0] = 'Sam Ghanem'
    else:
        holdvec[0] = thisdriver

    pstart = datetime.datetime(year=2019, month=1,day=7)
    pstarts = [pstart.strftime('%Y-%m-%d')]
    pstop = pstart + datetime.timedelta(13)
    pstops = [pstop.strftime('%Y-%m-%d')]
    for ix in range(50):
        pstart = pstart+datetime.timedelta(14)
        pstop = pstart+datetime.timedelta(13)
        pstarts.append(pstart.strftime('%Y-%m-%d'))
        pstops.append(pstop.strftime('%Y-%m-%d'))

    ichange = 0
    for jx,d1 in enumerate(pstarts):
        d1 = datetime.datetime.strptime(d1, '%Y-%m-%d')
        d1 = d1.date()
        if d1>today and ichange==0:
            ichange=1
            thispstart = d1
            thispstop = d1+datetime.timedelta(13)
            thispstart=thispstart.strftime('%Y-%m-%d')
            thispstop = thispstop.strftime('%Y-%m-%d')
            holdvec[1] = jx-1

    thispaycycle = request.values.get('paycycle')
    if thispaycycle is not None:
        thispaycycle = nonone(thispaycycle)
        pstart = pstarts[thispaycycle]
        pstop = pstops[thispaycycle]
        holdvec[1] = thispaycycle
    else:
        if thispstart !=  0:
            pstart = thispstart
        else:
            pstart = today_str
        if thispstop != 0:
            pstop = thispstop
        else:
            pstop = today_str

    update = request.values.get('UpdatePayroll')
    if update is not None:
        pstart = request.values.get('pstart')
        pstop = request.values.get('pstop')
        holdvec[7] = pstart
        holdvec[8] = pstop

    holdvec[2]=pstarts
    holdvec[3]=pstops

    #Now calculate payroll for the pay period
    plines=[]
    ptable='<table><thead><tr><th>Day</th><th align="center">Date</th><th align="center">Driver</th><th>Unit</th><th>Start</th><th>Unit</th><th>Stop</th><th>Hours</th></tr></thead><tbody>'
    tot1 = 0
    tot2 = 0
    d1 = datetime.datetime.strptime(pstart, '%Y-%m-%d')
    d1 = d1.date()
    wk1 = d1 + datetime.timedelta(6)
    a1 = d1.strftime('%a')
    d2 = datetime.datetime.strptime(pstop, '%Y-%m-%d')
    d2 = d2.date()
    while d1 < d2:
        dat = DriverAssign.query.filter( (DriverAssign.Driver==holdvec[0]) & (DriverAssign.Date==d1) ).first()
        if dat is not None:
            try:
                hours = float(dat.Hours)
            except:
                hours = 0.00
            t1 = str(dat.StartStamp)
            t2 = str(dat.EndStamp)
            try:
                t1 = t1[11:16]
            except:
                t1 = '0:00'
            try:
                t2 = t2[11:16]
            except:
                t2 = '0:00'

            if hours > 0.0:
                ptable=ptable+f'<tr><td>{a1}</td><td>{d1}&nbsp;</td><td>{holdvec[0]}</td><td>&nbsp;{dat.UnitStart}&nbsp;</td><td align="center">{t1}</td><td align="center">&nbsp;{dat.UnitStop}&nbsp;</td><td align="center">{t2}</td><td align="center">{dat.Hours}</td></tr>'
                if d1 <= wk1:
                    tot1 = tot1 + hours
                else:
                    tot2 = tot2 + hours

        d1 = d1 + datetime.timedelta(1)
        a1 = d1.strftime('%a')

    if tot1 > 40.0:
        ot1 = tot1 - 40.0
        tot1 = 40.0
    else:
        ot1 = 0.0

    if tot2 > 40.0:
        ot2 = tot2 - 40.0
        tot2 = 40.0
    else:
        ot2 = 0.0

    reg_hours = tot1 + tot2
    ot_hours = ot1 + ot2

    ptable=ptable+'</tbody></table>'
    plines.append(f'1st Week Summary: {d1s(tot1)} Regular Hours and {d1s(ot1)} OT')
    plines.append(f'2nd Week Summary: {d1s(tot2)} Regular Hours and {d1s(ot2)} OT')
    plines.append(f'Combined Summary: {d1s(reg_hours)} Regular Hours and {d1s(ot_hours)} OT')

    holdvec[4]=ptable
    holdvec[5]=plines

    err.append(f'Payroll Hours for Driver:{holdvec[0]}')
    return lbox,holdvec,err


def container_list(lbox,holdvec):
    today = datetime.date.today()
    stopdate = today-datetime.timedelta(days=20)
    err=[]
    comps = []
    tjobs = Orders.query.filter( (Orders.Hstat < 1) & (Orders.Date > stopdate) ).all()
    for job in tjobs:
        com = job.Shipper
        if com not in comps:
            comps.append(com)
    imlines='<br>'
    exlines='<br>'
    if len(comps) >= 1:
        for com in comps:
            tjobs = Orders.query.filter( (Orders.Hstat < 1) & (Orders.Shipper==com) & (Orders.Date > stopdate)).all()
            for ix,job in enumerate(tjobs):
                con = job.Container
                bk = job.Booking
                if con =='' or con == 'TBD':
                    if ix == 0:
                        exlines = exlines + f'<b>{com}</b><br>'
                    exlines = exlines + f'{bk}<br>'
                else:
                    if ix == 0:
                        imlines = imlines + f'<b>{com}</b><br>'
                    imlines = imlines + f'{con}<br>'

    holdvec[0] = imlines
    holdvec[1] = exlines
    err.append('Unpulled Import Container Last 20 Days')
    err.append('Unused Export Bookings Last 20 Days')

    return lbox, holdvec, err

def get_invo_data(invo, holdvec):
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')
    stopdate = today-datetime.timedelta(days=300)
    err=[]

    #Determine unique shippers:
    comps = []
    tjobs = Orders.query.filter( (Orders.Istat < 4) & (Orders.Date > stopdate) ).all()
    for job in tjobs:
        com = job.Shipper
        if com not in comps:
            comps.append(com)
    co = request.values.get('getaccount')
    holdvec[0] = co

    # If first time up there is not selection so set to todays date
    if co is None:
        holdvec[7] = today_str
    else:
        holdvec[7] = request.values.get('thisdate')

    #This is the relevant data for selection
    odata = Orders.query.filter((Orders.Shipper == co) & (Orders.Istat < 4) & (Orders.Istat > 1) & (Orders.Date > stopdate)).all()
    lenod = len(odata)
    if lenod < 1:
        if co is None:
            err.append('Choose Account to Receive Payments On')
        else:
            err.append(f'{holdvec[0]} has only uninvoiced orders')
    else:
        err.append(f'Showing invoices for {holdvec[0]}')
    holdvec[1] = odata
    holdvec[2] = comps

    thechecks = [0]*len(odata)
    amts = ['0.00']*len(odata)
    invts = ['0.00']*len(odata)
    runck = request.values.get('previewpay')
    update = request.values.get('updatepay')
    invotot = 0.0
    paytot = 0.0
    if runck is not None or update is not None:
        if runck is not None:
            err.append(f'Totaling Open Invoices for {holdvec[0]}')
        else:
            err.append(f'Recording Invoices for {holdvec[0]}')

        for jx,odat in enumerate(odata):

            #Make sure we have an invoice and get the invoice total if we do
            idat = Invoices.query.filter(Invoices.Jo == odat.Jo).first()
            if idat is not None:
                invototal = idat.Total
                invts[jx] = invototal
                amts[jx] = invototal

            ckon = request.values.get('oder'+str(odat.id))
            if ckon is not None:
                thechecks[jx]=1
                invotot = invotot + float(invts[jx])
                recthis = request.values.get('amount'+str(odat.id))
                try:
                    paytot = paytot+float(recthis)
                    amts[jx] = d2s(recthis)
                except:
                    err.append(f'Bad Amt Received JO {odat.Jo}')
                    amts[jx] = '0.00'
    else:
        #Need to get the invoice totals even on the first pass:
        for jx, odat in enumerate(odata):
            idat = Invoices.query.filter(Invoices.Jo == odat.Jo).first()
            if idat is not None:
                invototal = idat.Total
                invts[jx] = invototal
                amts[jx] = invototal

    holdvec[3] = thechecks
    holdvec[4] = d2s(invotot)
    holdvec[5] = d2s(paytot)
    holdvec[6] = amts
    holdvec[8] = request.values.get('thisref')
    holdvec[12] = invts
    print('amts=',amts)
    print(holdvec[7],holdvec[8])
    depmethod = request.values.get('paymethod')
    depref=None
    if depmethod is None:
        deps = ['Choose Pay Method First']
        acctdb = 'None'
        bank = None
    elif depmethod == 'Cash' or depmethod == 'Check':
        deps = ['Undeposited Funds']
        acctdb = 'Undeposited Funds'
        bank = None
    elif depmethod == 'Credit Card':
        acctdb = request.values.get('acctfordeposit')
        bank = acctdb
        deps = []
        acdata = Accounts.query.filter((Accounts.Type == 'Bank') & (Accounts.Description.contains('Merchant'))).all()
        for acd in acdata:
            deps.append(acd.Name)
    elif depmethod == 'Direct Deposit':
        acctdb = request.values.get('acctfordeposit')
        bank = acctdb
        depref = holdvec[8]
        #Get the account for deposit listing and the account for deposit selection:
        deps = []
        acdata = Accounts.query.filter( (Accounts.Type == 'Bank') | (Accounts.Type == 'Exch') ).all()
        for acd in acdata:
            deps.append(acd.Name)

    holdvec[9] = deps
    holdvec[14] = depmethod
    holdvec[10] = acctdb
    autodis = request.values.get('autodisbox')
    autodis = nonone(autodis)
    holdvec[11] = autodis

    # Enable Record button if all selections required are made
    try:
        paytotf = float(paytot)
        if paytotf > 0.0 and acctdb is not None:
            holdvec[13] = 1
            err.append('Record capability enabled')
        else:
            holdvec[13] = 0
            if co is not None:
                if paytotf == 0.00:
                    err.append('Choose Invoices to Receive Against')
                if acctdb is None:
                    err.append('Choose Account to Deposit Funds')
    except:
        holdvec[13] = 0

    if update is not None:
        err = []
        jolist = []
        #Apply the payments
        for jx, odat in enumerate(odata):
            if thechecks[jx]==1:
                invojo = odat.Jo

                if amts[jx] != '0.00':

                    # Begin Income Creation:
                    custref = holdvec[8]
                    recamount = amts[jx]
                    recdate = datetime.datetime.strptime(holdvec[7], '%Y-%m-%d')

                    incdat = Income.query.filter(Income.Jo == invojo).first()
                    if incdat is None:
                        err.append(f'Creating New Payment on Jo {invojo}')
                        paydesc = f'Received payment on Invoice {invojo}'

                        input = Income(Jo=odat.Jo, Account=acctdb, Pid=odat.Bid, Description=paydesc,
                                       Amount=recamount, Ref=custref, Date=recdate, Original=None,From=odat.Shipper,Bank=bank,Date2=recdate,Depositnum=depref)
                        db.session.add(input)
                        db.session.commit()

                    try:
                        rec = float(recamount)
                    except:
                        rec = 0.00
                    try:
                        owe = float(invts[jx])
                    except:
                        owe = 0.00

                    print('autodis=',autodis,rec,owe)
                    if autodis == 1 and rec < owe:
                        disamt = rec - owe
                        #Need to add a discounting invoice to zero out the balance
                        input = Invoices(Jo=invojo, SubJo=None, Pid=odat.Bid, Service='Discount', Description='Auto Discount',
                                         Ea=d2s(disamt), Qty=1, Amount=d2s(disamt), Total=d2s(rec), Date=today,
                                         Original=None, Status='P')
                        db.session.add(input)
                        db.session.commit()
                        #Adjust Invoice Totals for all Line Items on this Order:
                        ldata = Invoices.query.filter(Invoices.Jo == invojo).all()
                        for data in ldata:
                            data.Total = d2s(rec)
                            db.session.commit()
                        err.append(f'Info: Discount created for JO {odat.Jo} to balance invoice')
                        owe = 0.00

                    if rec < owe:
                        err.append(f'Warning: Payment for JO {odat.Jo} less than invoiced')
                    else:
                        ldata = Invoices.query.filter(Invoices.Jo == invojo).all()
                        for data in ldata:
                            data.Status = 'P'
                            db.session.commit()

                    hstat = odat.Hstat
                    if hstat == 2 or hstat == 3:
                        odat.Hstat = 4
                    odat.Istat = 4
                    db.session.commit()

                    jolist.append(invojo)
                    print(jx,invojo,jolist)
                    invo = 0

                else:
                    err.append(f'Have no Invoice to Receive Against for JO={invojo}')


        from gledger_write import gledger_multi_job
        gledger_multi_job('income',jolist,acctdb,0)




    return invo, holdvec, err

def Orders_Form_Update(oder):
    modata = Orders.query.get(oder)
    vals = ['order', 'bol', 'booking', 'container', 'pickup',
            'date', 'date2', 'amount', 'ctype', 'commodity', 'packing', 'seal', 'desc']
    a = list(range(len(vals)))
    for i, v in enumerate(vals):
        a[i] = stripper(request.values.get(v))
    shipper = request.values.get('shipper')
    modata.Shipper = shipper
    modata.Order = a[0]
    modata.BOL = a[1]
    modata.Booking = a[2]
    modata.Container = a[3]
    modata.Pickup = a[4]
    modata.Type = a[8]
    modata.Commodity = a[9]
    modata.Packing = a[10]
    modata.Seal = a[11]
    modata.Description = a[12]
    try:
        modata.Date = a[5]
    except:
        modata.Date = today
    try:
        modata.Date2 = a[6]
    except:
        modata.Date2 = today
    modata.Amount = d2s(a[7])
    try:
        modata.Label = f'{modata.Jo} {a[0]} {modata.Amount}'
    except:
        modata.Label = f'{modata.Jo}'
    db.session.commit()

def Orders_Drop_Update(oder):
    modata = Orders.query.get(oder)

    dropblock1 = request.values.get('dropblock1')
    dropblock2 = request.values.get('dropblock2')

    idl, newdrop1, company = testdrop(dropblock1)
    idd, newdrop2, company2 = testdrop(dropblock2)

    if idl == 0:
        company = dropupdate(dropblock1)
        newdrop1 = dropblock1
        lid = Drops.query.filter(Drops.Entity == company).first()
        idl = lid.id

    if idd == 0:
        company2 = dropupdate(dropblock2)
        newdrop2 = dropblock2
        did = Drops.query.filter(Drops.Entity == company2).first()
        idd = did.id

    modata.Company2 = company2
    modata.Company = company

    print(f'my new drop 2:{newdrop2}')
    modata.Dropblock2 = newdrop2
    modata.Dropblock1 = newdrop1
    bid = People.query.filter(People.Company == modata.Shipper).first()
    if bid is not None:
        modata.Bid = bid.id
    modata.Lid = idl
    modata.Did = idd

    hstat = modata.Hstat
    if hstat == -1:
        modata.Hstat = 0

    db.session.commit()

def loginvo_m(odat,ix):
    #if ix = 2 we are not emailing
    #if ix = 3 we ARE emailing
    from gledger_write import gledger_write
    alink = odat.Links
    print(ix,alink)
    if alink is not None:
        if 1 == 1:
            alist = json.loads(alink)
            for aoder in alist:
                aoder = nonone(aoder)
                thisodat = Orders.query.get(aoder)
                print(aoder,thisodat.Istat)
                jo = thisodat.Jo
                gledger_write('invoice', jo, 0, 0)
                thisodat.Istat = ix
                db.session.commit()
        if 1 == 2:
            odat.Links = None
            jo = odat.Jo
            gledger_write('invoice', jo, 0, 0)
            odat.Istat = ix
            db.session.commit()
    else:
        jo = odat.Jo
        gledger_write('invoice', jo, 0, 0)
        odat.Istat = ix
        db.session.commit()

def hv_capture(ilist):
    hvhere = [0]*18
    for ib,il in enumerate(ilist):
        hvhere[ib] = request.values.get(il)

    return hvhere

def get_def_bank(bdat):
    coo = bdat.Co
    pdat = Accounts.query.filter( (Accounts.Co == coo) & (Accounts.Type == 'Bank')).first()
    if pdat is not None:
        pacct = pdat.Name
    else:
        pacct = 'No Bank'
    print('The Paying Acct',pacct)
    return pacct



def get_tmap(atype, btype):
    print('atype is', atype)
    adat = Accttypes.query.filter(Accttypes.Name.contains(atype)).first()
    if adat is not None:
        ttype = stripper(adat.Taxtype)
    else:
        ttype = 'Not Tax Related'
    if atype== 'Expense' and btype == 'Direct':
        ttype = 'COGS'
    if ttype == 'Equity':
        ttype = 'Liabilities'
    print('ttype is',ttype)
    tdat = Taxmap.query.filter( (Taxmap.Category.contains(ttype)) | (Taxmap.Name.contains(ttype)) ).all()
    return tdat

def get_qmap(atype, btype):
    newatype=''
    print('qmap atype btype=', atype,btype)
    if atype == 'Expense' and btype == 'Direct':
        atype = 'Cost of Goods Sold'
    if 'asset' in atype.lower():
        atype = 'asset'
    qdat = QBaccounts.query.filter(QBaccounts.Type.contains(atype)).all()
    return qdat

def check_shared(co1,co2name, err):

    adat1 = Accounts.query.filter( (Accounts.Co == co1) & (Accounts.Name.contains('Due to')) & (Accounts.Name.contains(co2name)) ).first()
    if adat1 is not None:
        err.append(f'Account {adat1.Name} exists')
        return adat1.id, err
    else:
        #create the account:
        acctname = f'Due to {co2name}'
        acctdesc = f'Created automatically from account share setup'
        input = Accounts(Name=acctname, Balance=0.00, AcctNumber=None, Routing=None, Payee=None,
                         Type='Current Liability', Description=acctdesc, Category='Liabilities', Subcategory='Current Liabilities',
                         Taxrollup=None, Co=co1, QBmap=None, Shared=None)
        db.session.add(input)
        db.session.commit()
        adatnew = Accounts.query.filter((Accounts.Co == co1) & (Accounts.Name.contains('Due to')) & (
            Accounts.Name.contains(co2name))).first()
        if adatnew is not None:
            err.append(f'Account {adatnew.Name} created successfully')
            return adatnew.id, err
        else:
            return 0, err.append('Problem with shared account creation')

def check_mirror_exp(co,oid,oName,err):
    adat = Accounts.query.filter( (Accounts.Co == co) & (Accounts.Name == oName) ).first()
    if adat is not None:
        err.append(f'Mirror account in code {co} exists: {adat.Name}')
        return adat.id, err
    else:
        #create the required account
        adat1 = Accounts.query.get(oid)
        acctdesc = 'Mirror account created automatically from share setup'
        input = Accounts(Name=oName, Balance=0.00, AcctNumber=None, Routing=None, Payee=None,
                         Type=adat1.Type, Description=acctdesc, Category=adat1.Category, Subcategory=adat1.Subcategory,
                         Taxrollup=adat1.Taxrollup, Co=co, QBmap=adat1.QBmap, Shared=None)
        db.session.add(input)
        db.session.commit()
        adatnew = Accounts.query.filter( (Accounts.Co == co) & (Accounts.Name == oName) ).first()
        if adatnew is not None:
            err.append(f'Account {adatnew.Name} created successfully')
            return adatnew.id, err
        else:
            return 0, err.append('Problem with shared account creation')

def enter_bk_charges(acct,bkch,date,username):
    from gledger_write import gledger_write
    recdate = datetime.datetime.strptime(date,"%Y-%m-%d")
    recdate = recdate.date()
    print(recdate, acct, bkch)
    bdat = Bills.query.filter( (Bills.Company == acct) & (Bills.bDate == recdate) ).first()
    bacct = 'Bank Service Charges'
    if bdat is None:
        adat = Accounts.query.filter(Accounts.Name == acct).first()
        co = adat.Co
        desc = f'Bank service fees on {date}'
        nextjo = newjo(co + 'B', date)
        input = Bills(Jo=nextjo, Pid=adat.id, Company=acct, Memo='', Description=desc, bAmount=bkch, Status='Paid', Cache=0,
                      Original=None,
                      Ref='', bDate=recdate, pDate=recdate, pAmount=bkch, pMulti=None, pAccount=acct, bAccount=bacct,
                      bType='Expense',
                      bCat='G-A', bSubcat="Bank Charges", Link=None, User=username, Co=co, Temp1=None, Temp2=None, Recurring=0,
                      dDate=today,
                      pAmount2='0.00', pDate2=None, Code1=None, Code2=None, CkCache=0, QBi=0, iflag = 0, PmtList=None,
                             PacctList=None, RefList=None, MemoList=None, PdateList=None, CheckList=None, MethList=None)
        db.session.add(input)
        db.session.commit()
        gledger_write('dircharge',nextjo,bacct,acct)
        return nextjo
    else:
        print(f'Have this bill {bdat.id} {bdat.Company}')
        return bdat.Jo

def monvals(iback):
    today = datetime.datetime.today()
    from datetime import date
    monnam = []

    monlist = [0, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    mon = today.month
    yer = today.year
    prev12 = []
    year12 = []
    dfr = []
    dto = []
    nmonths = iback
    for ix in range(nmonths + 1):
        if mon < 1:
            mon = 12
            yer = yer - 1
        prev12.append(mon)
        year12.append(yer)
        mid_month = mon - 1
        mid_yer = yer
        if mid_month == 0:
            mid_month = 12
            mid_yer = mid_yer - 1
        monnam.append(f'{monlist[mid_month]} {str(mid_yer)}')
        print(date(yer, mon, 1))
        dfr.append(date(yer, mon, 1))
        mon = mon - 1

    dto = dfr[0:nmonths]
    dfr = dfr[1:nmonths + 1]
    monnam = monnam[:iback]
    return monnam

def getmonths(acct,mback,mstart):
    dat = IEroll.query.filter(IEroll.Name.contains(acct)).first()
    if dat is None:
        dat = Broll.query.filter(Broll.Name.contains(acct)).first()
    dlist = []
    if mback > mstart:
        if dat is not None:
            for ix in range(mstart,mback+1):
                try:
                    amt = float(getattr(dat, f'C{ix}'))
                except:
                    amt = 0.00
                dlist.append(amt)
        return dlist
    else:
        if dat is not None:
            print('mstuffhere',mback,mstart)
            for ix in range(mstart-1,mback-1,-1):
                print(ix)
                dlist.append(float(getattr(dat, f'C{ix}')))
        return dlist

def ticket_copy(tick):
    myi = Interchange.query.get(tick)
    type = myi.Type
    if type == 'Load In':
        newtype = 'Empty Out'
    if type == 'Empty Out':
        newtype = 'Load In'
    if type == 'Empty In':
        newtype = 'Load Out'
    if type == 'Load Out':
        newtype = 'Empty In'

    input = Interchange(Container=myi.Container, TruckNumber=myi.TruckNumber, Driver=myi.Driver, Chassis=myi.Chassis,
                        Date=myi.Date, Release=myi.Release, GrossWt=myi.GrossWt,
                        Seals=myi.Seals, ConType=myi.ConType, CargoWt=myi.CargoWt,
                        Time=myi.Time, Status='AAAAAA', Original=' ', Path=' ', Type=newtype, Jo=myi.Jo,
                        Company=myi.Company, Other=str(tick))
    db.session.add(input)
    db.session.commit()
    myo = Interchange.query.filter(Interchange.Other==str(tick)).first()
    return myo.id



def street_this():
    sdata = StreetTurns.query.filter(StreetTurns.Status == 0).all()
    for sdat in sdata:
        sdat.Status = 1
        con = sdat.Container
        bk = sdat.BookingTo
        dt = sdat.Date
        lookback = dt - datetime.timedelta(30)
        #Original Out Container
        idat = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lookback) & (Interchange.Type.contains('Out'))).first()
        if idat is not None:
            tick = idat.id
            #Create New Match to Original.  Both Original Out and its Street Turn Match have **
            ctick = ticket_copy(tick)
            newcon = f'*{con}*'
            idat.Container = newcon
            idat.Status = 'IO'
            myi = Interchange.query.get(ctick)
            if myi is not None:
                myi.Container = newcon
                myi.Release = idat.Release
                myi.Status = 'IO'
                myi.Date = dt
                #Create New Interchange for Future Match, This has the street turn booking and street turn reuse date
                input = Interchange(Container=con, TruckNumber=myi.TruckNumber, Driver=myi.Driver,
                                    Chassis=myi.Chassis,
                                    Date=dt, Release=bk, GrossWt=myi.GrossWt,
                                    Seals=myi.Seals, ConType=myi.ConType, CargoWt=myi.CargoWt,
                                    Time=myi.Time, Status='AAAAAA', Original=' ', Path=' ', Type='Empty Out', Jo=None,
                                    Company=None, Other=None)
                db.session.add(input)

            odat = Orders.query.filter( (Orders.Container == con) & (Orders.Date > lookback) ).first()
            if odat is not None:
                odat.Container = newcon
        db.session.commit()

        # Now see if this container has already been returned and get those matched....
        idatret = Interchange.query.filter( (Interchange.Container == con) & (Interchange.Date > lookback) & (Interchange.Type.contains('In'))).first()
        if idatret is not None:
            idatret.Status = 'IO'
            idatret.Type = 'Load In'
            idatret.Release = bk
            idatout = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lookback) & (Interchange.Type.contains('Out'))).first()
            if idatout is not None:
                idatout.Status = 'IO'
                idatout.Company = idatret.Company
                idatout.Jo = idatret.Jo
                idatout.Release = bk
            db.session.commit()

def check_prep(bill_list):
    billready = 1
    linkcode = json.dumps(bill_list)
    total = 0.00
    err = []
    for bill in bill_list:
        bdat = Bills.query.get(bill)
        trans_type = bdat.bType
        total = total + float(bdat.bAmount)
        if trans_type == 'XFER':
            acct_to = bdat.Company
            acdat = Accounts.query.filter(Accounts.Name == acct_to).first()
            if acdat is None:
                err.append(f'Account {acct_to} has no Payee Listed for Check')
                billready = 0
            else:
                pdat = People.query.filter(People.Company == acdat.Payee).first()
                if pdat is None:
                    err.append(f'From account {acct_to} with Payee {acdat.Payee}')
                    err.append(f'Could not find company or person in database with name {acdat.Payee}')
                    billready = 0
        else:
            pdat = People.query.get(bdat.Pid)
            if pdat is None:
                err.append(f'Could not find company with ID {bdat.Pid}')
                billready = 0

        if billready == 1:
            if bdat.Status == 'Unpaid': bdat.Status = 'Paid'
            bdat.Link = linkcode
            db.session.commit()
    for bill in bill_list:
        bdat = Bills.query.get(bill)
        bdat.pAmount = bdat.bAmount
        bdat.pMulti = d2s(total)
    db.session.commit()

    return billready, err, linkcode

def check_multi_line(jo):
    bdat = Bills.query.filter(Bills.Jo == jo).first()
    err = []
    try:
        links = json.loads(bdat.Link)
    except:
        links = [bdat.id]
    total = 0.00
    nbills = len(links)
    if nbills > 1:
        for bill in links:
            bd = Bills.query.get(bill)
            bacct = bd.bAccount
            bjo = bd.Jo
            co = bjo[0]
            bd.Status = 'Paid'
            adat = Accounts.query.filter((Accounts.Name == bacct) & (Accounts.Co == co) ).first()
            aid = adat.id
            #Update the previous gledger entry for expense account if it has been modified
            gdat = Gledger.query.filter( (Gledger.Type == 'ED') & (Gledger.Tcode == bjo) ).first()
            if gdat is not None:
                gdat.Account = bacct
                gdat.Aid = aid
            else:
                err.append(f'Bill {bd.id} was never recorded')
            total = total + float(bd.pAmount)
            # Remove any previous payments to individual accounts as this check about to be paid for all
            Gledger.query.filter( (Gledger.Tcode == bjo) & (Gledger.Type == 'PD') ).delete()
            Gledger.query.filter( (Gledger.Tcode == bjo) & (Gledger.Type == 'PC') ).delete()
    else:
        total = float(bdat.pAmount)
    db.session.commit()
    return err, total, nbills

def check_inputs(bill_list):
    err = []
    bill = bill_list[0]
    bdat = Bills.query.get(bill)
    billfrom = bdat.Pid
    if not hasinput(bdat.pAccount): err.append('Need to specify the account to pay from')
    if not hasinput(bdat.Ref): err.append('Enter some value for the payment reference, either check number, epay, ach...etc')
    for bi in bill_list:
        bidat = Bills.query.get(bi)
        pid = bidat.Pid
        if pid != billfrom: err.append(f'Payee for transaction {bidat.Jo} does not match {bdat.Jo}')
    if err == []: err.append('All is Well')
    return err

def run_adjustments():
    from datetime import date
    from dateutil import relativedelta
    adata = Adjusting.query.filter(Adjusting.Status == 0).all()
    for adat in adata:
        date_from = adat.Date
        date_to = adat.DateEnd
        testdate = adat.Date
        mtest = testdate.month
        ytest= testdate.year
        nmonths = 0
        if testdate < date_to:
            while testdate < date_to:
                nmonths = nmonths + 1
                mtest = mtest + 1
                if mtest > 12:
                    mtest = 1
                    ytest = ytest + 1
                testdate = date(ytest, mtest, 1)

        print('nmonths=',nmonths)
        jo = adat.Jo
        mop = adat.Mop
        total_remain = float(adat.Amtp)
        month_from = date_from.month
        prem_per_day = float(adat.Amta)
        year_from = date_from.year
        year_this = date_from.year

        for ix in range (nmonths):
            jx = month_from + ix
            if jx > 12:
                jx = jx - 12
                year_this = year_from + 1
            if ix == 0 or ix == nmonths-1:
                if ix == 0: adj_date = date_from
                else: adj_date = date(year_this,jx,1)
                if ix == 0: end_date = last_day_of_month(date_from)
                else: end_date = date_to
            else:
                adj_date = date(year_this,jx,1)
                end_date = last_day_of_month(adj_date)

            delta = end_date - adj_date
            monthdays = delta.days + 1
            #To avoid rounding errors, set last month of use to the remaining amount to guarantee zero balance
            if ix == nmonths-1: month_amt = total_remain
            else: month_amt = prem_per_day * monthdays
            print(year_this,jx,adj_date, today)
            total_remain = total_remain - month_amt
            kdat = Adjusting.query.filter( (Adjusting.Jo == jo) & (Adjusting.Moa == jx) ).first()
            if kdat is None:
                input = Adjusting(Jo=jo,Date=adj_date,DateEnd=end_date,Mop=mop,Moa=jx,Asset=adat.Asset,Expense=adat.Expense,Amtp=d2s(total_remain),Amta=d2s(month_amt),Status=1)
                db.session.add(input)
                db.session.commit()

    from gledger_write import gledger_write
    gledger_write('adjusting',jo,adat.Expense,adat.Asset)





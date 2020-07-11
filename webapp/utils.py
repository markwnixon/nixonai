from webapp.CCC_system_setup import addpath, scac, tpath, companydata
from flask import request
import datetime
import calendar
import re
import os
import shutil
import subprocess
import img2pdf
import json

def requester(alist):
    areturn = ['0']*len(alist)
    for ix, al in enumerate(alist):
        areturn[ix] = request.values.get(al)
    return areturn

def hv_capture(ilist):
    hvhere = [0]*18
    for ib,il in enumerate(ilist):
        hvhere[ib] = request.values.get(il)

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

def hasvalue(input):
    if input is None:
        return 0
    elif isinstance(input,str):
        input = input.strip()
        if input == '' or input == 'None' or input == 'none' or input=='0':
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

def hasinput(input):
    if input is None:
        return 0
    elif isinstance(input,str):
        input = input.strip()
        if input == '' or input == 'None' or input == 'none':
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

def txtfile(infile):
    base=os.path.splitext(infile)[0]
    tf=base+'.txt'
    return tf

def commaguard(instring):
    sandwich=re.compile(r',[A-Za-z]')
    t1=sandwich.findall(instring)
    for t in t1:
        l=t[1]
        instring=instring.replace(t,', '+l)
    return instring

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

def nonone(input):
    try:
        output=int(input)
    except:
        output=0
    return output

def nononestr(input):
    if input is None or input=='None':
        output=' '
    else:
        output=input
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

def erud(err):
    errup = ''
    for e in err:
        if len(e) > 0:
            errup = errup + e.strip() + '\n'
    if len(errup)<1:
        errup = 'All is Well'
    return errup

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

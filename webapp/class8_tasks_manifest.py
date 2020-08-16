from flask import request
from webapp.models import People, Drops, Drivers, Vehicles

def makemanifest(modata):
    #pdata1:Bid (Bill To)
    #pdata2:Lid (Load At)
    #pdata3:Did (Delv To)

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.pagesizes import landscape
    from reportlab.platypus import Image
    from reportlab.lib.units import inch
    import csv
    import math
    import datetime
    import shutil
    from viewfuncs import parseline, parselinenoupper
    from CCC_system_setup import manfile, addpath, bankdata, scac

    #Adding the representataion in the subroutine:
    pid = modata.Bid
    pdata1 = People.query.get(pid)
    jtype = 'Trucking'
    print('drv', modata.Driver)
    drvdata = Drivers.query.filter(Drivers.Name == modata.Driver).first()
    if drvdata is None:
        drvdata = Drivers.query.filter(Drivers.id > 1).first()
    cache = modata.Mcache
    if cache is None:
        cache = 0
    commodity = modata.Commodity
    packing = modata.Packing
    bol = modata.BOL
    driver = modata.Driver
    truck = modata.Truck
    tdata = Vehicles.query.filter(Vehicles.Unit == truck).first()
    if tdata is None:
        tdata = Vehicles.query.filter(Vehicles.id > 1).first()


    joborder=modata.Jo
    #file1='static/vmanifest/Manifest'+joborder+'.pdf'
    #file2='static/vmanifest/Manifest'+joborder+'c'+str(cache)+'.pdf'
    file1, file2 ,file3 = manfile(joborder,cache)
    today = datetime.datetime.today().strftime('%m/%d/%Y')

    try:
        invodate = request.values.get('sigdate')
        invodate = datetime.datetime.strptime(invodate,'%Y-%m-%d')
        invodate = invodate.strftime('%m/%d/%Y')
        if invodate is None:
            invodate=today
    except:
        invodate = today

    qnote, note, bank, us, lab, logoi = bankdata('FC')


    def dollar(infloat):
        outstr='$'+"%0.2f" % infloat
        return outstr

    def catline(instring,j):
        if len(instring)>j:
            instring=instring[0:j-1]
        return instring


    def avg(in1,in2):
        out=(in1+in2)/2
        return out

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
        if input is None or input=='None':
            input=''
        return input

    def nonone(input):
        if input is None:
            input=0
        return input

    billto=list(range(5))
    if pdata1 is not None:
        billto[0]=comporname(pdata1.Company, fullname(pdata1.First, pdata1.Middle, pdata1.Last))
        billto[1]=nononestr(pdata1.Addr1)
        billto[2]=nononestr(pdata1.Addr2)
        billto[3]=nononestr(pdata1.Telephone)
        billto[4]=nononestr(pdata1.Email).lower()
    else:
        for i in range(5):
            billto[i]=' '

    for j,bill in enumerate(billto):
        billto[j]=catline(bill,25)

    if jtype=='Overseas':
        loadat=list(range(5))
        if pdata2 is not None:
            loadat[0]=comporname(pdata2.Company, fullname(pdata2.First, pdata2.Middle, pdata2.Last))
            loadat[1]=nononestr(pdata2.Addr1)
            loadat[2]=nononestr(pdata2.Addr2)
            loadat[3]=nononestr(pdata2.Telephone)
            loadat[4]=nononestr(pdata2.Email)
        else:
            for i in range(5):
                loadat[i]=' '

        shipto=list(range(5))
        if pdata3 is not None:
            shipto[0]=comporname(pdata3.Company, fullname(pdata3.First, pdata3.Middle, pdata3.Last))
            shipto[1]=nononestr(pdata3.Addr1)
            shipto[2]=nononestr(pdata3.Addr2)
            shipto[3]=nononestr(pdata3.Telephone)
            shipto[4]=nononestr(pdata3.Email)
        else:
            for i in range(5):
                shipto[i]=' '

    elif jtype=='Moving' or jtype=='Trucking':
        loadat=[' ']*5
        p2=modata.Dropblock1
        if p2 is not None:
            p2=p2.splitlines()
            for j,p in enumerate(p2):
                if j<5:
                    loadat[j]=p.title()

        shipto=[' ']*5
        p2=modata.Dropblock2
        if p2 is not None:
            p2=p2.splitlines()
            for j,p in enumerate(p2):
                if j<5:
                    shipto[j]=p.title()

    for j,bill in enumerate(shipto):
        shipto[j]=catline(bill,25)

    for j,bill in enumerate(loadat):
        loadat[j]=catline(bill,25)


    driver=str(drvdata.Name)
    truck=str(tdata.Unit)
    tag=str(tdata.Plate)

    if modata.Container is not None: container=str(modata.Container)
    else: container = ''
    if modata.Booking is not None: book=str(modata.Booking)
    else: booking = ''

    if jtype=='Trucking' or jtype=='Moving':
        order=str(modata.Order)
        pickup=str(modata.Pickup)
        date1=modata.Date
        date2=modata.Date2
        type=modata.Type
    else:
        order=str(modata.Booking)
        pickup=''
        date1=modata.PuDate
        date2=modata.RetDate
        type=modata.ContainerType

    seal=str(modata.Seal)

    try:
        date1s=date1.strftime('%m/%d/%Y')
    except:
        date1s='Nodate'
    try:
        date2s=date2.strftime('%m/%d/%Y')
    except:
        date2s='Nodate'

    #chassis='S019762'
    type=str(type)
    #deliver='82890104'
    loaddatetime=date1s
    deliverdatetime=date2s

    if '53' in type:
        labc='Trailer No.'
    else:
        labc='Container No.'


    line1=['SCAC', 'Driver', 'Truck #', 'Tag #', 'Size/Type', labc, 'Bill of Lading', 'Seal']
    line1a=[scac, driver, truck, tag, type, container, bol, seal]
    for j,item in enumerate(line1a):
        if item is None:
            line1a[j]=' '

    line2=['Biller Load/Order','Booking', 'Pickup/ShipperID', 'PU Date/Time', 'DEL Date/Time']
    line2a=[order, book, pickup, loaddatetime, deliverdatetime]
    line3=['Commodity and Units', 'Packaging and Description']
    line3a=[str(commodity), str(packing)]

    desclines = modata.Description
    if desclines is None:
        desclines = 'No description provided'

    note=list(range(4))
    note[0]='All appointments must be met.  If late the load may be refused or worked in without detention.'
    note[1]='If shipper and receiver addresses do not match BOL contact office immediately'
    note[2]='Dates for arrivals and departures are local.'
    note[3]='Dates, times, and estimates are given without any gurantee and are subject to change without prior notice.'

#___________________________________________________________


    ltm=36
    rtm=575
    ctrall=310
    left_ctr=170
    right_ctr=480
    dl=17.6
    tdl=dl*2
    hls=500
    t1=765
    t2=735
    m1=hls-dl
    m2=hls-2*dl
    m3=hls-3*dl
    m4=hls-4*dl
    m5=hls-5*dl
    m6=hls-6*dl
    m7=hls-7*dl

    m8=hls-18*dl
    m9=hls-23*dl
    m10=hls-27*dl
    fulllinesat=[m1, m2, m3, m4, m5, m6, m7, m8, m9, m10]
    width=rtm-ltm
    delta1=width/8
    p1=ltm+delta1-25
    p2=ltm+2*delta1+5
    p3=ltm+3*delta1-20
    p4=ltm+4*delta1-25
    p5=ltm+5*delta1-25
    p6=ltm+6*delta1
    p7=rtm-delta1+18
    sds1   =[p1,p2,p3,p4,p5,p6,p7]
    delta2=width/5
    n1=ltm+delta2
    n2=ltm+2*delta2
    n3=ltm+3*delta2
    n4=rtm-delta2
    sds2    =[n1,n2,n3,n4]
    bump=2.5
    tb=bump*2

    c=canvas.Canvas(file1, pagesize=letter)
    c.setLineWidth(1)

    c.drawImage(logoi, 185, 650, mask='auto')

    #Date and JO boxes
    dateline=m1+8.2*dl
    c.rect(rtm-150,m1+7*dl,150,2*dl,stroke=1,fill=0)
    c.line(rtm-150,dateline,rtm,dateline)
    c.line(rtm-75,m1+7*dl,rtm-75,m1+9*dl)

    #Top Box
    c.setLineWidth(1.5)
    c.rect(rtm,t2,ltm-rtm,30,stroke=1,fill=0)
    c.setFont('Helvetica-Bold',24,leading=None)
    c.drawCentredString(avg(rtm,ltm),t2+8,'Straight Bill of Lading')



    #Address boxes
    c.setLineWidth(1)
    ctm=218
    c.rect(ltm, m1+dl,175,5*dl, stroke=1, fill=0)
    c.rect(ctm, m1+dl,175,5*dl, stroke=1, fill=0)
    c.rect(rtm-175, m1+dl,175,5*dl, stroke=1, fill=0)
    level1=m1+5*dl
    c.line(ltm,level1,ltm+175,level1)
    c.line(ctm,level1,ctm+175,level1)
    c.line(rtm-175,level1,rtm,level1)

    cl1=m7-dl
    cl2=cl1-dl
    cl3=cl2-dl
    cl4=cl3-dl
    cl5=cl4-dl
    commfulllines=[cl1,cl2,cl3,cl4,cl5]

    for i in fulllinesat:
        c.line(ltm,i,rtm,i)
    for i in commfulllines:
        c.line(ltm,i,rtm,i)
    for k in sds1:
        c.line(k,m1,k,m3)
    for l in sds2:
        c.line(l,m3,l,m5)

    c.line(ctrall,m5,ctrall,cl1)

    c.line(ltm,t1,ltm,m10)
    c.line(rtm,t1,rtm,m10)

    #h1=avg(m6,m7)-3
    #c.line(q2,h1,rtm,h1)



    c.setFont('Helvetica',12,leading=None)

    c.drawCentredString(rtm-112.5,dateline+bump,'Date')
    c.drawCentredString(rtm-37.7,dateline+bump,'Job Order')


    c.drawString(ltm+bump*3,m1+5*dl+bump*2,'Bill To')
    c.drawString(ctm+bump*3,m1+5*dl+bump*2,'Load At')
    c.drawString(rtm-170+bump*2,m1+5*dl+bump*2,'Delv To')

    c.setFont('Helvetica',10,leading=None)

    ctr=[avg(ltm,p1),avg(p1,p2),avg(p2,p3),avg(p3,p4),avg(p4,p5),avg(p5,p6),avg(p6,p7),avg(p7,rtm)]
    for j, i in enumerate(line1):
        c.setFont('Helvetica-Bold',10,leading=None)
        c.drawCentredString(ctr[j],m2+tb,i)
        c.setFont('Helvetica',10,leading=None)
        c.drawCentredString(ctr[j],m3+tb,line1a[j])

    ctr=[avg(ltm,n1),avg(n1,n2),avg(n2,n3),avg(n3,n4),avg(n4,rtm)]
    for j, i in enumerate(line2):
        c.setFont('Helvetica-Bold',10,leading=None)
        c.drawCentredString(ctr[j],m4+tb,i)
        c.setFont('Helvetica',10,leading=None)
        c.drawCentredString(ctr[j],m5+tb,line2a[j])

    ctr=[avg(ltm,ctrall),avg(ctrall,rtm)]
    for j, i in enumerate(line3):
        c.setFont('Helvetica-Bold',10,leading=None)
        c.drawCentredString(ctr[j],m6+tb,i)
        c.setFont('Helvetica',10,leading=None)
        c.drawCentredString(ctr[j],m7+tb,line3a[j])
    dh=12
    ycoor = m7+tb - 2*dl
    xcoor = 40
    c.setFont('Helvetica-Bold',10,leading=None)
    c.drawString(xcoor,ycoor,'Special Instructions:')
    ycoor=ycoor-dl
    for desc in desclines.splitlines():
        c.drawString(xcoor,ycoor,desc)
        ycoor=ycoor-dl



    dh=12
    ct=305

    top=m1+9*dl-5
    for i in us:
        c.drawString(ltm+bump,top,i)
        top=top-dh

    bottomline=m9-23
    c.setFont('Helvetica-Bold',10,leading=None)
    j=0
    dh=11
    top=m8-dh
    c.drawString(ltm+tb,top,'Driver Notes:')
    c.setFont('Helvetica',10,leading=None)
    top=top-dh
    for i in note:
        c.drawString(ltm+tb,top,note[j])
        j=j+1
        top=top-dh



#_______________________________________________________________________
    #Insert data here
#_______________________________________________________________________

    c.setFont('Helvetica',11,leading=None)



    dh=13
    top=level1-dh
    lft=ltm+bump*3
    for i in billto:
        c.drawString(lft,top,i)
        top=top-dh

    top=level1-dh
    lft=ctm+bump*3
    for i in loadat:
        thisstr=parselinenoupper(i,35)
        for j in thisstr:
            c.drawString(lft,top,j)
            top=top-dh

    top=level1-dh
    lft=rtm-175+bump*3
    for i in shipto:
        c.drawString(lft,top,i)
        top=top-dh

    x=avg(rtm-75,rtm)
    y=dateline-dh-bump
    c.drawCentredString(x,y,joborder)
    x=avg(rtm-75,rtm-150)
    c.drawCentredString(x,y,invodate)


    total=0
    top=m4-dh

    x=ctrall+110
    y = cl5 - 2 * dl
    c.drawRightString(x,y,'Date:')
    c.drawString(x+20, y+bump, invodate)
    c.line(x+4,y,x+150,y)

    y=y-dl*1.5
    c.drawRightString(x,y,'   Arrival Time:')
    c.line(x+4,y,x+150,y)
    y=y-dl*1.5
    c.drawRightString(x,y,'Depart Time:')
    c.line(x+4,y,x+150,y)

    x=ltm+5
    c.drawString(x,y,'Received By:')
    c.line(x + 75, y, ctrall + 35, y)

    c.showPage()
    c.save()
    #
    #Now make a cache copy
    shutil.copy(file1,file2)
    print('returning file',file3)
    return file3

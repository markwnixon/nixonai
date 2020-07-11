from flask import session, logging, request
from webapp import db
from webapp.models import OverSeas, Orders, People, Invoices, Income, Interchange, Bills, Gledger
from flask import session, request
import datetime
import calendar
from webapp.viewfuncs import nonone, nononef, dollar, nodollar, d2s, numcheckvec
import datetime
from operator import itemgetter


def depositcalcs(odervec):
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    depositdata=[]
    jolist=[]

    for oder in odervec:
        myo = Gledger.query.get(oder)
        jo = myo.Tcode
        pid = int(myo.Sid)
        myc = People.query.get(pid)
        company = myc.Company
        amount = d2s(float(myo.Debit)/100.)
        print('For',jo,myo.Ref,company,amount)
        if jo not in jolist:
            depositdata.append([jo,company,myo.Ref,amount])
            jolist.append(jo)



    return depositdata

def incomecalcs():
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    start=datetime.datetime.strptime(sdate, '%Y-%m-%d')
    end=datetime.datetime.strptime(fdate, '%Y-%m-%d')
    incomedata=[]

    idata=Invoices.query.filter((Invoices.Date>=start) & (Invoices.Date<=end)).order_by(Invoices.Date).all()
    for idat in idata:
        date=idat.Date
        date=date.strftime('%Y-%m-%d')
        pid=idat.Pid
        pdat=People.query.get(pid)
        if pdat is not None:
            customer=pdat.Company
        else:
            customer='Unknown'
        status=idat.Status
        try:
            bit2=status[1]
        except:
            bit2=9
            srep='Unknown'
        srep='Unknown'
        if bit2==0:
            srep='Open, Uninvoiced'
        if bit2==1:
            srep='Open, Inv Created'
        if bit2==2:
            srep='Open, Inv Sent'
        if bit2==3:
            srep='Paid'

        incomedata.append([ date, idat.Jo, customer, idat.Service, idat.Status, dollar(idat.Amount) ])
    return incomedata


def ticketcalcs():
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    start=datetime.datetime.strptime(sdate, '%Y-%m-%d')
    end=datetime.datetime.strptime(fdate, '%Y-%m-%d')
    unmatched=[]

    idata=Interchange.query.filter((Interchange.Date>=start) & (Interchange.Date<=end)).filter(Interchange.Status!='IO').order_by(Interchange.Date).all()
    for idat in idata:
        date=idat.Date
        date=date.strftime('%Y-%m-%d')
        unmatched.append([date,idat.Release, idat.Container, idat.Type, idat.TruckNumber, idat.Driver])
    return unmatched


def jaycalcs():

    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    start=datetime.datetime.strptime(sdate, '%Y-%m-%d')
    end=datetime.datetime.strptime(fdate, '%Y-%m-%d')
    startdate=start.date()

    itemlist=[]
    truckjobs=[]
    oceanjobs=[]
    jayjobs=[]
    partjobs=[]
    jaypartjobs=[]
    yardmoves=[]
    conlist=[]

    def get_take(con):
        take=0
        type='J'
        move='deliver'
        cdata=Interchange.query.filter(Interchange.Container==con).all()
        for cdat in cdata:
            driver=cdat.Driver
            chassis=cdat.Chassis
            if "Khoder" in driver or "Jay" in driver:
                take=take+1
                odat=Orders.query.filter(Orders.Container==con).first()
                if odat is not None:
                    type='T'
                ndat=OverSeas.query.filter(OverSeas.Container==con).first()
                if ndat is not None:
                    type='O'
                if 'toll' in chassis.lower():
                    type='Y'
                    if move=='ym1toll1':
                        move='ym2toll2'
                    if move=='ym1':
                        move='ym2toll1'
                    if move=='deliver':
                        move='ym1toll1'
                if 'yard' in chassis.lower():
                    type='Y'
                    if move=='ym1toll1':
                        move='ym2toll1'
                    if move=='ym1':
                        move='ym2'
                    if move=='deliver':
                        move='ym1'
                print(con,chassis,move)

        return take, type, move

    def get_chassisdays(con):
        d1=None
        d2=None
        ticket1=Interchange.query.filter(Interchange.Container==con).first()
        try:
            ticket2=Interchange.query.filter((Interchange.Container==con) & (Interchange.id != ticket1.id)).first()
        except:
            ticket2 is None
            chassisdays=0
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

        return d1,d2,chassisdays

    def get_special(con):
        dispo='N'
        ticket=Interchange.query.filter(Interchange.Container==con).first()
        if ticket is not None:
            chassis=ticket.Chassis
            if 'yard' in chassis.lower():
                dispo='Y'
            if 'toll' in chassis.lower():
                dispo='T'
        return dispo

    def jay_special(con):
        dispo='N'
        booking='UNK'
        ticket=Interchange.query.filter(Interchange.Container==con).first()
        if ticket is not None:
            chassis=ticket.Chassis
            booking=ticket.Release
            if 'jay' in chassis.lower():
                dispo='J'
        return dispo,booking

    def jay_special2(con):
        dispo='N'
        booking='UNK'
        d1='None'
        ticket=Interchange.query.filter(Interchange.Container==con).first()
        if ticket is not None:
            chassis=ticket.Chassis
            booking=ticket.Release
            d1=ticket.Date
            if 'jay' in chassis.lower():
                dispo='J'
        return dispo,booking,d1




    idata=Interchange.query.filter((Interchange.Date>=start) & (Interchange.Date<=end)).filter((Interchange.Driver.contains("Khoder")) | (Interchange.Driver.contains("Jay"))).order_by(Interchange.Date).all()
    for idat in idata:
        if idat.Status=='IO':
            con=idat.Container
            take,type,move=get_take(con)

            if move=='deliver':
                if take==2 and con not in conlist:
                    conlist.append(con)
                    if type=='O':
                        oceanjobs.append(con)
                    if type=='T':
                        truckjobs.append(con)
                    if type=='J':
                        jayjobs.append(con)
                if take==1:
                    if type!='J':
                        partjobs.append(con)
                    else:
                        jaypartjobs.append(con)
            else:
                yardmoves.append(con)

    print('yard=',yardmoves)
    #Financial Calcs:Ocean containers
    total=0.00
    for con in oceanjobs:
        odat=OverSeas.query.filter(OverSeas.Container==con).first()
        d1,d2,chassisdays=get_chassisdays(con)
        if d1>=startdate:
            booking=odat.Booking
            explain='Ocean container warehouse + return'
            paytojay=500.00
            fromjay=0.00
            netpay=paytojay-fromjay
            total=total+netpay
            itemlist.append([d1.strftime('%m/%d/%Y'),d2.strftime('%m/%d/%Y'),booking,con,explain,nodollar(paytojay),str(chassisdays),nodollar(fromjay),nodollar(netpay)])

#Financial Calcs:Trucking with containers
    for con in truckjobs:
        odat=Orders.query.filter(Orders.Container==con).first()
        d1,d2,chassisdays=get_chassisdays(con)
        if d1>=startdate:
            order=odat.Order
            booking=odat.Booking
            company=odat.Shipper
            explain='Trucking job '+company
            contractamt=float(odat.Amount)
            paytojay=.8*contractamt
            if 'Global' not in explain:
                fromjay=30.0*chassisdays
            else:
                fromjay=0.00
            netpay=paytojay-fromjay
            total=total+netpay
            itemlist.append([d1.strftime('%m/%d/%Y'),d2.strftime('%m/%d/%Y'),booking,con,explain,nodollar(paytojay),str(chassisdays),nodollar(fromjay),nodollar(netpay)])

#Financial Calcs:Trucking with dry van
    odata=Orders.query.filter( (Orders.Date>=start) & (Orders.Date<=end) & (Orders.Driver.contains("Khoder")) & (Orders.Container.contains('53DV')) ).all()
    for odat in odata:
        d1=odat.Date
        d2=odat.Date2
        order=odat.Order
        booking=odat.Booking
        company=odat.Shipper
        explain='Dry van job '+company
        contractamt=float(odat.Amount)
        paytojay=.8*contractamt
        fromjay=0.00
        netpay=paytojay-fromjay
        total=total+netpay
        itemlist.append([d1.strftime('%m/%d/%Y'),d2.strftime('%m/%d/%Y'),order,con,explain,nodollar(paytojay),str(chassisdays),nodollar(fromjay),nodollar(netpay)])

#Financial Calcs:One way Items
    for con in partjobs:
        odat=Orders.query.filter(Orders.Container==con).first()
        if odat is not None:
            d1,d2,chassisdays=get_chassisdays(con)
            #d1=odat.Date
            #d2=odat.Date2
            if d1>=startdate:
                chassisday='None'
                order=odat.Order
                booking=odat.Booking
                company=odat.Shipper
                contractamt=float(odat.Amount)

                dispo=get_special(con)
                if dispo=='N':
                    explain='Half-trucking job'
                    paytojay=.5*contractamt
                if dispo=='Y':
                    explain='Move to Yard'
                    paytojay=50.00
                if dispo=='T':
                    explain='Reposition with Tolls'
                    paytojay=100.00

                fromjay=0.00
                netpay=paytojay-fromjay
                total=total+netpay
                itemlist.append([d1.strftime('%m/%d/%Y'),d2.strftime('%m/%d/%Y'),order,con,explain,nodollar(paytojay),str(chassisdays),nodollar(fromjay),nodollar(netpay)])

        ndat=OverSeas.query.filter(OverSeas.Container==con).first()
        if ndat is not None:
            d1=ndat.PuDate
            d2=ndat.RetDate
            try:
                d1s=d1.strftime('%m/%d/%Y')
            except:
                d1s='None'
            try:
                d2s=d2.strftime('%m/%d/%Y')
            except:
                d2s='None'
            booking=ndat.Booking
            dispo=get_special(con)
            if dispo=='N':
                explain='Half-warehouse job'
                paytojay=250.00
            if dispo=='Y':
                explain='Move to Yard'
                paytojay=50.00
            if dispo=='T':
                explain='Reposition with Tolls'
                paytojay=100.00
            fromjay=0.00
            netpay=paytojay-fromjay
            total=total+netpay
            itemlist.append([d1s,d2s,booking,con,explain,nodollar(paytojay),str(chassisdays),nodollar(fromjay),nodollar(netpay)])

    #Financial Calcs: Jay containers
    for con in jayjobs:
        d1,d2,chassisdays=get_chassisdays(con)
        if d1>=startdate:
            verify,booking=jay_special(con)
            explain='Jay job verified as: '+verify
            paytojay=0.00
            fromjay=30.00*chassisdays
            netpay=paytojay-fromjay
            total=total+netpay
            itemlist.append([d1.strftime('%m/%d/%Y'),d2.strftime('%m/%d/%Y'),booking,con,explain,nodollar(paytojay),str(chassisdays),nodollar(fromjay),nodollar(netpay)])

    #Financial Calcs: Jay part containers
    for con in jaypartjobs:
        verify,booking,d1=jay_special2(con)
        explain='Jay job missing ticket: '+verify
        paytojay=0.00
        chassisdays=6
        fromjay=30.00*chassisdays
        netpay=paytojay-fromjay
        total=total+netpay
        itemlist.append([d1.strftime('%m/%d/%Y'),d1.strftime('%m/%d/%Y'),booking,con,explain,nodollar(paytojay),str(chassisdays),nodollar(fromjay),nodollar(netpay)])


    for con in yardmoves:
        idat=Interchange.query.filter(Interchange.Container==con).first()
        booking=idat.Release
        take,type,move=get_take(con)
        d1,d2,chassisdays=get_chassisdays(con)
        if move =='ym2toll2':
            explain='Two yard moves 2 tolls'
            paytojay=150.00
        if move=='ym2toll1':
            explain='Two yard moves 1 toll'
            paytojay=125.00
        if move=='ym2':
            explain='Two yard moves each'
            paytojay=50.00
        if move=='ym1toll1':
            explain='Yard move with toll'
            paytojay=75.00
        if move=='ym1':
            explain='Yard move'
            paytojay=50.00
        chassisdays=0
        fromjay=0.00
        netpay=paytojay-fromjay
        total=total+netpay
        print('Here is:',booking,con,explain,move)
        itemlist.append([d1.strftime('%m/%d/%Y'),d1.strftime('%m/%d/%Y'),booking,con,explain,nodollar(paytojay),str(chassisdays),nodollar(fromjay),nodollar(netpay)])

    bitemlist=[]
    #Find expenses paid for Jay

    paymentlist=[]
    servicelist=[]
    #Financial Calcs:Income Credits to Jay, Items Jay Paid For
    odata=OverSeas.query.filter( (OverSeas.PuDate>=start) & (OverSeas.RetDate<=end) & (OverSeas.BillTo.contains("Jays")) ).all()
    for odat in odata:
        d1=odat.PuDate
        d2=odat.RetDate
        jo=odat.Jo
        booking=odat.Booking
        print('Booking',booking,jo)
        con=odat.Container
        chassisdays=''
        explain='Credit for Payments made: Overseas Shipping'
        idat=Income.query.filter(Income.Jo==jo).first()
        print(idat)
        if idat is not None:
            print('Found Income')
            paytojay=float(idat.Amount)
            fromjay=0.00
            netpay=paytojay-fromjay
            total=total+netpay
            paymentlist.append([d1.strftime('%m/%d/%Y'),d2.strftime('%m/%d/%Y'),booking,con,explain,nodollar(paytojay)])

        indat=Invoices.query.filter(Invoices.Jo==jo).first()
        if indat is not None:
            print('Found Invoices')
            explain2='Services Provided: Overseas Shipping'
            amount=float(indat.Total)
            servicelist.append([d1.strftime('%m/%d/%Y'),d2.strftime('%m/%d/%Y'),booking,con,explain2,nodollar(amount)])
            print(bitemlist)

    bdata=FELBills.query.filter( (FELBills.bDate>=start) & (FELBills.bDate<=end) & ((FELBills.Co=='J') | (FELBills.bCat=='JaysAuto')) ).order_by(FELBills.bDate).all()
    for data in bdata:
        print(data.bDate,data.Description,data.bAmount)
        bitemlist.append([data.bDate.strftime('%Y-%m-%d'),data.Description,data.bAmount])

    btotal=0.00
    l2=len(bitemlist)
    print('l2=',l2)
    for i in range(l2):
        newlist=bitemlist[i]
        amount=newlist[2]
        btotal=btotal+float(amount)
        print(amount,btotal)

    print(dollar(btotal))

    nettotal=total-btotal
    print(dollar(nettotal))

    return paymentlist,servicelist,itemlist,bitemlist,total,btotal,nettotal


def custcalcs(thiscomp):
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    thisday=datetime.date.today()
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    start=datetime.datetime.strptime(sdate, '%Y-%m-%d')
    end=datetime.datetime.strptime(fdate, '%Y-%m-%d')
    d2=None

    oceantype=request.values.get('dt1')
    trucktype=request.values.get('dt2')
    openbalrequest=request.values.get('dc6')

    keyname=['JO','Order','Booking','Container','BOL']
    plist=[50,65,65,70,60]
    keydataname=[]
    ptot=0.0
    pstops=[]
    for i in range(5):
        key=request.values.get('dc'+str(i+1))
        if key=='on':
            keydataname.append(keyname[i])
            ptot=ptot+plist[i]
            pstops.append(plist[i])
    tofromavail=220-(ptot-140)
    tfeach=round(tofromavail/12.0/.8)
    print(oceantype,trucktype)
    itemlist=[]
    print(trucktype,oceantype,start,end)
    if trucktype=='on':
        if thiscomp == 'ALLT':
            odata = Orders.query.filter((Orders.Date >= start) & (Orders.Date <= end)).order_by(Orders.Date).all()
        else:
            odata=Orders.query.filter( (Orders.Date>=start) & (Orders.Date<=end) & (Orders.Shipper==thiscomp) ).order_by(Orders.Date).all()
    elif oceantype=='on':
        odata=OverSeas.query.filter( (OverSeas.PuDate>=start) & (OverSeas.PuDate<=end) & (OverSeas.BillTo==thiscomp) ).order_by(OverSeas.PuDate).all()

    for odat in odata:
        if trucktype=='on':
            d1=odat.Date
            keydata_all=[odat.Jo,odat.Order,odat.Booking,odat.Container,odat.BOL]
        elif oceantype=='on':
            d1=odat.PuDate
            keydata_all=[odat.Jo,odat.MoveType,odat.Booking,odat.Container,odat.ContainerType]

        #keydata_all=[odat.Jo,odat.Order,odat.Booking,odat.Container,odat.BOL]
        keydata=[]
        for i in range(5):
            key=request.values.get('dc'+str(i+1))
            if key=='on':
                keydata.append(keydata_all[i])

        invodat=Invoices.query.filter(Invoices.Jo==odat.Jo).first()
        if invodat is not None:
            invoamt=invodat.Total
            d2=invodat.Date
            try:
                invof=float(invoamt)
            except:
                invof=0.00
        else:
            invof=0.00

        incodat=Income.query.filter(Income.Jo==odat.Jo).first()
        if incodat is not None:
            incoamt=incodat.Amount
            try:
                incof=float(incoamt)
            except:
                incof=0.00
        else:
            incof=0.00
        openf=invof-incof

        if trucktype=='on':
            loc1=odat.Company
            loc2=odat.Company2
            if thiscomp == 'ALLT':
                loc1 = odat.Shipper
                loc2 = odat.Company
                if 'seagirt' in loc2.lower(): loc2 = odat.Company2
        elif oceantype=='on':
            loc1=odat.Pol
            loc2=odat.Pod
        if 'port' in loc1.lower() or 'baltimore' in loc1.lower():
            loc1='Seagirt'
        if 'baltimore' in loc2.lower():
            loc2='Seagirt'
        if len(loc1)>tfeach:
            loc1=loc1[0:tfeach-1]
        if len(loc2)>tfeach:
            loc2=loc2[0:tfeach-1]
        loc1=loc1.title()
        loc2=loc2.title()
        print('openbalrequest=',openbalrequest,openf)
        if d2 is not None:
            d1=d2
        if openbalrequest=='on' and openf>0.0:
            delta=thisday-d1
            ndays=delta.days
            itemlist.append([d1.strftime('%m/%d/%Y')]+keydata+[loc1,loc2,nodollar(invof),str(ndays),nodollar(openf)])
        elif openbalrequest=='off' or openbalrequest is None:
            itemlist.append([d1.strftime('%m/%d/%Y')]+keydata+[loc1,loc2,nodollar(invof),nodollar(incof),nodollar(openf)])

        #itemlist.append([d1.strftime('%m/%d/%Y'),order,container,loc1,loc2,nodollar(invof),nodollar(incof),nodollar(openf)])
    if openbalrequest=='on':
        if thiscomp == 'ALLT':
            headerlist = ['InvoDate'] + keydataname + ['Company', 'Key-Loc', 'Invo$', 'Days', 'Open$']
        else:
            headerlist=['InvoDate']+keydataname+['From','To','Invo$','Days','Open$']
    else:
        headerlist=['InvoDate']+keydataname+['From','To','Invo$','Paid$','Open$']
    print('headerlist=',headerlist)
    itemlist=sorted(itemlist, key=itemgetter(0))

    return itemlist,headerlist,pstops

def plcalcs():
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    start=datetime.datetime.strptime(sdate, '%Y-%m-%d')
    end=datetime.datetime.strptime(fdate, '%Y-%m-%d')
    itemlist=[]
    limit=20
    #Need itemlist in date order and job type order: T,O,S,M
    invodat=Invoices.query.filter((Invoices.Date>=start) & (Invoices.Date<=end) & (Invoices.Jo.contains('FT')) ).order_by(Invoices.Date).all()
    for invo in invodat:
        jo=invo.Jo
        invoamt=float(invo.Amount)
        d1=invo.Date
        service=invo.Service
        odat=Orders.query.filter( Orders.Jo==jo ).first()
        if odat is not None:
            order=odat.Order
            container=odat.Container
            if '53D' in container:
                container='53DryV'
            loc1=odat.Company
            loc2=odat.Company2
            if len(loc1)>limit:
                loc1=loc1[0:limit-1]
            if len(loc2)>limit:
                loc2=loc2[0:limit-1]
            if container is None:
                container=='None'
        itemlist.append([d1.strftime('%m/%d/%Y'),'T',service,order,container,loc1,loc2,nodollar(invoamt)])

    invodat=Invoices.query.filter((Invoices.Date>=start) & (Invoices.Date<=end) & (Invoices.Jo.contains('FO')) ).order_by(Invoices.Date).all()
    for invo in invodat:
        jo=invo.Jo
        invoamt=float(invo.Amount)
        d1=invo.Date
        service=invo.Service
        odat=OverSeas.query.filter( OverSeas.Jo==jo ).first()
        if odat is not None:
            booking=odat.Booking
            container=odat.Container
            if container is not None:
                if '53D' in container:
                    container='53DryV'
            else:
                container='None'
            loc1=odat.Pol
            loc2=odat.Pod
            if len(loc1)>limit:
                loc1=loc1[0:limit-1]
            if len(loc2)>limit:
                loc2=loc2[0:limit-1]
            if container is None:
                container=='None'
        if service=='Towing':
            try:
                desc=invo.Description
                vin=desc.split('VIN:',1)[1]
                loc1=vin.strip()
                if len(loc1)>17:
                    loc1=loc1[0:16]
            except:
                loc1='NoVin'
        itemlist.append([d1.strftime('%m/%d/%Y'),'O',service,booking,container,loc1,loc2,nodollar(invoamt)])

    invodat=Invoices.query.filter((Invoices.Date>=start) & (Invoices.Date<=end) & (Invoices.Jo.contains('FS')) ).order_by(Invoices.Date).all()
    for invo in invodat:
        jo=invo.Jo
        invoamt=float(invo.Amount)
        d1=invo.Date
        service=invo.Service
        container=''
        loc2=invo.Description
        if len(loc2)>limit:
            loc2=loc2[0:limit-1]
        odat=Storage.query.filter( Storage.Jo==jo ).first()
        if odat is not None:
            loc1=odat.Company
            if len(loc1)>limit:
                loc1=loc1[0:limit-1]
        else:
            loc1='None'
        itemlist.append([d1.strftime('%m/%d/%Y'),'S',service,jo,container,loc1,loc2,nodollar(invoamt)])

    invodat=Invoices.query.filter((Invoices.Date>=start) & (Invoices.Date<=end) & (Invoices.Jo.contains('FM')) ).order_by(Invoices.Date).all()
    for invo in invodat:
        jo=invo.Jo
        invoamt=float(invo.Amount)
        d1=invo.Date
        service=invo.Service
        container=''
        loc2=invo.Description
        if len(loc2)>limit:
            loc2=loc2[0:limit-1]
        odat=Moving.query.filter( Moving.Jo==jo ).first()
        if odat is not None:
            loc1=odat.Shipper
            if len(loc1)>limit:
                loc1=loc1[0:limit-1]
        else:
            loc1='None'
        itemlist.append([d1.strftime('%m/%d/%Y'),'M',service,jo,container,loc1,loc2,nodollar(invoamt)])

    blist=[]
    categories=['Container','Towing','Fuel','Payroll','Rentals','Other']
    for cat in categories:
        bdata=FELBills.query.filter((FELBills.bDate>=start) & (FELBills.bDate<=end) & (FELBills.bClass.contains(cat)) & ((FELBills.bType=='Direct') | (FELBills.bType=='JobSp'))).order_by(FELBills.bDate).all()
        for bdat in bdata:
            bclass=bdat.bClass
            d1=bdat.bDate
            company=bdat.Company
            if len(company)>limit:
                company=company[0:limit-1]
            desc=bdat.Description
            desc=desc.replace('\n',' ')
            desc=desc.replace('\r','')
            desc=desc.strip()
            if len(desc)>limit+10:
                desc=desc[0:limit+9]
            bamount=float(bdat.bAmount)
            acct=bdat.Account
            blist.append([d1.strftime('%m/%d/%Y'),'D:'+cat,company,desc,acct,nodollar(bamount)])

    categories=['BldRent','BldRepMaint','Utilities','Adv-Mark','BankFees','Taxes','OfficeSupp','Insurance','ProfFees','Other']
    for cat in categories:
        bdata=FELBills.query.filter((FELBills.bDate>=start) & (FELBills.bDate<=end) & (FELBills.bType=='G-A') & (FELBills.bClass.contains(cat)) ).order_by(FELBills.bDate).all()
        for bdat in bdata:
            bclass=bdat.bClass
            d1=bdat.bDate
            company=bdat.Company
            if len(company)>limit:
                company=company[0:limit-1]
            desc=bdat.Description
            desc=desc.replace('\n',' ')
            desc=desc.replace('\r','')
            desc=desc.strip()
            if len(desc)>limit+10:
                desc=desc[0:limit+9]
            bamount=float(bdat.bAmount)
            acct=bdat.Account
            if len(acct)>12:
                acct=acct[0:11]
            blist.append([d1.strftime('%m/%d/%Y'),'I:'+cat,company,desc,acct,nodollar(bamount)])

    return itemlist,blist

from webapp import db
from webapp.models import OverSeas, Orders, People, Interchange, Bookings
from flask import session, request
from webapp.viewfuncs import d2s, stat_update, hasinput
import datetime
import pytz
from datetime import timedelta

my_datetime = datetime.datetime.now(pytz.timezone('US/Eastern'))
today = my_datetime.date()
now = my_datetime.time()
cutoff = today - datetime.timedelta(45)

def real_use(bk,bol):
    if hasinput(bk) and not hasinput(bol):
        return bk
    elif hasinput(bol) and not hasinput(bk):
        return bol
    elif hasinput(bk) and hasinput(bol):
        return bk
    else:
        return None

def InterStrip(id):
    data = Interchange.query.get(id)
    release=data.Release
    contain=data.Container
    chassis=data.Chassis
    if chassis is None:
        chassis='Own'
    if release is None:
        release='TBD'
    if contain is None:
        contain='TBD'
    release=release.strip()
    contain=contain.strip()
    chassis=chassis.strip()
    data.Release=release
    data.Container=contain
    data.Chassis=chassis
    db.session.commit()

def InterRestart():
    idata=Interchange.query.filter( (Interchange.Status != 'AAAAAA') ).all()
    for data in idata:
        data.Status='Unmatched'
        db.session.commit()

def InterMatchV2():
    kdata = db.session.query(Interchange.Container).distinct()
    for data in kdata:
        container=data.Container
        idat=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (~Interchange.Status.contains('IO')) & (Interchange.Container==container) ).first()
        if idat is not None:
            testid=idat.id
            type=idat.Type
            if 'In' in type:
                matcher='Out'
            else:
                matcher='In'
            mdat=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (~Interchange.Status.contains('IO')) & (Interchange.Type.contains(matcher)) & (Interchange.Container==container)).first()
            if mdat is not None:
                idat.Status='IO'
                mdat.Status='IO'
                db.session.commit()

def InterMatchThis(id):
    idat=Interchange.query.get(id)
    container=idat.Container
    release=idat.Release
    if not hasinput(container): container = 'Con TBD'
    if not hasinput(release): release = 'Bk TBD'
    type=idat.Type
    if 'In' in type:
        matcher='Out'
    else:
        matcher='In'
    mdat=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (~Interchange.Status.contains('IO')) & (Interchange.Type.contains(matcher)) & (Interchange.Container==container)).first()
    if mdat is not None:
        idat.Status='IO'
        mdat.Status='IO'
        db.session.commit()
    odat=Orders.query.filter( (Orders.Container==container) | (Orders.Booking==release) ).first()
    if odat is not None:
        hstat = odat.Hstat
        if hstat==0 and 'Out' in type:
            if(odat.Container)=='TBD':
                odat.Container=idat.Container
            odat.Hstat = 1
            db.session.commit()
        if hstat==1 and 'In' in type:
            odat.Hstat = 2
            db.session.commit()
    odat=OverSeas.query.filter( (OverSeas.Container==container) | (OverSeas.Booking==release) ).first()
    if odat is not None:
        status=odat.Status
        bit1=status[0]
        if bit1=='0' and 'Out' in type:
            if(odat.Container)=='TBD':
                odat.Container=idat.Container
            newstatus=stat_update(status,'1',0)
            odat.Status=newstatus
            db.session.commit()
        if bit1=='1' and 'In' in type:
            newstatus=stat_update(status,'2',0)
            odat.Status=newstatus
            db.session.commit()

def Remove_Dup_Jobs():
    odata=OverSeas.query.all()
    for odat in odata:
        container=odat.Container
        booking=odat.Booking
        tdat=Orders.query.filter( (Orders.Container==container) | (Orders.Booking == booking) ).first()
        if tdat is not None:
            Orders.query.filter(Orders.id == tdat.id).delete()
            #Now change any interchange tickets that may have wrong company data
            idata=Interchange.query.filter( (Interchange.Container==container)|(Interchange.Release==booking) ).all()
            for idat in idata:
                idat.Company = odat.BillTo
    db.session.commit()



def Match_Trucking_Now():
    odata=Orders.query.filter(Orders.Hstat < 2).all()
    for data in odata:
        container=data.Container
        if container is None:
            container='TBD'
        bk = data.Booking
        bol = data.BOL
        bk = real_use(bk,bol)
        if not hasinput(bk): bk = 'Book TBD'

        start_date = data.Date - timedelta(30)
        end_date = data.Date + timedelta(30)

        idata = Interchange.query.filter( (Interchange.Status == 'IO') & (Interchange.Date > start_date) & (Interchange.Date < end_date) & ((Interchange.Container == container) | (Interchange.Release == bk)) ).all()
        if idata is not None:
            for idat in idata:
                if data.Hstat < 2: data.Hstat = 2
                if container=='TBD': data.Container = idat.Container

                idat.Company = data.Shipper
                idat.Jo = data.Jo
                rel = idat.Release
                if not hasinput(rel):
                    idat.Release = bk
                if 'Out' in idat.Type:
                    data.Date = idat.Date
                if 'In' in idat.Type:
                    data.Date2 = idat.Date
                db.session.commit()

        else:
            idat = Interchange.query.filter( (Interchange.Date > start_date) & (Interchange.Date < end_date) & ((Interchange.Container == container) | (Interchange.Release == bk)) ).first()
            if idat is not None:
                if data.Hstat == 0: data.Hstat = 1
                if container=='TBD': data.Container = idat.Container
                idat.Company = data.Shipper
                idat.Jo = data.Jo
                rel = idat.Release
                if not hasinput(rel):
                    idat.Release = bk
                if 'Out' in idat.Type:
                    data.Date = idat.Date
                if 'In' in idat.Type:
                    data.Date2 = idat.Date
                db.session.commit()

def InterRematch():
    for data in kdata:
        container=data.Container
        idat=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (Interchange.Container==container) ).first()
        if idat is not None:
            testid=idat.id
            type=idat.Type
            if 'In' in type:
                matcher='Out'
            else:
                matcher='In'
            mdat=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (Interchange.Type.contains(matcher)) & (Interchange.Container==container)).first()
            if mdat is not None:
                idat.Status='IO'
                mdat.Status='IO'
                db.session.commit()

def InterDups():
    kdata = db.session.query(Interchange.Container).distinct()
    for data in kdata:
        container=data.Container
        idat=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (~Interchange.Status.contains('IO')) & (Interchange.Container==container) ).first()
        if idat is not None:
            testid=idat.id
            type=idat.Type
            if 'In' in type:
                matcher='Out'
            else:
                matcher='In'

            #Test if other tickets are duplicate to this one:
            dupdata=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (~Interchange.Status.contains('IO')) & (Interchange.id != testid) & (Interchange.Type==type) & (Interchange.Container==container)).all()
            for dup in dupdata:
                dup.Status='Dup'+str(testid)
                db.session.commit()

            #Test if this ticket is a duplicate to a match already made:
            dupdata2=Interchange.query.filter( (Interchange.Status.contains('IO')) & (Interchange.id!=testid) & (Interchange.Type==type) & (Interchange.Container==container)).first()
            if dupdata2 is not None:
                idat.Status='Dup to IO'+str(dupdata2.id)
                db.session.commit()

def InterDupThis(id):
    idat=Interchange.query.get(id)
    container=idat.Container
    testid=idat.id
    type=idat.Type

    #Test if ticket is a duplicate to other match eligible tickets:
    dupdata=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (~Interchange.Status.contains('IO')) & (Interchange.id != testid) & (Interchange.Type==type) & (Interchange.Container==container)).first()
    if dupdata is not None:
        idat.Status='Dup'+str(dupdata.id)
        db.session.commit()

    #Test if this ticket is a duplicate to a match already made:
    dupdata2=Interchange.query.filter( (Interchange.Status.contains('IO')) & (Interchange.id != testid) & (Interchange.Type==type) & (Interchange.Container==container)).first()
    if dupdata2 is not None:
        idat.Status='Dup to IO'+str(dupdata2.id)
        db.session.commit()



def Push_Overseas():
    kdata = db.session.query(Interchange.Container).distinct()
    for data in kdata:
        container=data.Container
        idat=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (~Interchange.Status.contains('Lock')) & (Interchange.Container==container) & (Interchange.Type.contains('Out')) ).first()
        if idat is not None:
            testid=idat.id
            type=idat.Type
            booking=idat.Release
            if not hasinput(booking): booking = 'Book TBD'

            odat=OverSeas.query.filter(OverSeas.Booking==booking).first()
            if odat is not None:
                odat.Container=container
                idat.Company=odat.BillTo
                idat.Jo=odat.Jo
                status=odat.Status
                bit1=status[0]
                if bit1=='0':
                    newstatus=stat_update(status,'1',0)
                    odat.Status=newstatus
                #See if there is a matching interchange ticket to update as well
                mdat=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (~Interchange.Status.contains('Lock')) & (Interchange.Container==container) & (Interchange.Type.contains('In')) ).first()
                if mdat is not None:
                    mdat.Company=odat.BillTo
                    mdat.Jo=odat.Jo
                    if bit1=='0' or bit1=='1':
                        newstatus=stat_update(status,'2',0)
                        odat.Status=newstatus

                db.session.commit()

def Push_Orders():
    kdata = db.session.query(Interchange.Container).distinct()
    for data in kdata:
        container=data.Container
        idat=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (~Interchange.Status.contains('Lock')) & (Interchange.Container==container) & (Interchange.Type.contains('Out')) ).first()
        if idat is not None:
            testid=idat.id
            type=idat.Type
            booking=idat.Release
            if not hasinput(booking): booking = 'Book TBD'

            odat=Orders.query.filter( (Orders.Booking==booking) | (Orders.Container==container) ).first()
            if odat is not None:
                idat.Company=odat.Shipper
                idat.Jo=odat.Jo
                release = idat.Release
                if not hasinput(release): idat.Release = odat.Booking
                hstat = odat.Hstat
                if hstat == 0:
                    odat.Hstat = 1
                db.session.commit()

                #See if there is a matching interchange ticket to update as well
                mdat=Interchange.query.filter( (Interchange.Status != 'AAAAAA') & (~Interchange.Status.contains('Lock')) & (Interchange.Container==container) & (Interchange.Type.contains('In')) ).first()
                if mdat is not None:
                    mdat.Company=odat.Shipper
                    mdat.Jo=odat.Jo
                    if hstat<2:
                        odat.Hstat=2
                    db.session.commit()

def seektaken(container,dstart):
    ocheck = Orders.query.filter((Orders.Container==container) & (Orders.Date>dstart) ).first()
    if ocheck is not None: return 1
    else: return 0

def Order_Container_Update(oder):

    odat = Orders.query.get(oder)
    bk = odat.Booking
    bol = odat.BOL
    container = odat.Container
    ht = odat.HaulType

    start_date = odat.Date - timedelta(30)
    end_date = odat.Date + timedelta(30)
    pulled = False
    returned = False
    jimport = False
    jexport = False

    if 'Import' in ht and hasinput(container):
        jimport = True
        idata = Interchange.query.filter( (Interchange.Date > start_date) & (Interchange.Date < end_date) & (Interchange.Container == container) ).all()
        for jx,idat in enumerate(idata):
            type =  idat.Type
            if 'Out' in type:
                ao = idat
                pulled = True
            if 'In' in type:
                ai = idat
                returned = True
    elif 'Export' in ht and hasinput(bk):
        jexport = True
        idata = Interchange.query.filter((Interchange.Date > start_date) & (Interchange.Date < end_date) & (Interchange.Release == bk)).all()
        for jx,idat in enumerate(idata):
            type =  idat.Type
            if 'Out' in type:
                ao = idat
                pulled = True
                bkout = idat.Release
                # Container may be returned under different booking
                pulled_container = idat.Container
                rdat = Interchange.query.filter( (Interchange.Date > start_date) & (Interchange.Date < end_date) & (Interchange.Container == pulled_container) & ( Interchange.Type.contains('In')) ).first()
                if rdat is not None:
                    returned = True
                    ai = rdat

    print(f'For sid {oder} we have container {container} and pulled is {pulled} and returned is {returned}')
    if pulled and not returned:
        odat.Hstat = 1
        ao.Company = odat.Shipper
        ao.Jo = odat.Jo
        odat.Date = ao.Date
        if odat.Istat < 0: odat.Istat = 0
        if jexport:
            odat.Container = ao.Container
        odat.Chassis = ao.Chassis
        odat.Type = ao.ConType
        db.session.commit()
    if returned:
        if not hasinput(container): odat.Container = ai.Container
        if odat.Istat < 0: odat.Istat = 0
        ai.Company = odat.Shipper
        ai.Jo = odat.Jo
        odat.Hstat = 2
        odat.Date2 = ai.Date
        if not hasinput(odat.Chassis): odat.Chassis = ai.Chassis
        if not hasinput(odat.Type): odat.Type = ai.ConType
        db.session.commit()

    if jexport and pulled and returned:
        if ao.Release != ai.Release:
            odat.Booking = ai.Release
            odat.BOL = ao.Release
        else:
            odat.BOL = ai.Release
        db.session.commit()


def PushJobsThis(id):

    idat=Interchange.query.get(id)
    testid=idat.id
    type=idat.Type
    booking=idat.Release
    container=idat.Container
    if not hasinput(booking): booking = 'Book TBD'
    if not hasinput(container): container = 'Con TBD'

    odat=OverSeas.query.filter(OverSeas.Booking==booking).first()
    if odat is not None:
        odat.Container=container
        idat.Company=odat.BillTo
        idat.Jo=odat.Jo
        release = idat.Release
        if not hasinput(release): idat.Release = odat.Booking

        status=odat.Status
        bit1=status[0]
        if bit1=='0' and 'Out' in type:
            newstatus=stat_update(status,'1',0)
            odat.Status=newstatus
        if 'Out' in type:
            odat.PuDate=idat.Date

        if (bit1=='1' or bit1=='0') and 'In' in type:
            newstatus=stat_update(status,'2',0)
            odat.Status=newstatus
        if 'In' in type:
            odat.RetDate=idat.Date

        db.session.commit()

    odat=Orders.query.filter( ( (Orders.Booking==booking) | (Orders.Container==container) ) & (Orders.Date > cutoff) ).first()
    if odat is not None:
        idat.Company=odat.Shipper
        idat.Jo=odat.Jo
        release = idat.Release
        if not hasinput(release): idat.Release = odat.Booking
        odat.Container=container
        hstat = odat.Hstat
        if hstat == 0 and 'Out' in type:
            odat.Hstat=1
        if 'Out' in type:
            odat.Date=idat.Date
        if hstat<2 and 'In' in type:
            odat.Hstat=2
        if 'In' in type:
            odat.Date2=idat.Date
        db.session.commit()


        #And also push back to Interchange in case several new bookings have been created
    odata=OverSeas.query.filter(OverSeas.Container=='TBD')
    for data in odata:
        container=data.Container
        company=data.BillTo
        booking=data.Booking
        idat=Interchange.query.filter((Interchange.Release==booking) & (Interchange.Status != 'AAAAAA') ).first()
        if idat is not None:
            data.Container=idat.Container
            idat.Company=company
            idat.Jo=data.Jo
            db.session.commit()





def InterMatchOld():
    idata = db.session.query(Interchange.Container).distinct()
    for data in idata:
        idat=Interchange.query.filter((Interchange.Container==data.Container) & (Interchange.Status != 'AAAAAA') & ( ~Interchange.Status.contains('IO') )).first()
        if idat is not None:
            stat1=idat.Container
            amatch=Interchange.query.filter( (Interchange.Container==stat1) & (Interchange.id != idat.id) & (Interchange.Status != 'AAAAAA') & ( ~Interchange.Status.contains('IO') )).all()
            t1=len(amatch)
            print('The length of the query is: ',t1)
            if t1==0:
                print('There is no match for Container: ',stat1)
                idat.Status='Unmatched'
                db.session.commit()
            elif t1==1:
                for match in amatch:
                    if ('In' in idat.Type and 'Out' in match.Type) or ('Out' in idat.Type and 'In' in match.Type):
                        print('The match is correct for Container: ',stat1,idat.id,idat.Status,match.id,match.Status,'will now become IO')
                        idat.Status='IO'
                        match.Status='IO'
                        db.session.commit()
                    else:
                        print('There are two containers, but mismatch in Type for Container: ',stat1)
                        keystatus='Mismatch'+str(idat.id)
                        match.Status=keystatus
                        idat.Status=keystatus
                        db.session.commit()
            elif t1>0:
                print('There are more than two Containers: ',stat1)
                idat.Status='Multimatch'+str(idat.id)
                db.session.commit()
                for match in amatch:
                    match.Status='Multimatch'+str(idat.id)
                    db.session.commit()

def Check_Sailing():

    odata=OverSeas.query.filter(OverSeas.Status != '999').all()
    for data in odata:
        status=data.Status
        bit1=int(status[0])
        if bit1<6:
            bdat=Bookings.query.filter(Bookings.Booking==data.Booking).first()
            if bdat is not None:
                date1=data.PuDate
                date2=bdat.SailDate
                date3=bdat.EstArr

                if today>date2 and today<date3:
                    bit1=3

                if today>date3:
                    bit1=4

                status=stat_update(status,str(bit1),0)
                print('For booking ',data.Booking, 'status= ',status)

                data.Status=status
                db.session.commit()

def Match_Ticket(oder,tick):
    myo = Orders.query.get(oder)
    myi = Interchange.query.get(tick)

    bk = myo.Booking
    bol = myo.BOL
    con = myi.Container
    bk = real_use(bk,bol)

    start_date = myi.Date - timedelta(30)
    end_date = myi.Date + timedelta(30)
    idata = Interchange.query.filter( (Interchange.Status == 'IO') & (Interchange.Date > start_date) & (Interchange.Date < end_date) & (Interchange.Container == con) ).all()

    myo.Container = myi.Container
    myo.Type = myi.ConType
    db.session.commit()

    if idata is not None:
        for idat in idata:
            idat.Company = myo.Shipper
            idat.Jo = myo.Jo
            rel = idat.Release
            if not hasinput(rel):
                idat.Release = bk
            if 'Out' in idat.Type:
                myo.Date = idat.Date
            if 'In' in idat.Type:
                myo.Date2 = idat.Date
            db.session.commit()
    else:
        myi.Company = myo.Shipper
        myi.Jo = myo.Jo
        rel = myi.Release
        if not hasinput(rel):
            myi.Release = bk
        db.session.commit()
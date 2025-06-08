from webapp import db
from webapp.models import Orders, Interchange, StreetTurns, Vehicles, Drivers, DriverAssign
import datetime
from flask import request
from webapp.class8_utils import *
from webapp.utils import *

today=datetime.date.today()

def checkon(con,bk):
    if not hasinput(con): con = ''
    if not hasinput(bk): bk = ''
    if con == 'TBD' or len(con) < 9:
        retcon = 'XXX'
    else:
        retcon = con
    if len(bk) < 6:
        retbk = 'YYY'
    else:
        retbk = bk
    return retcon, retbk

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
                        Time=myi.Time, Status='AAAAAA', Source=' ', Path=' ', Type=newtype, Jo=myi.Jo,
                        Company=myi.Company, Other=str(tick), TimeExit='', PortHours=None)
    db.session.add(input)
    db.session.commit()
    myo = Interchange.query.filter(Interchange.Other==str(tick)).first()
    return myo.id

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

def hoursbydriver(drivers, fdata):
    ddata = []
    s = '</h6></td><td align="center"><h6>'
    h = '</h5></th><th><h5>'
    for driver in drivers:
        thisdriver = driver.Name
        cdata = f'<table class="table"><thead><tr><th> <h5>Day {h} Date {h} Driver {h} Unit {h} Time {h} Unit {h} Time {h} Hours </h5></th></tr></thead><tbody>'
        tot = 0.0
        for fdat in fdata:
            if fdat.Driver == thisdriver:
                try:
                    hours = float(fdat.Hours)
                except:
                    hours = 0.00
                t1 = str(fdat.StartStamp)
                t2 = str(fdat.EndStamp)
                try:
                    t1 = t1[11:16]
                except:
                    t1 = '0:00'
                try:
                    t2 = t2[11:16]
                except:
                    t2 = '0:00'

                tot = tot + hours
                thisdate = fdat.Date
                d1 = thisdate.strftime('%Y-%m-%d')
                a1 = thisdate.strftime('%a')

                cdata = cdata + f'<tr><td align = "center"> <h6>{a1} {s} {d1} {s} {fdat.Driver} {s} {fdat.UnitStart} {s} {t1} {s} {fdat.UnitStop} {s} {t2} {s} {fdat.Hours} </h6></td></tr>'
        cdata=cdata + '</tbody></table>'
        ddata.append([thisdriver, d2s(tot), cdata])

    return ddata

def Street_Turn_task(err, holdvec, iter):
    #print(f'Running Street Turn task')
    holdvec = ['']*30
    holdvec[23] = 0

    if iter == 0:
        #print(f'Running Street Turn Task Info Colleciton with iter {iter} to place the window')
        completed = False

    elif iter > 0:
        #print(f'Running Street Turn Task with iter {iter}')
        completed = True
        container = request.values.get('container')
        booking = request.values.get('booking')
        dateturn = request.values.get('dateturn')
        #print(f'Creating street turn for {container} to {booking} on {dateturn}')
        if container is not None: container=container.strip()
        if booking is not None: booking=booking.strip()

        tdat = StreetTurns.query.filter(StreetTurns.Container==container).first()
        if tdat is not None:
            #Check to see if previously failed and Status is still set to zero
            if tdat.Status == 0:
                print(f'Street Turn Already Exists, but did not complete previously')
                StreetTurns.query.filter(StreetTurns.Container==container).delete()
                db.session.commit()
                tdat = StreetTurns.query.filter(StreetTurns.Container == container).first()
        if tdat is None:
            #print(f'Adding street turn for {container} to {booking} on {dateturn}')
            input = StreetTurns(Container=container, BookingTo=booking, Date=dateturn, Status=0)
            db.session.add(input)
            db.session.commit()
            err.append(f'Street Turn Created for {container} to {booking} on {dateturn}')

            sdat = StreetTurns.query.filter( (StreetTurns.Container == container) & (StreetTurns.Status == 0) ).first()
            if sdat is not None:
                #print(f'Manipulating street turn for {container} to {booking} on {dateturn} to *****')
                sdat.Status = 1
                con = sdat.Container
                bk = sdat.BookingTo
                dt = sdat.Date
                lookback = dt - datetime.timedelta(30)
                # Original Out Container
                idat = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lookback) & (Interchange.Type.contains('Out'))).first()
                if idat is not None:
                    tick = idat.id
                    # Create New Match to Original.  Both Original Out and its Street Turn Match have **
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
                        # Create New Interchange for Future Match, This has the street turn booking and street turn reuse date
                        input = Interchange(Container=con, TruckNumber=myi.TruckNumber, Driver=myi.Driver,
                                            Chassis=myi.Chassis,
                                            Date=dt, Release=bk, GrossWt=myi.GrossWt,
                                            Seals=myi.Seals, ConType=myi.ConType, CargoWt=myi.CargoWt,
                                            Time=myi.Time, Status='AAAAAA', Source=' ', Path=' ', Type='Empty Out', Jo=None,
                                            Company=None, Other=None, TimeExit=None, PortHours=None)
                        db.session.add(input)

                    odat = Orders.query.filter((Orders.Container == con) & (Orders.Date > lookback)).first()
                    if odat is not None:
                        odat.Container = newcon
                        odat.Hstat = 2
                        idat.Jo = odat.Jo
                        idat.Company = odat.Shipper
                        idat2 = Interchange.query.filter(
                            (Interchange.Container == newcon) & (Interchange.Date > lookback) & (
                                Interchange.Type.contains('In'))).first()
                        if idat2 is not None:
                            idat2.Jo = odat.Jo
                            idat2.Company = odat.Shipper

                    odatbk = Orders.query.filter((Orders.Booking == bk) & (Orders.Date > lookback)).first()
                    if odatbk is not None:
                        odatbk.Container = con
                        odatbk.Hstat = 1
                        idat3 = Interchange.query.filter(
                            (Interchange.Container == con) & (Interchange.Date > lookback) & (
                                Interchange.Type.contains('Out'))).first()
                        if idat3 is not None:
                            idat3.Jo = odatbk.Jo
                            idat3.Company = odatbk.Shipper

                db.session.commit()


                # Now see if this container has already been returned and get those matched....
                idatret = Interchange.query.filter(
                    (Interchange.Container == con) & (Interchange.Date > lookback) & (Interchange.Type.contains('In'))).first()
                if idatret is not None:
                    idatret.Status = 'IO'
                    idatret.Type = 'Load In'
                    idatret.Release = bk
                    idatout = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lookback) & (
                        Interchange.Type.contains('Out'))).first()
                    if idatout is not None:
                        idatout.Status = 'IO'
                        idatout.Company = idatret.Company
                        idatout.Jo = idatret.Jo
                        idatout.Release = bk
                    db.session.commit()

            else:
                print(f'Could not find  {container} to {booking} on {dateturn}')

        else:
            print(f'Street Turn Already Exists')

    return completed, err, holdvec

def Unpulled_Containers_task(err, holdvec, task_iter):
    holdvec = ['']*30
    #print(f'Running Unpulled Containers task')
    impco,impcon,impbol,expco,expbk = [], [], [], [], []
    bol = request.values.get('BOL')

    stopdate = today-datetime.timedelta(days=20)
    comps = []
    tjobs = Orders.query.filter(Orders.Date > stopdate).all()
    for job in tjobs:
        com = job.Shipper
        hstat = job.Hstat
        if hstat is None:
            hstat = 0
            job.Hstat = 0
        if hstat < 1 and com not in comps:
            comps.append(com)
    db.session.commit()

    if len(comps) >= 1:
        for com in comps:
            tjobs = Orders.query.filter( (Orders.Hstat < 1) & (Orders.Shipper==com) & (Orders.Date > stopdate)).all()
            for ix,job in enumerate(tjobs):
                con = job.Container
                bk = job.Booking
                con, bk = checkon(con, bk)
                if con == 'XXX':
                    expco.append(com)
                    expbk.append(bk)
                else:
                    impco.append(com)
                    impcon.append(con)
                    impbol.append(bk)

    holdvec[1] = bol
    holdvec[2] = impco
    holdvec[3] = impcon
    holdvec[4] = impbol
    holdvec[5] = expco
    holdvec[6] = expbk
    err.append('Unpulled Import Container Last 20 Days')
    err.append('Unused Export Bookings Last 20 Days')

    completed = False
    err.append('Unpulled Container run Successful')

    return completed, err, holdvec

def Exports_Pulled_task(err, holdvec, task_iter):
    holdvec = ['']*30
    #print(f'Running Exports Pulled task')
    expco, expcon, expbk, expdt, expdrv = [], [], [], [], []

    ts = request.values.get('timeslot')
    if ts is None: ts=1
    else: ts = int(ts)

    stopdate = today-datetime.timedelta(days=ts)
    comps = []
    if ts == 7: tjobs = Orders.query.filter( (Orders.Date >= stopdate) & (Orders.HaulType.contains('Export')) ).all()
    else: tjobs = Orders.query.filter( (Orders.Date == stopdate) & (Orders.HaulType.contains('Export')) ).all()
    for job in tjobs:
        com = job.Shipper
        hstat = job.Hstat
        if hstat is None:
            hstat = 0
            job.Hstat = 0
        if hstat >= 1 and com not in comps:
            comps.append(com)
    db.session.commit()

    if len(comps) >= 1:
        for com in comps:
            if ts == 7: tjobs = Orders.query.filter( (Orders.Shipper==com) & (Orders.Date >= stopdate) & (Orders.Hstat >= 1) & (Orders.HaulType.contains('Export'))).all()
            else: tjobs = Orders.query.filter( (Orders.Shipper==com) & (Orders.Date == stopdate) & (Orders.Hstat >= 1) & (Orders.HaulType.contains('Export'))).all()
            for ix,job in enumerate(tjobs):
                con = job.Container
                bk = job.Booking
                idat = Interchange.query.filter( (Interchange.Container == con) & (Interchange.Date == job.Date) & (Interchange.Type.contains('Empty')) ).first()
                if idat is not None:
                    time = idat.Time
                    driver = idat.Driver
                else:
                    time = ''
                    driver = ''
                date = f'{job.Date} {time}'
                expco.append(com)
                expbk.append(bk)
                expcon.append(con)
                expdt.append(date)
                expdrv.append(driver)

    if  expdt:
        sorted_lists = sorted(zip(expdt, expco, expbk, expcon, expdrv))
        expdt, expco, expbk, expcon, expdrv = zip(*sorted_lists)

    holdvec[1] = ts
    holdvec[2] = expdt
    holdvec[3] = expco
    holdvec[4] = expbk
    holdvec[5] = expcon
    holdvec[6] = expdrv

    err.append('Exports Pulled History')

    completed = False
    err.append('Exports Pulled run Successful')
    return completed, err, holdvec

def Exports_Returned_task(err, holdvec, task_iter):
    holdvec = ['']*30
    #print(f'Running Exports Returned task')
    expco, expcon, expbk, expdt, expdrv = [], [], [], [], []

    ts = request.values.get('timeslot')
    if ts is None: ts=1
    else: ts = int(ts)

    stopdate = today-datetime.timedelta(days=ts)
    comps = []
    if ts == 7: tjobs = Orders.query.filter( (Orders.Date2 >= stopdate) & (Orders.HaulType.contains('Export')) ).all()
    else: tjobs = Orders.query.filter( (Orders.Date2 == stopdate) & (Orders.HaulType.contains('Export')) ).all()
    for job in tjobs:
        com = job.Shipper
        hstat = job.Hstat
        if hstat is None:
            hstat = 0
            job.Hstat = 0
        if hstat >= 2 and com not in comps:
            comps.append(com)
    db.session.commit()

    if len(comps) >= 1:
        for com in comps:
            if ts == 7: tjobs = Orders.query.filter( (Orders.Shipper==com) & (Orders.Date2 >= stopdate) & (Orders.Hstat >= 2) & (Orders.HaulType.contains('Export'))).all()
            else: tjobs = Orders.query.filter( (Orders.Shipper==com) & (Orders.Date2 == stopdate) & (Orders.Hstat >= 2) & (Orders.HaulType.contains('Export'))).all()
            for ix,job in enumerate(tjobs):
                con = job.Container
                inbk = job.BOL
                outbk = job.Booking
                idat = Interchange.query.filter( (Interchange.Container == con) & (Interchange.Date == job.Date2) & (Interchange.Type.contains('Load')) ).first()
                if idat is not None:
                    time = idat.Time
                    driver = idat.Driver
                else:
                    time = ''
                    driver = ''

                if inbk is None:
                    bk = outbk
                else:
                    if inbk == outbk:
                        bk = inbk
                    else:
                        bk = f'*{inbk}*'

                date = f'{job.Date2} {time}'
                expco.append(com)
                expbk.append(bk)
                expcon.append(con)
                expdt.append(date)
                expdrv.append(driver)

    if  expdt:
        sorted_lists = sorted(zip(expdt, expco, expbk, expcon, expdrv))
        expdt, expco, expbk, expcon, expdrv = zip(*sorted_lists)

    holdvec[1] = ts
    holdvec[2] = expdt
    holdvec[3] = expco
    holdvec[4] = expbk
    holdvec[5] = expcon
    holdvec[6] = expdrv

    err.append('Exports Load-In History')

    completed = False
    err.append('Exports Returned run Successful')
    return completed, err, holdvec

def Exports_Bk_Diff_task(err, holdvec, task_iter):
    holdvec = ['']*30
    #print(f'Running Exports With Bk Diff task')
    expco, expcon, expbk, expdt, expdrv = [], [], [], [], []

    ts = request.values.get('timeslot')
    if ts is None: ts=7
    else: ts = int(ts)

    stopdate = today-datetime.timedelta(days=ts)
    comps = []
    tjobs = Orders.query.filter( (Orders.Date2 >= stopdate) & (Orders.HaulType.contains('Export')) ).all()
    for job in tjobs:
        com = job.Shipper
        hstat = job.Hstat
        if hstat is None:
            hstat = 0
            job.Hstat = 0
        if hstat >= 2 and com not in comps:
            bkin = job.BOL
            bkout = job.Booking
            con = job.Container
            if bkin is not None:
                if bkin != bkout:
                    comps.append(con)
    db.session.commit()

    if len(comps) >= 1:
        for con in comps:
            tjobs = Orders.query.filter( (Orders.Container==con) & (Orders.Date2 >= stopdate) & (Orders.Hstat >= 2) & (Orders.HaulType.contains('Export'))).all()

            for ix,job in enumerate(tjobs):
                com = job.Shipper
                inbk = job.BOL
                outbk = job.Booking
                idat = Interchange.query.filter( (Interchange.Container == con) & (Interchange.Date == job.Date2) & (Interchange.Type.contains('Load')) ).first()
                if idat is not None:
                    time = idat.Time
                    driver = idat.Driver
                    inbki = idat.Release
                else:
                    time = ''
                    driver = ''
                    inbki = ''
                jdat = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date == job.Date) & (Interchange.Type.contains('Empty'))).first()
                if jdat is not None:
                    outbki = jdat.Release
                else:
                    outbki = ''

                if outbki == outbk and inbki == inbk:
                    gatematch = 'Gate Match'
                else:
                    gatematch = 'Gate Mismatch'


                bk = f'Out: {outbk}  In: {inbk} {gatematch}'

                date = f'{job.Date2} {time}'
                expco.append(com)
                expbk.append(bk)
                expcon.append(con)
                expdt.append(date)
                expdrv.append(driver)

    if  expdt:
        sorted_lists = sorted(zip(expdt, expco, expbk, expcon, expdrv))
        expdt, expco, expbk, expcon, expdrv = zip(*sorted_lists)

    holdvec[1] = ts
    holdvec[2] = expdt
    holdvec[3] = expco
    holdvec[4] = expbk
    holdvec[5] = expcon
    holdvec[6] = expdrv

    err.append('Exports Load-In History')

    completed = False
    err.append('Exports Returned run Successful')
    return completed, err, holdvec


def Assign_Drivers_task(err, holdvec, iter):
    drivers= Drivers.query.filter(Drivers.Active == 1).all()
    trucks = Vehicles.query.filter(Vehicles.Active == 1).all()
    drivernow = request.values.get('thisdriver')
    trucknow = request.values.get('truckdefault')
    lupdate = request.values.get('LboxUpdate')
    if drivernow is None:
        ddat = drivers[0]
        drivernow = ddat.Name
    if trucknow is None:
        tdat = trucks[0]
        trucknow = tdat.Unit

    if iter == 0:
        #print(f'Running Assign Drivers task setup with iter {iter} and driver {drivernow} and Unit {trucknow}')
        completed = False
        #Set initial dates to the
        saturday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=5, weeks=-1)
        sundaylast = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=-1, weeks=-1)
        holdvec[12] = sundaylast.strftime('%Y-%m-%d')
        holdvec[13] = saturday.strftime('%Y-%m-%d')
        lookback = today - datetime.timedelta(30)
        fdata = Trucklog.query.filter(Trucklog.Date > lookback).all()

    elif iter > 0:

        start = request.values.get('dstart')
        if isinstance(start, str):
            holdvec[12] = start
        else:
            holdvec[12] = today - datetime.timedelta(14)
            holdvec[12] = holdvec[12].strftime('%Y-%m-%d')

        stop = request.values.get('dfinish')
        if isinstance(stop, str):
            holdvec[13] = stop
        else:
            holdvec[13] = today.strftime('%Y-%m-%d')

        fdata = Trucklog.query.filter(Trucklog.Date > start).all()

    holdvec[14], holdvec[15], holdvec[16], holdvec[17] = getdatevec(holdvec[12], holdvec[13], drivernow, trucknow)

    completed = False
    err.append('Assign Drivers Successful')

    # If ready to update then update the driving records:
    if lupdate is not None:
        for jx, d1 in enumerate(holdvec[14]):
            d1 = datetime.datetime.strptime(d1, '%Y-%m-%d')
            drv = drivernow
            units = request.values.get('trks' + str(jx))
            unite = request.values.get('trke' + str(jx))
            #print(f'Updating units {units} and unite {unite}')
            tdat = DriverAssign.query.filter((DriverAssign.Date == d1) & (DriverAssign.Driver == drv)).first()
            if tdat is not None:
                tdat.UnitStart = units
                tdat.UnitStop = unite
                db.session.commit()
            else:
                if units is not None:
                    # Get the trucklog data for the Unit used:
                    input = DriverAssign(Date=d1, Driver=drv, UnitStart=units, UnitStop=unite, StartStamp=None,
                                         EndStamp=None, Hours=None, Miles=None, Status=0, Radius=None, Rloc=None)
                    db.session.add(input)
                    db.session.commit()

            tdat = DriverAssign.query.filter((DriverAssign.Date == d1) & (DriverAssign.Driver == drv)).first()
            tlog = Trucklog.query.filter((Trucklog.Date == d1) & (Trucklog.Unit == units)).first()
            if tlog is not None:
                tlog.DriverStart = drv
                tdat.StartStamp = tlog.GPSin
                tdat.Miles = tlog.Distance
                tdat.Radius = tlog.Rdist
                tdat.Rloc = tlog.Rloc
                db.session.commit()

            tlog = Trucklog.query.filter((Trucklog.Date == d1) & (Trucklog.Unit == unite)).first()
            if tlog is not None:
                tlog.DriverEnd = drv
                tdat.EndStamp = tlog.GPSout
                try:
                    diff = tdat.EndStamp - tdat.StartStamp
                    hours = diff.seconds / 3600.0
                except:
                    hours = 0
                tdat.Hours = d2s(hours)
                db.session.commit()
        err.append(f'Successful Update for Driver {drivernow}')

    holdvec[0] = drivers
    holdvec[1] = trucks
    holdvec[2] = fdata
    holdvec[10] = drivernow
    holdvec[11] = trucknow


    return completed, err, holdvec

def Driver_Hours_task(err, holdvec, iter):

    drivers= Drivers.query.filter(Drivers.Active == 1).all()
    trucks = Vehicles.query.filter(Vehicles.Active == 1).all()
    drivernow = request.values.get('thisdriver')
    trucknow = request.values.get('truckdefault')
    lupdate = request.values.get('LboxUpdate')
    if drivernow is None:
        ddat = drivers[0]
        drivernow = ddat.Name
    if trucknow is None:
        tdat = trucks[0]
        trucknow = tdat.Unit

    if iter == 0:
        #print(f'Running Driver Hours task setup with iter {iter} and driver {drivernow} and Unit {trucknow}')
        completed = False
        # Set initial dates to the
        saturday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=5, weeks=-1)
        sundaylast = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=-1, weeks=-1)
        holdvec[12] = sundaylast.strftime('%Y-%m-%d')
        holdvec[13] = saturday.strftime('%Y-%m-%d')
        lookback = today - datetime.timedelta(30)
        start = sundaylast
        stop = saturday

    elif iter > 0:

        start = request.values.get('dstart')
        if isinstance(start, str):
            holdvec[12] = start
        else:
            holdvec[12] = today - datetime.timedelta(14)
            holdvec[12] = holdvec[12].strftime('%Y-%m-%d')

        stop = request.values.get('dfinish')
        if isinstance(stop, str):
            holdvec[13] = stop
        else:
            holdvec[13] = today.strftime('%Y-%m-%d')

    fdata = DriverAssign.query.filter((DriverAssign.Hours != None) & (DriverAssign.Date > start) & (DriverAssign.Date < stop) ).all()
    ddata = hoursbydriver(drivers, fdata)


    completed = False
    err.append('Assign Drivers Successful')

    holdvec[0] = drivers
    holdvec[1] = trucks
    holdvec[2] = fdata
    holdvec[3] = ddata

    return completed, err, holdvec



def CMA_APL_task(err,holdvec, task_iter):
    #print(f'Running Text Output task')

    holdvec = ['']*30
    #print(f'Running CMA-APL task')
    cmajobs, apljobs, cmadone, apldone = [], [], [], []
    bol = request.values.get('BOL')

    stopdate = today-datetime.timedelta(days=40)
    comps = []
    tcma = Orders.query.filter( (Orders.Shipper == 'CMA-CMG')  & (Orders.Date > stopdate) ).all()
    tapl = Orders.query.filter((Orders.Shipper == 'American Presidents Line') & (Orders.Date > stopdate)).all()
    for ix,job in enumerate(tcma):
        con = job.Container
        bk = job.Booking
        if len(con) == 11:
            conpre = con[0:4]
            conpost = con[4:11]
        else:
            conpre = ''
            conpost = ''
        cmajobs.append(f'{job.Order} {bk} {conpre} {conpost}')

    for ix,job in enumerate(tapl):
        con = job.Container
        bk = job.Booking
        if len(con) == 11:
            conpre = con[0:4]
            conpost = con[4:11]
        else:
            conpre = ''
            conpost = ''
        apljobs.append(f'{job.Order} {bk} {conpre} {conpost}')

    holdvec[0] = cmajobs
    holdvec[1] = apljobs


    completed = False
    err.append('CMA-APL Successful')
    return completed, err, holdvec

def Container_Update_task(err):
    #print(f'Running Container Update task')
    runat = datetime.datetime.now()
    lookback = runat - datetime.timedelta(30)
    lbdate = lookback.date()

    idata = Interchange.query.filter(
        (Interchange.Type.contains('Out')) & (Interchange.Date > lbdate) & (Interchange.Status != 'IO')).all()
    for idat in idata:
        con, bk = checkon(idat.Container, idat.Release)
        jdat = Orders.query.filter((Orders.Container == con) & (Orders.Date > lbdate)).first()
        if jdat is not None:
            # Shoud be an import
            idat.Status = 'BBBBBB'
            idat.Company = jdat.Shipper
            idat.Jo = jdat.Jo
            jdat.Date = idat.Date
            jdat.Type = idat.ConType
            jdat.Chassis = idat.Chassis
            jdat.Hstat = 1
        else:
            kdat = Orders.query.filter((Orders.Booking == bk) & (Orders.Date > lbdate)).first()
            if kdat is not None:
                # Shoud be an export
                idat.Status = 'BBBBBB'
                idat.Company = kdat.Shipper
                idat.Jo = kdat.Jo
                kdat.Date = idat.Date
                kdat.Type = idat.ConType
                kdat.Chassis = idat.Chassis
                kdat.Hstat = 1
            else:
                print(f'No job match for {con}')
    db.session.commit()

    idata = Interchange.query.filter(
        (Interchange.Type.contains('Out')) & (Interchange.Date > lbdate) & (Interchange.Status != 'IO')).all()
    for idat in idata:
        con, bk = checkon(idat.Container, idat.Release)
        imat = Interchange.query.filter(
            ((Interchange.Container == con) | (Interchange.Release == bk)) & (Interchange.Type.contains('In')) & (
                        Interchange.Date > lbdate)).first()
        #print(con, bk)
        if imat is not None:
            imat.Status = 'IO'
            idat.Status = 'IO'
            imat.Company = idat.Company
            imat.Jo = idat.Jo
            # We have a return to port so update job status
            jdat = Orders.query.filter( ( (Orders.Container == con) | (Orders.Booking == bk) ) & (Orders.Date > lbdate) ).first()
            print(bk, con, jdat)
            if jdat is not None:
                jcon = jdat.Container
                if not hasinput(jcon): jdat.Container = con
                jdat.Hstat = 2
                jdat.Date2 = imat.Date
    db.session.commit()
    completed = True
    err.append('Container Update Successful')
    return completed, err
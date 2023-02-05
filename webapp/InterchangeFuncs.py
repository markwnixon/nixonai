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

def Order_Container_Update(oder):
    print('**********Update Function***********')
    okat = Orders.query.get(oder)
    bkout = okat.Booking
    con = okat.Container
    lbdate = okat.Date3 - timedelta(120)
    ntick = 0
    kdat = None

    if hasinput(con):
        idata = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lbdate)).all()
        ntick = len(idata)
    if hasinput(bkout):
        kdat = Interchange.query.filter((Interchange.Release == bkout) & (Interchange.Type == 'Empty Out') & (Interchange.Date > lbdate)).first()

    print(f'There are {ntick} interchange tickets based on container search')
    if ntick == 2:
        test = 1
        if 'Out' in idata[0].Type:
            idat0 = idata[0]
            idat1 = idata[1]
        elif 'Out' in idata[1].Type:
            idat1 = idata[0]
            idat0 = idata[1]
        else:
            test = 0
            print('Failed test of proper pairing')
        if test:
            print(f'{idat0.Type}: {idat0.Release} {idat0.Container}')
            print(f'{idat1.Type}: {idat1.Release} {idat1.Container}')
            # Check to see if pairing completed and this is only Order for that container (in case duplicated)
            if 'Out' in idat0.Type and 'In' in idat1.Type:
                allorders = idata = Orders.query.filter((Orders.Container == con) & (Orders.Date3 > lbdate)).all()
                if len(allorders) == 1:
                    jo = okat.Jo
                    shipper = okat.Shipper
                    idat0.Status = 'IO'
                    idat1.Status = 'IO'
                    idat0.Jo = jo
                    idat1.Jo = jo
                    idat0.Company = shipper
                    idat1.Company = shipper
            #If this is an import then the release will not be included in interchange ticket so do not update the order or it will be erased
            if 'Export' in okat.HaulType:
                okat.Booking = idat0.Release
                okat.BOL = idat1.Release
            okat.Chassis = idat0.Chassis
            okat.ConType = idat0.ConType
            okat.Date = idat0.Date
            okat.Date2 = idat1.Date
            okat.Hstat = 2
            db.session.commit()

    if ntick == 1:
        ikat = idata[0]
        con = ikat.Container
        release = ikat.Release
        movetyp = ikat.Type
        if movetyp == 'Load Out':
            #This should be an import, container will already be edited input
            okat.Chassis = ikat.Chassis
            okat.ConType = ikat.ConType
            okat.Date = ikat.Date
            okat.Hstat = 1
            db.session.commit()
        if movetyp == 'Empty Out':
            okat.Container = con
            okat.Chassis = ikat.Chassis
            okat.ConType = ikat.ConType
            okat.Booking = ikat.Release
            okat.Date = ikat.Date
            okat.Hstat = 1
            ikat.Company = okat.Shipper
            ikat.Jo = okat.Jo
            db.session.commit()
        if movetyp == 'Empty In':
            okat.Date2 = ikat.Date
            okat.Hstat = 2
            ikat.Status = 'No Load Out'
            db.session.commit()
        if movetyp == 'Load In':
            okat.Date2 = ikat.Date
            okat.Hstat = 2
            okat.BOL = ikat.Release
            ikat.Status = 'No Empty Out'
            db.session.commit()

    if ntick == 0 and kdat is not None:
        print('Doing the most dangerous update')
        #If only have no tickets based on container and have an empty out based on booking do that update
        con = kdat.Container
        movetyp = kdat.Type
        print(f'Performing update based on interchange empty out give con {con} and movetyp {movetyp}')
        if movetyp == 'Empty Out':
            okat.Container = con
            okat.Chassis = kdat.Chassis
            okat.ConType = kdat.ConType
            okat.Date = kdat.Date
            kdat.Company = okat.Shipper
            kdat.Jo = okat.Jo
            if okat.Hstat is None: okat.Hstat = 1
            elif okat.Hstat < 3: okat.Hstat = 1
        #And now we have to complete the assignment based on the container number of the first interchange
            ingate = Interchange.query.filter((Interchange.Container == con) & (Interchange.Type == 'Load In') & (Interchange.Date > lbdate)).first()
            if ingate is not None:
                okat.BOL = ingate.Release
                okat.Date2 = ingate.Date
                okat.Hstat = 2
                ingate.Company = okat.Shipper
                ingate.Jo = okat.Jo
                ingate.Status = 'IO'
                kdat.Status = 'IO'
            db.session.commit()
    else:
        print(f'nick is {ntick} and kdat is None')








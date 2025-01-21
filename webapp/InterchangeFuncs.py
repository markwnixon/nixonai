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

def scrub_export(idata):
    len_idata = len(idata)
    base = idata[0]
    release = base.Release
    type = base.Type
    for ix in range(1, len_idata):
        tdat = idata[ix]
        trel = tdat.Release
        ttype = tdat.Type
        if trel == release and ttype == type:
            #This is duplicate gate ticket, need to remove it
            idkill = tdat.id
            Interchange.query.filter(Interchange.id == idkill).delete()
            db.session.commit()
    return base

def add_dash(rout, rin):
    if '-' in rin:
        rbase, rdash = rin.split('-')
        print(f'rbase is {rbase}, rdash is {rdash}')
        rbase2, rdash2 = rout.split('-')
        print(f'rbase2 is {rbase2}, rdash2 is {rdash2}')
        new_rin = f'{rbase2}-{rdash}'
        return new_rin
    return rin






def Gate_Match(con, lbdate, nbk, ptype, odat):
    if ptype == 'Import':
        iout = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lbdate) & (Interchange.Type == 'Load Out')).first()
        iin = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lbdate) & (Interchange.Type == 'Empty In')).first()
        company = odat.Shipper
        jo = odat.Jo
        if iout and iin:
            if iout.Jo != jo or iin.Jo != jo or iout.Company != company or iin.Company != company:
                iout.Status = 'IO'
                iin.Status = 'IO'
                iout.Company = company
                iin.Company = company
                iout.Jo = jo
                iin.Jo = jo
                db.session.commit()
                return 2
            return 2
        elif iout:
            iout.Status = 'BBBBBB'
            db.session.commit()
            return 1
        elif iin:
            return 2
        else:
            return 0

    elif ptype == 'Export':
        iout = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lbdate) & (Interchange.Type == 'Empty Out')).all()
        iin = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lbdate) & (Interchange.Type == 'Load In')).all()
        #Make absolutely sure we only have one empty out and one load in for the export container
        niout = len(iout)
        niin = len(iin)
        if niout == 1: iout = iout[0]
        elif niout > 1: iout = scrub_export(iout)
        if niin == 1: iin = iin[0]
        elif niin > 1: iin = scrub_export(iin)

        if iout and iin:
            iout.Status = 'IO'
            iin.Status = 'IO'
            if nbk > 1:
                #If number of bookings is more than one, need to check the dash number.  Ensure the base number does not change
                updated_release = add_dash(iout.Release, iin.Release)
                iin.Release = updated_release
            iin.Jo = iout.Jo
            iin.Company = iout.Company
            db.session.commit()
            return 2
        elif iout:
            iout.Status = 'BBBBBB'
            db.session.commit()
            return 1
        elif iin:
            return 2
        else:
            return 0

    elif ptype == 'Dray In' or ptype == 'Import Dray-In':
        iout = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lbdate) & (Interchange.Type == 'Dray Out')).first()
        iin = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lbdate) & (Interchange.Type == 'Dray In')).first()

        niout = len(iout)
        niin = len(iin)
        if niout == 1: iout = iout[0]
        elif niout > 1: iout = scrub_export(iout)
        if niin == 1: iin = iin[0]
        elif niin > 1: iin = scrub_export(iin)

        if iout and iin:
            iout.Status = 'IO'
            iin.Status = 'IO'
            if nbk > 1:
                # If number of bookings is more than one, need to check the dash number.  Ensure the base number does not change
                updated_release = add_dash(iout.Release, iin.Release)
                iin.Release = updated_release
            iin.Jo = iout.Jo
            iin.Company = iout.Company
            db.session.commit()
            return 2
        elif iout:
            iout.Status = 'BBBBBB'
            db.session.commit()
            return 1
        elif iin:
            return 2
        else:
            return 0

    elif ptype == 'Dray Out':
        iout = Interchange.query.filter(
            (Interchange.Container == con) & (Interchange.Date > lbdate) & (Interchange.Type == 'Dray Out')).first()
        iin = Interchange.query.filter(
            (Interchange.Container == con) & (Interchange.Date > lbdate) & (Interchange.Type == 'Dray In')).first()
        if iout and iin:
            iout.Status = 'IO'
            iin.Status = 'IO'
            if nbk > 1:
                # If number of bookings is more than one, need to check the dash number.  Ensure the base number does not change
                updated_release = add_dash(iout.Release, iin.Release)
                iin.Release = updated_release
            iin.Jo = iout.Jo
            iin.Company = iout.Company
            db.session.commit()
            return 2
        elif iout:
            iout.Status = 'BBBBBB'
            db.session.commit()
            return 1
        elif iin:
            return 2
        else:
            return 0


def Gate_Update(ider):
    ikat = Interchange.query.get(ider)
    bk = ikat.Release
    con = ikat.Container
    htype = ikat.Type
    if hasinput(con) and hasinput(htype):
        err = ['Gate Update is well']
    else:
        err = ['Need both container and type']
        return err
    lbdate = ikat.Date - timedelta(120)
    nbk = 1
    if hasinput(bk) and len(bk)>5 and htype == 'Empty Out':
        if '-' in bk:
            bklist = bk.split('-')
            bk = bklist[0]
        # Check to see if there are multiple bookings for this job
        edata = Orders.query.filter((Orders.HaulType.contains('Export')) & (Orders.Booking.contains(bk)) & (Orders.Date > lbdate)).all()
        nbk = len(edata)
        if nbk > 1 and len(bk) > 6:
            # there are multiple bookings so we need to modify the interchange tickets to coincide, make sure have a valid booking not blankj
            idata = Interchange.query.filter((Interchange.Release.contains(bk)) & (Interchange.Date > lbdate) & (Interchange.Type == 'Empty Out')).all()
            if idata:
                for ix, idat in enumerate(idata):
                    bklabel = f'{bk}-{ix+1}'
                    idat.Release = bklabel
                db.session.commit()
                #May have rearranged the pulls to need to update all the Interchange tickets
                for idat in idata:
                    con = idat.Container
                    bk = idat.Release
                    chas = idat.Chassis
                    odat = Orders.query.filter((Orders.Booking == bk) & (Orders.Date > lbdate)).first()
                    if odat is not None:
                        ###print(f'UPdate order with booking {bk} to match the interchange release with container {con}')
                        jo = odat.Jo
                        shipper = odat.Shipper
                        idat.Jo = jo
                        idat.Company = shipper
                        odat.Container = con
                        odat.Chassis = chas
                        odat.Hstat = Gate_Match(con, lbdate, nbk, 'Export', odat)
                        db.session.commit()


    # Next match up the container and release to the job
    ikat = Interchange.query.get(ider)
    bk = ikat.Release
    con = ikat.Container
    htype = ikat.Type
    lbdate = ikat.Date - timedelta(120)
    if htype == 'Empty Out':
        gate_name = f'{con}_EMPTY_OUT.pdf'
        odat = Orders.query.filter((Orders.Booking == bk) & (Orders.Date > lbdate)).first()
        if odat is not None:
            jo = odat.Jo
            shipper = odat.Shipper
            con = ikat.Container
            chas = ikat.Chassis
            ikat.Jo = jo
            ikat.Company = shipper
            odat.Container = con
            odat.Chassis = chas
            odat.Hstat = Gate_Match(con, lbdate, nbk, 'Export', odat)
            db.session.commit()
    if htype == 'Load Out':
        gate_name = f'{con}_LOAD_OUT.pdf'
        odat = Orders.query.filter((Orders.Container == con) & (Orders.Date > lbdate)).first()
        if odat is not None:
            jo = odat.Jo
            shipper = odat.Shipper
            chas = ikat.Chassis
            ikat.Jo = jo
            ikat.Company = shipper
            odat.Chassis = chas
            odat.Hstat = Gate_Match(con, lbdate, nbk, 'Import', odat)
            db.session.commit()
    if htype == 'Dray Out':
        gate_name = f'{con}_LOAD_OUT.pdf'
        odat = Orders.query.filter((Orders.Container == con) & (Orders.Date > lbdate)).first()
        if odat is not None:
            jo = odat.Jo
            shipper = odat.Shipper
            chas = ikat.Chassis
            ikat.Jo = jo
            ikat.Company = shipper
            odat.Chassis = chas
            odat.Hstat = Gate_Match(con, lbdate, nbk, 'Dray Out', odat)
            db.session.commit()
    if htype == 'Dray In':
        gate_name = f'{con}_LOAD_OUT.pdf'
        odat = Orders.query.filter((Orders.Container == con) & (Orders.Date > lbdate)).first()
        if odat is not None:
            jo = odat.Jo
            shipper = odat.Shipper
            chas = ikat.Chassis
            ikat.Jo = jo
            ikat.Company = shipper
            odat.Chassis = chas
            odat.Hstat = Gate_Match(con, lbdate, nbk, 'Dray In', odat)
            db.session.commit()
    if htype == 'Load In':
        gate_name = f'{con}_LOAD_IN.pdf'
        #Could be different booking going in so have to look for both, but need to look at the inbook first
        odat = Orders.query.filter((Orders.BOL == bk) & (Orders.Date > lbdate)).first()
        if odat is None:
            odat = Orders.query.filter((Orders.Booking == bk) & (Orders.Date > lbdate)).first()
            if odat is None:
                odat = Orders.query.filter((Orders.Container == con) & (Orders.Date > lbdate)).first()
        if odat is not None:
            jo = odat.Jo
            shipper = odat.Shipper
            ikat.Jo = jo
            ikat.Company = shipper
            odat.Hstat = Gate_Match(con, lbdate, nbk, 'Export', odat)
            db.session.commit()
    if htype == 'Empty In':
        gate_name = f'{con}_EMPTY_IN.pdf'
        odat = Orders.query.filter((Orders.Container == con) & (Orders.Date > lbdate) & (Orders.HaulType.contains('Import')) ).first()
        if odat is not None:
            jo = odat.Jo
            shipper = odat.Shipper
            ikat.Jo = jo
            ikat.Company = shipper
            odat.Hstat = Gate_Match(con, lbdate, nbk, 'Import', odat)
            db.session.commit()

    #ikat = Interchange.query.get(ider)
    ###print(f'The interchange source doe is {ikat.Source}')
    ###print(f'The gate name should be {gate_name}')




def Order_Container_Update(oder, err):

    okat = Orders.query.get(oder)
    bkout = okat.Booking
    con = okat.Container
    htype = okat.HaulType
    lbdate = okat.Date3 - timedelta(120)
    ntick = 0
    kdat = None
    nbk = 1
    #print(f'**********Order_Container_Update*********** container:{con}, bkout:{bkout} htype:{htype}')

    #If export check for multiple bookings and control accordingly
    if 'Export' in htype:
        #Only run if have a legitimate booking number.
        if len(bkout) > 5:
            # Make sure start from the base booking without dashes:
            if '-' in bkout:
                bklist = bkout.split('-')
                bkout = bklist[0]
                if len(bkout) < 7: bkout = 'NoBook'
            edata = Orders.query.filter((Orders.HaulType.contains('Export')) & (Orders.Booking.contains(bkout)) & (Orders.Date > lbdate)).all()
            nbk = len(edata)
            multibooking = 1
            if nbk > 1:
                multibooking = 0
                #Check to make sure they all have the same base booking.
                jo_multibook = []
                for edat in edata:
                    tbooking = edat.Booking
                    tbklist = tbooking.split('-')
                    tbook = tbklist[0]
                    if tbook == bkout:
                        multibooking += 1
                        jo_multibook.append(edat.Jo)

                if multibooking > 1:
                    ix = 1
                    for edat in edata:
                        jo = edat.Jo
                        if jo in jo_multibook:
                            bklabel = f'{bkout}-{ix}'
                            edat.Booking = bklabel
                            ix += 1
                    db.session.commit()

                    # Now have to update and relabel the Interchange tickets to match, and make sure the dashes match the orders only if the base bookings match
                    ix = 1
                    idata = Interchange.query.filter((Interchange.Release.contains(bkout)) & (Interchange.Date > lbdate) & (Interchange.Type == 'Empty Out')).all()
                    if idata:
                        for jx, idat in enumerate(idata):
                            current_booking = idat.Release
                            base_nodash = current_booking.split('-')
                            release_nodash = base_nodash[0]
                            if bkout == release_nodash:
                                bklabel = f'{release_nodash}-{ix}'
                                idat.Release = bklabel
                                container = idat.Container
                                mdat = Interchange.query.filter((Interchange.Container == container) & (Interchange.Date > lbdate) & (Interchange.Type == 'Load In')).first()
                                if mdat is not None:
                                    mdat_booking = mdat.Release
                                    mbase_nodash = mdat_booking.split('-')
                                    mrelease_nodash = mbase_nodash[0]
                                    if bkout == mrelease_nodash:
                                        mbklabel = f'{mrelease_nodash}-{ix}'
                                        mdat.Release = mbklabel
                                ix += 1
                        db.session.commit()

                    #Now reset the order using the relabeled bookings that have dashes:
                    edata = Orders.query.filter((Orders.HaulType.contains('Export')) & (Orders.Booking.contains(bkout)) & (Orders.Date > lbdate)).all()
                    for edat in edata:
                        jo = edat.Jo
                        if jo in jo_multibook:
                            whole_booking = edat.Booking
                            jdat = Interchange.query.filter((Interchange.Release == whole_booking) & (Interchange.Date > lbdate) & (Interchange.Type == 'Empty Out')).first()
                            if jdat is not None:
                                jo = edat.Jo
                                shipper = edat.Shipper
                                jdat.Jo = jo
                                jdat.Company = shipper
                                con = jdat.Container
                                edat.Container = con
                                edat.Chassis = jdat.Chassis
                                edat.Hstat = Gate_Match(con, lbdate, multibooking, 'Export', edat)
                                db.session.commit()
                            else:
                                edat.Container = ''
                                edat.Chassis = ''
                                edat.Hstat = 0
                                db.session.commit()


        else:
            err = ['Cannot create or update an export without a booking number']

    if nbk == 1:
        if hasinput(con):
            idata = Interchange.query.filter((Interchange.Container == con) & (Interchange.Date > lbdate)).all()
            ntick = len(idata)
        if hasinput(bkout):
            kdat = Interchange.query.filter((Interchange.Release == bkout) & (Interchange.Type == 'Empty Out') & (Interchange.Date > lbdate)).first()

        #print(f'There are {ntick} interchange tickets based on container search')
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
                ###print('Failed test of proper pairing')
            if test:
                #print(f'{idat0.Type}: {idat0.Release} {idat0.Container}')
                #print(f'{idat1.Type}: {idat1.Release} {idat1.Container}')
                # Check to see if pairing completed and this is only Order for that container (in case duplicated)
                if 'Out' in idat0.Type and 'In' in idat1.Type:
                    allorders = Orders.query.filter((Orders.Container == con) & (Orders.Date3 > lbdate)).all()
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
                ikat.Status = 'BBBBBB'
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
                ikat.Status = 'BBBBBB'
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
            ###print('Doing the most dangerous update')
            #If only have no tickets based on container and have an empty out based on booking do that update
            con = kdat.Container
            movetyp = kdat.Type
            ###print(f'Performing update based on interchange empty out give con {con} and movetyp {movetyp}')
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
    return err







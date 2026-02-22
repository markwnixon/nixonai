from operator import truediv

from webapp import db
from webapp.models import OverSeas, Orders, People, Interchange, Bookings, Openi, Drivers, Vehicles
from flask import session, request
from webapp.viewfuncs import d2s, stat_update, hasinput
#import datetime
import pytz
from datetime import datetime, time, timedelta, date
import ast
from webapp.revenues import intdol

def repair_dates(odata):
    for odat in odata:
        gout = odat.Date
        gin = odat.Date2
        deliv = odat.Date3
        hstat = odat.Hstat
        if isinstance(gout, date) and isinstance(gin, date) and isinstance(deliv, date):
            if hstat == 1:
                #If it is pulled already the gateout is the gateout, dont change it.  Then delivery cannot occur before
                if gout > deliv:
                    odat.Date3 = gout
            if hstat < 1:
                #If not pulled yet then assume delivery date correct and gout cannot be greater
                if gout > deliv:
                    odat.Date = deliv
            if gin < deliv:
                odat.Date2 = deliv
    db.session.commit()
    return


def api_call(scac, now, data_needed, arglist):
    print(f'Inside api_call with data_needed={data_needed}, arglist={arglist}')
    if data_needed == 'shipper_containers_out':

        #postman api test call is: http://127.0.0.1:5000/get_api_data?data_needed=shipper_containers_out&arglist=['Absolute Worldwide Logistics']
        params = ast.literal_eval(arglist)
        shipper = params[0]
        print(f'Was able to get the shipper: {shipper}')
        lb_days = 20
        try:
            lb_days = params[1]
        except:
            lb_days = 50
            params.append(lb_days)
        lbdate = now.date()
        lbdate = lbdate - timedelta(days=lb_days)
        print(f'Looking back to this date: {lbdate}')
        odata = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat < 2) & (Orders.Shipper == shipper)).all()
        ret_data = []
        for odat in odata:
            ret_data.append({'id': odat.id, 'JO': odat.Jo, 'SCAC': scac, 'Shipper': odat.Shipper,
                              'Container': odat.Container, 'Hstat': odat.Hstat})


        return ret_data

    elif data_needed == 'out_containers':
        #postman api test call is: http://127.0.0.1:5000/get_api_data?data_needed=active_containers&arglist=[]
        lb_days = 7
        today = now.date()
        lbdate = today - timedelta(days=lb_days)
        print(f'Looking back to this date: {lbdate}')
        odata = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat == 1)).order_by(Orders.Date).all()
        ret_data = []
        containers = []
        for odat in odata:
            container = odat.Container
            source = odat.Source
            manifest = odat.Manifest
            if source is None and manifest is None:
                status_text = 'Out No POD'
            else:
                status_text = 'Out'
            containers.append(container)
            ret_data.append({'id': odat.id, 'containerNumber': container, 'status': status_text})
        odata0 = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat < 1)).order_by(Orders.Date).all()
        for odat in odata0:
            container = odat.Container
            source = odat.Source
            manifest = odat.Manifest
            if source is None and manifest is None:
                status_text = 'Unpulled No POD'
            else:
                status_text = 'Unpulled'
            if hasinput(container):
                if container not in containers:
                    containers.append(container)
                    ret_data.append({'id': odat.id, 'containerNumber': container, 'status': status_text})
        odata2 = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat > 1)).order_by(Orders.Date).all()
        for odat in odata2:
            container = odat.Container
            source = odat.Source
            manifest = odat.Manifest
            if source is None and manifest is None:
                status_text = 'Ret No POD'
            else:
                status_text = 'Ret'
            if hasinput(container):
                if container not in containers:
                    containers.append(container)
                    ret_data.append({'id': odat.id, 'containerNumber': container, 'status': status_text})

        print(ret_data)
        return ret_data

    elif data_needed == 'active_containers':

        #postman api test call is: http://127.0.0.1:5000/get_api_data?data_needed=active_containers&arglist=[]
        lb_days = 7
        today = now.date()
        lbdate = today - timedelta(days=lb_days)
        active_date = today + timedelta(days=7)
        fd = '1900-01-01'
        print(f'Looking back to this date: {lbdate}')
        odata = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat < 2)).order_by(Orders.Date).all()
        ret_data = []
        for odat in odata:
            hstat = odat.Hstat
            container = odat.Container

            if hstat >= 2 and odat.Date2 < active_date:
                print(f'Container {container} returned before the active date of {active_date}')
            else:
                booking = odat.Booking
                htype = odat.HaulType
                del_address = odat.Dropblock2

                #Must return dates in a valid date format or the api readers will fail
                if isinstance(odat.Date, date):
                    gateout = f'{odat.Date}'
                else:
                    gateout = fd
                if isinstance(odat.Date2, date):
                    gatein = f'{odat.Date2}'
                else:
                    gatein = fd
                if isinstance(odat.Date3, date):
                    delivery = f'{odat.Date3}'
                else:
                    delivery = fd
                if isinstance(odat.Date4, date):
                    port_early = f'{odat.Date4}'
                else:
                    port_early = fd
                if isinstance(odat.Date5, date):
                    port_late = f'{odat.Date5}'
                else:
                    port_late = fd
                if isinstance(odat.Date6, date):
                    dueback = f'{odat.Date6}'
                else:
                    dueback = fd


                if hstat <= 0:
                    status = 'Unpulled'
                elif hstat == 1:
                    status = 'Out'
                elif hstat >= 2:
                    status = 'Returned'
                else:
                    status = 'Undefined'

                if hstat <= 0 and 'Export' in htype:
                    print(f'Export job has not been pulled yet')
                    container = 'Unpulled Export'

                ret_data.append({'id': odat.id, 'jo': odat.Jo, 'scac': scac, 'shipper': odat.Shipper, 'release':booking,
                                  'container': container, 'status': status, 'haulType':htype, 'delAddress':del_address,
                                  'gateOut': gateout, 'gateIn': gatein, 'delivery': delivery,
                                  'portEarly': port_early, 'portLate': port_late, 'dueBack':dueback
                                 })
        print(ret_data)
        return ret_data


    elif data_needed == 'calendar':
        #postman api test call is: http://127.0.0.1:5000/get_api_data?data_needed=active_containers&arglist=[]
        lb_days = 60
        today = now.date()
        lbdate = today - timedelta(days=lb_days)
        active_date = today + timedelta(days=10)
        fd = '1900-01-01'
        print(f'Looking back to this date: {lbdate}')
        odata = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat < 2)).order_by(Orders.Date).all()
        repair_dates(odata)
        odata = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat < 2)).order_by(Orders.Date).all()
        ret_data = []
        earliest = None
        latest = None
        cal_id = 0
        for odat in odata:
            hstat = odat.Hstat
            container = odat.Container
            if hstat >= 2 and odat.Date2 < active_date:
                print(f'Container {container} returned before the active date of {active_date}')
            else:
                if earliest is None or odat.Date < earliest: earliest = odat.Date
                if latest is None or odat.Date2 > latest: latest = odat.Date2

        print(f'The min date is {earliest}')
        print(f'The max date is {latest}')
     # Repair any obviously wrong dates


        for odat in odata:
            hstat = odat.Hstat
            container = odat.Container
            release = odat.Booking
            deltype = odat.Delivery
            deltime = odat.Time3

            if hstat >= 2 and odat.Date2 < active_date:
                print(f'Container {container} returned before the active date of {active_date}')
            else:
                booking = odat.Booking
                htype = odat.HaulType
                del_address = odat.Dropblock2
                if 'DP' in htype:
                    droppick=True
                else:
                    droppick=False
                if 'Import' in htype:
                    importj=True
                else:
                    importj=False
                if 'Export' in htype:
                    exportj=True
                else:
                    exportj=False

                # Determine how many calendar entries we have for each job based on the gatein, gateout, and delivery dates
                gout = odat.Date
                gin = odat.Date2
                deliv = odat.Date3
                if isinstance(gout, date) and isinstance(gin, date) and isinstance(deliv, date):
                    #print('We have three good dates')
                    #We have three good dates to use and compare
                    cal_message = []
                    cal_dates = []
                    if deltype == 'Hard Time':
                        delmess = f' {deltime}'
                    else:
                        delmess = ''
                    print(f'delmess is {delmess}')
                    if gout == deliv and gout == gin:
                        #Plan is to pull deliv and return same day
                        if not droppick:
                            if exportj:
                                cal_message.append(f'Pull empty, deliver{delmess}, and return load same day')
                                cal_dates.append(gout)
                                dtype = 'All same day'
                            if importj:
                                cal_message.append(f'Pull load, deliver{delmess}, and return empty same day')
                                cal_dates.append(gout)
                                dtype = 'All same day'
                        else:
                            if exportj:
                                cal_message.append('Pull and drop empty')
                                cal_dates.append(gout)
                                dtype = 'All same day'
                            if importj:
                                cal_message.append('Pull and drop load')
                                cal_dates.append(gout)
                                dtype = 'All same day'
                    elif gout == deliv and gout != gin:
                        if droppick:
                            if exportj:
                                cal_message.append('Pull empty and drop')
                                cal_message.append(f'Return now-loaded container dropped on {deliv}')
                                cal_dates.append(gout)
                                cal_dates.append(gin)
                                dtype = 'Pull and deliver not return'
                            if importj:
                                cal_message.append('Pull load and drop')
                                cal_message.append(f'Return now-empty container dropped on {deliv}')
                                cal_dates.append(gout)
                                cal_dates.append(gin)
                                dtype = 'Pull and deliver not return'
                        else:
                            if exportj:
                                cal_message.append('Pull empty and deliver')
                                cal_message.append(f'Return now loaded container still out from {deliv}')
                                cal_dates.append(gout)
                                cal_dates.append(gin)
                                dtype = 'Pull and deliver not return'
                            if importj:
                                cal_message.append('Pull load and deliver')
                                cal_message.append(f'Return container still out from {deliv}')
                                cal_dates.append(gout)
                                cal_dates.append(gin)
                                dtype = 'Pull and deliver not return'

                    elif gout != deliv and deliv == gin:
                        if droppick:
                            if exportj:
                                cal_message.append(f'Prepull empty container for drop {deliv}')
                                cal_message.append(f'Pick loaded container and return')
                                cal_dates.append(gout)
                                cal_dates.append(gin)
                                dtype = 'Prepull then deliver and return'
                            if importj:
                                cal_message.append(f'Prepull loaded container for drop {deliv}')
                                cal_message.append(f'Pick empty container and return')
                                cal_dates.append(gout)
                                cal_dates.append(gin)
                                dtype = 'Prepull then deliver and return'
                        else:
                            if exportj:
                                cal_message.append(f'Prepull empty container, deliver {deliv}')
                                cal_message.append(f'Deliver container{delmess} and return load')
                                cal_dates.append(gout)
                                cal_dates.append(gin)
                                dtype = 'Prepull then deliver and return'
                            if importj:
                                cal_message.append(f'Prepull loaded container, deliver {deliv}')
                                cal_message.append(f'Deliver container{delmess} and return empty')
                                cal_dates.append(gout)
                                cal_dates.append(gin)
                                dtype = 'Prepull then deliver and return'


                    elif gout != deliv and deliv != gin:
                        if droppick:
                            if exportj:
                                cal_message.append(f'Prepull empty container for drop {deliv}')
                                cal_message.append(f'Drop empty container{delmess} for loading')
                                cal_message.append(f'Pick now-loaded container for port entry')
                                cal_dates.append(gout)
                                cal_dates.append(deliv)
                                cal_dates.append(gin)
                                dtype = 'Prepull, then deliver, then return'
                            if importj:
                                cal_message.append(f'Prepull loaded container for drop {deliv}')
                                cal_message.append(f'Drop loaded container{delmess}')
                                cal_message.append(f'Return now-empty container')
                                cal_dates.append(gout)
                                cal_dates.append(deliv)
                                cal_dates.append(gin)
                                dtype = 'Prepull, then deliver, then return'
                        else:
                            if exportj:
                                cal_message.append(f'Prepull empty container today, deliver {deliv}')
                                cal_message.append(f'Deliver container{delmess} but return {gin}')
                                cal_message.append(f'Return now-loaded container to port')
                                cal_dates.append(gout)
                                cal_dates.append(deliv)
                                cal_dates.append(gin)
                                dtype = 'Prepull, then deliver, then return'
                            if importj:
                                cal_message.append(f'Prepull loaded container today, deliver {deliv}')
                                cal_message.append(f'Deliver container{delmess} but return {gin}')
                                cal_message.append(f'Return now-empty container to port')
                                cal_dates.append(gout)
                                cal_dates.append(deliv)
                                cal_dates.append(gin)
                                dtype = 'Prepull, then deliver, then return'


                    #Must return dates in a valid date format or the api readers will fail
                    gateout = f'{gout}'
                    gatein = f'{gin}'
                    delivery = f'{deliv}'

                    if isinstance(odat.Date4, date):
                        port_early = f'{odat.Date4}'
                    else:
                        port_early = fd
                    if isinstance(odat.Date5, date):
                        port_late = f'{odat.Date5}'
                    else:
                        port_late = fd
                    if isinstance(odat.Date6, date):
                        dueback = f'{odat.Date6}'
                    else:
                        dueback = fd

                    if isinstance(earliest, date):
                        earliest_str = f'{earliest}'
                    else:
                        earliest_str = fd

                    if isinstance(latest, date):
                        latest_str = f'{latest}'
                    else:
                        latest_str = fd


                    if hstat <= 0:
                        status = 'Unpulled'
                    elif hstat == 1:
                        status = 'Out'
                    elif hstat >= 2:
                        status = 'Returned'
                    else:
                        status = 'Undefined'

                    if hstat <= 0 and 'Export' in htype:
                        print(f'Export job has not been pulled yet')
                        container = 'Unpulled Export'

                    for ix in range(len(cal_message)):
                        cal_id += 1

                        this_cal_date = f'{cal_dates[ix]}'

                        ret_data.append({'id': cal_id, 'jo': odat.Jo, 'scac': scac, 'shipper': odat.Shipper, 'release':booking,
                                          'container': container, 'status': status, 'haulType':htype, 'delAddress':del_address,
                                          'gateOut': gateout, 'gateIn': gatein, 'delivery': delivery,
                                          'portEarly': port_early, 'portLate': port_late, 'dueBack':dueback,
                                          'calDate':this_cal_date, 'calMessage':cal_message[ix], 'delType':dtype
                                         })
                else:
                    print(f'We have bad dates on container {container}')
        #Now sort the return data by the calendar dates
        ret_data_sorted = sorted(ret_data, key=lambda x: x['calDate'])

        return ret_data_sorted



    elif data_needed == 'active_shippers':

        #postman api test call is: http://127.0.0.1:5000/get_api_data?data_needed=active_customers&arglist=[]
        lb_days = 60
        lbdate = now.date()
        lbdate = lbdate - timedelta(days=lb_days)
        print(f'Looking back to this date: {lbdate}')
        odata = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat < 2)).all()
        shippers = []
        ret_data = []
        for odat in odata:
            shipper = odat.Shipper
            if shipper not in shippers: shippers.append(shipper)
        for ix, shipper in enumerate(shippers):
            ret_data.append({'id': ix+1, 'Shipper': shipper})

        return ret_data

    elif data_needed == 'drivers':
        info_id = 0
        ret_data = []
        odata = Drivers.query.filter(Drivers.Active==1).all()
        for odat in odata:
            info_id += 1
            name = odat.Name
            phone = odat.Phone
            email = odat.Email
            cdl = odat.CDLnum
            if name is None: name = 'xxx'
            if phone is None: phone = 'xxx'
            if email is None: email = 'xxx'
            if cdl is None: cdl = 'xxx'
            ret_data.append({'id': info_id, 'name': name, 'phone': phone, 'email': email, 'cdl': cdl})

        print(ret_data)
        return ret_data

    elif data_needed == 'pindrivers':
        info_id = 0
        ret_data = []
        odata = Drivers.query.filter(Drivers.Active == 1).all()
        for odat in odata:
            info_id += 1
            name = odat.Name
            if name is None: name = 'xxx'
            ret_data.append({'id': info_id, 'name': name})

        print(ret_data)

        return ret_data

    elif data_needed == 'pintrucks':
        info_id = 0
        ret_data = []
        odata = Vehicles.query.filter(Vehicles.Active == 1).all()
        for odat in odata:
            info_id += 1
            unit = odat.Unit
            if unit is None: unit = 'xxx'
            ret_data.append({'id': info_id, 'unit': unit})

        print(ret_data)

        return ret_data

    elif data_needed == 'piningates':
        lb_days = 60
        today = now.date()
        lbdate = today - timedelta(days=lb_days)
        info_id = 0
        ret_data = []
        odata = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat == 1)).order_by(Orders.Date).all()
        for odat in odata:
            info_id += 1
            unit = odat.Container
            if unit is None: unit = 'xxx'
            ret_data.append({'id': info_id, 'unit': unit})

        print(ret_data)

        return ret_data

    elif data_needed == 'pinoutgates':
        lb_days = 60
        today = now.date()
        lbdate = today - timedelta(days=lb_days)
        info_id = 0
        ret_data = []
        odata = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat < 1)).order_by(Orders.Date).all()
        for odat in odata:
            info_id += 1
            unit = odat.Container
            if not hasinput(unit):
                unit = odat.Booking
            if not hasinput(unit):
                unit = 'xxx'
            ret_data.append({'id': info_id, 'unit': unit})

        print(ret_data)

        return ret_data

    elif data_needed == 'pintimes':
        timenow = now.time()
        print(f'Current is: {timenow}')
        info_id = 0
        ret_data = []
        #timedata = [time(hour=7, minute=0, second=0, microsecond=0), time(hour=8, minute=0, second=0, microsecond=0),
         #           time(hour=9, minute=0, second=0, microsecond=0), time(hour=10, minute=0, second=0, microsecond=0),
          #          time(hour=11, minute=0, second=0, microsecond=0), time(hour=12, minute=0, second=0, microsecond=0),
           #         time(hour=13, minute=0, second=0, microsecond=0), time(hour=14, minute=0, second=0, microsecond=0),
            #        time(hour=15, minute=0, second=0, microsecond=0), time(hour=16, minute=30, second=0, microsecond=0)]

        odata = ['6:00-7:00', '7:00-8:00', '8:00-9:00', '9:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:30']
        for jx, odat in enumerate(odata):
            #timetest = timedata[jx]
            #dt1 = datetime.combine(datetime.today(), timenow)
            #dt2 = datetime.combine(datetime.today(), timetest)
            #timedeltamin = dt2 - dt1
            #timedeltamin = timedeltamin.total_seconds() / 60
            #print(f'Current time is: {timenow} back time range is: {timetest} and timedelta is: {timedeltamin}')
            #if timedeltamin >= 15:
            info_id += 1
            ret_data.append({'id': info_id, 'name': odat})

        print(ret_data)

        return ret_data

    elif data_needed == 'pindates':
        print('entering pindates')
        start_date = date.today()
        weekdays = []
        current = start_date
        info_id = 1
        print(f'the current data is {current}')
        while len(weekdays) < 3:
            # weekday(): Monday=0 ... Sunday=6
            if current.weekday() < 5:
                display = current.strftime("%a %b %d")
                weekdays.append({'id': info_id, 'date': f'{current}', 'display': display})
                info_id += 1
            current += timedelta(days=1)

        print(weekdays)

        return weekdays

    elif data_needed == 'financials':
        fin_id = 0
        ret_data = []
        odata = Openi.query.order_by(Openi.Open.desc()).all()
        for odat in odata:
            fin_id += 1
            if odat.Company == 'TOTAL':
                lastitem = [fin_id, odat.Company, intdol(odat.Open)]
            else:
                ret_data.append({'id': fin_id, 'company': odat.Company, 'ototal': intdol(odat.Open), 'duenow': intdol(odat.U30)})

        print(ret_data)

        return ret_data

    else:
        return []

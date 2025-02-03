from webapp import db
from webapp.models import OverSeas, Orders, People, Interchange, Bookings
from flask import session, request
from webapp.viewfuncs import d2s, stat_update, hasinput
import datetime
import pytz
from datetime import timedelta
import ast

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

    elif data_needed == 'active_containers':

        #postman api test call is: http://127.0.0.1:5000/get_api_data?data_needed=active_containers&arglist=[]
        lb_days = 60
        today = now.date()
        lbdate = today - timedelta(days=lb_days)
        active_date = today + timedelta(days=10)
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
                if isinstance(odat.Date, datetime.date):
                    gateout = f'{odat.Date}'
                else:
                    gateout = fd
                if isinstance(odat.Date2, datetime.date):
                    gatein = f'{odat.Date2}'
                else:
                    gatein = fd
                if isinstance(odat.Date3, datetime.date):
                    delivery = f'{odat.Date3}'
                else:
                    delivery = fd
                if isinstance(odat.Date4, datetime.date):
                    port_early = f'{odat.Date4}'
                else:
                    port_early = fd
                if isinstance(odat.Date5, datetime.date):
                    port_late = f'{odat.Date5}'
                else:
                    port_late = fd
                if isinstance(odat.Date6, datetime.date):
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


        for odat in odata:
            hstat = odat.Hstat
            container = odat.Container
            if hstat >= 2 and odat.Date2 < active_date:
                print(f'Container {container} returned before the active date of {active_date}')
            else:
                booking = odat.Booking
                htype = odat.HaulType
                del_address = odat.Dropblock2

                # Determine how many calendar entries we have for each job based on the gatein, gateout, and delivery dates
                gout = odat.Date
                gin = odat.Date2
                deliv = odat.Date3
                if isinstance(gout, datetime.date) and isinstance(gin, datetime.date) and isinstance(deliv, datetime.date):
                    print('We have three good dates')
                    #We have three good dates to use and compare
                    cal_message = []
                    cal_dates = []
                    if gout == deliv and gout == gin:
                        #Plan is to pull deliv and return same day
                        cal_message.append('Pull, deliver, and return same day')
                        cal_dates.append(gout)
                        dtype = 'All same day'
                    elif gout == deliv and gout != gin:
                        cal_message.append('Pull and deliver today')
                        cal_message.append(f'Return container still out from {deliv}')
                        cal_dates.append(gout)
                        cal_dates.append(gin)
                        dtype = 'Pull and deliver not return'
                    elif gout != deliv and deliv == gin:
                        cal_message.append(f'Pull container today, deliver {deliv}')
                        cal_message.append(f'Deliver container and return')
                        cal_dates.append(gout)
                        cal_dates.append(gin)
                        dtype = 'Prepull then deliver and return'
                    elif gout != deliv and deliv != gin:
                        cal_message.append(f'Pull container today, deliver {deliv}')
                        cal_message.append(f'Deliver container today but return {gout}')
                        cal_message.append(f'Return container today')
                        cal_dates.append(gout)
                        cal_dates.append(deliv)
                        cal_dates.append(gin)
                        dtype = 'Prepull, then deliver, then return'

                    #Must return dates in a valid date format or the api readers will fail
                    gateout = f'{gout}'
                    gatein = f'{gin}'
                    delivery = f'{deliv}'

                    if isinstance(odat.Date4, datetime.date):
                        port_early = f'{odat.Date4}'
                    else:
                        port_early = fd
                    if isinstance(odat.Date5, datetime.date):
                        port_late = f'{odat.Date5}'
                    else:
                        port_late = fd
                    if isinstance(odat.Date6, datetime.date):
                        dueback = f'{odat.Date6}'
                    else:
                        dueback = fd

                    if isinstance(earliest, datetime.date):
                        earliest_str = f'{earliest}'
                    else:
                        earliest_str = fd

                    if isinstance(latest, datetime.date):
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

    else:
        return []

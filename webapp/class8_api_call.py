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
        print(f'Looking back to this date: {lbdate}')
        odata = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Hstat < 2)).order_by(Orders.Date).all()
        ret_data = []
        for odat in odata:
            hstat = odat.Hstat
            htype = odat.HaulType
            container = odat.Container
            booking = odat.Booking
            if hstat >= 2 and odat.Date2 < active_date:
                print(f'Container {container} returned before the active date of {active_date}')
            else:
                gateout = f'{odat.Date}'
                gatein = f'{odat.Date2}'
                delivery = f'{odat.Date3}'
                port_early = f'{odat.Date4}'
                port_late = f'{odat.Date5}'
                dueback = f'{odat.Date6}'

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
                                  'container': container, 'status': status, 'gateOut': gateout, 'gateIn': gatein, 'delivery': delivery, 'portEarly': port_early, 'portLate': port_late, 'dueBack':dueback})

        return ret_data

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

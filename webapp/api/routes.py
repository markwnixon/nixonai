from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from webapp.extensions import db
from webapp.models import Orders, users, Pins
from webapp.viewfuncs import hasinput
from webapp.CCC_system_setup import addpath, scac, tpath
from webapp.services.api_data_service import api_call


import os
import datetime
now = datetime.datetime.now()

from flask import Blueprint
api_bp = Blueprint('api_bp', __name__)

@api_bp.route('/api/test')
def api_test():
    return {"message": "API blueprint working"}


@api_bp.route("/upload_pdf", methods=["POST"])
#@jwt_required()
def pdf_upload():
    username = request.form.get("username")
    container_number = request.form.get("container_number")
    file = request.files.get("file")

    print(f'The user uploading this file is: {username} for container {container_number} and file is {file}')


    if not username or not container_number or not file:
        return jsonify({"error": "Missing username, container number, or file"}), 400

    udat = users.query.filter(users.username == username).first()
    if udat is not None:
        utype = udat.authority
    else:
        utype = ''
    odat = Orders.query.filter(Orders.Container == container_number).order_by(Orders.id.desc()).first()
    if odat is not None:
        pcache = odat.D1cache
        if not hasinput(pcache): pcache = 1
        jo = odat.Jo
        filename = f'Proof_{jo}_{container_number}_c{str(pcache)}.pdf'
        outputpath = addpath(tpath('Orders-DrvProof', filename))
        odat.D1cache = pcache + 1
        odat.DrvProof = filename
        if utype == 'driver':
            odat.Driver = udat.name
        db.session.commit()
        file.save(outputpath)
        print(f'Saving file: {file} as {outputpath}')
        return jsonify({
            "message": "Uploaded successfully",
            "file": filename
        })

    else:
        return jsonify({"error": "Container not found in database"}), 400

@api_bp.route("/get_pins_now", methods=["GET"])
#@jwt_required(refresh=True)
def getpinsnow():
    pinid = request.args.get("pinid")
    #scac = request.args.get("scac")

    if not pinid or not scac:
        return {"error": "Missing scac or pinid"}, 400

    queue_dir = "/home/nixonai/tasks"
    queue_file = f"{queue_dir}/task_queue.txt"
    os.makedirs(queue_dir, exist_ok=True)

    job_line = f"{scac}|{pinid}\n"

    with open(queue_file, "a") as f:
        f.write(job_line)

    return {
        "status": "queued",
        "scac": scac,
        "pinid": pinid
    }


@api_bp.route("/pin_task_status", methods=["GET", "POST"])
def pin_task_status():
    pinid = request.args.get("pinid")
    print(f'Reviewing Status for pinid {pinid}')
    pinid = int(pinid)
    pin = db.session.get(Pins, pinid)

    if pin is not None:
        return_note = pin.Notes
        intext = pin.Intext
        outtext = pin.Outtext
        if 'Error' in return_note or 'Pin made' in return_note:
            return jsonify({"pinid": pinid, "message": "Completed", "note": return_note, "intext": intext, "outtext": outtext}), 200
        else:
            return jsonify({"pinid": pinid, "message": "NeedPin", "note": return_note, "intext": intext, "outtext": outtext}), 200
    else:
        return jsonify({"pinid": pinid, "message": "Missing task_id", "note": "Pin Not in Database", "intext": "Unknown", "outtext": "Unknown"}), 400



@api_bp.route("/get_pdf_for_container", methods=["GET"])
#@jwt_required()
def pdf_download():
    container_number = request.args.get("container_number")
    #file = request.files.get("file")
    print(f'Getting pdf files for container {container_number}')

    if not container_number:
        return jsonify({"error": "Missing container number or file"}), 400


    odat = Orders.query.filter(Orders.Container == container_number).order_by(Orders.id.desc()).first()
    if odat is not None:
        fileM = odat.Manifest
        if not fileM:
            print('There is no Manifest')
            filename = odat.Source
            outputpath = addpath(tpath('Orders-Source', filename))
        else:
            print('Using the Manifest')
            filename = odat.Manifest
            outputpath = addpath(tpath('Orders-Manifest', filename))

        return send_file(outputpath, mimetype="application/pdf")


    else:
        return jsonify({"error": "Container not found in database"}), 400


@api_bp.route('/get_existing_pins', methods=['GET', 'PUT', 'POST'])
@jwt_required()
def get_existing_pins():
    current_user = get_jwt_identity()
    print(f'user: {current_user}')
    maker = f'API-{current_user}'

    if request.method == 'GET':
        print(f'This is a GET of the existing pins for maker {maker}')
        #data_needed = request.args.get('data_needed')
        #print(f'data_needed: {data_needed}')
        #data = request.get_json()
        #print(f'data: {data}')

        lb_days = 60
        today = now.date()
        lbdate = today - timedelta(days=lb_days)
        active_date = today + timedelta(days=10)
        fd = '1900-01-01'
        print(f'Looking back to this date: {lbdate}')
        pdata = Pins.query.filter(Pins.Maker == maker).all()
        ret_data = []
        for pdat in pdata:
            havepin = pdat.OutPin
            if havepin == '0':
                mess = 'NeedPin'
            else:
                mess = 'HavePin'
            ret_data.append({'message': mess,'pinid': pdat.id, 'intext': pdat.Intext, 'outtext' : pdat.Outtext, 'note': pdat.Notes})
        print(f'return data is: {ret_data}')
        return ret_data


@api_bp.route('/delete_pin', methods=['GET', 'PUT', 'POST'])
@jwt_required()
def delete_pin():
    current_user = get_jwt_identity()
    print(f'user: {current_user}')

    if request.method == 'POST':
        print('This is a POST')
        pinid = request.args.get('pinid')
        print(f'pinid: {pinid}')
        pinid = int(pinid)
        pin = db.session.get(Pins, pinid)
        if pin:
            db.session.delete(pin)
            db.session.commit()
            return 'Success', 200
        else:
            return 'Already Deleted', 200

    return 'Failed', 400


@api_bp.route('/get_api_data', methods=['GET', 'PUT', 'POST'])
@jwt_required()
def handle_data():
    current_user = get_jwt_identity()
    print(f'user: {current_user}')

    if request.method == 'PUT':
        print('This is a put')
        data_needed = request.args.get('data_needed')
        print(f'data_needed: {data_needed}')

        if 'test1' in data_needed:
            print('made it to test1')
            data = request.get_json()
            print("Data received successfully:", data)
            old_data = [{'id':1,'container':'CAAU8649700','shipper':'one'},
                        {'id':2,'container':'XXXX8649700','shipper':'two'}]
            # Update the changes
            print(data['id'])
            if data:
                changeid = data['id']
                old_match = [item for item in old_data if item['id'] == changeid]
                con1 = old_match[0]['container']
                con2 = data['container']
                ship1 = old_match[0]['shipper']
                ship2 = data['shipper']
                print(con1, con2, ship1, ship2)
                if con1 == con2:
                    print('no update for containers')
                if ship1 == ship2:
                    print('no update for shipper')
                else:
                    print(f'Updating database for shipper from {ship1} to {ship2}')


            if not data:
                return jsonify({'error':'No data received'}), 400

            return jsonify({'message': 'Data received', 'data':data}), 200


    elif request.method == 'GET':
        data_needed = request.args.get('data_needed')
        #data_needed = 'api_test_two'
        print(f'This is a get request for data_needed:{data_needed}:')

        arglist = request.args.get('arglist')
        print(f'Was able to get the payload data for arglist:{arglist}:')

        data_return = api_call(scac, now, data_needed, arglist)
        return jsonify(data_return)

    else:
        return []

@api_bp.route('/make_pin_data', methods=['GET', 'PUT', 'POST'])
@jwt_required()
def make_pin_data():
    current_user = get_jwt_identity()
    print(f'user: {current_user}')

    if request.method == 'POST':
        print('This is a POST')
        data_needed = request.args.get('data_needed')
        print(f'data_needed: {data_needed}')
        data = request.get_json()
        print(f'data: {data}')

        lb_days = 60
        today = now.date()
        lbdate = today - timedelta(days=lb_days)
        active_date = today + timedelta(days=10)

        driver = data['driver']
        unit = data['truck']
        ingate = data['ingate']
        outgate = data['outgate']
        pintime = data['pintime']
        pindate = data['pindate']

        print(f' The pin date requested is {pindate} and timeslot {pintime}')
        pindate_obj = datetime.datetime.strptime(pindate, "%Y-%m-%d").date()
        print(f' The pin date object requested is {pindate_obj}')

        try:
            chassis = data['chassis']
        except:
            chassis = ''

        vdat = Vehicles.query.filter(Vehicles.Unit == unit).first()
        if vdat is not None:
            tag = vdat.Plate
        ddat = Drivers.query.filter(Drivers.Name == driver).first()
        if ddat is not None:
            phone = ddat.Phone
        indat = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Container == ingate)).first()
        if indat is not None:
            incon = indat.Container
            inchas = indat.Chassis
            contype = indat.Type

            ht = indat.HaulType
            ctext = ''
            if '45' in contype and '9' in contype: ctext = '45HC'
            if '40' in contype and '9' in contype: ctext = '40HC'
            if '40' in contype and '8' in contype: ctext = '40STD'
            if '45' in contype and '8' in contype: ctext = '45STD'
            if '20' in contype: ctext = '20'
            if 'R' in contype: ctext = ctext + ' Reefer'
            if 'U' in contype: ctext = ctext + ' OpenTop'

            address = indat.Dropblock2
            adata, backup = get_address_details(address)
            try:
                city = adata['city']
            except:
                city = backup

            if city == 'Baltimore':
                citiline = indat.Shipper
                citiline = citiline.split()
                city = citiline[0]

            if not hasinput(city):
                citiline = indat.Shipper
                citiline = citiline.split()
                city = citiline[0]

            if 'Export' in ht:
                if hasinput(indat.BOL):
                    inbook = indat.BOL
                else:
                    inbook = indat.Booking
                inbook = inbook.split('-', 1)[0]
                intext = f'Load In: *{inbook}  {incon}* ({ctext} {city})'

            if 'Import' in ht:
                intext = f'Empty In: *{incon}* ({ctext} {city})'
                inbook = None

        else:
            incon = None
            inbook = None
            inchas = chassis
            intext = 'Bare Chassis In'

        outdat = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Container == outgate)).first()
        if outdat is not None:
            outcon = outdat.Container
            outbook = outdat.Booking
        else:
            #Try matching on booking, cust be an empty out
            outdat = Orders.query.filter((Orders.Date3 > lbdate) & (Orders.Booking == outgate)).first()
            if outdat is not None:
                outcon = outdat.Container
                outbook = outdat.Booking
            else:
                outcon = None
                outbook = None
        if outdat is not None:
            outchas = inchas
            contype = outdat.Type

            ht = outdat.HaulType
            ctext = ''
            if '45' in contype and '9' in contype: ctext = '45HC'
            if '40' in contype and '9' in contype: ctext = '40HC'
            if '40' in contype and '8' in contype: ctext = '40STD'
            if '45' in contype and '8' in contype: ctext = '45STD'
            if '20' in contype: ctext = '20'
            if 'R' in contype: ctext = ctext + ' Reefer'
            if 'U' in contype: ctext = ctext + ' OpenTop'

            address = outdat.Dropblock2
            adata, backup = get_address_details(address)
            try:
                city = adata['city']
            except:
                city = backup

            if city == 'Baltimore':
                citiline = outdat.Shipper
                citiline = citiline.split()
                city = citiline[0]

            if not hasinput(city):
                citiline = outdat.Shipper
                citiline = citiline.split()
                city = citiline[0]

            if 'Export' in ht:
                outbook = outdat.Booking
                outbook = outbook.split('-', 1)[0]
                outtext = f'Empty Out: *{outbook}* ({ctext} {city})'

            if 'Import' in ht:
                try:
                    rel4 = outdat.Booking[-4:]
                except:
                    rel4 = outdat.Booking
                outtext = f'Load Out: *{rel4}  {outcon}* ({ctext} {city})'

        else:
            outcon = None
            outbook = None
            outchas = inchas
            outtext = 'Nothing Out'
        #Add this data to the pin database for today:
        #today = now.date()
        inpin = '0'
        outpin = '0'
        if inchas == None: inchas = 'OSLM007'
        # Now get the intext and outtext:
        #add_day = 2 # Need to make this an api argument
        #thisdate = today + timedelta(days=add_day)
        if driver is not None and unit is not None and inchas is not None:
            note = f'Will get pin for {driver} in unit {unit} using chassis {inchas} for {pindate_obj} {pintime}'

        input = Pins(Date=pindate_obj, Driver=driver, InBook=inbook, InCon=incon, InChas=inchas, InPin=inpin,
                     OutBook=outbook, OutCon=outcon, OutChas=outchas, OutPin=outpin, Unit=unit, Tag=tag, Phone=phone,
                     Timeslot=pintime, Intext=intext, Outtext=outtext, Notes=note, Active=0, Maker=f'API-{current_user}')
        db.session.add(input)
        db.session.commit()
        print(f'The new row has id {input.id}')

        #pdat = Pins.query.get(input.id)

        #pdat = Pins.query.filter(Pins.InCon == incon).first()
        #pinid = pdat.id

        return jsonify({'message': 'NeedPin', 'pinid': input.id, 'intext': intext, 'outtext' : outtext, 'note': note}), 200

    else:
        return jsonify({'error': 'No data received'}), 400
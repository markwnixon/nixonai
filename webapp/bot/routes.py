from flask import Blueprint, jsonify, request
from webapp.bot.decorators import bot_token_required
from webapp.services.api_data_service import api_call
from webapp.CCC_system_setup import scac, companydata, addpath, tpath
import datetime
from datetime import datetime, timedelta

from webapp.extensions import db
from webapp.models import Orders, People, Drops

# adjust these imports to match your app
from webapp.viewfuncs import newjo
from webapp.class8_tasks import next_business_day, Order_Addresses_Update, Add_New_Drop
import os
from sqlalchemy import func

bot_bp = Blueprint('bot_bp', __name__)

now = datetime.now()

def save_order_upload_file(order_row, uploaded_file, filetype):

    if uploaded_file is None:
        return None, None

    if uploaded_file.filename == '':
        return None, 'No file selected for upload'

    name, exto = os.path.splitext(uploaded_file.filename)
    ext = exto.lower()

    if ext != '.pdf':
        return None, 'Source file must be a PDF'

    fileout = f'Jo_{order_row.Jo}'

    if filetype == 'Source': sname = 'Scache'
    if filetype == 'Proof': sname = 'Pcache'
    if filetype == 'RateCon': sname = 'Rcache'

    # current cache value
    sn = getattr(order_row, sname)

    try:
        sn = int(sn)
        bn = sn + 1
    except:
        sn = 0
        bn = 0


    filename1 = f'{filetype}_{fileout}_c{str(bn)}{ext}'
    print(addpath(tpath(f'Orders-{filetype}', filename1)))
    output1 = addpath(tpath(f'Orders-{filetype}', filename1))

    uploaded_file.save(output1)

    # cleanup previous version if exists
    if bn > 0:
        oldfile = f'{filetype}_{fileout}_c{str(sn)}{exto}'
        oldoutput = addpath(tpath(f'Orders-{filetype}', oldfile))
        try:
            os.remove(oldoutput)
        except:
            pass

    # update DB fields
    setattr(order_row, filetype, filename1)
    setattr(order_row, sname, bn)

    return filename1, None


@bot_bp.route('/bot/get_api_data', methods=['GET'])
@bot_token_required(required_scopes={'read:orders'})
def bot_get_api_data():
    data_needed = request.args.get('data_needed')
    arglist = request.args.get('arglist')

    data = api_call(scac, now, data_needed, arglist)

    return jsonify(data), 200

@bot_bp.route('/bot/orders', methods=['GET'])
@bot_token_required(required_scopes={'read:orders'})
def bot_orders():
    days = request.args.get('days', default=30, type=int)
    limit = request.args.get('limit', default=200, type=int)

    if days is None or days < 1:
        days = 30
    if days > 365:
        days = 365

    if limit is None or limit < 1:
        limit = 200
    if limit > 1000:
        limit = 1000

    cutoff = datetime.now() - timedelta(days=days)

    query = (
        Orders.query
        .filter(Orders.Date3 != None)
        .filter(Orders.Date3 >= cutoff)
        .order_by(Orders.Date3.desc(), Orders.id.desc())
    )

    shipper = request.args.get('shipper')
    if shipper:
        query = query.filter(Orders.Shipper == shipper)

    container = request.args.get('container')
    if container:
        query = query.filter(Orders.Container == container)

    booking = request.args.get('booking')
    if booking:
        query = query.filter(Orders.Booking == booking)

    hstat = request.args.get('hstat', type=int)
    if hstat is not None:
        query = query.filter(Orders.Hstat == hstat)

    rows = query.limit(limit).all()

    orders = []
    for odat in rows:
        orders.append({
            "id": odat.id,
            "jo": odat.Jo,
            "haulType": odat.HaulType,
            "terminal": odat.Company,
            "release": odat.Booking,
            "inBooking": odat.BOL,
            "container": odat.Container,
            "containerType": odat.Type,
            "deliveryType": odat.Delivery,
            "gateOut": odat.Date.isoformat() if odat.Date else None,
            "gateIn": odat.Date2.isoformat() if odat.Date2 else None,
            "deliveryDate": odat.Date3.isoformat() if odat.Date3 else None,
            "portWindow1": odat.Date4.isoformat() if odat.Date4 else None,
            "portWindow2": odat.Date5.isoformat() if odat.Date5 else None,
            "shipper": odat.Shipper,
            "dropAddress": odat.Dropblock2,
            "hstat": odat.Hstat,
            "driver": odat.Driver,
            "truck": odat.Truck
        })

    return jsonify({
        "days": days,
        "limit": limit,
        "count": len(orders),
        "orders": orders
    }), 200

@bot_bp.route('/bot/orders/<int:order_id>', methods=['GET'])
@bot_token_required(required_scopes={'read:orders'})
def bot_order_detail(order_id):
    odat = Orders.query.get_or_404(order_id)

    return jsonify({
        "id": odat.id,
        "jo": odat.Jo,
        "shipper": odat.Shipper,
        "container": odat.Container,
        "booking": odat.Booking,
        "haulType": odat.HaulType,
        "status": odat.Status,
        "driver": odat.Driver,
        "dropAddress": odat.Dropblock2,
        "date3": odat.Date3.isoformat() if odat.Date3 else None,
        "hstat": odat.Hstat
    }), 200

@bot_bp.route('/bot/orders/by_container', methods=['GET'])
@bot_token_required(required_scopes={'read:orders'})
def bot_orders_by_container():
    container = request.args.get('container')

    if not container:
        return jsonify({"message": "container required"}), 400

    rows = Orders.query.filter(Orders.Container == container)\
        .order_by(Orders.Date3.desc())\
        .limit(20).all()

    return jsonify([{
        "id": o.id,
        "jo": o.Jo,
        "status": o.Status,
        "date3": o.Date3.isoformat() if o.Date3 else None
    } for o in rows]), 200

@bot_bp.route('/bot/orders/summary', methods=['GET'])
@bot_token_required(required_scopes={'read:orders'})
def bot_orders_summary():
    total = Orders.query.count()
    active = Orders.query.filter(Orders.Hstat == 1).count()
    unpulled = Orders.query.filter(Orders.Hstat == 0).count()

    return jsonify({
        "total_orders": total,
        "active_orders": active,
        "unpulled_orders": unpulled
    }), 200


def _size_text(container_type):
    ctype = str(container_type or "40").strip()

    if ctype == "40":
        return """40' GP 9'6\""""
    if ctype == "20":
        return """20' GP 8'6\""""
    return ctype


def _party_ids(shipper_name, port_name='Baltimore Seagirt'):
    pdat = People.query.filter(People.Company == shipper_name).first()
    if pdat is None:
        return None, None, None, f"People record not found for {shipper_name}"

    ldat = Drops.query.filter(Drops.Entity == shipper_name).first()
    if ldat is None:
        return None, None, None, f"Drops record not found for {shipper_name}"

    ddat = Drops.query.filter(Drops.Entity == port_name).first()
    if ddat is None:
        return None, None, None, f"Drops record not found for {port_name}"

    return pdat.id, ldat.id, ddat.id, None


def _is_export_haul(haul_type):
    h = (haul_type or "").lower()
    return "export" in h


def _is_import_haul(haul_type):
    h = (haul_type or "").lower()
    return "import" in h


@bot_bp.route('/bot/orders/create', methods=['POST'])
@bot_token_required(required_scopes={'write:orders'})
def bot_create_order():
    # Accept either JSON or multipart/form-data
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        data = request.form.to_dict()
        source_file = request.files.get('source_file')
        ratecon_file = request.files.get('ratecon_file')
    else:
        data = request.get_json(silent=True) or {}
        source_file = None
        ratecon_file = None

    haul_type = (data.get('haul_type') or '').strip()
    shipper = (data.get('shipper') or '').strip()
    loading_location = (data.get('loading_location') or '').strip()
    loading_address = (data.get('loading_address') or '').strip()
    container_type = data.get('container_type', '40')
    booking = (data.get('booking') or '').strip()
    bol = (data.get('bol') or '').strip()
    container = (data.get('container') or '').strip()
    order = (data.get('order') or '').strip()
    if order == '': order = None
    amount = (data.get('amount') or '').strip()
    quote = (data.get('quote') or '').strip()
    if amount == '':
        amount = '0.00'
    if quote == '':
        quote = None

    if not haul_type:
        return jsonify({"message": "haul_type is required"}), 400

    if not shipper:
        return jsonify({"message": "shipper is required"}), 400

    if not loading_location:
        return jsonify({"message": "loading_location is required"}), 400

    if not loading_address:
        return jsonify({"message": "loading_address is required"}), 400

    if not container_type:
        return jsonify({"message": "container_type is required"}), 400

    is_export = _is_export_haul(haul_type)
    is_import = _is_import_haul(haul_type)

    if not is_export and not is_import:
        return jsonify({
            "message": "haul_type must include either 'Export' or 'Import'"
        }), 400

    if is_export:
        if not booking:
            return jsonify({
                "message": "booking is required for export haul types"
            }), 400

    if is_import:
        if not bol:
            return jsonify({
                "message": "bol is required for import haul types"
            }), 400
        if not container:
            return jsonify({
                "message": "container is required for import haul types"
            }), 400

    # Keep this check: shipper should exist in People
    pdat = People.query.filter(People.Company == shipper).first()
    if pdat is None:
        return jsonify({
            "message": f"People record not found for {shipper}"
        }), 400

    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    putsize = _size_text(container_type)

    # Keep terminal hardwired for now
    terminal_name = 'Baltimore Seagirt'
    terminal_address = 'Baltimore Seagirt\n2600 Broening Hwy\nBaltimore, MD 21224'

    try:
        if is_export:
            existing_count = (
                db.session.query(func.count(Orders.id))
                .filter(Orders.Booking == booking)
                .scalar()
            )

            if existing_count >= 6:
                return jsonify({
                    "message": "Skipped duplicate export",
                    "reason": "booking limit reached (6 max)",
                    "booking": booking,
                    "current_count": existing_count
                }), 200

            cdata = companydata()
            jbcode = cdata[10] + 'T'
            nextjo = newjo(jbcode, today_str)

            input_row = Orders(
                Status='AO',
                Jo=nextjo,
                HaulType=haul_type,
                Order=order,
                Bid=pdat.id,          # initial value; Order_Addresses_Update will confirm/reset
                Lid=None,             # let Order_Addresses_Update set this
                Did=None,             # let Order_Addresses_Update set this
                Company2=loading_location,
                Location=None,
                BOL=None,
                Booking=booking,
                Container=None,
                Driver=None,
                Pickup=None,
                Delivery=None,
                Amount=amount,
                Date=today,
                Time=None,
                Time3=None,
                Date2=today,
                Time2=None,
                PaidInvoice=None,
                Source=None,
                Description=None,
                Chassis=None,
                Detention=None,
                Storage=None,
                Release=0,
                Company=terminal_name,
                Seal=None,
                Shipper=shipper,
                Type=putsize,
                Label=None,
                Dropblock2=loading_address,
                Dropblock1=terminal_address,
                Commodity=None,
                Packing=None,
                Links=None,
                Hstat=-1,
                Istat=-1,
                Proof=None,
                Invoice=None,
                Gate=None,
                Package=None,
                Manifest=None,
                Scache=0,
                Pcache=0,
                Icache=0,
                Mcache=0,
                Pkcache=0,
                QBi=None,
                InvoTotal='0.00',
                Truck=None,
                Dropblock3=None,
                Date3=today,
                Location3=None,
                InvoDate=None,
                PaidDate=None,
                PaidAmt=None,
                PayRef=None,
                PayMeth=None,
                PayAcct=None,
                BalDue=None,
                Payments=None,
                Quote=quote,
                Date4=today,
                Date5=today,
                Date6=today,
                RateCon=None,
                Rcache=0,
                Proof2=None,
                Pcache2=0,
                Emailjp=None,
                Emailoa=None,
                Emailap=None,
                Saljp=None,
                Saloa=None,
                Salap=None,
                Date7=None,
                SSCO=None,
                Date8=today,
                Ship=None,
                Voyage=None,
                UserMod=None,
                DelStat=None,
                DrvProof=None,
                DrvSeal=None,
                D1cache=None,
                D2cache=None

            )

            db.session.add(input_row)
            db.session.flush() #so we have so we have the JO

            saved_source, source_error = save_order_upload_file(input_row, source_file, 'Source')
            if source_error:
                db.session.rollback()
                return jsonify({"message": source_error}), 400

            saved_ratecon, ratecon_error = save_order_upload_file(input_row, ratecon_file, 'RateCon')
            if ratecon_error:
                db.session.rollback()
                return jsonify({"message": ratecon_error}), 400

            db.session.commit()

            # Match webapp behavior for address/drop updates
            Order_Addresses_Update(input_row.id)
            db.session.refresh(input_row)

            return jsonify({
                "message": "Export order created",
                "order_id": input_row.id,
                "jo": input_row.Jo,
                "order": order,
                "haul_type": haul_type,
                "booking": booking,
                "container_type": putsize,
                "shipper": shipper,
                "loading_location": loading_location,
                "source_file": saved_source,
                "ratecon_file": saved_ratecon,
                "lid": input_row.Lid,
                "did": input_row.Did,
                "bid": input_row.Bid
            }), 201


        if is_import:
            existing = Orders.query.filter(Orders.Container == container).first()
            if existing is not None:
                return jsonify({
                    "message": "Skipped duplicate import",
                    "reason": "container already exists",
                    "container": container,
                    "existing_order_id": existing.id
                }), 200

            cdata = companydata()
            jbcode = cdata[10] + 'T'
            nextjo = newjo(jbcode, today_str)

            input_row = Orders(
                Status='AO',
                Jo=nextjo,
                HaulType=haul_type,
                Order=order,
                Bid=pdat.id,
                Lid=None,
                Did=None,
                Company2=loading_location,
                Location=None,
                BOL=None,
                Booking=bol,
                Container=container,
                Driver=None,
                Pickup=None,
                Delivery=None,
                Amount=amount,
                Date=today,
                Time=None,
                Time3=None,
                Date2=today,
                Time2=None,
                PaidInvoice=None,
                Source=None,
                Description=None,
                Chassis=None,
                Detention=None,
                Storage=None,
                Release=0,
                Company=terminal_name,
                Seal=None,
                Shipper=shipper,
                Type=putsize,
                Label=None,
                Dropblock2=loading_address,
                Dropblock1=terminal_address,
                Commodity=None,
                Packing=None,
                Links=None,
                Hstat=-1,
                Istat=-1,
                Proof=None,
                Invoice=None,
                Gate=None,
                Package=None,
                Manifest=None,
                Scache=0,
                Pcache=0,
                Icache=0,
                Mcache=0,
                Pkcache=0,
                QBi=None,
                InvoTotal='0.00',
                Truck=None,
                Dropblock3=None,
                Date3=today,
                Location3=None,
                InvoDate=None,
                PaidDate=None,
                PaidAmt=None,
                PayRef=None,
                PayMeth=None,
                PayAcct=None,
                BalDue=None,
                Payments=None,
                Quote=quote,
                Date4=today,
                Date5=today,
                Date6=today,
                RateCon=None,
                Rcache=0,
                Proof2=None,
                Pcache2=0,
                Emailjp=None,
                Emailoa=None,
                Emailap=None,
                Saljp=None,
                Saloa=None,
                Salap=None,
                Date7=None,
                SSCO=None,
                Date8=today,
                Ship=None,
                Voyage=None,
                UserMod = None,
                DelStat = None,
                DrvProof = None,
                DrvSeal = None,
                D1cache = None,
                D2cache = None
            )

            db.session.add(input_row)
            db.session.flush() #so we have so we have the JO

            print(f'Going to upload and save the source file {source_file}')
            saved_source, source_error = save_order_upload_file(input_row, source_file, 'Source')
            if source_error:
                db.session.rollback()
                return jsonify({"message": source_error}), 400

            print(f'Going to upload and save the ratecon file {ratecon_file}')
            saved_ratecon, ratecon_error = save_order_upload_file(input_row, ratecon_file, 'RateCon')
            if ratecon_error:
                db.session.rollback()
                return jsonify({"message": ratecon_error}), 400

            db.session.commit()

            Order_Addresses_Update(input_row.id)
            db.session.refresh(input_row)

            return jsonify({
                "message": "Import order created",
                "order_id": input_row.id,
                "jo": input_row.Jo,
                "order": order,
                "haul_type": haul_type,
                "shipper": shipper,
                "bol": bol,
                "container": container,
                "container_type": putsize,
                "source_file": saved_source,
                "ratecon_file": saved_ratecon,
                "lid": input_row.Lid,
                "did": input_row.Did,
                "bid": input_row.Bid,
                "amount": amount,
                "quote": quote
            }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": "Failed to create order",
            "error": str(e)
        }), 500

@bot_bp.route('/bot/shippers/loading_locations', methods=['GET'])
@bot_token_required(required_scopes={'read:orders'})
def bot_loading_locations():
    shipper = (request.args.get('shipper') or '').strip()
    q = (request.args.get('loading_location') or '').strip().lower()

    if not shipper:
        return jsonify({"message": "shipper is required"}), 400

    rows = (
        db.session.query(
            Orders.Company2,
            Orders.Dropblock2,
            Orders.Amount,
            Orders.Quote,
            func.count(Orders.id).label('count'),
            func.max(Orders.Date3).label('last_used')
        )
        .filter(Orders.Shipper == shipper)
        .filter(Orders.Company2 != None)
        .filter(Orders.Dropblock2 != None)
        .group_by(Orders.Company2, Orders.Dropblock2, Orders.Amount, Orders.Quote)
        .order_by(func.max(Orders.Date3).desc(), func.count(Orders.id).desc())
        .all()
    )

    matches = []
    for company2, dropblock2, amount, quote, count, last_used in rows:
        company2_text = company2 or ''
        dropblock2_text = dropblock2 or ''

        if q:
            qmatch = (
                    q in company2_text.lower()
                    or q in dropblock2_text.lower()
            )
            if not qmatch:
                continue

        matches.append({
            "loading_location": company2_text,
            "loading_address": dropblock2_text,
            "amount": amount,
            "quote": quote,
            "count": count,
            "last_used": last_used.isoformat() if last_used else None
        })

    return jsonify({
        "shipper": shipper,
        "match_count": len(matches),
        "matches": matches
    }), 200
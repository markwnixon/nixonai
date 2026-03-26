from flask import Blueprint, jsonify, request
from webapp.bot.decorators import bot_token_required
from webapp.services.api_data_service import api_call
from webapp.CCC_system_setup import scac
import datetime
from datetime import datetime, timedelta
from webapp.models import Orders

bot_bp = Blueprint('bot_bp', __name__)

now = datetime.now()


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
            "company": odat.Company,
            "booking": odat.Booking,
            "container": odat.Container,
            "driver": odat.Driver,
            "deliveryType": odat.Delivery,
            "amount": odat.Amount,
            "date": odat.Date.isoformat() if odat.Date else None,
            "date2": odat.Date2.isoformat() if odat.Date2 else None,
            "date3": odat.Date3.isoformat() if odat.Date3 else None,
            "shipper": odat.Shipper,
            "type": odat.Type,
            "dropAddress": odat.Dropblock2,
            "hstat": odat.Hstat,
            "proof": odat.Proof,
            "manifest": odat.Manifest,
            "driverProof": odat.DrvProof,
            "truck": odat.Truck,
            "delStat": odat.DelStat,
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
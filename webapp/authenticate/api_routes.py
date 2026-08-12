from flask import Blueprint, request, jsonify
import json
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)

from webapp.extensions import bcrypt
from webapp.models import users, DispatchDriverAssignment

authenticate_api = Blueprint('authenticate_api', __name__)


def _pending_driver_assignments_for_login(driver_name):
    if not driver_name:
        return []
    try:
        rows = DispatchDriverAssignment.query.filter(
            DispatchDriverAssignment.Driver == driver_name,
            DispatchDriverAssignment.Active == 1,
            DispatchDriverAssignment.Status.in_(['pending', 'draft'])
        ).order_by(DispatchDriverAssignment.CreatedAt, DispatchDriverAssignment.id).all()
    except Exception:
        return []

    payloads = []
    for row in rows:
        route_payload = None
        if getattr(row, 'RouteJson', None):
            try:
                route_payload = json.loads(row.RouteJson)
            except (TypeError, ValueError):
                route_payload = None
        payloads.append({
            'id': row.id,
            'driver': row.Driver,
            'assignment_type': row.AssignmentType,
            'message_text': row.MessageText,
            'route': route_payload,
            'status': row.Status,
            'created_at': row.CreatedAt.isoformat() if row.CreatedAt else None,
        })
    return payloads

@authenticate_api.route('/api_login', methods=['POST'])
def api_login():
    if request.method == 'POST':
        print('This is a post')
        data = request.get_json()
        print("Data received successfully:", data)
        user = data['username']
        password = data['password']
        print(f'user: {user} and password: {password}')

        thisuser = users.query.filter_by(username=user).first()
        if thisuser is not None:
            print(f'user: {user} found')
            passhash = thisuser.password
            #Commented out....only needed for startup if no superuser in database
            #hashed_pw = bcrypt.generate_password_hash(thisuser.password).decode('utf-8')
            #print(hashed_pw)
            passcheck = bcrypt.check_password_hash(passhash, password)
            print(passcheck)
            if passcheck:
                access_token = create_access_token(identity=user)
                refresh_token = create_refresh_token(identity=user)
                #return jsonify({"access_token": token})
                return jsonify(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    authority=thisuser.authority,
                    display_name=thisuser.name,
                    pending_dispatch_assignments=_pending_driver_assignments_for_login(thisuser.name),
                )

        return jsonify({"message": "Invalid credentials"}), 401

@authenticate_api.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    new_access_token = create_access_token(identity=identity)
    return jsonify(access_token=new_access_token)


@authenticate_api.route("/api_logout", methods=["POST"])
#@jwt_required()
def logout():
    jti = get_jwt_identity()  # Get unique token ID
    print(f'logout: token revoked is {jti}')
    return jsonify({"message": "Token revoked"}), 200

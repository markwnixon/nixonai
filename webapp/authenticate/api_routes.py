from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)

from webapp.extensions import bcrypt
from webapp.models import users

authenticate_api = Blueprint('authenticate_api', __name__)

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
                return jsonify(access_token=access_token, refresh_token=refresh_token)

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
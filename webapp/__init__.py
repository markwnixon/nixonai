from flask import Flask
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, JWTManager
#from flask_sqlalchemy import SQLAlchemy
#from flask_bcrypt import Bcrypt
#from flask_login import LoginManager
from webapp.CCC_system_setup import scac, machine, statpath, dbp

from webapp.extensions import db, bcrypt, login_manager, jwt

from webapp.authenticate.routes import authenticate

####################################################################
########## SET DATABASE STRUCTURES #################################
####################################################################
a=statpath('1')
print(scac, machine,a)

SQLALCHEMY_DATABASE_URI = dbp[0] +"{username}:{password}@{hostname}/{databasename}".format(
            username=dbp[1],
            password=dbp[2],
            hostname=dbp[3],
            databasename=dbp[4]
        )

#print(f'username:{dbp[1]},password:{dbp[2]},hostname:{dbp[3]},databasname:{dbp[4]}')
def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    #app.config["SQLALCHEMY_POOL_RECYCLE"] = 3600
    #app.config['SQLALCHEMY_POOL_TIMEOUT'] = 60
    #app.config['SQLALCHEMY_POOL_PRE_PING'] = True
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["DEBUG"] = False
    app.config["SECRET_KEY"] = dbp[5]
    app.config["JWT_SECRET_KEY"] = dbp[5]
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 280, 'pool_timeout': 60, 'pool_pre_ping': True}
    #app.secret_key = dbp[5]

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)


    app.register_blueprint(authenticate)
    from webapp.routes import main
    app.register_blueprint(main)

    return app


from flask import Flask
#from flask_sqlalchemy import SQLAlchemy
#from flask_bcrypt import Bcrypt
#from flask_login import LoginManager
from webapp.CCC_system_setup import scac, machine, statpath, dbp

from webapp.extensions import db, bcrypt, login_manager
from webapp.routes import main
from webapp.authenticate.routes import authenticate

####################################################################
########## SET DATABASE STRUCTURES #################################
####################################################################
a=statpath('1')
#print(scac, machine,a)

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
    app.config["SQLALCHEMY_POOL_RECYCLE"] = 280
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 10
    app.config['SQLALCHEMY_POOL_PRE_PING'] = True
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["DEBUG"] = False
    app.config["SECRET_KEY"] = dbp[5]
    app.secret_key = dbp[5]

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(authenticate)
    app.register_blueprint(main)

    return app


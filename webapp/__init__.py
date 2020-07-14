from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from webapp.CCC_system_setup import scac, machine, statpath, dbp

app = Flask(__name__, static_folder = "static")

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
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["DEBUG"] = True
app.config["SECRET_KEY"] = dbp[5]
app.secret_key = dbp[5]

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'authenticate.login'

from webapp import routes
from webapp.authenticate.routes import authenticate

app.register_blueprint(authenticate)


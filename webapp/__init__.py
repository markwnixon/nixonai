from flask import Flask
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, JWTManager
#from flask_sqlalchemy import SQLAlchemy
#from flask_bcrypt import Bcrypt
#from flask_login import LoginManager
from webapp.CCC_system_setup import scac, machine, statpath, dbp

from webapp.extensions import db, bcrypt, login_manager, jwt
from webapp.authenticate.routes import authenticate
from webapp.authenticate.api_routes import authenticate_api
from webapp.api.routes import api_bp
from webapp.bot.routes import bot_bp
from webapp.authenticate.bot_routes import bot_auth
from webapp.routes import main
from sqlalchemy import inspect, text

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
    app.register_blueprint(authenticate_api)
    app.register_blueprint(api_bp)
    app.register_blueprint(bot_bp)
    app.register_blueprint(bot_auth)
    app.register_blueprint(main)

    @app.before_request
    def ensure_lightweight_schema_updates():
        if app.config.get('CLASS8_BILLS_RECONCILED_CHECKED'):
            return
        app.config['CLASS8_BILLS_RECONCILED_CHECKED'] = True
        try:
            inspector = inspect(db.engine)
            if inspector.has_table('bills'):
                columns = [column['name'] for column in inspector.get_columns('bills')]
                if 'Reconciled' not in columns:
                    db.session.execute(text(
                        'ALTER TABLE bills ADD COLUMN Reconciled INT NOT NULL DEFAULT 0'
                    ))
                    db.session.commit()
            if inspector.has_table('overseas'):
                overseas_columns = [column['name'] for column in inspector.get_columns('overseas')]
                overseas_adds = [
                    ('Shipper', 'VARCHAR(100) NULL'),
                    ('IngateDate', 'DATETIME NULL'),
                    ('InvoDate', 'DATETIME NULL'),
                    ('PaidDate', 'DATETIME NULL'),
                    ('InvoTotal', 'VARCHAR(45) NULL'),
                    ('PaidAmt', 'VARCHAR(45) NULL'),
                    ('BalDue', 'VARCHAR(45) NULL'),
                    ('Payments', 'VARCHAR(45) NULL'),
                    ('PayRef', 'VARCHAR(80) NULL'),
                    ('PayMeth', 'VARCHAR(45) NULL'),
                    ('PayAcct', 'VARCHAR(80) NULL'),
                    ('Istat', 'INT NULL DEFAULT 0'),
                    ('QBi', 'INT NULL'),
                ]
                for column_name, column_def in overseas_adds:
                    if column_name not in overseas_columns:
                        db.session.execute(text(
                            f'ALTER TABLE overseas ADD COLUMN {column_name} {column_def}'
                        ))
                        db.session.commit()
                db.session.execute(text(
                    'ALTER TABLE overseas '
                    'MODIFY COLUMN Exporter TEXT NULL, '
                    'MODIFY COLUMN Consignee TEXT NULL, '
                    'MODIFY COLUMN Notify TEXT NULL, '
                    'MODIFY COLUMN Description TEXT NULL, '
                    'MODIFY COLUMN Pol VARCHAR(100) NULL, '
                    'MODIFY COLUMN FrFor VARCHAR(100) NULL'
                ))
                db.session.commit()
        except Exception as exc:
            db.session.rollback()
            print(f'Could not ensure lightweight schema updates: {exc}')

    return app

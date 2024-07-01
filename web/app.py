from flask import Flask, redirect, url_for
from flask.cli import FlaskGroup
# from flask_sqlalchemy import SQLAlchemy

from pageHandlers.bpIndex import bpIndex
from pageHandlers.bpAttendance import bpAttendance
from pageHandlers.bpLookUpClient import bpFindClient
from pageHandlers.bpUpdateDB import bpUpdateDB
from pageHandlers.bpShowAllFriends import bpShowAllFriends
from pageHandlers.bpLogin import bpLogin
# from utils.dbDeb import db    # the db instance was created in dbDeb, putting all db stuff in one file
from utils.dbDeb import openPostgresConnection
from utils.qrGen import qrInit
from utils.genNameTagDoc import nameTagInit

app = Flask(__name__)
# -------- init the dateabse ---------------
# app.config[ "SQLALCHEMY_DATABASE_URI" ] = "sqlite:///DMBC4RFriends.db"
app.config['SECRET_KEY'] = "0453"
# db.init_app(app)    # to add the app inside SQLAlchemy, db.py created an instance importable
cli = FlaskGroup(app)

openPostgresConnection()
qrInit()
nameTagInit()

# ---------- register all the Blueprint route handlers ------
app.register_blueprint(bpLogin)
app.register_blueprint(bpIndex)
app.register_blueprint(bpAttendance)
app.register_blueprint(bpFindClient)
app.register_blueprint(bpUpdateDB)
app.register_blueprint(bpShowAllFriends)


if __name__ == '__main__':
    cli()

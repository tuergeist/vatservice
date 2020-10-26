import os

from flask import Flask, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

app = Flask(__name__)

app.config.from_mapping(
    SECRET_KEY=os.environ.get('SECRET_KEY') or 'dev_key',
    SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db = SQLAlchemy(app)
migrate = Migrate()
migrate.init_app(app, db)
db.create_all()


class Company(db.Model):
    # https://de.wikipedia.org/wiki/Umsatzsteuer-Identifikationsnummer#Aufbau_der_Identifikationsnummer
    vatNumber = db.Column(db.String(20), nullable=False, primary_key=True)
    name = db.Column(db.Text(), nullable=True)
    address = db.Column(db.Text(), nullable=True)
    valid = db.Column(db.Boolean())


@app.route('/', methods=('GET',))
def get_vat_info():
    vatid = request.args.get('vatid')
    if vatid is None:
        return 'Need vatid as parameter to check', 400

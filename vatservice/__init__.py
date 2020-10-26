import os

import zeep
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from zeep.transports import Transport

VIES_URL = os.getenv('VIES_URL', "https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl")

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

transport = Transport(timeout=int(os.getenv('EU_TIMEOUT', 10)))
client = zeep.Client(VIES_URL, transport=transport)


class Company(db.Model):
    # https://de.wikipedia.org/wiki/Umsatzsteuer-Identifikationsnummer#Aufbau_der_Identifikationsnummer
    vatNumber = db.Column(db.String(20), nullable=False, primary_key=True)
    name = db.Column(db.Text(), nullable=True)
    address = db.Column(db.Text(), nullable=True)
    valid = db.Column(db.Boolean())


class ServiceError(Exception):
    pass


def _get_vat_info(vat: str) -> dict:
    print('get info')

    try:
        print('checkvat')
        result = client.service.checkVat(countryCode=vat[:2], vatNumber=vat[2:])
        print('checkvat done')
    except zeep.exceptions.Fault as fault:
        print('CheckVAT Error: %s' % fault)

        return 'some server error', 500
    print('result: ', result)
    try:
        return {
            'varNumber': result['vatNumber'],
            'countryCode': result['countryCode'],
            'valid': result['valid'],
            'name': result['name'],
            'address': result['address']
        }
    except Exception as e:
        print('Exception: ', e)
        return 'unknown error', 500


@app.route('/check/<vatid>/', methods=('GET',))
def get_vat_info(vatid):
    print(vatid)
    if vatid is None:
        return {'error': 'Need vatid as query parameter to check'}, 400

    return _get_vat_info(vatid)


@app.route('/')
def home():
    return 'Usage: /check/&lt;vatid_to_check&gt;/'

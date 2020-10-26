import json
import os

import zeep
from flask import Flask, request
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

    def get_json(self):
        return json.dumps({
            'vatNumber': self.vatNumber[2:],
            'countryCode': self.vatNumber[:2],
            'valid': self.valid,
            'name': self.name,
            'address': self.address
        }, ensure_ascii=False)


class ServiceError(Exception):
    pass


def _get_vat_info(vat: str) -> dict:
    company = db.session.query(Company).filter_by(vatNumber=vat).one_or_none()
    if company is not None:
        print('database result')
        return company.get_json()

    try:
        result = client.service.checkVat(countryCode=vat[:2], vatNumber=vat[2:])
    except zeep.exceptions.Fault as fault:
        print('CheckVAT Error: %s' % fault)
        return 'some server error', 500
    print('SOAP result')
    try:
        company = Company(vatNumber=f"{result['countryCode']}{result['vatNumber']}",
                          name=result['name'],
                          valid=result['valid'],
                          address=result['address']
                          )
        db.session.add(company)
        db.session.commit()
        return company.get_json()
    except Exception as e:
        print('Exception: ', e)
        return 'unknown error', 500


@app.route('/check/<vatid>/', methods=('GET',))
def get_vat_info(vatid):
    ip_address = request.remote_addr
    print(ip_address, ' requested info for VATID: ', vatid)
    if vatid is None:
        return {'error': 'Need vatid as query parameter to check'}, 400

    return _get_vat_info(vatid)


@app.route('/')
def home():
    return 'Usage: /check/&lt;vatid_to_check&gt;/'


@app.route('/stats/')
def stats():
    num_comps = db.session.query(Company).count()
    return {'companies_in_db': num_comps}

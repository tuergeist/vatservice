import json
import os

import requests
import sqlalchemy
import zeep
from flask import Flask, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from zeep.transports import Transport

print(10 * ' -=-', 'START VAT SERVICE', 10 * '-=- ')

VIES_URL = os.getenv('VIES_URL', "https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl")

USE_VIES = os.getenv('USE_VIES')

PROXY_URL = os.getenv('PROXY_URL')

DB_URL = os.environ.get('DATABASE_URL', 'postgres://postgres:mysecretpassword@172.17.0.3:5432/postgres')
if os.getenv('RDS_HOSTNAME'):
    # eb specific
    print('Taking DB Config from RDS Vars')
    DB_URL = f"postgres://{os.getenv('RDS_USERNAME')}:{os.getenv('RDS_PASSWORD')}@{os.getenv('RDS_HOSTNAME')}:{os.getenv('RDS_PORT')}/{os.getenv('RDS_DB_NAME')}"

print("Using for Database: ", DB_URL)
print("VIES remote check: ", USE_VIES)
print("Proxy vatservice URL: ", PROXY_URL)

app = Flask(__name__)

app.config.from_mapping(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key'),
    SQLALCHEMY_DATABASE_URI=DB_URL,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db = SQLAlchemy(app, engine_options={'pool_pre_ping': True})
migrate = Migrate()
migrate.init_app(app, db)
db.create_all()

if USE_VIES:
    transport = Transport(timeout=int(os.getenv('EU_TIMEOUT', 10)))
    client = zeep.Client(VIES_URL, transport=transport)

fakes = 0


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


def get_company(vat: str) -> Company:
    company = None
    try:
        company = db.session.query(Company).filter_by(vatNumber=vat).one_or_none()
    except  sqlalchemy.exc.OperationalError as err:
        print('ERROR ', err)
    return company


def get_clean_vat(vat_in: str) -> str:
    return vat_in.strip().replace(' ', '')


def _get_fake_result(vat):
    print('Fake a result')
    result = {
        'countryCode': vat[:2],
        'vatNumber': vat[2:],
        'valid': False,
        'address': 'FAKED',
        'name': ''
    }
    return result


def _get_proxy_result(vat):
    r = requests.get(PROXY_URL + f"/check/{vat}/")
    if r.status_code != 200:
        print(f"Got error from proxy service: {r.content}")
        return _get_fake_result(vat)
    return r.json()


def _get_vat_info(vat_in: str) -> tuple:
    result = {'valid': False}
    vat = get_clean_vat(vat_in)
    company = get_company(vat)

    if company is not None:
        print('database result')
        return company.get_json(), 200

    if not USE_VIES:
        if PROXY_URL:
            result = _get_proxy_result(vat)
        else:
            result = _get_fake_result(vat)

    else:
        try:
            result = client.service.checkVat(countryCode=vat[:2], vatNumber=vat[2:])
        except zeep.exceptions.Fault as fault:
            print('CheckVAT Error: %s' % fault)
            result['error'] = f"VAT construction is invalid: {vat}"
            return result, 400
        print('CheckVAT SOAP result')

    try:
        company = Company(vatNumber=f"{result['countryCode']}{result['vatNumber']}",
                          name=result['name'],
                          valid=result['valid'],
                          address=result['address']
                          )
        db.session.add(company)
        db.session.commit()
        return company.get_json(), 200
    except Exception as e:
        print('Exception: ', e)
        return 'unknown error', 500


@app.route('/check/<vatid>/', methods=('GET',))
def get_vat_info(vatid):
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    print(ip_address, 'requested info for VATID:', vatid)
    if vatid is None:
        return {'error': 'Need vatid as query parameter to check'}, 400

    return _get_vat_info(vatid)


@app.route('/')
def home():
    return 'Usage: /check/&lt;vatid_to_check&gt;/'


@app.route('/stats/')
def stats():
    num_comps = db.session.query(Company).count()
    return {
        'companies_in_db': num_comps,
        'vies_service_enabled': USE_VIES,
        'proxy_url': PROXY_URL,
        'use_proxy': PROXY_URL and not USE_VIES
    }

import os

import requests
import zeep
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape
from zeep.transports import Transport

print(10 * ' ---', 'START VAT SERVICE', 10 * '--- ')

VIES_URL = os.getenv('VIES_URL', "https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl")
USE_VIES = os.getenv('USE_VIES')
PROXY_URL = os.getenv('PROXY_URL')
DB_URL = os.environ.get('DATABASE_URL', 'postgres://postgres:mysecretpassword@172.17.0.3:5432/postgres')

if os.getenv('RDS_HOSTNAME'):
    # elastic beanstack provides RDS_* env vars
    print('Taking DB Config from RDS Vars')
    DB_URL = f"postgres://{os.getenv('RDS_USERNAME')}:" \
             f"{os.getenv('RDS_PASSWORD')}@{os.getenv('RDS_HOSTNAME')}:" \
             f"{os.getenv('RDS_PORT')}/{os.getenv('RDS_DB_NAME')}"

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

# local imports here, after database
from vatservice.models import Company
from vatservice.helper import _is_well_formated, get_clean_vat
from vatservice.model_helper import get_company, set_company

if USE_VIES:
    # prepare connection to VIES service once
    transport = Transport(timeout=int(os.getenv('EU_TIMEOUT', 10)))
    client = zeep.Client(VIES_URL, transport=transport)


class ServiceError(Exception):
    pass


def _get_fake_result(vat):
    print('CheckVAT fake result', vat)
    result = {
        'countryCode': vat[:2],
        'vatNumber': vat[2:],
        'valid': False,
        'address': 'FAKED',
        'name': ''
    }
    return result


def _get_proxy_result(vat):
    url = PROXY_URL + f"/check/{vat}/"
    try:
        r = requests.get(url)
        if r.status_code != 200:
            print(f"Got error from proxy service: {r.content}")
            return _get_fake_result(vat)
        print('CheckVAT proxy result', vat)
        return r.json()
    except:  # catch all here to avoid error propagation
        print('Proxy error for', url)
        return {'valid': False}


def _get_vies_result(vat):
    try:
        result = client.service.checkVat(countryCode=vat[:2], vatNumber=vat[2:])
    except zeep.exceptions.Fault as fault:
        print('CheckVAT Error: %s' % fault)
        result = _get_fake_result(vat)
        result['error'] = f"VIES says VAT construction is invalid: {vat}"
    print('CheckVAT SOAP result', vat)
    return result


def _get_vat_info(vat: str) -> tuple:
    company = get_company(vat)

    if company is not None:
        print('CheckVAT database result', vat)
        return company.get_json(), 200

    if USE_VIES:
        result = _get_vies_result(vat)
    else:
        if PROXY_URL:
            result = _get_proxy_result(vat)
        else:
            result = _get_fake_result(vat)

    company = set_company(result)
    return company.get_json(), 200


@app.route('/check/<string:vatid>/', methods=('GET',))
def get_vat_info(vatid):
    _vatid = get_clean_vat(escape(vatid))

    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    print(ip_address, 'requested info for VATID:', _vatid)

    if not _is_well_formated(_vatid):
        print(f"format invalid", _vatid)
        return jsonify({
            'valid': False,
            'error': 'Need formally valid VATID as query parameter to check'
        })

    return _get_vat_info(_vatid)


@app.route('/')
def home():
    return 'contact info@exb.de'


@app.route('/stats/')
def stats():
    num_comps = db.session.query(Company).count()
    return jsonify({
        'companies_in_db': num_comps,
        'vies_service_enabled': USE_VIES,
        'proxy_url': PROXY_URL,
        'use_proxy': PROXY_URL and not USE_VIES,
        'database_only': not PROXY_URL and not USE_VIES,
    })

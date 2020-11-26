import sqlalchemy
from sqlalchemy.exc import IntegrityError


from vatservice.models import Company


def get_company(vat: str) -> Company:
    from vatservice import db
    company = None
    try:
        company = db.session.query(Company).filter_by(vatNumber=vat).one_or_none()
    except sqlalchemy.exc.OperationalError as err:
        print('ERROR ', err)
    return company


def set_company(result):
    from vatservice import db
    company = Company(
        vatNumber=f"{result['countryCode']}{result['vatNumber']}",
        name=result['name'],
        valid=result['valid'],
        address=result['address']
    )
    try:
        db.session.add(company)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
    except Exception as e:
        print('Unknown Exception: ', e)
    return company
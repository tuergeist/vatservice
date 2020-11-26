import json

from vatservice import db


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

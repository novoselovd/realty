from run import db, app, mail
from passlib.hash import pbkdf2_sha256 as sha256
from time import time
import jwt
from flask_mail import Message
from flask import render_template, url_for, Response
from sqlalchemy import and_, or_, not_
import datetime
import json
from threading import Thread


def async_send_mail(app, msg):
    with app.app_context():
        mail.send(msg)


class JsonModel(object):
    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class UserModel(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(120), unique = True, nullable = False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable = False)
    
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
    

    @classmethod
    def find_by_username(cls, username):
        return cls.query.filter_by(username=username).first()

    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def return_all(cls):
        def to_json(x):
            return {
                'username': x.username,
                'id': x.id,
                'email': x.email,
            }

        return {'users': list(map(lambda x: to_json(x), UserModel.query.all()))}

    @classmethod
    def return_user_by_id(cls, id):
        def to_json(x):
            return {
                'username': x.username,
                'id': x.id,
                'email': x.email,
            }

        return {'user': to_json(cls.find_by_id(id))}

    @classmethod
    def delete_all(cls):
        try:
            num_rows_deleted = db.session.query(cls).delete()
            db.session.commit()
            return {'message': '{} row(s) deleted'.format(num_rows_deleted)}
        except:
            return {'message': 'Something went wrong'}

    @staticmethod
    def generate_hash(password):
        return sha256.hash(password)
    
    @staticmethod
    def verify_hash(password, hash):
        return sha256.verify(password, hash)

    def change_password(self, new_password):
        db.session.query(UserModel).filter(UserModel.username == self.username).\
            update({UserModel.password: new_password},
                   synchronize_session=False)
        db.session.commit()

    def get_reset_password_token(self, expires_in=60000):
        return jwt.encode(
            {'id': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'])['id']
        except:
            return
        return db.session.query(UserModel).filter(UserModel.id == id).first()

    @staticmethod
    def send_password_reset_email(user):
        token = user.get_reset_password_token()
        msg = Message('Reset your password',
                      sender='realtyanalyzer@yandex.ru', recipients=[user.email])
        link = 'https://real-estate-research-6f694.firebaseapp.com/auth/restore-password?token=' + \
            str(token)[2:-1]
        msg.body = render_template('reset_password.txt',
                                   user=user, link=link)
        msg.html = render_template('reset_password.html',
                                   user=user, link=link)
        # thr = Thread(target=async_send_mail,  args=[app,  msg])
        # thr.start()
        # return thr

        mail.send(msg)


    @staticmethod
    def send_feedback(name, email, subject, message):
        msg = Message(subject,
                      sender='realtyanalyzer@yandex.ru', recipients=['realtyanalyzer@yandex.ru'])
        msg.body = name + ' ' + email + ' ' + message
        msg.html = name + ' ' + email + ' ' + message

        mail.send(msg)


class RevokedTokenModel(db.Model):
    __tablename__ = 'revoked_tokens'
    id = db.Column(db.Integer, primary_key = True)
    jti = db.Column(db.String(120))
    
    def add(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def is_jti_blacklisted(cls, jti):
        query = cls.query.filter_by(jti = jti).first()
        return bool(query)


class RealtyModel(db.Model, JsonModel):
    __tablename__ = 'realty'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer)
    url = db.Column(db.String(120))
    price = db.Column(db.Float)
    phone = db.Column(db.String(120))
    address = db.Column(db.String(120))
    metro = db.Column(db.String(120))
    area = db.Column(db.Float)
    rooms_count = db.Column(db.Integer)
    floor_number = db.Column(db.Integer)
    floors_count = db.Column(db.Integer)
    images = db.Column(db.Text)
    description = db.Column(db.Text)
    city = db.Column(db.String(120))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @staticmethod
    def autocomplete(address):
        query = db.session.query(RealtyModel.address).filter(RealtyModel.address.ilike('%' + str(address) + '%'))
        results = [r for r in query.all()]
        return results


    @staticmethod
    def filter(floor=0, square=0.0, rooms=0):
        query = db.session.query(RealtyModel).filter(and_(RealtyModel.rooms_count >= float(rooms), RealtyModel.floor_number >= float(floor),
                                                          RealtyModel.area >= float(square)))
        results = query.all()
        return results

    @staticmethod
    def to_json(x):
        return {
            'id': x.id,
            'type': x.type,
            'url': x.url,
            'price': x.price,
            'description': x.description,
            'phone': x.phone,
            'address': x.address,
            'metro': x.metro,
            'area': x.area,
            'rooms_count': x.rooms_count,
            'floor_number': x.floor_number,
            'floors_count': x.floors_count,
            'images': x.images,
            'city': x.city,
            'latitude': x.latitude,
            'longitude': x.longitude
        }

    @classmethod
    def return_realty_by_id(cls, id):
        return {'realty': cls.to_json(cls.find_by_id(id))}



    @staticmethod
    def find_addresses():
        result = 0
        latlon = []
        sell = db.session.query(RealtyModel).filter(RealtyModel.type == 1).all()
        rent = db.session.query(RealtyModel).filter(RealtyModel.type == 2).all()

        res = []

        for r in sell:
            for q in rent:
                if r.latitude == q.latitude and r.longitude == q.longitude and abs(r.area-q.area) < 5.0:
                    if [r.latitude, r.longitude] not in latlon:
                        latlon.append([r.latitude, r.longitude])
                        result += 1
                        res.append([r, q])

        print(result)
        return res


class TempModel(db.Model, JsonModel):
    __tablename__ = 'temp'
    id = db.Column(db.Integer, primary_key=True)
    sell_url = db.Column(db.String(120))
    rent_url = db.Column(db.String(120))
    sell_price = db.Column(db.Float)
    rent_price = db.Column(db.Float)
    coeff = db.Column(db.Integer)
    address = db.Column(db.String(120))
    area = db.Column(db.Float)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()
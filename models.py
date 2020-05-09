from run import db, app, mail
from passlib.hash import pbkdf2_sha256 as sha256
from time import time
import jwt
from flask_mail import Message
from flask import render_template, url_for, Response
from sqlalchemy import and_, or_, not_, ForeignKey
from sqlalchemy import func
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.dialects.postgresql import ARRAY
# from sqlalchemy.dialects import postgresql
import datetime
import json
from threading import Thread


class MutableList(Mutable, list):

    def __setitem__(self, key, value):
        list.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        list.__delitem__(self, key)
        self.changed()

    def append(self, value):
        list.append(self, value)
        self.changed()

    def pop(self, index=0):
        value = list.pop(self, index)
        self.changed()
        return value

    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)
            return Mutable.coerce(key, value)
        else:
            return value


def async_send_mail(app, msg):
    with app.app_context():
        mail.send(msg)


class JsonModel(object):
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class UserModel(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    favourites = db.Column(MutableList.as_mutable(ARRAY(db.BigInteger)), server_default="{}")

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
                'favourites': x.favourites,
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
        db.session.query(UserModel).filter(UserModel.username == self.username). \
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

    def add_fav(self, sell_id, rent_id):

        self.favourites.append([sell_id, rent_id])

        # db.session.query(UserModel).filter(UserModel.username == self.username).\
        #     update({UserModel.favourites: UserModel.favourites.append([sell_id, rent_id])},
        #            synchronize_session=False)
        db.session.commit()

    def remove_fav(self, sell_id, rent_id):
        # self.favourites.pop([sell_id, rent_id])
        favourites = self.favourites

        ind = favourites.index([sell_id, rent_id])

        self.favourites.pop(ind)
        # print(ind)

        db.session.commit()

    def empty_fav(self):
        db.session.query(UserModel).filter(UserModel.username == self.username). \
            update({UserModel.favourites: {}},
                   synchronize_session=False)

        db.session.commit()

    def get_fav(self):
        data = self.favourites
        return data


class RevokedTokenModel(db.Model):
    __tablename__ = 'revoked_tokens'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120))

    def add(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def is_jti_blacklisted(cls, jti):
        query = cls.query.filter_by(jti=jti).first()
        return bool(query)


class RealtyModel(db.Model, JsonModel):
    __tablename__ = 'realty'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer)
    url = db.Column(db.Text)
    price = db.Column(db.Float)
    phone = db.Column(db.Text)
    address = db.Column(db.Text)
    metro = db.Column(db.Text)
    area = db.Column(db.Float)
    rooms_count = db.Column(db.Integer)
    floor_number = db.Column(db.Integer)
    floors_count = db.Column(db.Integer)
    images = db.Column(db.Text)
    description = db.Column(db.Text)
    city = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    area_kitchen = db.Column(db.Float)
    time_publish = db.Column(db.DateTime)
    building_material_type = db.Column(db.Text)
    status = db.Column(db.Integer)
    dist = db.Column(db.Integer, ForeignKey('districts.id'))

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
    def count():
        return db.session.query(RealtyModel).count()

    @staticmethod
    def find_addresses():
        result = 0
        sell = db.session.query(RealtyModel).filter(RealtyModel.type == 1).all()
        rent = db.session.query(RealtyModel).filter(RealtyModel.type == 2).all()

        res = {}

        for r in sell:
            for q in rent:
                if r.latitude == q.latitude and r.longitude == q.longitude and abs(r.area - q.area) < 5.0:
                    if tuple([r.latitude, r.longitude]) not in res:
                        res[tuple([r.latitude, r.longitude])] = [r, q, int(r.price / (12.0 * q.price))]
                        result += 1
                    else:
                        if res[tuple([r.latitude, r.longitude])][2] > int(r.price / (12.0 * q.price)):
                            res.pop(tuple([r.latitude, r.longitude]), None)
                            res[tuple([r.latitude, r.longitude])] = [r, q, int(r.price / (12.0 * q.price))]

        return res

    @staticmethod
    def update_dist():
        # self.dist = dist_id
        db.session.commit()


class TempModel(db.Model, JsonModel):
    __tablename__ = 'temp'
    id = db.Column(db.Integer, primary_key=True)
    sell_url = db.Column(db.Text)
    rent_url = db.Column(db.Text)
    sell_price = db.Column(db.Float)
    rent_price = db.Column(db.Float)
    coeff = db.Column(db.Integer)
    address = db.Column(db.Text)
    area = db.Column(db.Float)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    dist = db.Column(db.Integer, ForeignKey('districts.id'))

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def delete(cls, id):
        deleted = cls.query.filter_by(id=id).delete()
        db.session.commit()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def find_by_latlon(cls, lat, lon):
        return cls.query.filter_by(latitude=lat, longitude=lon).first()

    @staticmethod
    def filter(squareMin, squareMax, coeffMin, coeffMax, priceMin, priceMax):
        query = db.session.query(TempModel).filter(
            and_(TempModel.coeff >= float(coeffMin), TempModel.coeff <= float(coeffMax),
                 TempModel.sell_price >= float(priceMin), TempModel.sell_price <= float(priceMax),
                 TempModel.area >= float(squareMin), TempModel.area <= float(squareMax)))
        results = query.all()
        return results

    @staticmethod
    def count():
        return db.session.query(TempModel).count()

    @staticmethod
    def count_payback():
        query = db.session.query(TempModel.coeff)
        results = [r[0] for r in query.all()]

        # print(results)
        return round(sum(results) / len(results))

    @staticmethod
    def top():
        query = db.session.query(TempModel).order_by(TempModel.coeff).limit(10)

        return query

    @staticmethod
    def get_intervals():
        coeffMax = db.session.query(func.max(TempModel.coeff)).scalar()
        coeffMin = db.session.query(func.min(TempModel.coeff)).scalar()

        squareMax = db.session.query(func.max(TempModel.area)).scalar()
        squareMin = db.session.query(func.min(TempModel.area)).scalar()

        priceMax = db.session.query(func.max(TempModel.sell_price)).scalar()
        priceMin = db.session.query(func.min(TempModel.sell_price)).scalar()

        return [coeffMin, coeffMax, squareMin, squareMax, priceMin, priceMax]


class DistrictModel(db.Model, JsonModel):
    __tablename__ = 'districts'
    id = db.Column(db.Integer, primary_key=True)
    okato_ao = db.Column(db.BigInteger)
    name = db.Column(db.String(120))
    type = db.Column(db.String(120))
    avg_sq = db.Column(db.Float)
    avg_coeff = db.Column(db.Integer)
    coordinates = db.Column(MutableList.as_mutable(ARRAY(db.Float)), server_default="{}")

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def delete(cls, id):
        deleted = cls.query.filter_by(id=id).delete()
        db.session.commit()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def return_all(cls):
        def to_json(x):
            return {
                'id': x.id,
                'okato_ao': x.okato_ao,
                'name': x.name,
                'type': x.type,
                'avg_sq': x.avg_sq,
                'avg_coeff': x.avg_coeff,
                'coordinates': x.coordinates
            }

        return {'districts': list(map(lambda x: to_json(x), DistrictModel.query.all()))}


class AoModel(db.Model, JsonModel):
    __tablename__ = 'ao'
    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(120))
    type = db.Column(db.String(120))
    avg_sq = db.Column(db.Float)
    avg_coeff = db.Column(db.Integer)

    # coordinates = db.Column(MutableList.as_mutable(ARRAY(db.Float)), server_default="{}")

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def delete(cls, id):
        deleted = cls.query.filter_by(id=id).delete()
        db.session.commit()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def return_all(cls):
        def to_json(x):
            return {
                'id': x.id,
                'name': x.name,
                'type': x.type,
                'avg_sq': x.avg_sq,
                'avg_coeff': x.avg_coeff,
                # 'coordinates': x.coordinates
            }

        return {'ao': list(map(lambda x: to_json(x), AoModel.query.all()))}

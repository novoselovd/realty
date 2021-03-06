from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_cors import CORS
from flask import jsonify
import datetime

errors = {
    'ExpiredSignatureError': {
        'message': 'Token has expired',
        'status': 401
    }
}

app = Flask(__name__)
CORS(app)
api = Api(app, errors=errors)


app.config['MAIL_SERVER'] = 'smtp.yandex.ru'
app.config['MAIL_USERNAME'] = 'realtyanalyzer'
app.config['MAIL_PASSWORD'] = 'Stope123'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True
mail = Mail(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://rtwktcfx:NITaFpgQWBqeHE-H7UyiyCoYE1AjIOZU@balarama.db.elephantsql.com:5432/rtwktcfx'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'some-secret-string'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(seconds=900)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = datetime.timedelta(days=30)

db = SQLAlchemy(app)


@app.before_first_request
def create_tables():
    db.create_all()



app.config['JWT_SECRET_KEY'] = 'jwt-secret-string'
jwt = JWTManager(app)


app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']


@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    jti = decrypted_token['jti']
    return models.RevokedTokenModel.is_jti_blacklisted(jti)


@jwt.revoked_token_loader
def revoked_token_callback():
    return jsonify({
        'status': 401,
        'sub_status': 44,
        'msg': 'The token has been revoked'
    }), 401


@jwt.invalid_token_loader
def invalid_token_callback(reason):
    return jsonify({
        'status': 401,
        'sub_status': 43,
        'msg' : reason
    }), 401


@jwt.expired_token_loader
def expired_token_callback(expired_token):
    token_type = expired_token['type']
    return jsonify({
        'status': 401,
        'sub_status': 42,
        'msg': 'The {} token has expired'.format(token_type)
    }), 401


@jwt.user_identity_loader
def user_identity_lookup(user):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email
    }


import resources, views, models

api.add_resource(resources.UserRegistration, '/register')
api.add_resource(resources.UserLogin, '/login')
api.add_resource(resources.UserLogoutAccess, '/logout/access')
api.add_resource(resources.UserLogoutRefresh, '/logout/refresh')
api.add_resource(resources.TokenRefresh, '/token/refresh')
api.add_resource(resources.AllUsers, '/users')
api.add_resource(resources.SecretResource, '/secret')
api.add_resource(resources.UserChangePassword, '/password/change')
api.add_resource(resources.UserForgotPassword, '/password/forgot')
api.add_resource(resources.UserResetPasswordViaEmail,
                 '/password/forgot/reset/<token>')
api.add_resource(resources.UpdateDatabase, '/update')
api.add_resource(resources.ReturnData, '/data')
api.add_resource(resources.Autocomplete, '/autocomplete')
api.add_resource(resources.FilterData, '/filter')
api.add_resource(resources.Feedback, '/feedback')
api.add_resource(resources.GetRealtyById, '/realty/<id>')
api.add_resource(resources.CountSameAddresses, '/count')
api.add_resource(resources.CountAveragePayback, '/payback')
api.add_resource(resources.RecordsCount, '/records')
api.add_resource(resources.FlatsCount, '/flats')
api.add_resource(resources.ReturnTop, '/top')
api.add_resource(resources.ReturnIntervals, '/intervals')
api.add_resource(resources.AddFav, '/add_favourite')
api.add_resource(resources.RemoveFav, '/remove_favourite')
api.add_resource(resources.EmptyFav, '/empty_favourites')
api.add_resource(resources.ReturnFav, '/favourites')
api.add_resource(resources.UserFindById, '/user/<id>')
api.add_resource(resources.ParsePolygons, '/polygons')
api.add_resource(resources.ReturnDistricts, '/districts')
api.add_resource(resources.ReturnAo, '/ao')
api.add_resource(resources.ReturnAoCoords, '/ao_coords')
api.add_resource(resources.FindLatLon, '/latlon')
api.add_resource(resources.Estimate, '/estimate')
api.add_resource(resources.GetTopDistricts, '/top_dist')
# api.add_resource(resources.MatchMl, '/match')
api.add_resource(resources.CompareMlPrediction, '/mlcoeff')
api.add_resource(resources.PriceToPredicted, '/compare')
api.add_resource(resources.Alternatives, '/alternatives')












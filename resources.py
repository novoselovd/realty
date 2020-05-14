from flask_restful import Resource, reqparse
from flask import request, jsonify
from models import UserModel, RevokedTokenModel, RealtyModel, TempModel, DistrictModel, AoModel
from flask_jwt_extended import (create_access_token, create_refresh_token, jwt_required, jwt_refresh_token_required,
                                get_jwt_identity, get_raw_jwt)
from parser import update_db
from polygons import parse_polygons, check_point_is_in_polygon, count_avg_sq, count_avg_coeff, parse_ao
import json
from opencage.geocoder import OpenCageGeocode
from sqlalchemy import and_
import pandas as pd
import dill as pickle
from geopy.distance import geodesic
import numpy as np
import math
import requests


parser = reqparse.RequestParser()
parser.add_argument('username', help='This field cannot be blank', required=True)
parser.add_argument('password', help='This field cannot be blank', required=True)
parser.add_argument(
    'email', help='This field cannot be blank', required=True)


class UserRegistration(Resource):
    def post(self):
        data = parser.parse_args()

        if UserModel.find_by_username(data['username']) or UserModel.find_by_email(data['email']):
            return {'message': "User with such username or email already exists"}, 400

        new_user = UserModel(
            username=data['username'],
            email=data['email'],
            password=UserModel.generate_hash(data['password'])
        )

        # try:
        new_user.save_to_db()
        access_token = create_access_token(identity=new_user)
        refresh_token = create_refresh_token(identity=new_user)
        return {
            'message': 'User {} was created'.format(data['username']),
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        # except:
        #     return {'message': 'Something went wrong'}, 500


login_parser = reqparse.RequestParser()
login_parser.add_argument(
    'username', help='This field cannot be blank', required=True)
login_parser.add_argument(
    'password', help='This field cannot be blank', required=True)


class UserLogin(Resource):
    def post(self):
        data = login_parser.parse_args()
        current_user = UserModel.find_by_username(data['username'])

        if not current_user:
            return {'message': 'User {} doesn\'t exist'.format(data['username'])}, 400

        if UserModel.verify_hash(data['password'], current_user.password):
            access_token = create_access_token(identity=current_user)
            refresh_token = create_refresh_token(identity=current_user)
            return {
                'message': 'Logged in as {}'.format(current_user.username),
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        else:
            return {'message': 'Wrong credentials'}, 400


class UserLogoutAccess(Resource):
    @jwt_required
    def post(self):
        jti = get_raw_jwt()['jti']
        try:
            revoked_token = RevokedTokenModel(jti=jti)
            revoked_token.add()
            return {'message': 'Access token has been revoked'}
        except:
            return {'message': 'Something went wrong'}, 500


class UserLogoutRefresh(Resource):
    @jwt_refresh_token_required
    def post(self):
        jti = get_raw_jwt()['jti']
        try:
            revoked_token = RevokedTokenModel(jti=jti)
            revoked_token.add()
            return {'message': 'Refresh token has been revoked'}
        except:
            return {'message': 'Something went wrong'}, 500


class TokenRefresh(Resource):
    @jwt_refresh_token_required
    def post(self):
        jti = get_raw_jwt()['jti']
        try:
            current_user_identity = get_jwt_identity()
            revoked_token = RevokedTokenModel(jti=jti)
            revoked_token.add()
            current_user = UserModel.find_by_username(current_user_identity['username'])
            access_token = create_access_token(identity=current_user)
            refresh_token = create_refresh_token(identity=current_user)
            return {
                       'access_token': access_token,
                       'refresh_token': refresh_token
                   }, 200
        except:
            return {'message': 'Something went wrong'}, 500


class AllUsers(Resource):
    def get(self):
        return UserModel.return_all()

    def delete(self):
        return UserModel.delete_all()


class SecretResource(Resource):
    @jwt_required
    def get(self):
        return {
            'answer': 42
        }


password_change_parser = reqparse.RequestParser()
password_change_parser.add_argument(
    'current_password', help='Please fill in your current password', required=True)
password_change_parser.add_argument(
    'new_password', help='Please fill in your new password', required=True)


class UserChangePassword(Resource):
    @jwt_required
    def post(self):
        data = password_change_parser.parse_args()

        current_user = UserModel.find_by_username(get_jwt_identity()['username'])
        if not current_user:
            return {'message': 'Verification failed'}, 400

        if UserModel.verify_hash(data['current_password'], current_user.password):
            current_user.change_password(
                UserModel.generate_hash(data['new_password']))
            return {
                'message': 'You have successfully changed your password!'
            }
        else:
            return {'message': 'Wrong password'}, 400


password_recover_parser = reqparse.RequestParser()
password_recover_parser.add_argument(
    'email', help='Please fill in your email address', required=True)


class UserForgotPassword(Resource):
    def post(self):
        data = password_recover_parser.parse_args()

        current_user = UserModel.find_by_email(data['email'])
        if not current_user:
            return {'message': 'User with such email doesn\'t exist'}, 400
        UserModel.send_password_reset_email(current_user)
        return {
            'message': "An e-mail was sent to {}. Follow the instructions to reset the password".format(data['email'])}


after_confirmation_password_change_parser = reqparse.RequestParser()
after_confirmation_password_change_parser.add_argument(
    'new_password', help='Please fill in your new password', required=True)


class UserResetPasswordViaEmail(Resource):
    def post(self, token):
        user = UserModel.verify_reset_password_token(token)
        if not user:
            return {'message': 'Verification failed. Please try again'}, 400
        data = after_confirmation_password_change_parser.parse_args()
        user.change_password(UserModel.generate_hash(data['new_password']))
        access_token = create_access_token(identity=user)
        refresh_token = create_refresh_token(identity=user)

        return {'message': 'You have successfully changed your password!', 'access_token': access_token,
                'refresh_token': refresh_token}, 200


realty_parser = reqparse.RequestParser()
realty_parser.add_argument(
    'deal_id', help='Please fill in deal id(1 - selling, 2 - renting)', required=True)
realty_parser.add_argument(
    'price', help='Please fill in the starting price', required=True)


class UpdateDatabase(Resource):
    # @jwt_required
    def get(self):
        # user_dict = get_jwt_identity()
        # if user_dict['username'] != 'dmitry':
        #     return {'message': 'No access'}, 403

        data = realty_parser.parse_args()
        update_db(data['price'], data['deal_id'])
        return {'message': 'Successfully updated db'}, 200


class ReturnData(Resource):
    @jwt_required
    def get(self):
        return [r.as_dict() for r in TempModel.query.all()], 200


class FilterData(Resource):
    @jwt_required
    def get(self):
        coeffMin = request.args.get('coeffMin')
        coeffMax = request.args.get('coeffMax')
        squareMin = request.args.get('squareMin')
        squareMax = request.args.get('squareMax')
        priceMin = request.args.get('priceMin')
        priceMax = request.args.get('priceMax')
        results = TempModel.filter(squareMin, squareMax, coeffMin, coeffMax, priceMin, priceMax)

        return [r.as_dict() for r in results], 200


class Autocomplete(Resource):
    @jwt_required
    def get(self):
        address = request.args.get('adr')
        results = RealtyModel.autocomplete(address)

        return jsonify(matching_results=results), 200


feedback_parser = reqparse.RequestParser()
feedback_parser.add_argument('name', help='Please explain your problem', type=str, required=True, nullable=False)
feedback_parser.add_argument('email', help='Please explain your problem', type=str, required=True, nullable=False)
feedback_parser.add_argument('subject', help='Please explain your problem', type=str, required=True, nullable=False)
feedback_parser.add_argument('message', help='Please explain your problem', type=str, required=True, nullable=False)


class Feedback(Resource):
    def post(self):
        name = feedback_parser.parse_args()['name']
        email = feedback_parser.parse_args()['email']
        subject = feedback_parser.parse_args()['subject']
        message = feedback_parser.parse_args()['message']
        UserModel.send_feedback(name, email, subject, message)

        return {'message': 'Thank you for contacting us!'}, 200


class GetRealtyById(Resource):
    @jwt_required
    def get(self, id):
        return RealtyModel.return_realty_by_id(id)


class CountSameAddresses(Resource):
    def get(self):
        res = RealtyModel.find_addresses()

        for key, value in res.items():
            realty = TempModel.find_by_latlon(key[0], key[1])
            if not realty:
                new_temp = TempModel(
                    id=value[0].id,
                    sell_url=value[0].url,
                    rent_url=value[1].url,
                    sell_price=value[0].price,
                    rent_price=value[1].price,
                    address=value[0].address,
                    area=value[0].area,
                    latitude=value[0].latitude,
                    longitude=value[0].longitude,
                    coeff=value[2]
                )

                new_temp.save_to_db()
            else:
                if realty.coeff > value[2]:
                    realty.delete(realty.id)

                    new_temp = TempModel(
                        id=value[0].id,
                        sell_url=value[0].url,
                        rent_url=value[1].url,
                        sell_price=value[0].price,
                        rent_price=value[1].price,
                        address=value[0].address,
                        area=value[0].area,
                        latitude=value[0].latitude,
                        longitude=value[0].longitude,
                        coeff=value[2]
                    )

                    new_temp.save_to_db()

        return {'message': 'Successfully updated db!'}, 200


class CountAveragePayback(Resource):
    def get(self):
        avg = TempModel.count_payback()
        return {'Average payback period': avg}, 200


class RecordsCount(Resource):
    def get(self):
        count = RealtyModel.count()
        return {'Total records': count}, 200


class FlatsCount(Resource):
    def get(self):
        count = TempModel.count()
        return {'Total flats': count}, 200


class ReturnTop(Resource):
    @jwt_required
    def get(self):
        results = TempModel.top()
        return [r.as_dict() for r in results], 200


class ReturnIntervals(Resource):
    @jwt_required
    def get(self):
        results = TempModel.get_intervals()
        return {'coeffMin': results[0], 'coeffMax': results[1], 'squareMin': results[2], 'squareMax': results[3],
                'priceMin': results[4], 'priceMax': results[5]}, 200


fav_parser = reqparse.RequestParser()
fav_parser.add_argument('sell', help='Please add sell id', type=int, required=True, nullable=False)
fav_parser.add_argument('rent', help='Please rent id', type=int, required=True, nullable=False)


class AddFav(Resource):
    @jwt_required
    def post(self):
        sell = int(fav_parser.parse_args()['sell'])
        rent = int(fav_parser.parse_args()['rent'])

        current_user = UserModel.find_by_username(get_jwt_identity()['username'])

        if [sell, rent] in current_user.get_fav():
            return {'message': 'This item is already in list'}, 400

        current_user.add_fav(sell, rent)

        return {'message': 'Successfully added item to favourites list!'}, 200


class RemoveFav(Resource):
    @jwt_required
    def post(self):
        sell = int(fav_parser.parse_args()['sell'])
        rent = int(fav_parser.parse_args()['rent'])

        current_user = UserModel.find_by_username(get_jwt_identity()['username'])

        current_user.remove_fav(sell, rent)

        return {'message': 'Successfully removed item from favourites list!'}, 200


class EmptyFav(Resource):
    @jwt_required
    def post(self):
        current_user = UserModel.find_by_username(get_jwt_identity()['username'])
        current_user.empty_fav()

        return {'message': 'Successfully removed everything from favourites!'}, 200


class ReturnFav(Resource):
    @jwt_required
    def get(self):
        current_user = UserModel.find_by_username(get_jwt_identity()['username'])
        results = []

        data = current_user.get_fav()

        for i in data:
            results.append([RealtyModel.return_realty_by_id(i[0]), RealtyModel.return_realty_by_id(i[1])])

        return {'favourites': results}, 200


class UserFindById(Resource):
    @jwt_required
    def get(self, id):
        if int(get_jwt_identity()['id']) != int(id):
            return {'message': 'Access denied'}, 400
        return UserModel.return_user_by_id(id)


class ParsePolygons(Resource):
    # @jwt_required
    def get(self):
        # user_dict = get_jwt_identity()
        # if user_dict['username'] != 'dmitry':
        #     return {'message': 'No access'}, 403
        #
        # parse_polygons()
        #
        # check_point_is_in_polygon()

        # count_avg_sq()
        #
        # count_avg_coeff()
        #
        parse_ao()

        return {'message': 'Successfully updated districts'}, 200


class ReturnDistricts(Resource):
    @jwt_required
    def get(self):
        return DistrictModel.return_all()


class ReturnAo(Resource):
    @jwt_required
    def get(self):
        return AoModel.return_all()


class ReturnAoCoords(Resource):
    # @jwt_required
    def get(self):
        with open('ao.json', 'r') as myfile:
            data = myfile.read()

        obj = json.loads(data)
        return obj



latlon_parser = reqparse.RequestParser()
latlon_parser.add_argument('address', help='Please fill in address field', type=str, required=True, nullable=False)

class FindLatLon(Resource):
    def get(self):
        query = latlon_parser.parse_args()['address']

        key = 'a45c9a9a30e74fe2a9049689754b7774'
        geocoder = OpenCageGeocode(key)

        results = geocoder.geocode(query)

        found = False

        for i in results:
            if i['components']['city'] == 'Moscow':
                lat = i['geometry']['lat']
                lon = i['geometry']['lng']
                found = True
                break

        if not found:
            return {'message': 'Could not find lat/lon'}, 400
        else:
            return {'coords': [lat, lon]}, 200

def get_azimuth(latitude, longitude):
    rad = 6372795

    llat1 = city_center_coordinates[0]
    llong1 = city_center_coordinates[1]
    llat2 = latitude
    llong2 = longitude

    lat1 = llat1 * math.pi / 180.
    lat2 = llat2 * math.pi / 180.
    long1 = llong1 * math.pi / 180.
    long2 = llong2 * math.pi / 180.

    cl1 = math.cos(lat1)
    cl2 = math.cos(lat2)
    sl1 = math.sin(lat1)
    sl2 = math.sin(lat2)
    delta = long2 - long1
    cdelta = math.cos(delta)
    sdelta = math.sin(delta)

    y = math.sqrt(math.pow(cl2 * sdelta, 2) + math.pow(cl1 * sl2 - sl1 * cl2 * cdelta, 2))
    x = sl1 * sl2 + cl1 * cl2 * cdelta
    ad = math.atan2(y, x)

    x = (cl1 * sl2) - (sl1 * cl2 * cdelta)
    y = sdelta * cl2
    z = math.degrees(math.atan(-y / x))

    if (x < 0):
        z = z + 180.

    z2 = (z + 180.) % 360. - 180.
    z2 = - math.radians(z2)
    anglerad2 = z2 - ((2 * math.pi) * math.floor((z2 / (2 * math.pi))))
    angledeg = (anglerad2 * 180.) / math.pi

    return round(angledeg, 2)

city_center_coordinates = [55.7522, 37.6156]



estimate_parser = reqparse.RequestParser()
estimate_parser.add_argument('wallsMaterial', help='Please fill in wallsMaterial', type=int, required=True, nullable=False)
estimate_parser.add_argument('floorNumber', help='Please fill in floorNumber', type=int, required=True, nullable=False)
estimate_parser.add_argument('floorsTotal', help='Please fill in floorsTotal', type=int, required=True, nullable=False)
estimate_parser.add_argument('totalArea', help='Please fill in totalArea', type=float, required=True, nullable=False)
estimate_parser.add_argument('kitchenArea', help='Please fill in kitchenArea', type=float, required=True, nullable=False)
estimate_parser.add_argument('latitude', help='Please fill in latitude', type=float, required=True, nullable=False)
estimate_parser.add_argument('longitude', help='Please fill in longitude', type=float, required=True, nullable=False)


class Estimate(Resource):
    def get(self):
        query = estimate_parser.parse_args()

        with open('xgb.pk', 'rb') as f:
            loaded_model2 = pickle.load(f)

        flat = pd.DataFrame({
            'wallsMaterial': [query['wallsMaterial']],
            'floorNumber': [query['floorNumber']],
            'floorsTotal': [query['floorsTotal']],
            'totalArea': [query['totalArea']],
            'kitchenArea': [query['kitchenArea']],
            'latitude': [query['latitude']],
            'longitude': [query['longitude']]
        })

        flat['distance'] = list(
            map(lambda x, y: geodesic(city_center_coordinates, [x, y]).meters, flat['latitude'], flat['longitude']))
        flat['azimuth'] = list(map(lambda x, y: get_azimuth(x, y), flat['latitude'], flat['longitude']))
        flat['distance'] = flat['distance'].round(0)
        flat['azimuth'] = flat['azimuth'].round(0)

        flat = flat.drop('latitude', axis=1)
        flat = flat.drop('longitude', axis=1)

        # rf_prediction_flat = loaded_model1.predict(flat).round(0)
        xgb_prediction_flat = loaded_model2.predict(flat).round(0)

        price = xgb_prediction_flat * flat['totalArea'][0]

        return {'Predicted price': (int(price[0].round(-3)))}, 200


class GetTopDistricts(Resource):
    def get(self):
        results = DistrictModel.top()
        return [r.as_dict() for r in results], 200



# class MatchMl(Resource):
#     def get(self):
#         d = {'None': 0, 'block': 1, 'brick': 2, 'monolith': 3, 'monolithBrick': 4, 'old': 5, 'panel': 6, 'stalin': 7,
#          'wood': 8}
#
#         flats = RealtyModel.query.filter(and_(RealtyModel.area_kitchen != None, RealtyModel.building_material_type != None))
#         URL = "http://realty.pythonanywhere.com/estimate"
#         count = 0
#
#         for i in flats:
#             try:
#                 count+=1
#                 PARAMS = {'wallsMaterial': d[i.building_material_type], 'floorNumber': i.floor_number, 'floorsTotal': i.floors_count, 'totalArea': i.area, 'kitchenArea': i.area_kitchen, 'latitude': i.latitude, 'longitude': i.longitude}
#                 r = requests.get(url=URL, params=PARAMS)
#
#                 data = r.json()['Predicted price']
#                 i.predicted = data
#
#                 print (str(count) + '/13290')
#             except:
#                 print('error')
#                 continue
#
#             if count % 500 == 0:
#                 RealtyModel.update_dist()
#
#         return {'Message': 'success'}, 200


class CompareMlPrediction(Resource):
    def get(self):
        flats = RealtyModel.query.filter(and_(RealtyModel.predicted != None, RealtyModel.type == 1))

        sum_flats = 0
        sum_predicted = 0

        for i in flats:
            if i.price > 80000000.0:
                continue
            sum_flats += i.price
            sum_predicted += i.predicted

        return {'Rate': 100-sum_predicted/sum_flats*100}, 200


class PriceToPredicted(Resource):
    def get(self):
        data = RealtyModel.return_all()

        return data, 200


alt_parser = reqparse.RequestParser()
alt_parser.add_argument('latitude', help='Please fill in latitude', type=float, required=True, nullable=False)
alt_parser.add_argument('longitude', help='Please fill in longitude', type=float, required=True, nullable=False)
alt_parser.add_argument('area', help='Please fill in area', type=float, required=True, nullable=False)


class Alternatives(Resource):
    def get(self):
        latitude = alt_parser.parse_args()['latitude']
        longitude = alt_parser.parse_args()['longitude']
        area = alt_parser.parse_args()['area']

        data = RealtyModel.find_alt(latitude, longitude, area)

        return {'Matching results': data}, 200
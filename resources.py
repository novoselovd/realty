from flask_restful import Resource, reqparse
from models import UserModel, RevokedTokenModel
from flask_jwt_extended import (create_access_token, create_refresh_token, jwt_required, jwt_refresh_token_required, get_jwt_identity, get_raw_jwt)

parser = reqparse.RequestParser()
parser.add_argument('username', help = 'This field cannot be blank', required = True)
parser.add_argument('password', help = 'This field cannot be blank', required = True)
parser.add_argument(
    'email', help='This field cannot be blank', required=True)


class UserRegistration(Resource):
    def post(self):
        data = parser.parse_args()
        
        if UserModel.find_by_username(data['username']) or UserModel.find_by_email(data['email']):
            return {'message': "User with such username or email already exists"}, 400
        
        new_user = UserModel(
            username = data['username'],
            email = data['email'],
            password = UserModel.generate_hash(data['password'])
        )
        
        # try:
        new_user.save_to_db()
        access_token = create_access_token(identity = new_user)
        refresh_token = create_refresh_token(identity = new_user)
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
            revoked_token = RevokedTokenModel(jti = jti)
            revoked_token.add()
            return {'message': 'Access token has been revoked'}
        except:
            return {'message': 'Something went wrong'}, 500


class UserLogoutRefresh(Resource):
    @jwt_refresh_token_required
    def post(self):
        jti = get_raw_jwt()['jti']
        try:
            revoked_token = RevokedTokenModel(jti = jti)
            revoked_token.add()
            return {'message': 'Refresh token has been revoked'}
        except:
            return {'message': 'Something went wrong'}, 500


class TokenRefresh(Resource):
    @jwt_refresh_token_required
    def post(self):
        current_user = get_jwt_identity()
        access_token = create_access_token(identity = current_user)
        return {'access_token': access_token}


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
        return {'message': "An e-mail was sent to {}. Follow the instructions to reset the password".format(data['email'])}


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

        return {'message': 'You have successfully changed your password!', 'access_token': access_token, 'refresh_token': refresh_token}, 200




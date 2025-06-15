# users/authentication.py
import token
from django.conf import settings
import jwt

from user.backends import MongoAuthBackend
from .utils.token_utils import decode_jwt_token  # Add this import
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
import logging



logger = logging.getLogger(__name__)


from rest_framework_simplejwt.exceptions import InvalidToken

class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return None
            
        try:
            # Split header
            parts = auth_header.split()
            
            if parts[0].lower() != 'bearer':
                raise AuthenticationFailed('Authorization header must start with Bearer')
                
            if len(parts) == 1:
                raise AuthenticationFailed('No token provided')
            elif len(parts) > 2:
                raise AuthenticationFailed('Authorization header must be Bearer token')
                
            token = parts[1]
            
            # Ensure token is a string before decoding
            if not isinstance(token, str):
                raise AuthenticationFailed('Token must be a string')
                
            # Decode token
            try:
                payload = jwt.decode(
                    token.encode('utf-8'),  # Explicitly encode to bytes
                    settings.SECRET_KEY,
                    algorithms=['HS256'],
                    options={
                        'verify_exp': True,
                        'verify_aud': False,
                    }
                )
            except Exception as e:
                raise InvalidToken(str(e))
            
            # Get user ID
            user_id = payload.get('user_id')
            if not user_id:
                raise AuthenticationFailed('Token contains no user identifier')
            
            # Get user
            user = MongoAuthBackend().get_user(user_id)
            if not user:
                raise AuthenticationFailed('User not found')
                
            return (user, token)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')
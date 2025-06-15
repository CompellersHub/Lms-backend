# users/utils/token_utils.py
import jwt
from django.conf import settings
from datetime import datetime, timedelta
from rest_framework_simplejwt.tokens import RefreshToken

def create_jwt_tokens(user, token_type='both'):
    """
    Creates JWT tokens with flexible return types
    
    Args:
        user: Django user object
        token_type: 'both'|'access'|'refresh' - what to return
        
    Returns:
        dict: {'access': str, 'refresh': str} if token_type='both'
        str: single token if token_type='access' or 'refresh'
    """
    # Create token pair using SimpleJWT
    refresh = RefreshToken.for_user(user)
    
    # Create legacy token (without .decode())
    legacy_token = jwt.encode(
        {
            'user_id': str(user.id),
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow(),
        },
        settings.SECRET_KEY,
        algorithm='HS256'
    )
    
    # Return based on requested type
    if token_type == 'both':
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'legacy': legacy_token  # Optional: include if needed
        }
    elif token_type == 'access':
        return str(refresh.access_token)
    elif token_type == 'refresh':
        return str(refresh)
    elif token_type == 'legacy':
        return legacy_token
    else:
        raise ValueError("Invalid token_type. Use 'both', 'access', 'refresh', or 'legacy'")

def create_access_token(user):
    """
    Creates just an access token
    
    Args:
        user: Django user object
    
    Returns:
        str: Access token
    """
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

def decode_jwt_token(token):
    """
    Decodes and verifies a JWT token
    
    Args:
        token (str): JWT token string
    
    Returns:
        dict: Decoded payload if valid
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256'],
            options={
                'verify_exp': True,
                'verify_aud': False,
            }
        )
    except jwt.PyJWTError as e:
        raise ValueError(f"Invalid token: {str(e)}")
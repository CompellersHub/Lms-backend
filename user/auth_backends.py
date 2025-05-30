# user/backends.py (or wherever your GoogleAuthBackend is located)
import logging
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import make_password # For new user creation
from django.conf import settings
from datetime import datetime
from bson import ObjectId

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from courses.mongo_utils import get_mongo_db
from .models import CustomUser # Your CustomUser proxy model

logger = logging.getLogger(__name__)

class GoogleAuthBackend(BaseBackend):
    def authenticate(self, request, id_token_str=None, **kwargs):
        if not id_token_str:
            return None

        db = get_mongo_db()
        users_collection = db.customusers

        try:
            # 1. Verify the Google ID token
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            google_id = idinfo['sub']
            google_email = idinfo['email']
            google_first_name = idinfo.get('given_name', '')
            google_last_name = idinfo.get('family_name', '')
            google_picture = idinfo.get('picture', '')

            # 2. Try to find user by linked Google ID first
            user_data = users_collection.find_one({"google_id": google_id})

            if user_data:
                # User found by Google ID - This account is already linked.
                # Just return the user to be logged in.
                logger.info(f"User {google_email} logged in via Google (existing google_id link).")
                user = CustomUser(
                    _id=user_data['_id'], # Ensure _id is correctly passed for PK
                    id=str(user_data['_id']),
                    email=user_data['email'],
                    username=user_data.get('username', user_data['email']),
                    # ... other fields for CustomUser initialization
                    is_active=user_data.get('is_active', True),
                    is_staff=user_data.get('is_staff', False),
                    is_superuser=user_data.get('is_superuser', False),
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    role=user_data.get('role', ''),
                    date_joined=user_data.get('date_joined'),
                    last_login=user_data.get('last_login'),
                    google_id=user_data.get('google_id'),
                    google_email=user_data.get('google_email'),
                    google_profile_pic=user_data.get('google_profile_pic'),
                    password=user_data.get('password', '') # Important if you expect check_password later
                )
                user.backend = 'user.backends.GoogleAuthBackend'
                return user
            else:
                # 3. No user found by Google ID. Try to find by Google-provided email.
                user_data = users_collection.find_one({"email": google_email})

                if user_data:
                    # User found by email, but not yet linked to this Google ID.
                    # Link the Google ID to this existing account and return the user.
                    update_fields = {
                        "google_id": google_id,
                        "google_email": google_email,
                        "google_profile_pic": google_picture,
                    }
                    # Optionally update name fields if they are empty on existing account
                    if not user_data.get('first_name'):
                        update_fields['first_name'] = google_first_name
                    if not user_data.get('last_name'):
                        update_fields['last_name'] = google_last_name

                    users_collection.update_one(
                        {"_id": user_data['_id']},
                        {"$set": update_fields}
                    )
                    logger.info(f"User {google_email} auto-linked and logged in via Google (email match).")
                    # Re-fetch updated user_data to ensure the CustomUser object is complete
                    user_data = users_collection.find_one({"_id": user_data['_id']})

                    user = CustomUser(
                        _id=user_data['_id'],
                        id=str(user_data['_id']),
                        email=user_data['email'],
                        username=user_data.get('username', user_data['email']),
                        is_active=user_data.get('is_active', True),
                        is_staff=user_data.get('is_staff', False),
                        is_superuser=user_data.get('is_superuser', False),
                        first_name=user_data.get('first_name', ''),
                        last_name=user_data.get('last_name', ''),
                        role=user_data.get('role', ''),
                        date_joined=user_data.get('date_joined'),
                        last_login=user_data.get('last_login'),
                        google_id=user_data.get('google_id'),
                        google_email=user_data.get('google_email'),
                        google_profile_pic=user_data.get('google_profile_pic'),
                        password=user_data.get('password', '')
                    )
                    user.backend = 'user.backends.GoogleAuthBackend'
                    return user
                else:
                    # 4. No user found by Google ID or email. Create a new account.
                    new_user_data_for_mongo = {
                        "email": google_email,
                        "username": google_email.split('@')[0], # Default username from email
                        "password": make_password("!RANDOM_SOCIAL_PASS!"), # Set a dummy/unusable password as it's social login
                        "first_name": google_first_name,
                        "last_name": google_last_name,
                        "role": "STUDENT", # Default role for new signups
                        "phone_number": None,
                        "profile_pic": google_picture,
                        "course": [],
                        "is_active": True,
                        "is_staff": False,
                        "is_superuser": False,
                        "date_joined": datetime.utcnow(),
                        "last_login": None,
                        "google_id": google_id,
                        "google_email": google_email,
                        "google_profile_pic": google_picture,
                    }
                    result = users_collection.insert_one(new_user_data_for_mongo)
                    mongo_id = str(result.inserted_id)
                    logger.info(f"New user {google_email} signed up and logged in via Google.")

                    # Create CustomUser object from the newly inserted data
                    user = CustomUser(
                        _id=result.inserted_id,
                        id=mongo_id,
                        email=new_user_data_for_mongo['email'],
                        username=new_user_data_for_mongo['username'],
                        is_active=new_user_data_for_mongo['is_active'],
                        is_staff=new_user_data_for_mongo['is_staff'],
                        is_superuser=new_user_data_for_mongo['is_superuser'],
                        first_name=new_user_data_for_mongo['first_name'],
                        last_name=new_user_data_for_mongo['last_name'],
                        role=new_user_data_for_mongo['role'],
                        date_joined=new_user_data_for_mongo['date_joined'],
                        last_login=new_user_data_for_mongo['last_login'],
                        google_id=new_user_data_for_mongo['google_id'],
                        google_email=new_user_data_for_mongo['google_email'],
                        google_profile_pic=new_user_data_for_mongo['google_profile_pic'],
                        password=new_user_data_for_mongo['password']
                    )
                    user.backend = 'user.backends.GoogleAuthBackend'
                    return user

        except ValueError as e:
            logger.error(f"GoogleAuthBackend: Invalid ID token or token verification failed - {e}")
            return None
        except Exception as e:
            logger.error(f"GoogleAuthBackend: An unexpected error occurred during authentication - {e}", exc_info=True)
            return None

    def get_user(self, user_id):
        # This method remains the same, ensuring it can reconstruct the CustomUser object
        # with all necessary fields, including the new Google ones.
        db = get_mongo_db()
        try:
            user_data = db.customusers.find_one({"_id": ObjectId(user_id)})
            if user_data:
                user = CustomUser(
                    _id=user_data['_id'],
                    id=str(user_data['_id']),
                    email=user_data['email'],
                    username=user_data.get('username', user_data['email']),
                    is_active=user_data.get('is_active', True),
                    is_staff=user_data.get('is_staff', False),
                    is_superuser=user_data.get('is_superuser', False),
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    role=user_data.get('role', ''),
                    date_joined=user_data.get('date_joined'),
                    last_login=user_data.get('last_login'),
                    google_id=user_data.get('google_id'),
                    google_email=user_data.get('google_email'),
                    google_profile_pic=user_data.get('google_profile_pic'),
                    password=user_data.get('password', '')
                )
                user.backend = 'user.backends.GoogleAuthBackend'
                return user
        except Exception as e:
            logger.error(f"Error retrieving user with ID {user_id} from MongoDB in GoogleAuthBackend: {e}")
        return None
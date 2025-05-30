# user/backends.py
import logging
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import make_password
from django.conf import settings
from datetime import datetime
from bson import ObjectId

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from courses.mongo_utils import get_mongo_db
from .models import CustomUser

logger = logging.getLogger(__name__)

class GoogleAuthBackend(BaseBackend):
    def authenticate(self, request, id_token_str=None, **kwargs):
        print(f"\n--- GoogleAuthBackend.authenticate called ---")
        print(f"Received id_token_str (first 20 chars): {id_token_str[:20] if id_token_str else 'None'}")
        print(f"GOOGLE_CLIENT_ID from settings: {settings.GOOGLE_CLIENT_ID}")

        if not id_token_str:
            print("Error: id_token_str is None or empty.")
            return None

        db = get_mongo_db()
        users_collection = db.customusers

        try:
            # 1. Verify the Google ID token
            print("Attempting to verify Google ID token...")
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
            print(f"Google ID token verified successfully!")
            print(f"idinfo: {idinfo}") # <-- IMPORTANT: What's inside idinfo?

            google_id = idinfo['sub']
            google_email = idinfo['email']
            google_first_name = idinfo.get('given_name', '')
            google_last_name = idinfo.get('family_name', '')
            google_picture = idinfo.get('picture', '')

            print(f"Extracted Google ID: {google_id}")
            print(f"Extracted Google Email: {google_email}")

            # 2. Try to find user by linked Google ID first
            print(f"Searching for user with google_id: {google_id}...")
            user_data = users_collection.find_one({"google_id": google_id})

            if user_data:
                print(f"User found by google_id: {user_data.get('email')}")
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
                print(f"--- GoogleAuthBackend.authenticate finished (found by google_id) ---")
                return user
            else:
                print(f"No user found by google_id. Searching by email: {google_email}...")
                # 3. No user found by Google ID. Try to find by Google-provided email.
                user_data = users_collection.find_one({"email": google_email})

                if user_data:
                    print(f"User found by email: {user_data.get('email')}. Linking Google ID...")
                    update_fields = {
                        "google_id": google_id,
                        "google_email": google_email,
                        "google_profile_pic": google_picture,
                    }
                    if not user_data.get('first_name'):
                        update_fields['first_name'] = google_first_name
                    if not user_data.get('last_name'):
                        update_fields['last_name'] = google_last_name

                    users_collection.update_one(
                        {"_id": user_data['_id']},
                        {"$set": update_fields}
                    )
                    user_data = users_collection.find_one({"_id": user_data['_id']}) # Re-fetch updated data
                    print(f"User {google_email} auto-linked with Google ID.")

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
                    print(f"--- GoogleAuthBackend.authenticate finished (found by email, linked) ---")
                    return user
                else:
                    print(f"No user found by email. Creating new account...")
                    # 4. No user found by Google ID or email. Create a new account.
                    new_user_data_for_mongo = {
                        "email": google_email,
                        "username": google_email.split('@')[0],
                        "password": make_password("!RANDOM_SOCIAL_PASS!"),
                        "first_name": google_first_name,
                        "last_name": google_last_name,
                        "role": "STUDENT",
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
                    print(f"New user created with MongoDB ID: {mongo_id}")

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
                    print(f"--- GoogleAuthBackend.authenticate finished (new user created) ---")
                    return user

        except ValueError as e:
            # THIS IS THE MOST LIKELY PLACE THE ERROR IS HAPPENING
            print(f"ERROR: ValueError during Google ID token verification: {e}")
            logger.error(f"GoogleAuthBackend: Invalid ID token or token verification failed - {e}")
            return None
        except Exception as e:
            print(f"ERROR: An unexpected exception occurred in GoogleAuthBackend: {e}")
            logger.error(f"GoogleAuthBackend: An unexpected error occurred during authentication - {e}", exc_info=True)
            return None

    def get_user(self, user_id):
        # ... (keep get_user as it was, or add prints if it's failing during session retrieval)
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
            print(f"ERROR: Error retrieving user with ID {user_id} from MongoDB in GoogleAuthBackend.get_user: {e}")
            logger.error(f"Error retrieving user with ID {user_id} from MongoDB in GoogleAuthBackend: {e}")
        return None
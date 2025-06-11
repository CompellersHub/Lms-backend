# users/backends.py

from django.utils import timezone # Ensure this is the correct import for timezone
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from bson import ObjectId
import logging
from courses.mongo_utils import get_mongo_db # Ensure this path is correct
from .models import CustomUser, TeacherProfile # Ensure these models are imported correctly

logger = logging.getLogger(__name__)

class MongoAuthBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        db = get_mongo_db()
        # Change this line:
        if db is None: # Explicitly check for None, as the error suggests
            logger.error("MongoDB connection not available in MongoAuthBackend. 'db' is None.")
            return None

        if not email or not password:
            return None

        # --- Try to authenticate as a Teacher first ---
        teacher_doc = db.teacherprofiles.find_one({"email": email})
        if teacher_doc:
            if check_password(password, teacher_doc.get("password")):
                user = TeacherProfile(
                    id=str(teacher_doc['_id']),
                    email=teacher_doc.get('email'),
                    username=teacher_doc.get('username'),
                    password=teacher_doc.get('password'),
                    first_name=teacher_doc.get('first_name', ''),
                    last_name=teacher_doc.get('last_name', ''),
                    role=teacher_doc.get('role', 'TEACHER'),
                    is_active=True,
                    is_staff=True,
                    is_superuser=False,
                )
                user.backend = 'users.backends.MongoAuthBackend'
                user._mongo_doc = teacher_doc # Fix was already here, confirmed by you

                logger.debug(f"MongoAuthBackend: Authenticated Teacher {email}. _mongo_doc attached: {hasattr(user, '_mongo_doc')}")
                return user
            else:
                logger.debug(f"Authentication failed for teacher {email}: incorrect password.")
                return None

        # --- If not a Teacher, try to authenticate as a CustomUser (student/general user) ---
        custom_user_doc = db.customusers.find_one({"email": email})
        if custom_user_doc:
            if check_password(password, custom_user_doc.get("password")):
                user = CustomUser(
                    id=str(custom_user_doc['_id']),
                    email=custom_user_doc.get('email'),
                    username=custom_user_doc.get('username'),
                    password=custom_user_doc.get('password'),
                    first_name=custom_user_doc.get('first_name', ''),
                    last_name=custom_user_doc.get('last_name', ''),
                    role=custom_user_doc.get('role', 'STUDENT'),
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                    date_joined=custom_user_doc.get('date_joined', timezone.now()),
                )
                user.backend = 'users.backends.MongoAuthBackend'
                user._mongo_doc = custom_user_doc # Fix was already here, confirmed by you

                logger.debug(f"MongoAuthBackend: Authenticated CustomUser {email}. _mongo_doc attached: {hasattr(user, '_mongo_doc')}")
                return user
            else:
                logger.debug(f"Authentication failed for custom user {email}: incorrect password.")
                return None

        logger.debug(f"No user found with email {email} in either collection.")
        return None

    def get_user(self, user_id):
        db = get_mongo_db()
        # Change this line:
        if db is None: # Explicitly check for None
            return None

        try:
            oid = ObjectId(user_id)
        except Exception:
            logger.warning(f"Invalid ObjectId format for user_id in get_user: {user_id}")
            return None

        # --- Try to retrieve from TeacherProfile collection ---
        teacher_doc = db.teacherprofiles.find_one({"_id": oid})
        if teacher_doc:
            user = TeacherProfile(
                id=str(teacher_doc['_id']),
                email=teacher_doc.get('email'),
                username=teacher_doc.get('username'),
                password=teacher_doc.get('password'),
                first_name=teacher_doc.get('first_name', ''),
                last_name=teacher_doc.get('last_name', ''),
                role=teacher_doc.get('role', 'TEACHER'),
                is_active=True,
                is_staff=True,
                is_superuser=False,
            )
            user.backend = 'users.backends.MongoAuthBackend'
            user._mongo_doc = teacher_doc # Fix was already here, confirmed by you
            logger.debug(f"MongoAuthBackend: get_user for Teacher {user_id}. _mongo_doc attached: {hasattr(user, '_mongo_doc')}")
            return user
        
        # --- Try to retrieve from CustomUser collection ---
        custom_user_doc = db.customusers.find_one({"_id": oid})
        if custom_user_doc:
            user = CustomUser(
                id=str(custom_user_doc['_id']),
                email=custom_user_doc.get('email'),
                username=custom_user_doc.get('username'),
                password=custom_user_doc.get('password'),
                first_name=custom_user_doc.get('first_name', ''),
                last_name=custom_user_doc.get('last_name', ''),
                role=custom_user_doc.get('role', 'STUDENT'),
                is_active=True,
                is_staff=False,
                is_superuser=False,
                date_joined=custom_user_doc.get('date_joined', timezone.now()),
            )
            user.backend = 'users.backends.MongoAuthBackend'
            user._mongo_doc = custom_user_doc # Fix was already here, confirmed by you
            logger.debug(f"MongoAuthBackend: get_user for CustomUser {user_id}. _mongo_doc attached: {hasattr(user, '_mongo_doc')}")
            return user

        return None
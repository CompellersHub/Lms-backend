from django.utils import timezone
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from bson import ObjectId
import logging
from courses.mongo_utils import get_mongo_db
from .models import CustomUser, TeacherProfile

logger = logging.getLogger(__name__)

class MongoAuthBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        db = get_mongo_db()
        if db is None:
            logger.error("MongoDB connection not available")
            return None

        if not email or not password:
            return None

        # Try to authenticate as Teacher first
        teacher_doc = db.teacherprofiles.find_one({"email": email})
        if teacher_doc:
            if check_password(password, teacher_doc.get("password")):
                return self._create_user_from_doc(teacher_doc, TeacherProfile)
            return None

        # Try as CustomUser
        user_doc = db.customusers.find_one({"email": email})
        if user_doc and check_password(password, user_doc.get("password")):
            return self._create_user_from_doc(user_doc, CustomUser)
        
        return None

    def get_user(self, user_id):
        db = get_mongo_db()
        if db is None:
            return None

        try:
            oid = ObjectId(user_id)
        except Exception:
            logger.warning(f"Invalid ObjectId format: {user_id}")
            return None

        # Search in both collections
        user_doc = db.customusers.find_one({"_id": oid})
        if user_doc:
            return self._create_user_from_doc(user_doc, CustomUser)

        user_doc = db.teacherprofiles.find_one({"_id": oid})
        if user_doc:
            return self._create_user_from_doc(user_doc, TeacherProfile)

        return None

    def _create_user_from_doc(self, doc, user_class):
        """Helper method to create user instances from MongoDB documents"""
        user = user_class(
            id=str(doc['_id']),
            email=doc.get('email'),
            username=doc.get('username'),
            password=doc.get('password'),
            first_name=doc.get('first_name', ''),
            last_name=doc.get('last_name', ''),
            role=doc.get('role', 'STUDENT'),
            is_active=doc.get('is_active', True),
            is_staff=doc.get('is_staff', False),
            is_superuser=doc.get('is_superuser', False),
            date_joined=doc.get('date_joined', timezone.now()),
        )
        user._mongo_doc = doc  # Attach raw document
        user.backend = f"{self.__module__}.{self.__class__.__name__}"
        return user
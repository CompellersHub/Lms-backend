from django.utils import timezone
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from bson import ObjectId
import logging
from blog.models import BlogUser
from courses.mongo_utils import get_mongo_db

# Assuming these are your actual Django models
from .models import CustomUser, TeacherProfile # <-- Make sure CustomUser is also a Django model

logger = logging.getLogger(__name__)

class MongoAuthBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        db = get_mongo_db()
        if db is None:
            logger.error("MongoDB connection not available")
            return None

        if not email or not password:
            return None

        # --- AUTHENTICATION ORDER: Teacher -> CustomUser -> BlogUser (Blogger) ---

        # 1. Try to authenticate as Teacher
        teacher_doc = db.teacherprofiles.find_one({"email": email})
        if teacher_doc:
            if check_password(password, teacher_doc.get("password")):
                return self._create_user_from_doc(teacher_doc, TeacherProfile)
            return None # Password mismatch for teacher

        # 2. Try to authenticate as CustomUser (e.g., Student)
        custom_user_doc = db.customusers.find_one({"email": email}) # Renamed for clarity
        if custom_user_doc:
            if check_password(password, custom_user_doc.get("password")):
                return self._create_user_from_doc(custom_user_doc, CustomUser)
            return None # Password mismatch for custom user

        # 3. Try to authenticate as BlogUser (Blogger)
        #    This is the new part to accommodate your Signup endpoint
        blog_user_doc = db.bloguser.find_one({"email": email}) 
        if blog_user_doc:
            if check_password(password, blog_user_doc.get("password")):
                return self._create_user_from_doc(blog_user_doc, BlogUser) # Use your Django BlogUser model
            return None # Password mismatch for blog user
        
        return None # No user found or authenticated

    def get_user(self, user_id):
        db = get_mongo_db()
        if db is None:
            return None

        try:
            oid = ObjectId(user_id)
        except Exception:
            logger.warning(f"Invalid ObjectId format: {user_id}")
            return None

        # --- GET_USER ORDER: BlogUser -> CustomUser -> Teacher ---
        # Search in the general user collection first (BlogUser/blogger)
        

        # Then search in CustomUser collection (e.g., Student)
        custom_user_doc = db.customusers.find_one({"_id": oid}) # Renamed for clarity
        if custom_user_doc:
            return self._create_user_from_doc(custom_user_doc, CustomUser)

        # Then search in TeacherProfile collection
        teacher_doc = db.teacherprofiles.find_one({"_id": oid})
        if teacher_doc:
            return self._create_user_from_doc(teacher_doc, TeacherProfile)

        blog_user_doc = db.bloguser.find_one({"_id": oid})
        if blog_user_doc:
            return self._create_user_from_doc(blog_user_doc, BlogUser)

        return None # User not found in any collection

    def _create_user_from_doc(self, doc, user_class):
        """Helper method to create Django user instances from MongoDB documents"""
        # Ensure all necessary fields for AbstractUser (and your custom models) are mapped.
        # This assumes your CustomUser and TeacherProfile models also inherit from AbstractUser or a similar base
        # that allows setting these attributes.
        user = user_class(
            # Django's PK (id) is set from MongoDB's _id
            id=str(doc['_id']), 
            email=doc.get('email'),
            username=doc.get('username'),
            # The password stored in Mongo should be the HASHED password, which check_password verified.
            # This is assigned to the Django user object but isn't used for re-hashing by Django's auth system.
            password=doc.get('password'), 
            first_name=doc.get('first_name', ''),
            last_name=doc.get('last_name', ''),
            
            # The 'role' field is crucial for your Login view's logic.
            # Ensure it's present in all your MongoDB user documents (blogger, student, teacher).
            role=doc.get('role', None), # Default to None if not found, to avoid incorrect assumptions.

            is_active=doc.get('is_active', True),
            is_staff=doc.get('is_staff', False),
            is_superuser=doc.get('is_superuser', False),
            # date_joined must be a datetime object. Adjust if stored differently in Mongo.
            date_joined=doc.get('date_joined', timezone.now()), 
        )
        # Store the raw MongoDB document on the Django user object.
        # This is what your Login view uses with `user._mongo_doc['_id']`.
        user._mongo_doc = doc  
        # Set the backend attribute for Django's session management
        user.backend = f"{self.__module__}.{self.__class__.__name__}"
        return user
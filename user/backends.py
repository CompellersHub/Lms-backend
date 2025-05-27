from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from courses.mongo_utils import get_mongo_db # Assuming this gets your MongoDB client
from bson.objectid import ObjectId, InvalidId # To convert _id string to ObjectId

# Get the active User model (it might be Django's default or a custom one you defined,
# but for MongoDB, you'll need to create a proxy/dummy Django User)
User = get_user_model()

class MongoAuthBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        db = get_mongo_db()
        mongo_user_data = db.customusers.find_one({"email": email}) # Authenticate by email

        if mongo_user_data:
            # Check if the provided password matches the hashed password from MongoDB
            # Ensure check_password is compatible with how you hashed passwords in MongoDB
            if check_password(password, mongo_user_data['password']):
                # Create a Django User object from MongoDB data.
                # This user object only needs minimum fields to satisfy Django's auth system.
                # The 'id' field is crucial here, it needs to be the MongoDB _id
                # If you override User model, ensure it can accept _id as pk
                user = User(
                    id=str(mongo_user_data['_id']), # Store MongoDB _id as Django user's PK
                    username=mongo_user_data.get('username', mongo_user_data['email']), # Use email as username if no dedicated username field
                    email=mongo_user_data['email'],
                    is_active=True # Assume active
                    # Add other fields as needed, e.g., first_name, last_name, is_staff, is_superuser
                )
                user.is_staff = mongo_user_data.get('is_staff', False)
                user.is_superuser = mongo_user_data.get('is_superuser', False)
                # You might need to set a backend attribute
                user.backend = 'user.backends.MongoAuthBackend' # Important for sessions

                return user
        return None

    def get_user(self, user_id):
        # This method is called by Django's session middleware to retrieve the user
        # from the session. user_id here will be the ID stored in the session,
        # which we set to the MongoDB _id string.
        db = get_mongo_db()
        try:
            # Ensure user_id is a string that can be converted to ObjectId
            mongo_user_data = db.customusers.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            return None # Invalid ID format

        if mongo_user_data:
            user = User(
                id=str(mongo_user_data['_id']),
                username=mongo_user_data.get('username', mongo_user_data['email']),
                email=mongo_user_data['email'],
                is_active=True
            )
            user.is_staff = mongo_user_data.get('is_staff', False)
            user.is_superuser = mongo_user_data.get('is_superuser', False)
            user.backend = 'user.backends.MongoAuthBackend'
            return user
        return None
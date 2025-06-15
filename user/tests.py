
# from django.test import TestCase, RequestFactory
# from django.contrib.auth import get_user_model
# from rest_framework import exceptions
# from .authentication import JWTAuthentication  # Replace with the actual import path
# from unittest.mock import patch


# class JWTAuthenticationTestCase(TestCase):
#     def setUp(self):
#         self.User = get_user_model()
#         self.client = APIClient()

#         # Mock the Celery task dispatch for tests
#         # The path here is crucial: 'your_app.module_where_task_is_defined.task_name.delay'
#         # Assuming send_welcome_email_task is in user/tasks.py
#         self.patcher = patch('user.tasks.send_welcome_email_task.delay')
#         self.mock_delay = self.patcher.start()

#         # Now, create the user, which will trigger the signal
#         # The signal will call the *mocked* send_welcome_email_task.delay
#         self.user = self.User.objects.create_user(
#             email='testuser@example.com',
#             password='password123',
#             username='testuser' # Make sure to include username if your CustomUser uses it
#         )
#         self.token = str(AccessToken.for_user(self.user))

#     def tearDown(self):
#         # Stop the patcher to ensure the original method is restored after the test
#         self.patcher.stop()

#     @patch('user.signals.send_welcome_email_task.delay')
#     def test_valid_token(self, mock_task):
#         # Generate a valid token for the test user
#         token = 'your_valid_token_here'  # Replace with actual token generation logic

#         # Create a request with the valid token
#         request = self.factory.get('/some-endpoint', HTTP_AUTHORIZATION=f'Bearer {token}')

#         # Test the authenticate method
#         user, auth_token = self.authentication.authenticate(request)
#         self.assertEqual(user, self.user)
#         self.assertEqual(auth_token, token)

#     @patch('user.signals.send_welcome_email_task.delay')
#     def test_invalid_token(self, mock_task):
#         # Create a request with an invalid token
#         request = self.factory.get('/some-endpoint', HTTP_AUTHORIZATION='Bearer invalid_token')

#         # Test that the authenticate method raises an AuthenticationFailed exception
#         with self.assertRaises(exceptions.AuthenticationFailed):
#             self.authentication.authenticate(request)

#     @patch('user.signals.send_welcome_email_task.delay')
#     def test_missing_token(self, mock_task):
#         # Create a request without a token
#         request = self.factory.get('/some-endpoint')

#         # Test that the authenticate method returns None
#         result = self.authentication.authenticate(request)
#         self.assertIsNone(result)







# from django.test import TestCase
# from django.contrib.auth import get_user_model
# from django.contrib.auth.hashers import make_password, check_password
# from user.backends import MockMongoDB, MongoAuthBackend
# import logging

# logger = logging.getLogger(__name__)

# class MongoAuthBackendTestCase(TestCase):
#     def setUp(self):
#         self.backend = MongoAuthBackend()
#         self.email = "test@example.com"
#         self.password = "testpassword"

#     def test_authenticate_success(self):
#         # Mock the MongoDB connection and user data
#         db = MockMongoDB()
#         self.backend.get_mongo_db = lambda: db

#         # Add a test user to the mock database
#         user_data = {
#             "email": self.email,
#             "password": make_password(self.password),
#             "username": "testuser",
#             "first_name": "Test",
#             "last_name": "User",
#             "role": "STUDENT"
#         }
#         db.customusers.insert_one(user_data)

#         # Debug: Print the inserted user data
#         logger.debug(f"Inserted User Data: {db.customusers.data}")

#         # Test authentication
#         user = self.backend.authenticate(request=None, email=self.email, password=self.password)

#         # Debug: Print the user object returned by authenticate
#         logger.debug(f"Authenticated User: {user}")

#         self.assertIsNotNone(user)
#         self.assertEqual(user.email, self.email)

#     def test_authenticate_failure(self):
#         # Mock the MongoDB connection and user data
#         db = MockMongoDB()
#         self.backend.get_mongo_db = lambda: db

#         # Add a test user to the mock database
#         user_data = {
#             "email": self.email,
#             "password": make_password(self.password),
#             "username": "testuser",
#             "first_name": "Test",
#             "last_name": "User",
#             "role": "STUDENT"
#         }
#         db.customusers.insert_one(user_data)

#         # Test authentication with incorrect password
#         user = self.backend.authenticate(request=None, email=self.email, password="wrongpassword")

#         # Debug: Print the user object returned by authenticate
#         logger.debug(f"Authenticated User with Wrong Password: {user}")

#         self.assertIsNone(user)

#     def test_user_addition_to_customusers(self):
#         # Mock the MongoDB connection
#         db = MockMongoDB()
#         self.backend.get_mongo_db = lambda: db

#         # User data to be inserted
#         user_data = {
#             "email": self.email,
#             "password": make_password(self.password),
#             "username": "testuser",
#             "first_name": "Test",
#             "last_name": "User",
#             "role": "STUDENT"
#         }

#         # Insert the user into the customusers collection
#         inserted_user_id = db.customusers.insert_one(user_data).inserted_id

#         # Debug: Print the inserted user ID
#         logger.debug(f"Inserted User ID: {inserted_user_id}")

#         # Retrieve the inserted user data from the mock database
#         inserted_user_data = db.customusers.find_one({"_id": inserted_user_id})

#         # Debug: Print the inserted user data
#         logger.debug(f"Inserted User Data: {inserted_user_data}")

#         # Assert that the user data is not None and matches the inserted data
#         self.assertIsNotNone(inserted_user_data, "User was not added to the customusers collection.")
#         self.assertEqual(inserted_user_data["email"], self.email, "The email of the inserted user does not match.")
#         self.assertTrue(check_password(self.password, inserted_user_data["password"]), "The password of the inserted user does not match.")

#         logger.debug("User successfully added to customusers collection.")

#     def test_get_user_success(self):
#         # Mock the MongoDB connection and user data
#         db = MockMongoDB()
#         self.backend.get_mongo_db = lambda: db

#         # Add a test user to the mock database
#         user_data = {
#             "email": self.email,
#             "password": make_password(self.password),
#             "username": "testuser",
#             "first_name": "Test",
#             "last_name": "User",
#             "role": "STUDENT"
#         }
#         user_id = db.customusers.insert_one(user_data).inserted_id

#         # Debug: Print the inserted user ID and data
#         logger.debug(f"Inserted User ID: {user_id}")
#         logger.debug(f"Inserted User Data: {db.customusers.data}")

#         # Test retrieving the user
#         user = self.backend.get_user(str(user_id))

#         # Debug: Print the user object returned by get_user
#         logger.debug(f"Retrieved User: {user}")

#         self.assertIsNotNone(user)
#         self.assertEqual(user.email, self.email)

#     def test_get_user_failure(self):
#         # Mock the MongoDB connection and user data
#         db = MockMongoDB()
#         self.backend.get_mongo_db = lambda: db

#         # Test retrieving a non-existent user
#         user = self.backend.get_user("507f1f77bcf86cd799439011")  # Use a valid ObjectId string

#         # Debug: Print the user object returned by get_user
#         logger.debug(f"Retrieved Non-Existent User: {user}")

#         self.assertIsNone(user)


# from django.test import TestCase
# from django.contrib.auth import get_user_model
# from rest_framework.test import APIClient
# from rest_framework import status
# from unittest.mock import patch
# import logging

# # Configure logging
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)

# class GetCurrentUserProfileTestCase(TestCase):
#     @patch('user.signals.send_welcome_email_task.delay')
#     def setUp(self, mock_task):
#         self.User = get_user_model()
#         self.user = self.User.objects.create_user(
#             username='testuser',
#             email='testuser@example.com',
#             password='testpassword'
#         )
#         self.client = APIClient()
#         self.token_url = '/api/token/'
#         self.profile_url = '/customuser/profile/'

#     @patch('user.signals.send_welcome_email_task.delay')
#     def test_authenticated_access(self, mock_task):
#         # Obtain token
#         response = self.client.post(
#             self.token_url,
#             {'email': 'testuser@example.com', 'password': 'testpassword'},
#             format='json'
#         )

#         logger.debug(f"Token response status code: {response.status_code}")
#         logger.debug(f"Token response data: {response.data}")

#         self.assertEqual(response.status_code, status.HTTP_200_OK, "Failed to obtain token")

#         token = response.data['access']

#         # Access protected view
#         self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
#         response = self.client.get(self.profile_url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#     @patch('user.signals.send_welcome_email_task.delay')
#     def test_unauthenticated_access(self, mock_task):
#         # Access protected view without token
#         response = self.client.get(self.profile_url)
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)



from bson import ObjectId

from courses.mongo_utils import get_mongo_db
db = get_mongo_db()
user = db.customusers.find_one({"_id": ObjectId("6844c3316b0e985f716bbca5")})
print(user)  # Should return the user document

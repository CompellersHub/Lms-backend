# payments/tests.py
import datetime
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch, MagicMock
from bson import ObjectId
import json
import os
import stripe

# Assuming get_mongo_db is in payments/mongo_utils.py or courses/mongo_utils.py
# Adjust import based on where get_mongo_db() is defined
from courses.mongo_utils import get_mongo_db 
# Or from courses.mongo_utils import get_mongo_db

# Assuming your CustomUserSerializer is in user/serializers.py
from user.serializer import CustomUserSerializer 
# Assuming your CourseSerializer is in courses/serializers.py
from courses.serializer import CourseSerializer 

# Define test Stripe keys (ensure your settings.py picks these up for tests)
os.environ['STRIPE_PUBLISHABLE_KEY'] = 'pk_test_xyz'
os.environ['STRIPE_TEST_kEY'] = 'sk_test_abc'


class StripePaymentTests(APITestCase):

    def setUp(self):
        # 1. Mock the MongoDB connection
        # We need a mock for the database and its collections
        self.mock_db = MagicMock()
        # Patch get_mongo_db so it always returns our mock_db during tests
        self.patcher_get_mongo_db = patch('payments.views.get_mongo_db', return_value=self.mock_db)
        self.patcher_get_mongo_db.start()

        # If get_mongo_db is also used in serializers, you might need another patch
        # e.g., patch('user.serializers.get_mongo_db', return_value=self.mock_db)
        # patch('courses.serializers.get_mongo_db', return_value=self.mock_db)


        # 2. Create a test user and obtain a JWT token for authentication
        self.user_id = str(ObjectId()) # Generate a fake user ObjectId
        self.test_user_data = {
            '_id': ObjectId(self.user_id), # Store as ObjectId in mock DB
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'StrongPassword123!', # Password in plain text for login attempt
            'role': 'STUDENT',
            'course': [] # Empty initially
        }
        # Mock the find_one for the user collection for authentication during login
        self.mock_db.customusers.find_one.return_value = self.test_user_data.copy()

        # Mock the password checking logic for authentication (if using Django's check_password)
        with patch('django.contrib.auth.hashers.check_password', return_value=True):
            # Programmatically obtain a token for the test user
            # You might need to import your actual login view or a JWT serializer to do this
            # For simplicity, we'll simulate the token acquisition process if your JWT setup is standard.
            # If you have a custom login view, you'd call that.
            
            # This is a generic way to get a JWT token for a mocked user:
            from rest_framework_simplejwt.tokens import AccessToken
            mock_user_obj = MagicMock()
            mock_user_obj.id = self.user_id # Simulate Django user.id
            mock_user_obj.email = self.test_user_data['email']
            mock_user_obj.is_authenticated = True
            mock_user_obj.get_mongo_doc.return_value = self.test_user_data # For MongoAuthBackend
            
            # This is simplified; in real projects, you'd usually call your auth endpoint
            # from user.views import LoginView
            # response = self.client.post(reverse('your-login-url'), {'email': 'test@example.com', 'password': 'StrongPassword123!'})
            # self.access_token = response.data['access']
            
            # Manual token creation for isolated testing
            access_token = AccessToken.for_user(mock_user_obj)
            self.access_token = str(access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # 3. Define a mock course
        self.course_id = str(ObjectId())
        self.test_course_data = {
            '_id': ObjectId(self.course_id),
            'name': 'Test Course for Stripe',
            'price': 49.99, # Price in dollars
            'description': 'A fantastic course for testing.',
            'category': {'_id': ObjectId(), 'name': 'Test Category'},
            'level': 'beginner',
        }
        # Mock the course lookup when fetching it by ID
        self.mock_db.courses.find_one.return_value = self.test_course_data.copy()
        
        # Mock user update operations
        self.mock_db.customusers.update_one.return_value = MagicMock(modified_count=1, matched_count=1)
        self.mock_db.enrollments_transactions.insert_one.return_value = MagicMock(inserted_id=ObjectId())

    def tearDown(self):
        # Stop all patches
        self.patcher_get_mongo_db.stop()
        patch.stopall() # Ensure all patches are stopped

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_success(self, mock_stripe_create):
        # Mock Stripe's response for creating a PaymentIntent
        mock_stripe_create.return_value = MagicMock(
            client_secret='pi_test_xyz_secret',
            id='pi_test_xyz'
        )

        url = reverse('create-payment-intent') # Make sure this matches your payments/urls.py name
        data = {'course_id': self.course_id}
        
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('clientSecret', response.data)
        self.assertEqual(response.data['clientSecret'], 'pi_test_xyz_secret')
        self.assertIn('publishableKey', response.data)
        self.assertEqual(response.data['publishableKey'], os.environ['STRIPE_PUBLISHABLE_KEY'])
        self.assertIn('course_id', response.data)
        self.assertEqual(response.data['course_id'], self.course_id)

        # Assert that MongoDB was queried for the course
        self.mock_db.courses.find_one.assert_called_with({"_id": ObjectId(self.course_id)})
        
        # Assert that Stripe.PaymentIntent.create was called with correct arguments
        mock_stripe_create.assert_called_once()
        args, kwargs = mock_stripe_create.call_args
        self.assertEqual(kwargs['amount'], int(self.test_course_data['price'] * 100))
        self.assertEqual(kwargs['currency'], 'usd')
        self.assertIn('metadata', kwargs)
        self.assertEqual(kwargs['metadata']['course_id'], self.course_id)
        self.assertEqual(kwargs['metadata']['user_id'], self.user_id)
        self.assertEqual(kwargs['metadata']['course_price_at_payment'], str(self.test_course_data['price']))


    def test_create_payment_intent_missing_course_id(self):
        url = reverse('create-payment-intent')
        response = self.client.post(url, {}, format='json') # No course_id
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Course ID is required.')

    def test_create_payment_intent_course_not_found(self):
        self.mock_db.courses.find_one.return_value = None # Mock course not found

        url = reverse('create-payment-intent')
        data = {'course_id': str(ObjectId())} # Use a different, non-existent ID
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Course not found.')

    @patch('stripe.PaymentIntent.retrieve')
    def test_payment_success_view_success_new_enrollment(self, mock_stripe_retrieve):
        # Mock Stripe's response for retrieving a succeeded PaymentIntent
        mock_stripe_retrieve.return_value = MagicMock(
            status='succeeded',
            id='pi_successful_123',
            amount=int(self.test_course_data['price'] * 100),
            currency='usd',
            metadata={
                'course_id': self.course_id,
                'user_id': self.user_id,
                'course_price_at_payment': str(self.test_course_data['price']),
            }
        )

        # Mock the user document lookup (initially not enrolled)
        self.mock_db.customusers.find_one.side_effect = [
            self.test_user_data.copy(), # First call for user_document
            self.test_course_data.copy(), # Then for course_document (inside, as part of validation)
            # No third call needed if update_one is mocked and returns success
        ]
        
        # Mock the update_one to show a change occurred
        self.mock_db.customusers.update_one.return_value = MagicMock(modified_count=1, matched_count=1)

        url = reverse('payment-success-webhook-alternative')
        data = {
            'payment_intent_id': 'pi_successful_123',
            'course_id': self.course_id
        }
        
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Payment successful and course enrolled!')

        # Assert Stripe.PaymentIntent.retrieve was called
        mock_stripe_retrieve.assert_called_once_with('pi_successful_123')

        # Assert user and course documents were fetched
        self.mock_db.customusers.find_one.assert_any_call({"_id": ObjectId(self.user_id)})
        self.mock_db.courses.find_one.assert_any_call({"_id": ObjectId(self.course_id)}) # Called during price check

        # Assert user's course array was updated with the full course document
        self.mock_db.customusers.update_one.assert_called_once()
        args, kwargs = self.mock_db.customusers.update_one.call_args
        self.assertEqual(args[0], {"_id": ObjectId(self.user_id)})
        
        # Verify the pushed data contains the course document including its _id
        pushed_data = args[1]['$push']['course']
        self.assertEqual(pushed_data['_id'], ObjectId(self.course_id))
        self.assertEqual(pushed_data['name'], self.test_course_data['name'])
        self.assertEqual(pushed_data['price'], self.test_course_data['price'])

        # Assert enrollment transaction was recorded
        self.mock_db.enrollments_transactions.insert_one.assert_called_once()
        args, _ = self.mock_db.enrollments_transactions.insert_one.call_args
        self.assertEqual(args[0]['user_id'], ObjectId(self.user_id))
        self.assertEqual(args[0]['course_id'], ObjectId(self.course_id))
        self.assertEqual(args[0]['payment_intent_id'], 'pi_successful_123')
        self.assertEqual(args[0]['amount_paid'], self.test_course_data['price'])


    @patch('stripe.PaymentIntent.retrieve')
    def test_payment_success_view_already_enrolled(self, mock_stripe_retrieve):
        # Mock Stripe's response for retrieving a succeeded PaymentIntent
        mock_stripe_retrieve.return_value = MagicMock(
            status='succeeded',
            id='pi_successful_123_already_enrolled',
            amount=int(self.test_course_data['price'] * 100),
            currency='usd',
            metadata={
                'course_id': self.course_id,
                'user_id': self.user_id,
                'course_price_at_payment': str(self.test_course_data['price']),
            }
        )

        # Mock the user document lookup (already enrolled)
        user_data_already_enrolled = self.test_user_data.copy()
        user_data_already_enrolled['course'] = [self.test_course_data.copy()] # User is already enrolled
        
        self.mock_db.customusers.find_one.side_effect = [
            user_data_already_enrolled, # First call for user_document
            self.test_course_data.copy() # Then for course_document
        ]

        url = reverse('payment-success-webhook-alternative')
        data = {
            'payment_intent_id': 'pi_successful_123_already_enrolled',
            'course_id': self.course_id
        }
        
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Course already enrolled.')

        # Assert Stripe.PaymentIntent.retrieve was called
        mock_stripe_retrieve.assert_called_once_with('pi_successful_123_already_enrolled')

        # Assert user and course documents were fetched
        self.mock_db.customusers.find_one.assert_any_call({"_id": ObjectId(self.user_id)})
        self.mock_db.courses.find_one.assert_any_call({"_id": ObjectId(self.course_id)})

        # Assert that update_one was NOT called as the user is already enrolled
        self.mock_db.customusers.update_one.assert_not_called()
        self.mock_db.enrollments_transactions.insert_one.assert_not_called()


    @patch('stripe.PaymentIntent.retrieve')
    def test_payment_success_view_payment_failed(self, mock_stripe_retrieve):
        # Mock Stripe's response for a failed PaymentIntent
        mock_stripe_retrieve.return_value = MagicMock(
            status='failed',
            id='pi_failed_456'
        )

        url = reverse('payment-success-webhook-alternative')
        data = {
            'payment_intent_id': 'pi_failed_456',
            'course_id': self.course_id
        }
        
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Payment not successful. Status: failed')
        
        # Ensure no DB updates for a failed payment
        self.mock_db.customusers.update_one.assert_not_called()
        self.mock_db.enrollments_transactions.insert_one.assert_not_called()

    @patch('stripe.PaymentIntent.retrieve', side_effect=stripe.error.APIError("Stripe API Error"))
    def test_payment_success_view_stripe_api_error(self, mock_stripe_retrieve):
        url = reverse('payment-success-webhook-alternative')
        data = {
            'payment_intent_id': 'pi_error_789',
            'course_id': self.course_id
        }
        
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
        self.assertIn('Stripe API error', response.data['error'])
        
        self.mock_db.customusers.update_one.assert_not_called()
        self.mock_db.enrollments_transactions.insert_one.assert_not_called()

    def test_payment_success_view_missing_data(self):
        url = reverse('payment-success-webhook-alternative')
        response = self.client.post(url, {}, format='json') # Missing both
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Payment Intent ID and Course ID are required.')

        response = self.client.post(url, {'payment_intent_id': 'test'}, format='json') # Missing course_id
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Payment Intent ID and Course ID are required.')
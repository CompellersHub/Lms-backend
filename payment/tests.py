# payments/tests.py
# import datetime
# from django.urls import reverse
# from rest_framework import status
# from rest_framework.test import APITestCase
# from unittest.mock import patch, MagicMock
# from bson import ObjectId
# import json
# import os
# import stripe
# from user.backends import MongoAuthBackend

# # Assuming get_mongo_db is in payment/mongo_utils.py, but imported from courses.mongo_utils
# # This import is primarily for direct use in this test file if needed.
# from courses.mongo_utils import get_mongo_db # Keep this as per your project structure

# # Assuming your CustomUserSerializer is in user/serializer.py
# from user.serializer import CustomUserSerializer 
# # Assuming your CourseSerializer is in courses/serializer.py
# from courses.serializer import CourseSerializer 

# # Define test Stripe keys (ensure your settings.py picks these up for tests)
# os.environ['STRIPE_PUBLISHABLE_KEY'] = 'pk_test_xyz'
# os.environ['STRIPE_SECRET_KEY'] = 'sk_test_abc'


# class StripePaymentTests(APITestCase):

#     def setUp(self):
#         # 1. Mock the MongoDB connection
#         self.mock_db = MagicMock()
        
#         # Patch get_mongo_db where it's used in your views
#         self.patcher_views_db = patch('payment.views.get_mongo_db', return_value=self.mock_db)
#         self.patcher_views_db.start()

#         # Patch get_mongo_db where user.backends imports it from
#         self.patcher_auth_backend_db = patch('courses.mongo_utils.get_mongo_db', return_value=self.mock_db)
#         self.patcher_auth_backend_db.start()

#         # 2. Create a test user
#         self.user_id = str(ObjectId()) 
#         self.test_user_data = {
#             '_id': ObjectId(self.user_id), 
#             'username': 'testuser',
#             'email': 'test@example.com',
#             'password': 'StrongPassword123!', 
#             'role': 'STUDENT',
#             'course': [] 
#         }
#         # Mock find_one for customusers, in case your actual backend still calls it for some reason
#         self.mock_db.customusers.find_one.return_value = self.test_user_data.copy()

#         # *** THE ONLY AUTHENTICATION-RELATED CHANGE YOU NEED ***
#         # Create a mock user object that behaves like an authenticated Django user
#         self.mock_authenticated_user = MagicMock()
#         self.mock_authenticated_user.is_authenticated = True # Crucial for DRF's IsAuthenticated
#         self.mock_authenticated_user.id = self.user_id # Needed if any part of your code uses user.id
#         self.mock_authenticated_user.email = self.test_user_data['email'] 
#         self.mock_authenticated_user.get_mongo_doc.return_value = self.test_user_data.copy() # For your views if they access _mongo_doc directly

#         # Force the test client to use this mock user for all subsequent requests
#         # This bypasses the full JWT token validation in the test environment for `request.user`
#         self.client.force_authenticate(user=self.mock_authenticated_user)

#         # Remove JWT token generation and credentials setting since force_authenticate handles it
#         # You can remove these lines if you only use force_authenticate
#         # with patch('django.contrib.auth.hashers.check_password', return_value=True):
#         #     from rest_framework_simplejwt.tokens import AccessToken
#         #     token_generating_mock = MagicMock(id=self.user_id) 
#         #     access_token = AccessToken.for_user(token_generating_mock)
#         #     self.access_token = str(access_token)
#         # self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')


#         # 3. Define a mock course
#         self.course_id = str(ObjectId())
#         self.test_course_data = {
#             '_id': ObjectId(self.course_id),
#             'name': 'Test Course for Stripe',
#             'price': 49.99, 
#             'description': 'A fantastic course for testing.',
#             'category': {'_id': ObjectId(), 'name': 'Test Category'},
#             'level': 'beginner',
#         }
#         self.mock_db.courses.find_one.return_value = self.test_course_data.copy()
        
#         self.mock_db.customusers.update_one.return_value = MagicMock(modified_count=1, matched_count=1)
#         self.mock_db.enrollments_transactions.insert_one.return_value = MagicMock(inserted_id=ObjectId())

#     def tearDown(self):
#         self.patcher_views_db.stop()
#         self.patcher_auth_backend_db.stop() 
#         # No need to stop patcher_auth_backend_get_user if force_authenticate is used,
#         # as it's no longer necessary to patch the backend's get_user.
#         patch.stopall() 

#     @patch('stripe.PaymentIntent.create')
#     def test_create_payment_intent_success(self, mock_stripe_create):
#         mock_stripe_create.return_value = MagicMock(
#             client_secret='pi_test_xyz_secret',
#             id='pi_test_xyz'
#         )
#         url = reverse('payment:create-payment-intent') 
#         data = {'course_id': self.course_id}
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertIn('clientSecret', response.data)
#         self.assertEqual(response.data['clientSecret'], 'pi_test_xyz_secret')
#         self.assertIn('publishableKey', response.data)
#         self.assertEqual(response.data['publishableKey'], os.environ['STRIPE_PUBLISHABLE_KEY'])
#         self.assertIn('course_id', response.data)
#         self.assertEqual(response.data['course_id'], self.course_id)
#         self.mock_db.courses.find_one.assert_called_with({"_id": ObjectId(self.course_id)})
#         mock_stripe_create.assert_called_once()
#         args, kwargs = mock_stripe_create.call_args
#         self.assertEqual(kwargs['amount'], int(self.test_course_data['price'] * 100))
#         self.assertEqual(kwargs['currency'], 'usd')
#         self.assertIn('metadata', kwargs)
#         self.assertEqual(kwargs['metadata']['course_id'], self.course_id)
#         self.assertEqual(kwargs['metadata']['user_id'], self.user_id)
#         self.assertEqual(kwargs['metadata']['course_price_at_payment'], str(self.test_course_data['price']))


#     def test_create_payment_intent_missing_course_id(self):
#         url = reverse('payment:create-payment-intent')
#         response = self.client.post(url, {}, format='json') 
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('error', response.data)
#         self.assertEqual(response.data['error'], 'Course ID is required.')

#     def test_create_payment_intent_course_not_found(self):
#         self.mock_db.courses.find_one.return_value = None 
#         url = reverse('payment:create-payment-intent')
#         data = {'course_id': str(ObjectId())} 
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
#         self.assertIn('error', response.data)
#         self.assertEqual(response.data['error'], 'Course not found.')

#     @patch('stripe.PaymentIntent.retrieve')
#     def test_payment_success_view_success_new_enrollment(self, mock_stripe_retrieve):
#         mock_stripe_retrieve.return_value = MagicMock(
#             status='succeeded',
#             id='pi_successful_123',
#             amount=int(self.test_course_data['price'] * 100),
#             currency='usd',
#             metadata={
#                 'course_id': self.course_id,
#                 'user_id': self.user_id,
#                 'course_price_at_payment': str(self.test_course_data['price']),
#             }
#         )
#         self.mock_db.customusers.find_one.side_effect = [
#             self.test_user_data.copy(), 
#             self.test_course_data.copy(), 
#         ]
#         self.mock_db.customusers.update_one.return_value = MagicMock(modified_count=1, matched_count=1)
#         url = reverse('payment:payment-success-webhook-alternative')
#         data = {
#             'payment_intent_id': 'pi_successful_123',
#             'course_id': self.course_id
#         }
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertIn('message', response.data)
#         self.assertEqual(response.data['message'], 'Payment successful and course enrolled!')
#         mock_stripe_retrieve.assert_called_once_with('pi_successful_123')
#         self.mock_db.customusers.find_one.assert_any_call({"_id": ObjectId(self.user_id)})
#         self.mock_db.courses.find_one.assert_any_call({"_id": ObjectId(self.course_id)})
#         self.mock_db.customusers.update_one.assert_called_once()
#         args, kwargs = self.mock_db.customusers.update_one.call_args
#         self.assertEqual(args[0], {"_id": ObjectId(self.user_id)})
#         pushed_data = args[1]['$push']['course']
#         self.assertEqual(pushed_data['_id'], ObjectId(self.course_id))
#         self.assertEqual(pushed_data['name'], self.test_course_data['name'])
#         self.assertEqual(pushed_data['price'], self.test_course_data['price'])
#         self.mock_db.enrollments_transactions.insert_one.assert_called_once()
#         args, _ = self.mock_db.enrollments_transactions.insert_one.call_args
#         self.assertEqual(args[0]['user_id'], ObjectId(self.user_id))
#         self.assertEqual(args[0]['course_id'], ObjectId(self.course_id))
#         self.assertEqual(args[0]['payment_intent_id'], 'pi_successful_123')
#         self.assertEqual(args[0]['amount_paid'], self.test_course_data['price'])


#     @patch('stripe.PaymentIntent.retrieve')
#     def test_payment_success_view_already_enrolled(self, mock_stripe_retrieve):
#         mock_stripe_retrieve.return_value = MagicMock(
#             status='succeeded',
#             id='pi_successful_123_already_enrolled',
#             amount=int(self.test_course_data['price'] * 100),
#             currency='usd',
#             metadata={
#                 'course_id': self.course_id,
#                 'user_id': self.user_id,
#                 'course_price_at_payment': str(self.test_course_data['price']),
#             }
#         )
#         user_data_already_enrolled = self.test_user_data.copy()
#         user_data_already_enrolled['course'] = [self.test_course_data.copy()] 
#         self.mock_db.customusers.find_one.side_effect = [
#             user_data_already_enrolled, 
#             self.test_course_data.copy() 
#         ]
#         url = reverse('payment:payment-success-webhook-alternative')
#         data = {
#             'payment_intent_id': 'pi_successful_123_already_enrolled',
#             'course_id': self.course_id
#         }
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertIn('message', response.data)
#         self.assertEqual(response.data['message'], 'Course already enrolled.')
#         mock_stripe_retrieve.assert_called_once_with('pi_successful_123_already_enrolled')
#         self.mock_db.customusers.find_one.assert_any_call({"_id": ObjectId(self.user_id)})
#         self.mock_db.courses.find_one.assert_any_call({"_id": ObjectId(self.course_id)})
#         self.mock_db.customusers.update_one.assert_not_called()
#         self.mock_db.enrollments_transactions.insert_one.assert_not_called()


#     @patch('stripe.PaymentIntent.retrieve')
#     def test_payment_success_view_payment_failed(self, mock_stripe_retrieve):
#         mock_stripe_retrieve.return_value = MagicMock(
#             status='failed',
#             id='pi_failed_456'
#         )
#         url = reverse('payment:payment-success-webhook-alternative')
#         data = {
#             'payment_intent_id': 'pi_failed_456',
#             'course_id': self.course_id
#         }
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('error', response.data)
#         self.assertEqual(response.data['error'], 'Payment not successful. Status: failed')
#         self.mock_db.customusers.update_one.assert_not_called()
#         self.mock_db.enrollments_transactions.insert_one.assert_not_called()

#     @patch('stripe.PaymentIntent.retrieve', side_effect=stripe.error.APIError("Stripe API Error"))
#     def test_payment_success_view_stripe_api_error(self, mock_stripe_retrieve):
#         url = reverse('payment:payment-success-webhook-alternative')
#         data = {
#             'payment_intent_id': 'pi_error_789',
#             'course_id': self.course_id
#         }
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
#         self.assertIn('error', response.data)
#         self.assertIn('Stripe API error', response.data['error'])
#         self.mock_db.customusers.update_one.assert_not_called()
#         self.mock_db.enrollments_transactions.insert_one.assert_not_called()

#     def test_payment_success_view_missing_data(self):
#         url = reverse('payment:payment-success-webhook-alternative')
#         response = self.client.post(url, {}, format='json') 
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('error', response.data)
#         self.assertEqual(response.data['error'], 'Payment Intent ID and Course ID are required.')
#         response = self.client.post(url, {'payment_intent_id': 'test'}, format='json') 
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('error', response.data)
#         self.assertEqual(response.data['error'], 'Payment Intent ID and Course ID are required.')















import pytest
from unittest.mock import Mock, patch
from bson import ObjectId
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()

# --------------------------
# FIXTURES
# --------------------------

@pytest.fixture
def mock_auth_client():
    """Authenticated test client with mock user"""
    user = Mock(
        id=str(ObjectId()),
        is_authenticated=True,
        email='test@example.com'
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.fixture
def mock_db():
    """Mock MongoDB database"""
    db = Mock()
    
    # Configure default mock responses
    db.customusers.find_one.return_value = {
        '_id': ObjectId(),
        'course': []
    }
    db.courses.find_one.return_value = {
        '_id': ObjectId(),
        'name': 'Test Course',
        'price': 99.99
    }
    db.enrollments_transactions.insert_one.return_value = Mock(inserted_id=ObjectId())
    
    return db

# --------------------------
# TESTS
# --------------------------

@patch('payment.views.paypal_client')  # Update to your actual PayPal client path
@patch('payment.views.get_mongo_db')    # Update to your actual DB getter path
def test_successful_enrollment(mock_get_db, mock_paypal, mock_auth_client, mock_db):
    # Setup mocks
    mock_get_db.return_value = mock_db
    test_course_id = str(ObjectId())
    
    mock_paypal.return_value = {
        'purchase_units': [{
            'custom_id': f"{mock_auth_client.user.id}|{test_course_id}"
        }]
    }

    # Make request
    response = mock_auth_client.post(
        '/api/verify-paypal-order/',
        {'orderID': 'TEST_ORDER_123'},
        format='json'
    )

    # Assertions
    assert response.status_code == status.HTTP_200_OK
    assert 'Successfully enrolled' in response.data['message']
    mock_db.customusers.update_one.assert_called_once()

@patch('payment.views.paypal_client')
def test_missing_order_id(mock_paypal, mock_auth_client):
    response = mock_auth_client.post(
        '/api/verify-paypal-order/',
        {},  # Missing orderID
        format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'orderID is required' in response.data['error']

@patch('your_app.paypal._make_request')
@patch('your_app.views.get_mongo_db')
def test_user_id_mismatch(mock_get_db, mock_paypal, mock_auth_client, mock_db):
    mock_get_db.return_value = mock_db
    # Simulate PayPal returning wrong user ID
    mock_paypal.return_value = {
        'purchase_units': [{
            'custom_id': f"WRONG_USER_ID|{ObjectId()}"
        }]
    }

    response = mock_auth_client.post(
        '/api/verify-paypal-order/',
        {'orderID': 'TEST_ORDER_123'},
        format='json'
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Security check failed" in response.data['error']

@patch('your_app.paypal._make_request')
@patch('your_app.views.get_mongo_db')
def test_already_enrolled(mock_get_db, mock_paypal, mock_auth_client, mock_db):
    mock_get_db.return_value = mock_db
    test_course_id = ObjectId()
    
    # Mock user already enrolled
    mock_db.customusers.find_one.return_value = {
        '_id': ObjectId(mock_auth_client.user.id),
        'course': [{'_id': test_course_id}]
    }
    
    mock_paypal.return_value = {
        'purchase_units': [{
            'custom_id': f"{mock_auth_client.user.id}|{test_course_id}"
        }]
    }

    response = mock_auth_client.post(
        '/api/verify-paypal-order/',
        {'orderID': 'TEST_ORDER_123'},
        format='json'
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert 'already enrolled' in response.data['message']

@patch('your_app.views.get_mongo_db')
def test_database_error(mock_get_db, mock_auth_client):
    mock_get_db.return_value = None  # Simulate DB failure
    
    response = mock_auth_client.post(
        '/api/verify-paypal-order/',
        {'orderID': 'TEST_ORDER_123'},
        format='json'
    )
    
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert 'Database connection error' in response.data['error']
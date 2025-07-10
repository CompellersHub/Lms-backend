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















# payment/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from bson import ObjectId
from datetime import datetime, timedelta
import json
from unittest.mock import patch
import hmac
import hashlib

# Fix imports to point to correct locations
from payment.views import BankTransferEnrollmentView, EnrollmentStatusView, bank_webhook
from payment.services.validation import validate_course
from payment.services.enrollment import enroll_student

from rest_framework.test import APIClient, force_authenticate
from user.models import CustomUser

class BankTransferEnrollmentTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass',
            first_name='Test',
            last_name='User',
            username='user'
        )
        self.client.force_authenticate(user=self.user)
        self.enroll_url = reverse('payment:bank-enrollment')
        self.test_course = {
            '_id': ObjectId(),
            'name': 'Test Course',
            'price': 99.99,
            'is_active': True,
            'enrollment_open': True
        }
        
    @patch('payment.services.validation.db.courses.find_one')
    def test_successful_enrollment_initiation(self, mock_find):
        mock_find.return_value = self.test_course
        
        response = self.client.post(
            self.enroll_url,
            {'course_id': str(self.test_course['_id'])},
            HTTP_AUTHORIZATION='Bearer validtoken'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('payment_instructions', response.data)
        self.assertEqual(response.data['status'], 'pending')
        
    def test_missing_course_id(self):
        response = self.client.post(
            self.enroll_url,
            {},
            HTTP_AUTHORIZATION='Bearer validtoken'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    @patch('payment.services.validation.db.courses.find_one')
    def test_inactive_course(self, mock_find):
        self.test_course['is_active'] = False
        mock_find.return_value = self.test_course
        
        response = self.client.post(
            self.enroll_url,
            {'course_id': str(self.test_course['_id'])},
            HTTP_AUTHORIZATION='Bearer validtoken'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BankWebhookTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.webhook_url = reverse('payment:bank-webhook')
        self.test_transfer = {
            '_id': ObjectId(),
            'user_id': ObjectId(),
            'course_id': ObjectId(),
            'amount': 99.99,
            'status': 'PENDING',
            'reference': 'ENROLL-TEST123',
            'virtual_account': '12345678'
        }
        
    def generate_webhook_signature(self, payload):
        secret = b'testsecret'
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()
        
    @patch('payment.views.db.bank_transfers.find_one')
    @patch('payment.services.enrollment.db.courses.find_one')
    @patch('payment.services.enrollment.enroll_student')
    def test_successful_payment_webhook(self, mock_enroll, mock_course_find, mock_transfer_find):
        # Ensure the mock returns a transaction matching the reference
        test_transfer = self.test_transfer.copy()
        test_transfer['reference'] = 'ENROLL-TEST123'
        mock_transfer_find.return_value = test_transfer
        
        payload = {
            'event': 'payment.received',
            'data': {
                'account': '12345678',
                'reference': 'ENROLL-TEST123',
                'amount': 99.99,
                'transaction_id': 'BANKTX123'
            }
        }
        json_payload = json.dumps(payload).encode('utf-8')
        signature = self.generate_webhook_signature(json_payload)
        
        response = self.client.post(
            self.webhook_url,
            data=json_payload,
            content_type='application/json',
            HTTP_X_BANK_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, 200)


class EnrollmentStatusTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpass',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        
        self.test_reference = 'ENROLL-TEST123'
        self.status_url = reverse('payment:enrollment-status', args=[self.test_reference])
        self.test_transfer = {
            'user_id': ObjectId(self.user.id),  # Use _id instead of id for MongoDB
            'course_id': ObjectId(),
            'status': 'COMPLETED',
            'reference': self.test_reference,
            'amount': 99.99,
            'created_at': datetime.utcnow(),
            'completed_at': datetime.utcnow()
        }
        
    @patch('payment.services.validation.db.courses.find_one')
    def test_successful_enrollment_initiation(self, mock_find):
        mock_find.return_value = self.test_course

        response = self.client.post(
            self.enroll_url,
            {
                'course_id': str(self.test_course['_id']),
                'payment_method': 'bank_transfer'  # Add required field
            },
            format='json',
            HTTP_AUTHORIZATION='Bearer validtoken'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    @patch('payment.views.db.bank_transfers.find_one')
    def test_not_found(self, mock_find):
        mock_find.return_value = None
        
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CourseValidationTests(TestCase):
    @patch('payment.services.validation.db.courses.find_one')
    def test_validate_course(self, mock_find):
        test_course = {
            '_id': ObjectId("507f1f77bcf86cd799439011"),  # Fixed specific ID
            'name': 'Test Course',
            'price': 99.99,
            'is_active': True,
            'enrollment_open': True
        }
        mock_find.return_value = test_course
        
        # Use the same ID as in the test_course
        result = validate_course("507f1f77bcf86cd799439011")
        self.assertIsNotNone(result)
        self.assertEqual(str(result['_id']), "507f1f77bcf86cd799439011")
            
    def test_invalid_course_id(self):
        result = validate_course('invalidid')
        self.assertIsNone(result)


class EnrollmentServiceTests(TestCase):
    @patch('payment.services.enrollment.db.users.update_one')
    @patch('payment.services.enrollment.db.courses.find_one')
    @patch('payment.services.enrollment.db.transactions.insert_one')
    def test_enroll_student(self, mock_insert, mock_find, mock_update):
        test_course = {
            '_id': ObjectId("607f1f77bcf86cd799439011"),
            'name': 'Test Course',
            'price': 99.99,
            'instructor': {'name': 'Test Instructor'},
            'curriculum': [{
                '_id': ObjectId("707f1f77bcf86cd799439011"),
                'title': 'Module 1',
                'lessons': [{'_id': ObjectId("807f1f77bcf86cd799439011"), 'title': 'Lesson 1'}]
            }]
        }

        mock_find.return_value = test_course
        mock_update.return_value.modified_count = 1
        mock_insert.return_value.inserted_id = ObjectId()

        enrollment_data = {
            'user_id': ObjectId("907f1f77bcf86cd799439011"),
            'course_id': ObjectId("607f1f77bcf86cd799439011"),  # Match the test_course ID
            'payment_method': 'bank_transfer',
            'amount': 99.99,
            'bank_reference': 'TESTREF123'
        }

        result = enroll_student(enrollment_data)
        self.assertIsNotNone(result)
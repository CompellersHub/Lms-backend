from dotenv import load_dotenv
import os
from pathlib import Path
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from pymongo import MongoClient


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()


MONGO_URI = os.getenv('MONGO_URI')
MONGO_DATABASE_NAME = os.getenv('DATABASE_NAME')

# For your signals.py
FRONTEND_RESET_PASSWORD_URL = 'https://titanscareers/api/password_reset/' # Replace with your actual frontend URL
FRONTEND_DOMAIN = 'titanscareers.com' # Your frontend domain
SITE_NAME = 'Titans Careers' # Your site name


# uri = "MONGO_URI"
# client = MongoClient(uri, ssl=True, ssl_cert_reqs='CERT_NONE')
# db = client['MONGO_DATABASE_NAME']
# print(db.list_collection_names())



# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
#SECRET_KEY = 'django-insecure-f($n54+mp@2@3bx$smc=$2-rxd6jyzbbz4%=h-_34%^w37_*--'
SECRET_KEY = os.getenv('SECRET_KEY') or 'django-insecure-f($n54+mp@2@3bx$smc=$2-rxd6jyzbbz4%=h-_34%^w37_*--'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# ALLOWED_HOSTS = ['lms-backend-bn1v.onrender.com', '127.0.0.1', 'DOMAIN_NAME']
DOMAIN_NAME = os.getenv('DOMAIN_NAME')
ALLOWED_HOSTS =  [DOMAIN_NAME] if DOMAIN_NAME else ['*'] 

#Application definition

INSTALLED_APPS = [
    
    'jazzmin',
    "unfold.contrib.import_export",
    "import_export",
    'unfold',
    "unfold.contrib.forms",
    # default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'user',
    'courses',
    'blog',
    'rest_framework',
    'rest_framework.authtoken',
    'django_rest_passwordreset',
    'payment',
    'student_dashboard',
    'dj_rest_auth',
    'django.contrib.sites',
    'drf_yasg',
    'channels',
    # allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.google',


    'corsheaders',
    # Aws storage
    'storages',
]

# AWS S3 Settings
# Get these from your AWS IAM user credentials or instance profile
AWS_ACCESS_KEY_ID = os.getenv('AKIA3LJ4RV54VBU3THAR')
AWS_SECRET_ACCESS_KEY = os.getenv('/h9y+MyKXbhbcrkD8JISBpTulOvktpOAwSWGr+QO')
AWS_STORAGE_BUCKET_NAME = os.getenv('titanscareers') # The S3 bucket name you created
AWS_S3_REGION_NAME = os.getenv('eu-north-1') # e.g., 'us-east-1'
AWS_S3_FILE_OVERWRITE = False # Prevents overwriting files with the same name

# Optional: If you want to use a custom domain for S3 (e.g., if you map a CNAME to S3 direct)
# AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'

# For media files (user uploads)
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/media/' # Direct S3 URL for media uploads

# For CloudFront Integration (highly recommended for video)
# Use your CloudFront Distribution Domain Name here
# AWS_S3_CUSTOM_DOMAIN = 'yourcloudfrontdomain.cloudfront.net' # e.g., d1234abcd.cloudfront.net
# MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/' # CloudFront URL for media uploads
# AWS_CLOUDFRONT_DOMAIN = 'yourcloudfrontdomain.cloudfront.net' # Store this separately for clarity if needed

# If you need private content with signed URLs (see below)
# AWS_QUERYSTRING_AUTH = False # Set to False if you use CloudFront for public content
# If using signed URLs with CloudFront:
# AWS_CLOUDFRONT_KEY_ID = 'YOUR_CLOUDFRONT_PUBLIC_KEY_ID'
# AWS_CLOUDFRONT_PRIVATE_KEY_PATH = '/path/to/your/cloudfront_private_key.pem' # Store securely!
# Important Security Note: Never hardcode your AWS access keys directly in settings.py in production. Use environment variables (e.g., os.environ.get('AWS_ACCESS_KEY_ID')) or better yet, IAM roles for EC2 instances if your Django app is hosted on AWS.

SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_STORE_TOKENS = True

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Add the account middleware:
    "allauth.account.middleware.AccountMiddleware",
]

CORS_ALLOWED_ORIGINS = [
    "https://titanscareers.com",
    "https://lms-react-frontend-sand.vercel.app",
    "http://127.0.0.1:5502",
    "http://localhost:3000",
    "http://127.0.0.1:9000",
    "http://localhost:5173",
    
]


CORS_ALLOW_CREDENTIALS = True



CORS_ALLOWED_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
] 

CORS_ALLOW_HEADERS = (
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
)

ROOT_URLCONF = 'amlpro.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # django allauth
                'django.template.context_processors.request'
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    'user.backends.MongoAuthBackend',
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by email
    'allauth.account.auth_backends.AuthenticationBackend',

    'user.auth_backends.EmailBackend',

]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        #'rest_framework.authentication.TokenAuthentication',
    ],
         'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly', #  desired default permission
    ],
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'


ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
# ACCOUNT_EMAIL_VERIFICATION = 'mandatory'



LOGIN_REDIRECT_URL = 'http://localhost:5173/'
ACCOUNT_LOGOUT_REDIRECT_URL = 'http://localhost:5173/'

SOCIALACCOUNT_FORMS = {
    'disconnect': 'allauth.socialaccount.forms.DisconnectForm',
    'signup': 'allauth.socialaccount.forms.SignupForm',
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com' # Or your email host (e.g., SendGrid, Mailgun)
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_ADDRESS') # Your email address
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWORD') # Your email password or app password
DEFAULT_FROM_EMAIL = 'olomoshuaomozafen@gmail.com' # From address for emails

AUTH_USER_MODEL = 'user.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


SOCIALACCOUNT_PROVIDERS = {
    'google': {
        # For each OAuth based provider, either add a ``SocialApp``
        # (``socialaccount`` app) containing the required client
        # credentials, or list them here:
        'APP': {
            'client_id' : os.getenv('CLIENT_ID'),
            'secret': os.getenv('SECRET'),
            'key': ''
        },

        'SCOPE' : {
            'profile',
            'email',
        },
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PRICE_ENABLED': True
    }
}

import paypalrestsdk

PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET')
PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')

SITE_ID = 1

# SOCIALACCOUNT_ADAPTER = 'user.adapters.CustomSocialAccountAdapter'


WSGI_APPLICATION = 'amlpro.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}



# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators




# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Lagos'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'




JAZZMIN_SETTINGS = {
     "site_title": "Titans career",
     "site_header": "Titans career",
     "site_logo": "/amlpro/staticfiles/logo/logo.jpg",
     "login_logo": "/amlpro/staticfiles/logo/logo.jpg",
     "copyright": "Titans career site",
     "topmenu_links":[
          {"app": "Titans career"},
          {"name": "Support", "url": "https://chowdeck.com/store/alimosho-1/restaurants/mb-shawarma-bite", "new_window": True},
     ],
     "use_google_fonts_cdn": True,
      "show_ui_builder": True,
}

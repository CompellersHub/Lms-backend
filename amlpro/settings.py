from dotenv import load_dotenv
import os
from pathlib import Path
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from pymongo import MongoClient
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()


MONGO_URI = os.getenv('MONGO_URI')
MONGO_DATABASE_NAME = os.getenv('DATABASE_NAME')

# For your signals.py
FRONTEND_RESET_PASSWORD_URL = 'https://www.titanscareers.com/courses/password-reset/confirm/' # Replace with your actual frontend URL
FRONTEND_DOMAIN = 'titanscareers.com' # Your frontend domain
SITE_NAME = 'Titans Careers' # Your site name


# uri = "MONGO_URI"
# client = MongoClient(uri, ssl=True, ssl_cert_reqs='CERT_NONE')
# db = client['MONGO_DATABASE_NAME']
# print(db.list_collection_names())



# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-f($n54+mp@2@3bx$smc=$2-rxd6jyzbbz4%=h-_34%^w37_*--'
# SECRET_KEY =  os.getenv('SECRET_KEY')
print(f"--- DEBUG: Current SECRET_KEY in use: '{SECRET_KEY}' ---")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# ALLOWED_HOSTS = ['lms-backend-bn1v.onrender.com', '127.0.0.1', 'DOMAIN_NAME']
DOMAIN_NAME = os.getenv('DOMAIN_NAME')
ALLOWED_HOSTS =  [DOMAIN_NAME] if DOMAIN_NAME else ['*'] 

#Application definition



STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_TEST_KEY = os.getenv('STRIPE_TEST_kEY')





INSTALLED_APPS = [
    
    'daphne',
    # 'jazzmin',
    'unfold',  # must be before django.contrib.admin
    'unfold.contrib.filters',  # optional, for enhanced filters
    'unfold.contrib.forms',  # optional, for better form styling
    
     
    # default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'user',
    'courses',
    'blog',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework.authtoken',
    'django_rest_passwordreset',
    'payment',
    'student_dashboard',
    'dj_rest_auth',
    'django.contrib.sites',
    'drf_yasg',
    
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

    # brevo anymail
    'anymail',
]

ASGI_APPLICATION = 'amlpro.asgi.application'

# Channel layer configuration (Redis recommended)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                os.getenv("CHANNEL_REDIS_HOST", "redis://localhost:6379")
                #("127.0.0.1", 6379)
                ],  # Update if your Redis is elsewhere
        },
    },
}

# AWS S3 Settings
# Get these from your AWS IAM user credentials or instance profile
AWS_ACCESS_KEY_ID = os.getenv('S3_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('S3_BUCKET') # The S3 bucket name you created
AWS_S3_REGION_NAME = os.getenv('S3_REGION') # e.g., 'us-east-1'
AWS_S3_FILE_OVERWRITE = False # Prevents overwriting files with the same name
# In your storage backend configuration
AWS_S3_MAX_MEMORY_SIZE = 1024 * 1024 * 1024  # 1 GB

# Add these to your AWS S3 Settings section
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_DEFAULT_ACL = None  # or None for private files
AWS_QUERYSTRING_AUTH = False  # For public files
AWS_S3_SIGNATURE_VERSION = 's3v4'


# Optional: If you want to use a custom domain for S3 (e.g., if you map a CNAME to S3 direct)
# AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'

# For media files (user uploads)

DEFAULT_FILE_STORAGE = 'courses.storage_backends.PublicMediaStorage'
MEDIA_URL = f'https://d2907c0nlcl1a.cloudfront.net/'
MEDIA_ROOT = ''  # This should be empty for S3

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
    "https://www.titanscareers.com",
    "https://titanscareers.com",
    "https://lms-react-frontend-sand.vercel.app",
    "http://127.0.0.1:5502",
    "http://localhost:3000",
    "http://127.0.0.1:9000",
    "http://127.0.0.1:8080",
    "http://localhost:5173",
    "http://localhost:5174",
    "https://titans-facilitators.vercel.app",
    "https://compliance.titanscareers.com",
    "https://facilitatorshub.titanscareers.com",
    "https://management.titanscareers.com",
    "https://tools.titanscareers.com",
    'http://localhost',
    'http://127.0.0.1',
    'https://admin.titanscareers.com'
    
]

# settings.py
TIKTOK_PIXEL_ID = 'D39E7O3C77UE7L6G8TU0'  # Replace with your actual Pixel ID

# settings.py
# Bank Transfer Configuration
BARCLAYS_BANK_CONFIG = {
    'BANK_NAME': 'Barclays Bank UK',
    'ACCOUNT_NAME': 'YOUR_COMPANY_NAME',  # e.g., "EDUHUB LTD"
    'ACCOUNT_NUMBER': 'YOUR_ACCOUNT_NUMBER',  # 8-digit account number
    'SORT_CODE': '20-11-43',  # Barclays sort code
    'IBAN': 'GBXXBARC201143XXXXXXXX',  # Your full IBAN
    'SWIFT_BIC': 'BARCGB22',  # Barclays SWIFT code
    'BANK_ADDRESS': '1 Churchill Place, London E14 5HP, UK',
    'PAYMENT_REF_PREFIX': 'EDU',  # Prefix for payment references
    'SUPPORT_EMAIL': 'finance@yourdomain.com',
    'SUPPORT_PHONE': '+44 20 XXXX XXXX'
}


# settings.py
STRIPE_CONFIG = {
    'SECRET_KEY': os.getenv('STRIPE_SECRET_KEY'),
    'WEBHOOK_SECRET': os.getenv('STRIPE_WEBHOOK_SECRET'),
    'BANK_TRANSFER_ENABLED': True,  # Enable Stripe bank transfers
    'BANK_TRANSFER_TYPES': ['gb_bank_transfer'],  # For UK banks
    'BARCLAYS_SORT_CODE': '20-11-43'  # Your Barclays details
}

# For testing webhook signatures
BANK_WEBHOOK_SECRET = 'testsecret'


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
        'user.authentication.JWTAuthentication',
    ],
         'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly', #  desired default permission
    ],
}

# Configure Simple JWT
# Configure Simple JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=200), # Adjust as needed
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),   # Adjust as needed
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False, # Keep track of last login
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY, # Use your project's SECRET_KEY
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id', # This MUST match the PK field name in your CustomUser model
    'USER_ID_CLAIM': 'user_id', # The claim name in the token for the user ID
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=60),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}


SESSION_ENGINE = 'django.contrib.sessions.backends.db'


ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
# ACCOUNT_EMAIL_VERIFICATION = 'mandatory'



LOGIN_REDIRECT_URL = 'https://api.titanscareers.com/'
ACCOUNT_LOGOUT_REDIRECT_URL = 'https://api.titanscareers.com/'

SOCIALACCOUNT_FORMS = {
    'disconnect': 'allauth.socialaccount.forms.DisconnectForm',
    'signup': 'allauth.socialaccount.forms.SignupForm',
}

# Email reset settings

# Brevo (Sendinblue) SMTP Settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp-relay.brevo.com' # Brevo's SMTP host
EMAIL_PORT = 587                    # Brevo's SMTP port (587 for TLS, 465 for SSL)
EMAIL_USE_TLS = True                # Use TLS for encryption
EMAIL_HOST_USER = os.getenv('BREVO_SMTP_LOGIN') # Your Brevo SMTP login (often your Brevo email)
EMAIL_HOST_PASSWORD = os.getenv('BREVO_SMTP_KEY') # Your Brevo SMTP key (the auto-generated password)
# DEFAULT_FROM_EMAIL = 'olomoshuaomozafen@gmail.com' # The email address you want emails to appear from



# brevo email 

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", 'amqp://localhost')
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", 'rpc://')
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'

# Task specific settings
CELERY_TASK_ANNOTATIONS = {
    'send_welcome_otp': {
        'rate_limit': '10/m'  # 10 emails per minute max
    }
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024  # 1 GB
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024  # 1 GB


BREVO_API_KEY = os.getenv('Brevo_API')
DEFAULT_FROM_EMAIL = 'marketing@titanscareers.com' # Required for Django's mail functions
DEFAULT_FROM_NAME = 'Titans Careers' # Default name for emails sent by Django
SERVER_EMAIL = DEFAULT_FROM_EMAIL # Default from-email for Django errors
OTP_TEMPLATE_ID = 4  # Your template ID

# OTP Settings
OTP_EXPIRY_MINUTES = 15
PROJECT_NAME = 'Titans Careers'


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
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_SECRET')
PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'live')

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



# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'




# Unfold Admin Configuration
UNFOLD = {
    "SITE_TITLE": "Course Admin",
    "SITE_HEADER": "Course Management System",
    "SITE_URL": "/",
    
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Navigation",
                "separator": True,
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": "/admin/",
                    },
                ],
            },
            {
                "title": "Courses",
                "separator": True,
                "items": [
                    {
                        "title": "All Courses",
                        "icon": "school",
                        "link": "/admin/courses/course/",
                    },
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": "/admin/courses/category/",
                    },
                    {
                        "title": "Curriculums",
                        "icon": "library_books",
                        "link": "/admin/courses/curriculum/",
                    },
                    {
                        "title": "Modules",
                        "icon": "view_module",
                        "link": "/admin/courses/module/",
                    },
                ],
            },
            {
                "title": "Content",
                "separator": True,
                "items": [
                    {
                        "title": "Videos",
                        "icon": "video_library",
                        "link": "/admin/courses/video/",
                    },
                    {
                        "title": "Course Notes",
                        "icon": "note",
                        "link": "/admin/courses/coursenote/",
                    },
                    {
                        "title": "Course Libraries",
                        "icon": "local_library",
                        "link": "/admin/courses/courselibrary/",
                    },
                    {
                        "title": "Library Videos",
                        "icon": "video_file",
                        "link": "/admin/courses/courselibraryvideo/",
                    },
                ],
            },
            {
                "title": "Assignments",
                "separator": True,
                "items": [
                    {
                        "title": "Assignments",
                        "icon": "assignment",
                        "link": "/admin/courses/make_assignment/",
                    },
                    {
                        "title": "Submissions",
                        "icon": "assignment_turned_in",
                        "link": "/admin/courses/submission/",
                    },
                ],
            },
            {
                "title": "Live Sessions",
                "separator": True,
                "items": [
                    {
                        "title": "Live Classes",
                        "icon": "live_tv",
                        "link": "/admin/courses/liveclass/",
                    },
                ],
            },
            {
                "title": "Course Components",
                "separator": True,
                "items": [
                    {
                        "title": "Course Includes",
                        "icon": "checklist",
                        "link": "/admin/courses/course_include/",
                    },
                    {
                        "title": "Required Materials",
                        "icon": "construction",
                        "link": "/admin/courses/requiredmaterial/",
                    },
                    {
                        "title": "Learning Outcomes",
                        "icon": "outcome",
                        "link": "/admin/courses/learningoutcome/",
                    },
                    {
                        "title": "Target Audience",
                        "icon": "people",
                        "link": "/admin/courses/targetaudience/",
                    },
                ],
            },
            {
                "title": "Users",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": "/admin/user/customuser/",
                    },
                    {
                        "title": "Teachers",
                        "icon": "person_outline",
                        "link": "/admin/user/teacherprofile/",
                    },
                ],
            },
            # {
            #     "title": "Orders",
            #     "separator": True,
            #     "items": [
            #         {
            #             "title": "Course Orders",
            #             "icon": "shopping_cart",
            #             "link": "/admin/courses/courseorder/",
            #         },
            #         {
            #             "title": "Order Items",
            #             "icon": "list_alt",
            #             "link": "/admin/courses/courseorderitem/",
            #         },
            #     ],
            # },
        ],
    },
    
    "COLORS": {
        "primary": {
            "50": "250 245 255",
            "100": "243 232 255",
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "192 132 252",
            "500": "168 85 247",
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
            "950": "59 7 100",
        },
    },
}

# For your MongoDB integration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "course_management")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose', # Use verbose to get more info
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO', # Default level
    },
    'loggers': {
        'user.backends': { # Your custom backend
            'handlers': ['console'],
            'level': 'DEBUG', # VERY IMPORTANT: See all debug messages here
            'propagate': False,
        },
        'rest_framework': { # General DRF logging
            'handlers': ['console'],
            'level': 'DEBUG', # See DRF authentication/permission debugs
            'propagate': False,
        },
        'django.request': { # See what Django itself is doing with the request
            'handlers': ['console'],
            'level': 'DEBUG', # Important for tracing request lifecycle
            'propagate': False,
        },
        'django.security.DisallowedHost': {
            'handlers': ['console'],
            'propagate': False,
            'level': 'ERROR',
        },
        'paypal_api_client': { # Your specific logger name
            'handlers': ['console'],
            'level': 'CRITICAL', # Set this to CRITICAL to see your debug messages
                                 # or DEBUG if you want all debug messages from this logger
            'propagate': False, # Prevent messages from being passed to root logger
        },
        'rankyak_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'rankyak_webhooks.log'),
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose'
        },
    }
}



# https://titanscareers.s3.eu-north-1.amazonaws.com/course_images/choong-deng-xiang--WXQm_NTK0U-unsplash.jpg
# https://titanscareers.s3.eu-north-1.amazonaws.com/course_images/choong-deng-xiang--WXQm_NTK0U-unsplash_q17xrgU.jpg



# settings.py
RANKYAK_WEBHOOK_SECRET = os.environ.get('RANKYAK_SECRET', 'your-secret-token-here')
AUTO_PUBLISH = os.environ.get('AUTO_PUBLISH', True)

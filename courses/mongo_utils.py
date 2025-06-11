# courses/mongo_utils.py

from django.conf import settings
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, InvalidURI
import logging

logger = logging.getLogger(__name__)

_mongo_client = None
_mongo_db = None # Cache the database object too

def get_mongo_client():
    global _mongo_client
    if _mongo_client is None:
        mongo_uri = getattr(settings, 'MONGO_URI', None)
        if not mongo_uri:
            logger.error("MONGO_URI is not set in Django settings.")
            return None
        try:
            _mongo_client = MongoClient(mongo_uri)
            # Test connection immediately
            _mongo_client.admin.command('ping')
            logger.info("Successfully connected to MongoDB client.")
        except (ConnectionFailure, InvalidURI) as e:
            logger.error(f"MongoDB client connection failed: {e}")
            _mongo_client = None # Ensure it's explicitly None on failure
        except Exception as e:
            logger.error(f"An unexpected error occurred during MongoDB client connection: {e}")
            _mongo_client = None
    return _mongo_client

def get_mongo_db():
    global _mongo_db
    if _mongo_db is None: # Only connect to DB if not already cached
        client = get_mongo_client()
        if client is None:
            logger.error("MongoDB client is not available, cannot get database.")
            return None # Ensure None is returned if client fails

        database_name = getattr(settings, 'MONGO_DATABASE_NAME', None)
        if not database_name:
            logger.error("MONGO_DATABASE_NAME is not set in Django settings.")
            return None

        try:
            _mongo_db = client[database_name]
            logger.info(f"Successfully connected to MongoDB database: {database_name}")
        except Exception as e:
            logger.error(f"Error getting MongoDB database '{database_name}': {e}")
            _mongo_db = None # Ensure explicit None on failure

    return _mongo_db

# The Command class is a separate management command, not directly related to runtime errors.
# It looks fine as a command.
from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = 'Ensure unique indexes on username and email fields in the users collection'

    def handle(self, *args, **kwargs):
        db = get_mongo_db()
        if db: # Important to check if db is valid before trying to create index
            try:
                db.customusers.create_index("username", unique=True)
                db.customusers.create_index("email", unique=True)
                self.stdout.write(self.style.SUCCESS('Unique indexes created successfully'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating indexes: {e}'))
        else:
            self.stdout.write(self.style.ERROR('Could not get MongoDB connection. Indexes not created.'))
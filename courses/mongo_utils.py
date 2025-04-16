from django.conf import settings
from pymongo import MongoClient
from django.core.management.base import BaseCommand

_mongo_client = None

def get_mongo_client():
    global _mongo_client
    if _mongo_client is None:
        mongo_uri = settings.MONGO_URI
        _mongo_client = MongoClient(mongo_uri)
    return _mongo_client

def get_mongo_db():
    client = get_mongo_client()
    database_name = settings.MONGO_DATABASE_NAME
    return client[database_name]

class Command(BaseCommand):
    help = 'Ensure unique indexes on username and email fields in the users collection'

    def handle(self, *args, **kwargs):
        db = get_mongo_db()
        db.users.create_index("username", unique=True)
        db.users.create_index("email", unique=True)
        self.stdout.write(self.style.SUCCESS('Unique indexes created successfully'))
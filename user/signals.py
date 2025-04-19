from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from pymongo import MongoClient
from .models import *
import os

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DATABASE_NAME = os.getenv('DATABASE_NAME')

        # Connect to MongoDB
client = MongoClient(MONGO_URI, ssl=True, ssl_cert_reqs='CERT_NONE')
db = client[MONGO_DATABASE_NAME]

def export_to_mongo(instance):
    if isinstance(instance, CustomUser):
        collection = db.users
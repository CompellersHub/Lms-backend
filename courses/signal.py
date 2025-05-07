import json
from django.core.management.base import BaseCommand
from pymongo import MongoClient
from courses.models import *
import os
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from bson import ObjectId
from .mongo_utils import get_mongo_db

class Command(BaseCommand):
    help = 'Export data from Django models to MongoDB'

    def handle(self, *args, **kwargs):
        # MongoDB connection settings
        MONGO_URI = os.getenv('MONGO_URI')
        MONGO_DATABASE_NAME = os.getenv('DATABASE_NAME')

        # Connect to MongoDB
        client = MongoClient(MONGO_URI, ssl=True, ssl_cert_reqs='CERT_NONE')
        db = client[MONGO_DATABASE_NAME]

def model_to_dict(instance):
    # Assuming your model_to_dict already handles serialization correctly
    data = instance.to_dict()
    # Optionally, keep the original Django ID
    data['django_id'] = instance.pk
    return data

# Signal to handle saving and updating models
@receiver(post_save, sender=Category)
@receiver(post_save, sender=Video)
@receiver(post_save, sender=CourseNote)
@receiver(post_save, sender=Module)
@receiver(post_save, sender=RequiredMaterial)
@receiver(post_save, sender=LearningOutcome)
@receiver(post_save, sender=TargetAudience)
@receiver(post_save, sender=Course)
@receiver(post_save, sender=CourseLibrary)
@receiver(post_save, sender=Make_Assignment)
@receiver(post_save, sender=Submission)
@receiver(post_save, sender=CourseOrder)
@receiver(post_save, sender=CourseOrderItem)
@receiver(post_save, sender=LiveClass)
@receiver(post_save, sender=Notification)
def sync_to_mongodb(sender, instance, **kwargs):
    db = get_mongo_db()
    collection_name = sender.__name__.lower() + 's'
    data = model_to_dict(instance)

    # Check if a document with the Django ID exists
    existing_document = db[collection_name].find_one({"django_id": instance.pk})

    if existing_document:
        # Update the existing document
        db[collection_name].update_one({"_id": existing_document['_id']}, {"$set": data})
    else:
        # Insert a new document with a new ObjectId
        db[collection_name].insert_one(data)

# Signal to handle deleting models
@receiver(post_delete, sender=Category)
@receiver(post_delete, sender=Video)
@receiver(post_delete, sender=CourseNote)
@receiver(post_delete, sender=Module)
@receiver(post_delete, sender=RequiredMaterial)
@receiver(post_delete, sender=LearningOutcome)
@receiver(post_delete, sender=TargetAudience)
@receiver(post_delete, sender=Course)
@receiver(post_delete, sender=CourseLibrary)
@receiver(post_delete, sender=Make_Assignment)
@receiver(post_delete, sender=Submission)
@receiver(post_delete, sender=CourseOrder)
@receiver(post_delete, sender=CourseOrderItem)
@receiver(post_delete, sender=LiveClass)
@receiver(post_delete, sender=Notification)
def delete_from_mongodb(sender, instance, **kwargs):
    db = get_mongo_db()
    collection_name = sender.__name__.lower() + 's'
    # Delete based on the Django ID
    db[collection_name].delete_one({"django_id": instance.pk})
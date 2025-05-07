from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from pymongo import MongoClient
from .models import *
import os
from bson import ObjectId
from courses.mongo_utils import get_mongo_db

def model_to_dict(instance):
    return instance.to_dict()

# Signal to handle saving and updating models
@receiver(post_save, sender=Category)
@receiver(post_save, sender=Blog)
@receiver(post_save, sender=BlogUser)
def sync_to_mongodb(sender, instance, **kwargs):
    db = get_mongo_db()
    collection_name = sender.__name__.lower() + 's'
    data = model_to_dict(instance)
    # Convert primary key to string
    data['_id'] = str(instance.pk)
    db[collection_name].update_one({"_id": data['_id']}, {"$set": data}, upsert=True)

# Signal to handle deleting models
@receiver(post_delete, sender=Category)
@receiver(post_delete, sender=Blog)
@receiver(post_delete, sender=BlogUser)
def delete_from_mongodb(sender, instance, **kwargs):
    db = get_mongo_db()
    collection_name = sender.__name__.lower() + 's'
    # Convert primary key to string
    db[collection_name].delete_one({"_id": str(instance.pk)})
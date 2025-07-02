from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from pymongo import MongoClient
from .models import *
import os
from bson import ObjectId
from courses.mongo_utils import get_mongo_db
import logging

def model_to_dict(instance):
    return instance.to_dict()

# Signal to handle saving and updating models

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Blog)
def blog_pre_save(sender, instance, **kwargs):
    """Handle pre-save operations"""
    try:
        # Generate slug if not provided
        if not instance.slug:
            instance.slug = instance.generate_slug()
            
        # Set published_at if publishing
        if instance.status == 'published' and not instance.published_at:
            instance.published_at = timezone.now()
            
        # Convert legacy content to blocks if empty
        if not instance.content_blocks and instance.description:
            instance.convert_description_to_blocks()
            
    except Exception as e:
        logger.error(f"Pre-save error for Blog {instance.id}: {str(e)}")
        raise

@receiver(post_save, sender=Blog)
def blog_post_save(sender, instance, created, **kwargs):
    """Sync with MongoDB after save"""
    try:
        db = get_mongo_db()
        if not db:
            logger.error("MongoDB connection not available")
            return
            
        blog_data = instance.to_mongo_dict()
        
        if created:
            # Insert new document
            result = db.blogs.insert_one(blog_data)
            if not result.inserted_id:
                logger.error("Failed to insert blog into MongoDB")
        else:
            # Update existing document
            result = db.blogs.update_one(
                {"_id": instance.mongo_id},
                {"$set": blog_data},
                upsert=True
            )
            if result.matched_count == 0 and not result.upserted_id:
                logger.warning("No documents matched during update")
                
    except Exception as e:
        logger.error(f"MongoDB sync failed for Blog {instance.id}: {str(e)}")

@receiver(post_save, sender=Category)

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
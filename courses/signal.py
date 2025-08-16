import json
from django.core.management.base import BaseCommand
from pymongo import MongoClient
from courses.models import *
import os
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from bson import ObjectId
from .mongo_utils import get_mongo_db
import logging


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
    return instance.to_dict()

# Signal to handle saving and updating models
@receiver(post_save, sender=Category)
@receiver(post_save, sender=Video)
@receiver(post_save, sender=CourseNote)
@receiver(post_save, sender=Module)
@receiver(post_save, sender=Curriculum)
@receiver(post_save, sender=RequiredMaterial)
@receiver(post_save, sender=LearningOutcome)
@receiver(post_save, sender=TargetAudience)
@receiver(post_save, sender=Course)
@receiver(post_save, sender=CourseLibrary)
@receiver(post_save, sender=CourseLibraryVideo)
@receiver(post_save, sender=Make_Assignment)
@receiver(post_save, sender=Course_include)
@receiver(post_save, sender=Event)
# @receiver(post_save, sender=CourseOrder)
# @receiver(post_save, sender=CourseOrderItem)
@receiver(post_save, sender=LiveClass)
def sync_to_mongodb(sender, instance, **kwargs):
    db = get_mongo_db()
    collection_name = sender.__name__.lower() + 's'
    data = model_to_dict(instance)  # Call the top-level function

    # Ensure django_id is always set in the data being saved
    if hasattr(instance, 'pk'):
        data['django_id'] = instance.pk
    else:
        data['django_id'] = None # Or some other default value

    
    if sender == Make_Assignment and hasattr(instance, 'course') and instance.course and hasattr(instance.course, 'pk'):
        # Query MongoDB to get the _id of the related Course document
        courses_collection = db['courses']
        related_course_doc = courses_collection.find_one({'django_id': instance.course.pk})
        if related_course_doc and '_id' in related_course_doc:
            data['course'] = related_course_doc['_id']
        if 'course_id' in data:
            del data['course_id']

    if sender == CourseLibrary and hasattr(instance, 'course') and instance.course and hasattr(instance.course, 'pk'):
        # Query MongoDB to get the _id of the related Course document
        courses_collection = db['courses']
        related_course_doc = courses_collection.find_one({'django_id': instance.course.pk})
        if related_course_doc and '_id' in related_course_doc:
            data['course'] = related_course_doc['_id']
        if 'course_id' in data:
            del data['course_id']

       

    if sender == LiveClass and hasattr(instance, 'course') and instance.course and hasattr(instance.course, 'pk'):
        # Query MongoDB to get the _id of the related Course document
        courses_collection = db['courses']
        related_course_doc = courses_collection.find_one({'django_id': instance.course.pk})
        if related_course_doc and '_id' in related_course_doc:
            data['course'] = related_course_doc['_id']
        if 'course_id' in data:
            del data['course_id']

    existing_document = db[collection_name].find_one({"django_id": data.get('django_id')})

    if existing_document:
        # Update the existing document, ensuring django_id is present
        db[collection_name].update_one({"_id": existing_document['_id']}, {"$set": data})
    else:
        # Insert a new document with django_id
        db[collection_name].insert_one(data)

# Signal to handle deleting models
@receiver(post_delete, sender=Category)
@receiver(post_delete, sender=Video)
@receiver(post_delete, sender=CourseNote)
@receiver(post_delete, sender=Module)
@receiver(post_delete, sender=Curriculum)
@receiver(post_delete, sender=RequiredMaterial)
@receiver(post_delete, sender=LearningOutcome)
@receiver(post_delete, sender=TargetAudience)
@receiver(post_delete, sender=Course)
@receiver(post_delete, sender=CourseLibrary)
@receiver(post_delete, sender=CourseLibraryVideo)
@receiver(post_delete, sender=Make_Assignment)
@receiver(post_delete, sender=Course_include)
@receiver(post_delete, sender=Event)
# @receiver(post_delete, sender=CourseOrder)
# @receiver(post_delete, sender=CourseOrderItem)
@receiver(post_delete, sender=LiveClass)
def delete_from_mongodb(sender, instance, **kwargs):
    db = get_mongo_db()
    collection_name = sender.__name__.lower() + 's'
    # Delete based on the Django ID
    db[collection_name].delete_one({"django_id": instance.pk})

logger = logging.getLogger(__name__)

@receiver(post_save, sender=CourseEnrollment)
def course_enrollment_post_save(sender, instance, created, **kwargs):
    db = get_mongo_db()
    if created:
        user_id = str(instance.user_id.id)
        course_id = str(instance.course_id.id)

        user = db['users'].find_one({'_id': ObjectId(user_id)})
        course = db['courses'].find_one({'_id': ObjectId(course_id)})

        if user and course:
            db['users'].update_one(
                {'_id': ObjectId(user_id)},
                {'$push': {'enrolled_courses': {'course_id': ObjectId(course_id), 'enrollment_date': instance.enrollment_date}}}
            )
            logger.info(f"User {user.get('email', 'unknown')} enrolled in course {course.get('name', 'unknown')}")
        else:
            logger.warning(f"User or Course not found in MongoDB for enrollment. Django User ID: {user_id}, Django Course ID: {course_id}")
    else:
        logger.info(f"Course enrollment updated for user {instance.user_id.email} and course {instance.course_id.name}")
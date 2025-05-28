from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group
from .models import *
from allauth.socialaccount.models import SocialAccount
from unfold.admin import ModelAdmin
import os
from pymongo import MongoClient
from bson.objectid import ObjectId


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

class MongoConnection:
    client = None
    db = None

    @classmethod
    def get_db(cls):
        if cls.db is None:
            MONGO_URI = os.getenv('MONGO_URI')
            MONGO_DATABASE_NAME = os.getenv('DATABASE_NAME')
            if MONGO_URI and MONGO_DATABASE_NAME:
                cls.client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
                cls.db = cls.client[MONGO_DATABASE_NAME]
            else:
                raise Exception("MONGO_URI or DATABASE_NAME environment variables not set.")
        return cls.db

def get_mongo_id(model_name, obj):
    db = MongoConnection.get_db()
    if db is not None :
        collection_name = model_name.lower() + 's'
        doc = db[collection_name].find_one({'django_id': obj.pk})
        return str(doc['_id']) if doc and '_id' in doc else 'N/A'
    return 'MongoDB not connected'



@admin.register(CustomUser)
class UserAdmin(ModelAdmin):
    list_display = ['username', 'email', 'role', 'is_staff', 'mongo_id']
    list_filter = ['role']
    readonly_fields = ['mongo_id']

    def mongo_id(self, obj):
        return get_mongo_id('CustomUser', obj)
    mongo_id.short_description = 'MongoDB ID'

    def has_social_accounts(self, obj):
        return SocialAccount.objects.filter(user=obj).exists()

    has_social_accounts.boolean = True
    has_social_accounts.short_description = 'Linked Social Accounts'

@admin.register(TeacherProfile)
class TeacherAdmin(ModelAdmin):
    list_display = ['username', 'email', 'profile_picture', 'mongo_id']
    readonly_fields = ['mongo_id']

    def mongo_id(self, obj):
        return get_mongo_id('TeacherProfile', obj)
    mongo_id.short_description = 'MongoDB ID'


@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):
    list_display = ['student', 'assignment', 'submission_date', 'marks_obtained', 'mongo_id']
    search_fields = ['student__email', 'assignment__title']
    readonly_fields = ['mongo_id']
    list_filter = ['student']

    def mongo_id(self, obj):
        return get_mongo_id('Submission', obj)
    mongo_id.short_description = 'MongoDB ID'

@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ['student', 'message', 'created_at', 'mongo_id']
    search_fields = ['student__email', 'message']
    list_filter = ['student']
    readonly_fields = ['mongo_id']

    def mongo_id(self, obj):
        return get_mongo_id('Notification', obj)
    mongo_id.short_description = 'MongoDB ID'
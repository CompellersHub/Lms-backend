from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import *
from pymongo import MongoClient
import os
from bson.objectid import ObjectId

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


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'mongo_id']
    search_fields = ['name']
    readonly_fields = ['mongo_id']
    def mongo_id(self, obj): return get_mongo_id('Categories', obj)
    mongo_id.short_description = 'MongoDB ID'

@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = ['name', 'level', 'price', 'instructor', 'estimated_time', 'mongo_id']
    search_fields = ['name', 'category__name', 'instructor__email']
    readonly_fields = ['mongo_id']

    def mongo_id(self, obj): return get_mongo_id('Course', obj)
    mongo_id.short_description = 'MongoDB ID'

@admin.register(CourseNote)
class CourseNoteAdmin(ModelAdmin):
    list_display = ['title', 'note_file', 'mongo_id']
    search_fields = ['title', 'note_file']
    readonly_fields = ['mongo_id']
    def mongo_id(self, obj): return get_mongo_id('CourseNote', obj)
    mongo_id.short_description = 'MongoDB ID'


@admin.register(Curriculum)
class CurriculumAdmin(ModelAdmin):
    list_display = ['title', 'mongo_id']
    search_fields = ['title']
    readonly_fields = ['mongo_id']
    def mongo_id(self, obj): return get_mongo_id('Curriculum', obj)
    mongo_id.short_description = 'MongoDB ID'

@admin.register(Course_include)
class Course_include(ModelAdmin):
    list_display = ['include', 'mongo_id']
    search_fields = ['include']
    readonly_fields = ['mongo_id']
    def mongo_id(self, obj): return get_mongo_id('Course_include', obj)
    mongo_id.short_description = 'MongoDB ID'

@admin.register(Make_Assignment)
class AssignmentAdmin(ModelAdmin):
    list_display = ['title', 'course', 'teacher', 'due_date', 'mongo_id']
    search_fields = ['title', 'course__name', 'teacher__email']
    list_filter = ['course', 'teacher']
    readonly_fields = ['mongo_id']
    def mongo_id(self, obj): return get_mongo_id('Make_Assignment', obj)
    mongo_id.short_description = 'MongoDB ID'


@admin.register(Module)
class ModuleAdmin(ModelAdmin):
    list_display = ['title', 'mongo_id']
    search_fields = ['title']
    readonly_fields = ['mongo_id']
    def mongo_id(self, obj): return get_mongo_id('Module', obj)
    mongo_id.short_description = 'MongoDB ID'

@admin.register(CourseLibrary)
class CourseLibraryAdmin(ModelAdmin):
    list_display = ['title', 'mongo_id']
    search_fields = ['title']
    readonly_fields = ['mongo_id']
    def mongo_id(self, obj): return get_mongo_id('CourseLibrary', obj)
    mongo_id.short_description = 'MongoDB ID'

@admin.register(CourseLibraryVideo)
class CourseLibraryVideoAdmin(ModelAdmin):
    list_display = ['title', 'video_id', 'mongo_id']
    search_fields = ['title']
    readonly_fields = ['mongo_id']
    def mongo_id(self, obj): return get_mongo_id('CourseLibraryVideo', obj)
    mongo_id.short_description = 'MongoDB ID'


@admin.register(Video)
class VideoAdmin(ModelAdmin):
    list_display = ['title' ,'duration', 'mongo_id']
    search_fields = ['title', 'created_by__email']
    readonly_fields = ['mongo_id']
    def mongo_id(self, obj): return get_mongo_id('Video', obj)
    mongo_id.short_description = 'MongoDB ID'

@admin.register(LiveClass)
class LiveClassAdmin(ModelAdmin):
    list_display = ['title', 'course', 'start_time', 'end_time', 'mongo_id']
    search_fields = ['title', 'course__name']
    list_filter = ['course']
    readonly_fields = ['mongo_id']
    def mongo_id(self, obj): return get_mongo_id('LiveClass', obj)
    mongo_id.short_description = 'MongoDB ID'

# ... (rest of your admin.py - CourseOrder and CourseOrderItem remain unchanged as you didn't ask for them)

@admin.register(Event)
class EventAdmin(ModelAdmin):
    list_display = ['title', 'timezone', 'instructor']
# user/management/commands/export_data.py

import json
from django.core.management.base import BaseCommand
from pymongo import MongoClient
from user.models import CustomUser, TeacherProfile 
import os # Use absolute import

class Command(BaseCommand):
    help = 'Export data from Django models to MongoDB'

    def handle(self, *args, **kwargs):
        # MongoDB connection settings
        MONGO_URI = os.getenv('MONGO_URI')
        MONGO_DATABASE_NAME = os.getenv('DATABASE_NAME')

        # Connect to MongoDB
        client = MongoClient(MONGO_URI, ssl=True, ssl_cert_reqs='CERT_NONE')
        db = client[MONGO_DATABASE_NAME]

        # Export users
        users = CustomUser.objects.all()
        users_data = [user.to_dict() for user in users]
        if users_data:
            db.users.insert_many(users_data)
            self.stdout.write(self.style.SUCCESS('Users data exported successfully'))
        else:
            self.stdout.write(self.style.WARNING('No users data to export'))

        # Export teachers
        teachers = TeacherProfile.objects.all()
        teachers_data = [teacher.to_dict() for teacher in teachers]
        if teachers_data:
            db.teacher_profiles.insert_many(teachers_data)
            self.stdout.write(self.style.SUCCESS('Teachers data exported successfully'))
        else:
            self.stdout.write(self.style.WARNING('No teachers data to export'))

        # Export courses
        

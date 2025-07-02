# user/management/commands/export_data.py

import json
from django.core.management.base import BaseCommand
from pymongo import MongoClient
from blog.models import Category, Blog, BlogUser
import os # Use absolute import

class Command(BaseCommand):
    help = 'Export data from Django models to MongoDB'

    def handle(self, *args, **kwargs):
        # MongoDB connection settings
        MONGO_URI = os.getenv('MONGO_URI')
        MONGO_DATABASE_NAME = os.getenv('DATABASE_NAME')

        # Connect to MongoDB
        client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
        db = client[MONGO_DATABASE_NAME]

        # Export categories
        # categories = Category.objects.all()
        # categories_data = [category.to_dict() for category in categories]
        # if categories_data:
        #     db.categories.insert_many(categories_data)
        #     self.stdout.write(self.style.SUCCESS('categories data exported successfully'))
        # else:
        #     self.stdout.write(self.style.WARNING('No users data to export'))

        # Export blogs
        blogs = Blog.objects.all()
        blogs_data = [blog.to_dict() for blog in blogs]
        if blogs_data:
            db.blogs.insert_many(blogs_data)
            self.stdout.write(self.style.SUCCESS('blogs data exported successfully'))
        else:
            self.stdout.write(self.style.WARNING('No teachers data to export'))

        # Export courses
        # bloguser = BlogUser.objects.all()
        # bloguser_data = [bloguser.to_dict() for bloguser in bloguser]
        # if bloguser_data:
        #     db.bloguser.insert_many(bloguser_data)
        #     self.stdout.write(self.style.SUCCESS('bloguser data exported successfully'))
        # else:
        #     self.stdout.write(self.style.WARNING('No students data to export'))

# user/management/commands/export_data.py

import json
from django.core.management.base import BaseCommand
from pymongo import MongoClient
from courses.models import Category, Course, Make_Assignment, Submission, Module, Video, CourseOrder, CourseOrderItem
import os

class Command(BaseCommand):
    help = 'Export data from Django models to MongoDB'

    def handle(self, *args, **kwargs):
        # MongoDB connection settings
        MONGO_URI = os.getenv('MONGO_URI')
        MONGO_DATABASE_NAME = os.getenv('DATABASE_NAME')

        # Connect to MongoDB
        client = MongoClient(MONGO_URI, ssl=True, ssl_cert_reqs='CERT_NONE')
        db = client[MONGO_DATABASE_NAME]

        


        # Export categories
        categories = Category.objects.all()
        categories_data = [category.to_dict() for category in categories]
        if categories_data:
            db.categories.insert_many(categories_data)
            self.stdout.write(self.style.SUCCESS('Categories data exported successfully'))
        else:
            self.stdout.write(self.style.WARNING('No categories data to export'))

        # Export courses
        courses = Course.objects.all()
        courses_data = [course.to_dict() for course in courses]
        if courses_data:
            db.courses.insert_many(courses_data)
            self.stdout.write(self.style.SUCCESS('Courses data exported successfully'))
        else:
            self.stdout.write(self.style.WARNING('No courses data to export'))

        # Export assignments
        assignments = Make_Assignment.objects.all()
        assignments_data = [assignment.to_dict() for assignment in assignments]
        if assignments_data:
            db.assignments.insert_many(assignments_data)
            self.stdout.write(self.style.SUCCESS('Assignments data exported successfully'))
        else:
            self.stdout.write(self.style.WARNING('No assignments data to export'))

        # Export submissions
        submissions = Submission.objects.all()
        submissions_data = [submission.to_dict() for submission in submissions]
        if submissions_data:
            db.submissions.insert_many(submissions_data)
            self.stdout.write(self.style.SUCCESS('Submissions data exported successfully'))
        else:
            self.stdout.write(self.style.WARNING('No submissions data to export'))

        # Export modules
        modules = Module.objects.all()
        modules_data = [module.to_dict() for module in modules]
        if modules_data:
            db.modules.insert_many(modules_data)
            self.stdout.write(self.style.SUCCESS('Modules data exported successfully'))
        else:
            self.stdout.write(self.style.WARNING('No modules data to export'))

        # Export videos
        videos = Video.objects.all()
        videos_data = [video.to_dict() for video in videos]
        if videos_data:
            db.videos.insert_many(videos_data)
            self.stdout.write(self.style.SUCCESS('Videos data exported successfully'))
        else:
            self.stdout.write(self.style.WARNING('No videos data to export'))

        # Export course orders
        course_orders = CourseOrder.objects.all()
        course_orders_data = [order.to_dict() for order in course_orders]
        if course_orders_data:
            db.course_orders.insert_many(course_orders_data)
            self.stdout.write(self.style.SUCCESS('Course orders data exported successfully'))
        else:
            self.stdout.write(self.style.WARNING('No course orders data to export'))

        # Export course order items
        course_order_items = CourseOrderItem.objects.all()
        course_order_items_data = [item.to_dict() for item in course_order_items]
        if course_order_items_data:
            db.course_order_items.insert_many(course_order_items_data)
            self.stdout.write(self.style.SUCCESS('Course order items data exported successfully'))
        else:
            self.stdout.write(self.style.WARNING('No course order items data to export'))

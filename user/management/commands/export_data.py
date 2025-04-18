# user/management/commands/export_data.py

import json
from django.core.management.base import BaseCommand
from user.models import CustomUser, TeacherProfile  # Use absolute import

class Command(BaseCommand):
    help = 'Export data from SQLite to JSON'

    def handle(self, *args, **kwargs):
        users = CustomUser.objects.all()
        teachers = TeacherProfile.objects.all()

        users_data = [user.to_dict() for user in users]
        teachers_data = [teacher.to_dict() for teacher in teachers]

        with open('users.json', 'w') as users_file:
            json.dump(users_data, users_file, indent=4)

        with open('teachers.json', 'w') as teachers_file:
            json.dump(teachers_data, teachers_file, indent=4)

        self.stdout.write(self.style.SUCCESS('Data exported successfully'))

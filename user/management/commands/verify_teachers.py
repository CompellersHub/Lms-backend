# app/management/commands/verify_teachers.py
from django.core.management.base import BaseCommand
from courses.mongo_utils import get_mongo_db


class Command(BaseCommand):
    help = 'Verify all existing teachers in the system'

    def handle(self, *args, **options):
        db = get_mongo_db()
        result = db.teacherprofiles.update_many(
            {},  # Empty filter matches all documents
            {"$set": {"is_verified": True}}
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully verified {result.modified_count} teachers')
        )
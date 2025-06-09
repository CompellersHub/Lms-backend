import csv
import os
import logging
from django.core.management.base import BaseCommand
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Exports registered users from MongoDB to a CSV file for Brevo import.'

    def handle(self, *args, **options):
        output_file = 'brevo_contacts_export.csv'
        # Ensure MONGO_URI is set in your settings.py (ideally from env vars)
        mongo_uri = os.getenv('MONGO_URI')
        mongo_db_name = os.getenv('DATABASE_NAME', 'your_default_db_name')  # Replace with your default DB name

        client = None
        try:
            client = MongoClient(mongo_uri)
            client.admin.command('ismaster') # Verify connection
            db = client[mongo_db_name]
            users_collection = db.customusers

            # Define the fields you want to export. 'email' is mandatory for Brevo.
            # Use standard Brevo attribute names if possible (e.g., FIRSTNAME, LASTNAME)
            # or map them during Brevo import.
            # Here, we'll use lowercase and map later.
            fields_to_export = ['email', 'username', 'first_name', 'last_name']

            self.stdout.write(f"Exporting users to {output_file}...")

            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(fields_to_export) # Write header row

                for user_data in users_collection.find({}, {field: 1 for field in fields_to_export}):
                    row = [user_data.get(field, '') for field in fields_to_export]
                    writer.writerow(row)

            self.stdout.write(self.style.SUCCESS(f"Successfully exported users to {output_file}"))

        except ConnectionFailure as e:
            self.stderr.write(self.style.ERROR(f"Could not connect to MongoDB: {e}"))
            logger.error(f"MongoDB connection failed: {e}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred during export: {e}"))
            logger.error(f"Error during Brevo contacts export: {e}", exc_info=True)
        finally:
            if client:
                client.close()
# Assuming this is in payments/mongo_utils.py or courses/mongo_utils.py
import os
from pymongo import MongoClient

_db = None

def get_mongo_db():
    global _db
    if _db is None:
        MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
        MONGO_DB_NAME = os.environ.get("DATABASE_NAMEE", "your_database_name_for_app") # Use a specific DB name
        
        # For testing, you might want a separate test database
        if os.environ.get("DJANGO_SETTINGS_MODULE") == "your_project.settings_test": # Example of conditional settings
            MONGO_DB_NAME = os.environ.get("DATABASE_NAME", "your_test_database_name")

        client = MongoClient(MONGO_URI)
        _db = client[MONGO_DB_NAME]
    return _db
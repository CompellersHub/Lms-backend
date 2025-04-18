# import_data.py

import json
from pymongo import MongoClient
from datetime import datetime

# MongoDB connection settings
MONGO_URI = "mongodb://titans:TitansCareer@ac-72om8zm-shard-00-00.tu1atbz.mongodb.net:27017,ac-72om8zm-shard-00-01.tu1atbz.mongodb.net:27017,ac-72om8zm-shard-00-02.tu1atbz.mongodb.net:27017/?replicaSet=atlas-iov063-shard-0&ssl=true&authSource=admin"
MONGO_DATABASE_NAME = "titans"

client = MongoClient(MONGO_URI, ssl=True, ssl_cert_reqs='CERT_NONE')
db = client[MONGO_DATABASE_NAME]

# Import users
with open('users.json', 'r') as users_file:
    users_data = json.load(users_file)
    for user in users_data:
        user['created_at'] = datetime.fromisoformat(user['created_at'])
        db.users.insert_one(user)

# Import teachers
with open('teachers.json', 'r') as teachers_file:
    teachers_data = json.load(teachers_file)
    for teacher in teachers_data:
        teacher['created_at'] = datetime.fromisoformat(teacher['created_at'])
        db.teacher_profiles.insert_one(teacher)

print("Data imported successfully")

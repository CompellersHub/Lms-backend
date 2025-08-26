# test_user_query.py
from pymongo import MongoClient
from bson import ObjectId
import os

# Connect to MongoDB
client = MongoClient(os.getenv('MONGO_URI'))
db = client['titans']  # Your database name

# Test course ID (use one from your user's course array)
test_course_id = "68238b8c98930563248cbe09"  # Cybersecurity course ID

# Test the query
enrolled_students = db.customusers.find({
    'course._id': ObjectId(test_course_id)
}, {'_id': 1, 'username': 1, 'email': 1, 'course.$': 1})  # Include matching course

students = list(enrolled_students)
print(f"Found {len(students)} students enrolled in course {test_course_id}")

for student in students:
    print(f"Student: {student.get('username', 'No username')}")
    print(f"Email: {student.get('email', 'No email')}")
    print(f"Student ID: {student['_id']}")
    if 'course' in student and student['course']:
        print(f"Enrolled since: {student['course'][0].get('enrollment_date', 'Unknown date')}")
    print("---")

# services/enrollment.py
from datetime import datetime
from bson import ObjectId
from pymongo.errors import PyMongoError
import logging
from courses.mongo_utils import get_mongo_db
db = get_mongo_db()

logger = logging.getLogger(__name__)

def enroll_student(enrollment_data):
    """
    Creates enrollment record and updates user profile
    Returns MongoDB insert result
    """
    try:
        # 1. Get complete course data
        course = db.courses.find_one(
            {"_id": enrollment_data['course_id']},
            {
                "name": 1,
                "price": 1,
                "instructor": 1,
                "course_image": 1,
                "description": 1,
                "curriculum": 1,
                "category": 1,
                "level": 1
            }
        )

        if not course:
            raise ValueError("Course not found")

        # 2. Prepare curriculum progress
        curriculum_progress = []
        if course.get('curriculum'):
            curriculum_progress = [
                {
                    "module_id": module.get('_id'),
                    "title": module.get('title'),
                    "completed": False,
                    "lessons": [
                        {
                            "lesson_id": lesson.get('_id'),
                            "title": lesson.get('title'),
                            "completed": False
                        }
                        for lesson in module.get('lessons', [])
                    ]
                }
                for module in course['curriculum']
            ]

        # 3. Create enrollment document
        enrollment_doc = {
            "course_id": enrollment_data['course_id'],
            "enrollment_date": datetime.utcnow(),
            "payment_method": enrollment_data['payment_method'],
            "transaction_id": enrollment_data.get('transaction_id'),
            "bank_reference": enrollment_data.get('bank_reference'),
            "amount_paid": float(enrollment_data['amount']),
            "status": "active",
            "progress": {
                "completed_modules": 0,
                "total_modules": len(curriculum_progress),
                "completion_percentage": 0
            },
            "curriculum_progress": curriculum_progress,
            "last_accessed": None,
            "course_data": {  # Snapshot of course at time of enrollment
                "name": course['name'],
                "instructor": course.get('instructor'),
                "image": course.get('course_image'),
                "description": course.get('description'),
                "category": course.get('category'),
                "level": course.get('level')
            }
        }

        # 4. Update user record
        update_result = db.users.update_one(
            {"_id": enrollment_data['user_id']},
            {
                "$push": {"enrollments": enrollment_doc},
                "$inc": {"stats.enrollment_count": 1}
            }
        )

        if update_result.modified_count == 0:
            raise ValueError("User not found or not updated")

        # 5. Create transaction record
        transaction_doc = {
            "user_id": enrollment_data['user_id'],
            "course_id": enrollment_data['course_id'],
            "type": "enrollment",
            "amount": float(enrollment_data['amount']),
            "currency": "GBP",
            "payment_method": enrollment_data['payment_method'],
            "transaction_id": enrollment_data.get('transaction_id'),
            "bank_reference": enrollment_data.get('bank_reference'),
            "status": "completed",
            "timestamp": datetime.utcnow(),
            "metadata": {
                "course_name": course['name'],
                "instructor": course.get('instructor', {}).get('name')
            }
        }

        return db.transactions.insert_one(transaction_doc)

    except PyMongoError as e:
        logger.error(f"Database error during enrollment: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Enrollment failed: {str(e)}")
        raise
# services/validation.py
from bson import ObjectId
from pymongo.errors import PyMongoError
import logging
from courses.mongo_utils import get_mongo_db
db = get_mongo_db()



logger = logging.getLogger(__name__)

def validate_course(course_id):
    """
    Validates course existence and returns course data
    Returns None if invalid
    """
    try:
        if not course_id or not ObjectId.is_valid(course_id):
            logger.warning(f"Invalid course ID format: {course_id}")
            return None

        course = db.courses.find_one(
            {"_id": ObjectId(course_id)},
            {
                "name": 1,
                "price": 1,
                "currency": 1,
                "is_active": 1,
                "enrollment_open": 1,
                "instructor": 1,
                "course_image": 1,
                "description": 1
            }
        )

        if not course:
            logger.warning(f"Course not found: {course_id}")
            return None

        if not course.get('is_active', False) or not course.get('enrollment_open', False):
            logger.warning(f"Course not available for enrollment: {course_id}")
            return None

        return {
            "_id": course["_id"],
            "name": course["name"],
            "price": float(course["price"]),
            "currency": course.get("currency", "GBP"),
            "instructor": course.get("instructor"),
            "course_image": course.get("course_image"),
            "description": course.get("description")
        }

    except PyMongoError as e:
        logger.error(f"Database error during course validation: {str(e)}")
        return None
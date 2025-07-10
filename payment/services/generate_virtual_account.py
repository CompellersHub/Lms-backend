from datetime import datetime
import hashlib
from bson import ObjectId
from pymongo.errors import PyMongoError
import logging
from courses.mongo_utils import get_mongo_db

def generate_virtual_account(user_id, course_id, amount):
    """
    Generates deterministic virtual account details
    Format: INST[2] + USER[5] + COURSE[3] + CHECK[1]
    Example: 99-12345-678-1
    """
    institution_code = "99"  # Your bank-assigned code
    
    # Create stable components
    user_part = hashlib.md5(str(user_id).encode()).hexdigest()[:5]
    course_part = hashlib.md5(str(course_id).encode()).hexdigest()[:3]
    
    # Generate check digit
    base_number = f"{institution_code}{user_part}{course_part}"
    check_digit = str(sum(int(c) for c in base_number if c.isdigit()) % 10)
    
    return {
        "account_number": f"{institution_code}{user_part}{course_part}{check_digit}",
        "reference": f"ENROLL-{user_part}-{course_part}",
        "routing_number": "040004"  # UK sort code format
    }
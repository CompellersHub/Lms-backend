# debug_serializer.py
import os
import sys
import django

# Set up Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'amlpro.settings')

try:
    django.setup()
    print("✓ Django setup successful")
    
    # Import your serializer - replace 'your_app' with your actual app name
    # Common app names: profiles, accounts, users, teachers, etc.
    try:
        from teachers.serializers import TeacherProfileSerializer
        print("✓ Imported from teachers.serializers")
    except ImportError:
        try:
            from profiles.serializers import TeacherProfileSerializer
            print("✓ Imported from profiles.serializers")
        except ImportError:
            try:
                from accounts.serializers import TeacherProfileSerializer
                print("✓ Imported from accounts.serializers")
            except ImportError:
                from users.serializers import TeacherProfileSerializer
                print("✓ Imported from users.serializers")
    
    # Test data matching your MongoDB document
    test_data = {
        "_id": {"$oid": "6836e07b2c88216deb9d9d99"},
        "user_id": 2,
        "first_name": "Lumi",
        "last_name": "Otolorin", 
        "role": "TEACHER",
        "bio": "Lumi Otolorin is a dual-qualified lawyer...",
        "profile_picture": "https://titanscareers.s3.amazonaws.com/Teacher_profile/IMG-20250821-WA0033.jpg",
        "phone_number": "",
        "past_experience": "",
        "course_taken": "AML/KYC Compliance",
        "created_at": "2025-05-28T10:07:44.922433+00:00",
        "django_id": 2,
        "email": "lumiotolorin@gmail.com",
        "username": "Lumi",
        "last_login": {"$date": "2025-09-21T18:12:22.755Z"},
        "is_verified": True
    }
    
    print("\n" + "="*60)
    print("TESTING TEACHER PROFILE SERIALIZER")
    print("="*60)
    
    serializer = TeacherProfileSerializer(instance=test_data)
    result = serializer.data
    
    print("✓ Serialization successful!")
    print(f"Profile picture in result: {result.get('profile_picture')}")
    print(f"ID in result: {result.get('id')}")
    print(f"All fields: {list(result.keys())}")
    print("\nFull result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
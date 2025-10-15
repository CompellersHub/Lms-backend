# test_serializer_fix.py
import os
import sys
import django
import traceback

print("🔧 Starting serializer test...")

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
print(f"📁 Current directory: {current_dir}")

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'amlpro.settings')
    print("✅ Django settings configured")
    
    django.setup()
    print("✅ Django setup completed")
    
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    print("Traceback:")
    traceback.print_exc()
    sys.exit(1)

# Now try to import the serializer
print("\n🔍 Looking for serializer...")
try:
    # Try different possible app locations
    from teachers.serializers import TeacherProfileSerializer
    print("✅ Found TeacherProfileSerializer in teachers app")
except ImportError as e:
    print(f"❌ Not in teachers app: {e}")
    try:
        from profiles.serializers import TeacherProfileSerializer
        print("✅ Found TeacherProfileSerializer in profiles app")
    except ImportError as e:
        print(f"❌ Not in profiles app: {e}")
        try:
            from accounts.serializers import TeacherProfileSerializer
            print("✅ Found TeacherProfileSerializer in accounts app")
        except ImportError as e:
            print(f"❌ Not in accounts app: {e}")
            try:
                from user.serializer import TeacherProfileSerializer
                print("✅ Found TeacherProfileSerializer in user_profiles app")
            except ImportError as e:
                print(f"❌ Not in user_profiles app: {e}")
                print("🤔 Where is your TeacherProfileSerializer located?")
                print("Please check your app structure and update the import.")
                sys.exit(1)

# Test data
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
print("🧪 TESTING SERIALIZER")
print("="*60)

try:
    serializer = TeacherProfileSerializer(instance=test_data)
    result = serializer.data
    
    print("✅ Serialization successful!")
    print(f"📸 Profile picture in result: {result.get('profile_picture')}")
    print(f"🆔 ID in result: {result.get('id')}")
    print(f"📋 All fields: {list(result.keys())}")
    
    print("\n📊 Full result:")
    for key, value in result.items():
        print(f"  {key}: {repr(value)}")
        
except Exception as e:
    print(f"❌ Serialization failed: {e}")
    print("Traceback:")
    traceback.print_exc()
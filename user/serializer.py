from rest_framework import serializers
from rest_framework.validators import ValidationError
from .models import CustomUser
import re

# This will check length and type of characters passed in password
def check_password(password):
    password_pattern = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    match = re.match(password_pattern, string=password)
    return bool(match)

def validate_password(password):
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if check_password(password) == False:
        raise ValidationError("Password must contain at least one uppercase, one lowercase, one digit and one special character")

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name', 'role', 'phone_number', 'created_at'
        ]

        extra_kwargs = {
            'password': {'write_only': True, 'required': True},
            'created_at': {'read_only': True},
            # 'username': {'required': True},
            'phone_number':{'required': True},
        }

        def create(self, validated_data):
            password = validate_password['password']
            if not check_password(password):
                raise ValidationError("Password must contain at least one uppercase, one lowercase, one digit and one special character")
            
            user = CustomUser.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                phone_number = validated_data['phone_number'],
                password=password
            )
            return user

        
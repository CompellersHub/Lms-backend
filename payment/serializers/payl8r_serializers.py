from rest_framework import serializers
from bson import ObjectId
from datetime import datetime

class Payl8rProductSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)

class Payl8rAddressSerializer(serializers.Serializer):
    line_1 = serializers.CharField(max_length=200)
    line_2 = serializers.CharField(max_length=200, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100)
    postcode = serializers.CharField(max_length=10)
    country = serializers.CharField(max_length=2, default='GB')

class Payl8rCustomerSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    date_of_birth = serializers.DateField()
    address = Payl8rAddressSerializer()

class CreatePayl8rApplicationSerializer(serializers.Serializer):
    course_id = serializers.CharField(max_length=24)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    products = Payl8rProductSerializer(many=True)
    customer = Payl8rCustomerSerializer()


from rest_framework import serializers
from bson import ObjectId
from datetime import datetime


class Payl8rApplicationSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True, source='_id')
    payl8r_application_id = serializers.CharField(read_only=True)
    merchant_reference = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Handle MongoDB ObjectId conversion
        if '_id' in instance:
            representation['id'] = str(instance['_id'])
        
        return representation
    

class Payl8rStatusSerializer(serializers.Serializer):
    application_id = serializers.CharField(max_length=100)
    status = serializers.CharField(read_only=True)
    redirect_url = serializers.URLField(read_only=True, required=False)
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert MongoDB ObjectId if present
        if '_id' in instance:
            representation['id'] = str(instance['_id'])
        
        return representation
    
class Payl8rSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    

class Payl8rWebhookSerializer(serializers.Serializer):
    application_id = serializers.CharField(max_length=100)
    status = serializers.CharField(max_length=50)
    merchant_reference = serializers.CharField(max_length=100, required=False)
    
    def validate_status(self, value):
        valid_statuses = ['pending', 'approved', 'declined', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of {valid_statuses}")
        return value
    

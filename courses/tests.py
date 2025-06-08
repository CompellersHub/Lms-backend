import boto3
from django.conf import settings
import os

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

file_path = 'media/videos/VID-20250302-WA0253.mp4'  # Replace with a real path
s3_key = 'videos/'  # Replace with your desired S3 path

try:
    s3_client.upload_file(file_path, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
    print(f"Successfully uploaded to s3://{settings.AWS_STORAGE_BUCKET_NAME}/{s3_key}")
except Exception as e:
    print(f"Error uploading: {e}")


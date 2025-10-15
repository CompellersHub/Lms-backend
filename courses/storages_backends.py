from storages.backends.s3boto3 import S3Boto3Storage

class PublicMediaStorage(S3Boto3Storage):
    location = 'media'
    default_acl = None
    file_overwrite = False

class PrivateMediaStorage(S3Boto3Storage):
    location = 'private'
    default_acl = 'private'
    file_overwrite = False
    custom_domain = False

class UserMediaStorage(S3Boto3Storage):
    location = 'users'  # Files will be in s3://your-bucket/users/
    file_overwrite = False

class DocumentStorage(S3Boto3Storage):
    location = 'documents'  # Files will be in s3://your-bucket/documents/
    file_overwrite = False

class ProfilePicturesStorage(S3Boto3Storage):
    location = 'profile_pictures'  # s3://your-bucket/profile_pictures/
    file_overwrite = False  # Prevent overwriting existing files

class TeacherPicturesStorage(S3Boto3Storage):
    location = 'Teacher_profile'  # s3://your-bucket/profile_pictures/
    file_overwrite = False  # Prevent overwriting existing files


class VideoMediaStorage(S3Boto3Storage):
    location = 'videos'
    file_overwrite = False

class BlogMediaStorage(S3Boto3Storage):
    location = 'blogs'
    file_overwrite = False

    def get_valid_name(self, name):
        """Preserve folder structure when saving files"""
        # If already has folder prefix (from upload endpoint)
        if name.startswith(('main/', 'content/')):
            return name
        return super().get_valid_name(name)

    def generate_filename(self, filename):
        """Ensure unique filenames while preserving folder structure"""
        if filename.startswith(('main/', 'content/')):
            folder, name = filename.split('/', 1)
            name = super().get_valid_name(name)
            return f"{folder}/{name}"
        return super().generate_filename(filename)

class SubmissionStorage(S3Boto3Storage):
    location = 'submissions'
    file_overwrite = False

class AssignmentStorage(S3Boto3Storage):
    location = 'assignments'
    file_overwrite = False

class CourseMediaStorage(S3Boto3Storage):
    location = ''
    file_overwrite = False

class CourseNotesStorage(S3Boto3Storage):
    location = 'course_notes'
    file_overwrite = False

class EventStorage(S3Boto3Storage):
    location = 'events'
    file_overwrite = False

class CourseLibraryStorage(S3Boto3Storage):
    location = 'course_library'
    file_overwrite = False


class ReceiptStorage(S3Boto3Storage):
    location = 'receipts'
    file_overwrite = False
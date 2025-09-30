from django.db import models
from bson import ObjectId
from django.forms import ValidationError

class Hero(models.Model):

    CONTENT_CHOICES = [
        ('icon', 'Icon'),
        ('text', 'Text'),
    ]

    h1 = models.CharField(max_length=200)
    paragraph = models.TextField(max_length=100)
    content_type = models.JSONField(default='text')
    

    def __str__(self):
        return self.h1

    def clean(self):
        """Validate content blocks before saving"""
        super().clean()
        self.validate_content_blocks(self.content_type)

    @staticmethod
    def validate_content_blocks(blocks):
        """Validate the structure of content blocks"""
        if not isinstance(blocks, list):
            raise ValidationError("Content blocks must be a list")
        
        for block in blocks:
            if not isinstance(block, dict):
                raise ValidationError("Each block must be a dictionary")
            
            # Required fields
            if 'type' not in block:
                raise ValidationError("Content block missing 'type' field")
            if 'content' not in block:
                raise ValidationError("Content block missing 'content' field")
            
            # Type validation
            if block['type'] not in dict(Hero.CONTENT_CHOICES).keys():
                raise ValidationError(f"Invalid content type: {block['type']}")

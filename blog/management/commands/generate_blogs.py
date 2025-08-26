# blog/management/commands/generate_blog.py
from django.core.management.base import BaseCommand
from blog.rankyak import RankYakClient
from blog.serializer import BlogSerializer

class Command(BaseCommand):
    help = 'Generate a blog post using RankYak AI'
    
    def add_arguments(self, parser):
        parser.add_argument('--title', type=str, help='Blog title')
        parser.add_argument('--category', type=str, help='Blog category')
        parser.add_argument('--tags', type=str, help='Comma separated tags')
        
    def handle(self, *args, **options):
        client = RankYakClient()
        
        # Generate content using RankYak
        result = client.generate_blog_content(
            title=options['title'],
            category=options['category'],
            tags=options['tags'].split(',')
        )
        
        # Prepare data for serializer
        blog_data = {
            'title': result['title'],
            'slug': result['slug'],
            'category': options['category'],
            'tags': options['tags'].split(','),
            'excerpt': result['excerpt'],
            'content': result['content'],
            'status': 'draft'
        }
        
        # Validate and save using your BlogSerializer
        serializer = BlogSerializer(data=blog_data)
        if serializer.is_valid():
            blog = serializer.save()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created blog: {blog.title}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'Errors: {serializer.errors}')
            )
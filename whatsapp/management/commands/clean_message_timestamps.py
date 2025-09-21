"""
Django management command to clean timestamps from existing WhatsApp messages
"""

import re
from django.core.management.base import BaseCommand
from whatsapp.models import WhatsAppMessage


class Command(BaseCommand):
    help = 'Remove timestamps from existing WhatsApp message content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually updating the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS('🧹 Cleaning timestamps from WhatsApp messages...')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN MODE - No changes will be made')
            )
        
        # Find messages with timestamps
        messages_with_timestamps = []
        all_messages = WhatsAppMessage.objects.all()
        
        for message in all_messages:
            content = message.content
            if re.search(r'\d{1,2}:\d{2}', content):
                messages_with_timestamps.append(message)
        
        self.stdout.write(
            f'📊 Found {len(messages_with_timestamps)} messages with timestamps out of {all_messages.count()} total'
        )
        
        if not messages_with_timestamps:
            self.stdout.write(
                self.style.SUCCESS('✅ No messages with timestamps found - nothing to clean!')
            )
            return
        
        # Process each message
        updated_count = 0
        for message in messages_with_timestamps:
            original_content = message.content
            
            # Remove timestamps from end of lines
            cleaned_content = re.sub(r'\d{1,2}:\d{2}$', '', original_content, flags=re.MULTILINE).strip()
            
            # Remove standalone timestamp lines
            lines = cleaned_content.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line and not re.match(r'^\d{1,2}:\d{2}$', line):
                    cleaned_lines.append(line)
            
            cleaned_content = '\n'.join(cleaned_lines)
            
            if cleaned_content != original_content:
                self.stdout.write(
                    f'📝 Message ID: {message.message_id}'
                )
                self.stdout.write(
                    f'   Before: "{original_content[:100]}..."'
                )
                self.stdout.write(
                    f'   After:  "{cleaned_content[:100]}..."'
                )
                
                if not dry_run:
                    message.content = cleaned_content
                    message.save()
                    updated_count += 1
                
                self.stdout.write('---')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'🔍 DRY RUN: Would update {len(messages_with_timestamps)} messages')
            )
            self.stdout.write(
                self.style.WARNING('Run without --dry-run to actually update the database')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Updated {updated_count} messages successfully!')
            )
            
            # Update content hashes for deduplication
            self.stdout.write('🔄 Updating content hashes...')
            import hashlib
            hash_updated_count = 0
            
            for message in WhatsAppMessage.objects.filter(content_hash=''):
                if message.content:
                    content_hash = hashlib.md5(message.content.encode('utf-8')).hexdigest()
                    message.content_hash = content_hash
                    message.save()
                    hash_updated_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Updated {hash_updated_count} content hashes')
            )

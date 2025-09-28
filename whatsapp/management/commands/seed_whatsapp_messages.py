"""
Django management command to seed WhatsApp messages from JSON test data
"""

import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from whatsapp.models import WhatsAppMessage
from whatsapp.services import classify_message_type
from whatsapp.views import clean_timestamp_from_text


class Command(BaseCommand):
    help = 'Seed WhatsApp messages from JSON test data files - one day at a time'

    def add_arguments(self, parser):
        parser.add_argument(
            '--day',
            type=str,
            help='Specific day to load (e.g., "Tuesday_01_09_2025", "Thursday_03_09_2025"). Use --list-days to see available days.'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Specific JSON file to load (e.g., Tuesday_01_09_2025_messages.json)'
        )
        parser.add_argument(
            '--list-days',
            action='store_true',
            help='List all available days of message data'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing messages before seeding'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )

    def handle(self, *args, **options):
        # Path to test data (relative to this command file)
        test_data_path = os.path.join(os.path.dirname(__file__), 'test_data')
        
        # List available days if requested
        if options['list_days']:
            self.list_available_days(test_data_path)
            return
        
        if options['clear']:
            if options['dry_run']:
                count = WhatsAppMessage.objects.count()
                self.stdout.write(f"Would delete {count} existing messages")
            else:
                count = WhatsAppMessage.objects.count()
                WhatsAppMessage.objects.all().delete()
                self.stdout.write(
                    self.style.WARNING(f'Deleted {count} existing messages')
                )

        # Determine which files to load
        if options['day']:
            # Load specific day
            day_file = f"{options['day']}_messages.json"
            json_files = [day_file]
            self.stdout.write(f"🗓️  Loading messages for day: {options['day']}")
        elif options['file']:
            # Load specific file
            json_files = [options['file']]
        else:
            # Show available days and exit
            self.stdout.write(self.style.ERROR("❌ Please specify a day to load messages for."))
            self.list_available_days(test_data_path)
            return

        total_imported = 0
        total_skipped = 0

        for json_file in json_files:
            file_path = os.path.join(test_data_path, json_file)
            
            if not os.path.exists(file_path):
                self.stdout.write(
                    self.style.ERROR(f'File not found: {file_path}')
                )
                continue

            self.stdout.write(f'\n📄 Processing {json_file}...')
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    messages_data = json.load(f)

                imported_count = 0
                skipped_count = 0

                for msg_data in messages_data:
                    try:
                        # Check if message already exists
                        if WhatsAppMessage.objects.filter(message_id=msg_data['id']).exists():
                            skipped_count += 1
                            continue

                        # Parse timestamp
                        timestamp_str = msg_data.get('timestamp', '')
                        if timestamp_str:
                            try:
                                # Try different timestamp formats
                                formats = [
                                    '%Y-%m-%d %H:%M:%S',     # Standard format
                                    '%Y-%m-%dT%H:%M:%S',     # ISO format
                                    '%Y-%m-%d %H:%M',        # Without seconds
                                    '%H:%M, %d/%m/%Y',       # WhatsApp format: "12:46, 27/08/2025"
                                ]
                                
                                for fmt in formats:
                                    try:
                                        timestamp = datetime.strptime(timestamp_str, fmt)
                                        timestamp = timezone.make_aware(timestamp)
                                        break
                                    except ValueError:
                                        continue
                                else:
                                    # If no format worked, use current time
                                    timestamp = timezone.now()
                            except:
                                timestamp = timezone.now()
                        else:
                            timestamp = timezone.now()

                        # Clean content from timestamps before processing
                        raw_content = msg_data.get('text', msg_data.get('content', ''))
                        cleaned_content = clean_timestamp_from_text(raw_content)
                        
                        # Classify message type - map JSON fields to expected format
                        classification_data = {
                            'id': msg_data['id'],
                            'content': cleaned_content,
                            'sender': msg_data.get('sender', 'Unknown')
                        }
                        message_type = classify_message_type(classification_data)

                        if options['dry_run']:
                            self.stdout.write(
                                f"  Would import: {msg_data['id']} - {msg_data.get('sender', 'Unknown')} - {message_type}"
                            )
                            imported_count += 1
                            continue

                        # Create message
                        message = WhatsAppMessage.objects.create(
                            message_id=msg_data['id'],
                            chat_name=msg_data.get('chat_name', 'ORDERS Restaurants'),
                            sender_name=msg_data.get('sender', 'Unknown'),
                            sender_phone=msg_data.get('sender_phone', ''),
                            content=cleaned_content,  # Use cleaned content without timestamps
                            cleaned_content=cleaned_content,  # Also set cleaned_content field
                            timestamp=timestamp,
                            message_type=message_type,
                            media_url=msg_data.get('media_url', ''),
                            media_type=msg_data.get('media_type', ''),
                            media_info=msg_data.get('media_info', ''),
                            is_deleted=False,
                            processed=False,
                            edited=False
                        )

                        imported_count += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  Error importing message {msg_data.get("id", "unknown")}: {e}')
                        )

                total_imported += imported_count
                total_skipped += skipped_count

                self.stdout.write(
                    f'  ✅ {imported_count} imported, {skipped_count} skipped from {json_file}'
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {json_file}: {e}')
                )

        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(f'\n🔍 DRY RUN: Would import {total_imported} messages, skip {total_skipped}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Successfully imported {total_imported} messages, skipped {total_skipped} duplicates')
            )

        # Show summary
        if not options['dry_run']:
            total_messages = WhatsAppMessage.objects.count()
            order_messages = WhatsAppMessage.objects.filter(message_type='order').count()
            stock_messages = WhatsAppMessage.objects.filter(message_type='stock').count()
            
            self.stdout.write(f'\n📊 Database Summary:')
            self.stdout.write(f'  Total messages: {total_messages}')
            self.stdout.write(f'  Order messages: {order_messages}')
            self.stdout.write(f'  Stock messages: {stock_messages}')
            self.stdout.write(f'  Other messages: {total_messages - order_messages - stock_messages}')

    def list_available_days(self, test_data_path):
        """List all available days of message data"""
        self.stdout.write(f'\n📅 Available days of message data:')
        
        if not os.path.exists(test_data_path):
            self.stdout.write(self.style.ERROR(f'Test data directory not found: {test_data_path}'))
            return
            
        json_files = [f for f in os.listdir(test_data_path) if f.endswith('_messages.json')]
        
        if not json_files:
            self.stdout.write(self.style.ERROR('No message files found in test data directory'))
            return
            
        days = []
        for json_file in sorted(json_files):
            # Extract day from filename (remove '_messages.json')
            day = json_file.replace('_messages.json', '')
            days.append(day)
            
            # Show file info
            file_path = os.path.join(test_data_path, json_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    messages_data = json.load(f)
                    message_count = len(messages_data)
                    self.stdout.write(f'  📄 {day} ({message_count} messages)')
            except Exception as e:
                self.stdout.write(f'  📄 {day} (error reading file: {e})')
        
        self.stdout.write(f'\n💡 Usage examples:')
        self.stdout.write(f'  python manage.py seed_whatsapp_messages --day Tuesday_01_09_2025')
        self.stdout.write(f'  python manage.py seed_whatsapp_messages --day Thursday_03_09_2025 --dry-run')
        self.stdout.write(f'  python manage.py seed_whatsapp_messages --day Tuesday_08_09_2025 --clear')
        self.stdout.write(f'\n🔄 Recommended workflow:')
        self.stdout.write(f'  1. Start with: --day Tuesday_01_09_2025 --clear --dry-run')
        self.stdout.write(f'  2. If looks good: --day Tuesday_01_09_2025 --clear')
        self.stdout.write(f'  3. Test your system with day 1 data')
        self.stdout.write(f'  4. Add next day: --day Thursday_03_09_2025')
        self.stdout.write(f'  5. Continue day by day...')

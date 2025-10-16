"""
Django management command to seed WhatsApp messages for October 15, 2025
"""

import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from whatsapp.models import WhatsAppMessage
from whatsapp.services import classify_message_type
from whatsapp.views import clean_timestamp_from_text


class Command(BaseCommand):
    help = 'Seed WhatsApp messages for October 15, 2025 (Tuesday)'

    def add_arguments(self, parser):
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
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('🗓️  Seeding messages for Tuesday, October 15, 2025'))
        
        if options['clear']:
            if dry_run:
                count = WhatsAppMessage.objects.count()
                self.stdout.write(f"Would delete {count} existing messages")
            else:
                count = WhatsAppMessage.objects.count()
                WhatsAppMessage.objects.all().delete()
                self.stdout.write(
                    self.style.WARNING(f'Deleted {count} existing messages')
                )

        # Path to test data
        test_data_path = os.path.join(os.path.dirname(__file__), 'test_data')
        json_file = 'Tuesday_15_10_2025_messages.json'
        file_path = os.path.join(test_data_path, json_file)
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'File not found: {file_path}')
            )
            return

        self.stdout.write(f'📄 Processing {json_file}...')
        
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

                    # Parse timestamp - handle WhatsApp format: "08:00, 10/15/2025"
                    timestamp_str = msg_data.get('timestamp', '')
                    if timestamp_str:
                        try:
                            # Parse WhatsApp format: "08:00, 10/15/2025"
                            if ', ' in timestamp_str:
                                time_part, date_part = timestamp_str.split(', ')
                                # Convert to standard format
                                datetime_str = f"{date_part} {time_part}"
                                timestamp = datetime.strptime(datetime_str, "%m/%d/%Y %H:%M")
                                timestamp = timezone.make_aware(timestamp)
                            else:
                                timestamp = timezone.now()
                        except Exception as e:
                            self.stdout.write(f"  Warning: Failed to parse timestamp '{timestamp_str}': {e}")
                            timestamp = timezone.now()
                    else:
                        timestamp = timezone.now()

                    # Clean content from timestamps
                    raw_content = msg_data.get('content', '')
                    cleaned_content = clean_timestamp_from_text(raw_content)
                    
                    # Classify message type
                    classification_data = {
                        'id': msg_data['id'],
                        'content': cleaned_content,
                        'sender': msg_data.get('sender', 'Unknown')
                    }
                    message_type = classify_message_type(classification_data)

                    if dry_run:
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
                        content=cleaned_content,
                        cleaned_content=cleaned_content,
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

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'🔍 DRY RUN: Would import {imported_count} messages, skip {skipped_count}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully imported {imported_count} messages, skipped {skipped_count} duplicates')
                )

            # Show summary
            if not dry_run:
                total_messages = WhatsAppMessage.objects.count()
                order_messages = WhatsAppMessage.objects.filter(message_type='order').count()
                stock_messages = WhatsAppMessage.objects.filter(message_type='stock').count()
                
                self.stdout.write(f'\n📊 Database Summary:')
                self.stdout.write(f'  Total messages: {total_messages}')
                self.stdout.write(f'  Order messages: {order_messages}')
                self.stdout.write(f'  Stock messages: {stock_messages}')
                self.stdout.write(f'  Other messages: {total_messages - order_messages - stock_messages}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing {json_file}: {e}')
            )

        self.stdout.write(self.style.SUCCESS('\n✅ October 15, 2025 seeding completed!'))

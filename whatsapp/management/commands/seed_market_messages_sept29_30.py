import json
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from whatsapp.models import WhatsAppMessage
from whatsapp.views import clean_timestamp_from_text
from whatsapp.services import classify_message_type
from datetime import datetime
import re
from bs4 import BeautifulSoup


class Command(BaseCommand):
    help = 'Seed WhatsApp messages for September 29-30, 2025 (heavy order period)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing messages for these dates before seeding',
        )

    def handle(self, *args, **options):
        clear_existing = options['clear']
        
        self.stdout.write(self.style.SUCCESS('🌱 Seeding WhatsApp messages for Sept 29-30, 2025 (Heavy Order Period)'))
        
        # Load the comprehensive messages data
        data_file = os.path.join(
            os.path.dirname(__file__), 
            'test_data', 
            'comprehensive_messages_20251011.json'
        )
        
        if not os.path.exists(data_file):
            self.stdout.write(self.style.ERROR(f'❌ Data file not found: {data_file}'))
            return
            
        with open(data_file, 'r', encoding='utf-8') as f:
            messages_data = json.load(f)
        
        # Filter messages for Sept 29-30, 2025
        target_dates = ['9/29/2025', '9/30/2025']
        filtered_messages = []
        
        for msg in messages_data:
            timestamp_str = msg.get('timestamp', '')
            if any(date in timestamp_str for date in target_dates):
                filtered_messages.append(msg)
        
        self.stdout.write(f'📊 Found {len(filtered_messages)} messages for target dates')
        
        if clear_existing:
            # Clear existing messages for these dates
            self.stdout.write('🧹 Clearing existing messages for Sept 29-30, 2025...')
            # Convert to proper date range for deletion
            existing_count = WhatsAppMessage.objects.filter(
                timestamp__date__in=[
                    datetime(2025, 9, 29).date(),
                    datetime(2025, 9, 30).date()
                ]
            ).count()
            
            WhatsAppMessage.objects.filter(
                timestamp__date__in=[
                    datetime(2025, 9, 29).date(),
                    datetime(2025, 9, 30).date()
                ]
            ).delete()
            
            self.stdout.write(f'🗑️  Cleared {existing_count} existing messages')
        
        created_count = 0
        skipped_count = 0
        
        for message_data in filtered_messages:
            try:
                # Extract basic data
                message_id = message_data.get('id', '')
                content = message_data.get('text', '').strip()
                timestamp_str = message_data.get('timestamp', '')
                html_content = message_data.get('html', '')
                
                if not content or not timestamp_str:
                    self.stdout.write(f'⚠️  Skipping message with missing content or timestamp')
                    skipped_count += 1
                    continue
                
                # Extract sender info from HTML if available
                sender_name, sender_phone = self.extract_sender_from_html(html_content)
                
                if not sender_name:
                    sender_name = 'Unknown'
                
                # Parse timestamp
                parsed_timestamp = self.parse_timestamp(timestamp_str)
                if not parsed_timestamp:
                    self.stdout.write(f'⚠️  Skipping message with invalid timestamp: {timestamp_str}')
                    skipped_count += 1
                    continue
                
                # Clean content and classify message type
                cleaned_content = clean_timestamp_from_text(content)
                classification_data = {
                    'content': cleaned_content,
                    'sender': sender_name
                }
                message_type = classify_message_type(classification_data)
                
                # Create or get the message
                message_obj, created = WhatsAppMessage.objects.get_or_create(
                    message_id=message_id,
                    defaults={
                        'sender_name': sender_name,
                        'sender_phone': sender_phone or '',
                        'content': cleaned_content,
                        'cleaned_content': cleaned_content,
                        'timestamp': parsed_timestamp,
                        'message_type': message_type
                    }
                )
                
                if created:
                    created_count += 1
                    # Log message type for verification
                    if message_type == 'stock':
                        self.stdout.write(f'  📦 STOCK: {sender_name}')
                    elif message_type == 'order':
                        self.stdout.write(f'  🍽️  ORDER: {sender_name}')
                else:
                    skipped_count += 1
                    
            except Exception as e:
                self.stdout.write(f'❌ Error processing message: {str(e)}')
                skipped_count += 1
                continue
        
        # Show summary
        self.stdout.write(f'\n🎉 Seeding completed!')
        self.stdout.write(f'   • Created: {created_count} messages')
        self.stdout.write(f'   • Skipped: {skipped_count} messages')
        
        # Show context
        self.stdout.write(f'\n📈 Market Context for Sept 29-30, 2025:')
        self.stdout.write(f'   • Heavy Order Period: Restaurant orders throughout Sept 29')
        self.stdout.write(f'   • Stock Update: Hazvinei\'s comprehensive stock report on Sept 30')
        self.stdout.write(f'   • Order Volume: 25+ order messages on Sept 29 alone')
        self.stdout.write(f'   • Peak Times: 08:00-16:00 on Sept 29')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Command completed!'))
    
    def extract_sender_from_html(self, html_content):
        """Extract sender name and phone from HTML content"""
        if not html_content:
            return None, None
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for sender name in specific elements
            sender_element = soup.find('span', {'aria-label': True})
            if sender_element and 'Maybe' in sender_element.get('aria-label', ''):
                sender_name = sender_element.get('aria-label', '').replace('Maybe ', '')
            else:
                sender_name = None
            
            # Look for phone number
            phone_element = soup.find('span', class_='_ahx_')
            sender_phone = phone_element.get_text(strip=True) if phone_element else None
            
            return sender_name, sender_phone
            
        except Exception:
            return None, None
    
    def parse_timestamp(self, timestamp_str):
        """Parse timestamp string into Django timezone-aware datetime"""
        try:
            # Format: "HH:MM, M/D/YYYY"
            clean_timestamp = timestamp_str.strip()
            
            # Parse the timestamp
            dt = datetime.strptime(clean_timestamp, '%H:%M, %m/%d/%Y')
            
            # Make it timezone-aware
            return timezone.make_aware(dt)
            
        except ValueError:
            try:
                # Try alternative format
                dt = datetime.strptime(clean_timestamp, '%H:%M, %m/%d/%Y')
                return timezone.make_aware(dt)
            except ValueError:
                return None

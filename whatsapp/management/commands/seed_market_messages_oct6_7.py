#!/usr/bin/env python3
"""
Django management command to seed WhatsApp messages for Oct 6-7, 2025
This correlates with Tshwane Market invoice: R16,602.00 (902.7kg)

Usage:
    python manage.py seed_market_messages_oct6_7 [--clear] [--dry-run]
"""

import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from whatsapp.models import WhatsAppMessage
from whatsapp.services import classify_message_type
from whatsapp.views import clean_timestamp_from_text


class Command(BaseCommand):
    help = 'Seed WhatsApp messages for Oct 6-8, 2025 (Market Invoice Day + day after)'

    def extract_sender_from_html(self, html_content):
        """Extract sender name/phone from HTML content"""
        if not html_content:
            return 'Unknown', ''
        
        # Try to extract from data-pre-plain-text attribute
        # Format: [13:22, 9/30/2025] +27 61 674 9368: 
        import re
        pre_text_pattern = r'data-pre-plain-text="[^"]+'
        pre_text_match = re.search(pre_text_pattern, html_content)
        if pre_text_match:
            pre_text = pre_text_match.group(0)
            # Extract sender info: [timestamp] sender: 
            sender_pattern = r'\] ([^:]+):'
            sender_match = re.search(sender_pattern, pre_text)
            if sender_match:
                sender_info = sender_match.group(1).strip()
                
                # Check if it's a phone number
                phone_pattern = r'\+27\s?\d{2}\s?\d{3}\s?\d{4}'
                if re.match(phone_pattern, sender_info):
                    return sender_info, sender_info
                else:
                    return sender_info, ''
        
        # Try to extract sender name from HTML structure
        # Look for sender name in span elements
        name_patterns = [
            r'aria-label="Maybe ([^"]+)"',
            r'<span[^>]*>([A-Za-z]+)</span>.*role="button">\+27',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, html_content)
            if match:
                sender_name = match.group(1).strip()
                if sender_name and len(sender_name) > 1:
                    return sender_name, ''
        
        return 'Unknown', ''


    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing messages for these dates before seeding',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        clear_existing = options['clear']
        
        self.stdout.write(f"{'🔍 DRY RUN: ' if dry_run else ''}Seeding WhatsApp messages for Oct 6-8, 2025 (Heavy Order Period)")
        
        # Target dates for filtering
        target_dates = ['2025-10-06', '2025-10-07', '2025-10-08']
        
        # Load messages from comprehensive file
        messages_to_seed = []
        
        file_path = os.path.join('whatsapp', 'management', 'commands', 'test_data', 'comprehensive_messages_20251011.json')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Filter for Oct 6-7, 2025 messages
                oct_messages = [
                    msg for msg in data 
                    if any(date_pattern in msg.get('timestamp', '') for date_pattern in ['10/6/2025', '10/7/2025', '10/8/2025'])
                ]
                messages_to_seed.extend(oct_messages)
                self.stdout.write(f"📁 Loaded {len(oct_messages)} Oct 6-8 messages from comprehensive file")
        
        if not messages_to_seed:
            self.stdout.write(self.style.WARNING('No messages found to seed'))
            return
        
        self.stdout.write(f"📊 Total messages to process: {len(messages_to_seed)}")
        
        # Clear existing messages for these dates if requested
        if clear_existing and not dry_run:
            deleted_count = 0
            for target_date in target_dates:
                count = WhatsAppMessage.objects.filter(
                    timestamp__date=datetime.strptime(target_date, '%Y-%m-%d').date()
                ).delete()[0]
                deleted_count += count
            self.stdout.write(f"🗑️  Cleared {deleted_count} existing messages for Oct 6-7, 2025")
        
        # Show key messages that will be seeded
        self.stdout.write("\n📝 Key messages to seed:")
        
        # Group messages by type/restaurant
        restaurant_orders = {}
        stock_updates = []
        other_messages = []
        
        for msg in messages_to_seed:
            content = msg.get('content') or msg.get('text', '')
            sender = msg.get('sender', 'Unknown')
            
            # Categorize messages
            if 'casa bella' in content.lower():
                if 'Casa Bella' not in restaurant_orders:
                    restaurant_orders['Casa Bella'] = []
                restaurant_orders['Casa Bella'].append(msg)
            elif 'maltos' in content.lower():
                if 'Maltos' not in restaurant_orders:
                    restaurant_orders['Maltos'] = []
                restaurant_orders['Maltos'].append(msg)
            elif 'valley' in content.lower():
                if 'Valley' not in restaurant_orders:
                    restaurant_orders['Valley'] = []
                restaurant_orders['Valley'].append(msg)
            elif 'barchef' in content.lower():
                if 'Barchef' not in restaurant_orders:
                    restaurant_orders['Barchef'] = []
                restaurant_orders['Barchef'].append(msg)
            elif any(keyword in content.lower() for keyword in ['asparagus', 'harvest', 'maturity', 'reject']):
                stock_updates.append(msg)
            else:
                other_messages.append(msg)
        
        # Display categorized messages
        for restaurant, orders in restaurant_orders.items():
            self.stdout.write(f"  🍽️  {restaurant}: {len(orders)} messages")
            if orders:
                sample_content = (orders[0].get('content') or orders[0].get('text', ''))[:80]
                self.stdout.write(f"     Sample: {sample_content}...")
        
        if stock_updates:
            self.stdout.write(f"  📦 Stock/Quality Updates: {len(stock_updates)} messages")
            sample_content = (stock_updates[0].get('content') or stock_updates[0].get('text', ''))[:80]
            self.stdout.write(f"     Sample: {sample_content}...")
        
        if other_messages:
            self.stdout.write(f"  📝 Other Messages: {len(other_messages)} messages")
        
        if not dry_run:
            with transaction.atomic():
                created_count = 0
                skipped_count = 0
                
                for msg in messages_to_seed:
                    try:
                        # Parse timestamp
                        timestamp_str = msg.get('timestamp', '')
                        if not timestamp_str:
                            skipped_count += 1
                            continue
                        
                        # Parse timestamp using existing formats
                        formats = [
                            '%Y-%m-%d %H:%M:%S',     # Standard format
                            '%Y-%m-%dT%H:%M:%S',     # ISO format
                            '%Y-%m-%d %H:%M',        # Without seconds
                            '%H:%M, %m/%d/%Y',       # WhatsApp format: "08:20, 10/6/2025"
                        ]
                        
                        for fmt in formats:
                            try:
                                naive_dt = datetime.strptime(timestamp_str, fmt)
                                timestamp = timezone.make_aware(naive_dt)
                                break
                            except ValueError:
                                continue
                        else:
                            # If no format worked, use current time
                            timestamp = timezone.now()
                        
                        # Clean content using existing service
                        raw_content = msg.get('text', msg.get('content', ''))
                        cleaned_content = clean_timestamp_from_text(raw_content)
                        
                        # Extract sender information (handle different JSON formats)
                        sender_name = msg.get('sender', '')
                        sender_phone = msg.get('sender_phone', '')
                        
                        # If sender not available in JSON, try to extract from HTML
                        if not sender_name or sender_name == 'Unknown':
                            html_content = msg.get('html', '')
                            if html_content:
                                extracted_name, extracted_phone = self.extract_sender_from_html(html_content)
                                if extracted_name != 'Unknown':
                                    sender_name = extracted_name
                                if extracted_phone:
                                    sender_phone = extracted_phone
                        
                        # Fallback to Unknown if still no sender
                        if not sender_name:
                            sender_name = 'Unknown'
                        
                        # Classify message type using existing service
                        classification_data = {
                            'id': msg.get('id', f"seed_oct_{created_count}_{timestamp.strftime('%Y%m%d_%H%M%S')}"),
                            'content': cleaned_content,
                            'sender': sender_name
                        }
                        message_type = classify_message_type(classification_data)
                        
                        # Create WhatsAppMessage using proper field structure
                        message, created = WhatsAppMessage.objects.get_or_create(
                            message_id=msg.get('id', f"seed_oct_{created_count}_{timestamp.strftime('%Y%m%d_%H%M%S')}"),
                            defaults={
                                'sender_name': sender_name,
                                'sender_phone': sender_phone,
                                'content': cleaned_content,
                                'cleaned_content': cleaned_content,
                                'timestamp': timestamp,
                                'chat_name': msg.get('chat_name', 'ORDERS Restaurants'),
                                'message_type': message_type,
                                'media_url': msg.get('media_url', '') or None,
                                'media_type': msg.get('media_type', ''),
                                'media_info': msg.get('media_info', ''),
                                'is_deleted': False,
                                'processed': False,
                                'edited': False,
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            skipped_count += 1
                            
                    except Exception as e:
                        self.stdout.write(f"⚠️  Error processing message: {e}")
                        skipped_count += 1
                        continue
                
                self.stdout.write(self.style.SUCCESS(f'\n🎉 Seeding completed!'))
                self.stdout.write(f"   • Created: {created_count} messages")
                if skipped_count > 0:
                    self.stdout.write(f"   • Skipped: {skipped_count} messages")
        else:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN COMPLETE - No changes made'))
            self.stdout.write(f"   • Would create: {len(messages_to_seed)} messages")
        
        # Show context about these dates
        self.stdout.write(f"\n📈 Market Context for Oct 6-8, 2025:")
        self.stdout.write(f"   • Oct 6: Restaurant orders (Casa Bella, Maltos, Valley, Barchef)")
        self.stdout.write(f"   • Oct 7: Market trip day + Tshwane Market Invoice")
        self.stdout.write(f"   • Invoice Amount: R16,602.00")
        self.stdout.write(f"   • Total Weight Purchased: 902.7kg")
        self.stdout.write(f"   • Key Activities: Order collection → Market purchase → Quality control")
        self.stdout.write(f"   • Notable: Asparagus quality issues discussion")
        
        # Show supplier correlation
        self.stdout.write(f"\n🏪 Supplier Invoice Correlation:")
        self.stdout.write(f"   • Tshwane Market: R16,602 (Oct 7)")
        self.stdout.write(f"   • Products: 43 different items from fruits to vegetables")
        self.stdout.write(f"   • Price Range: R1.27/kg (Cabbage) to R176.47/kg (Spaghetti Baby)")
        
        self.stdout.write(f"\n✅ Command completed!")

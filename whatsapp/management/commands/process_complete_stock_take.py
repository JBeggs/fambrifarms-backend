from django.core.management.base import BaseCommand
from whatsapp.models import WhatsAppMessage, StockUpdate
from whatsapp.services import parse_stock_message, apply_stock_updates_to_inventory
from django.db import transaction
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Process a complete stock take from SHALLOME messages with proper reset'

    def add_arguments(self, parser):
        parser.add_argument(
            '--message-id',
            type=str,
            help='Specific message ID to process as complete stock take',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Process stock messages from specific date (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--latest',
            action='store_true',
            help='Process the latest stock message as complete stock take',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        message_id = options.get('message_id')
        date_str = options.get('date')
        latest = options.get('latest')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Find the stock message(s) to process
        messages = None
        
        if message_id:
            messages = WhatsAppMessage.objects.filter(
                message_id=message_id,
                message_type='stock'
            )
            self.stdout.write(f'Processing specific message: {message_id}')
            
        elif date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                messages = WhatsAppMessage.objects.filter(
                    timestamp__date=target_date,
                    message_type='stock'
                ).order_by('-timestamp')
                self.stdout.write(f'Processing stock messages from: {target_date}')
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD'))
                return
                
        elif latest:
            messages = WhatsAppMessage.objects.filter(
                message_type='stock'
            ).order_by('-timestamp')[:1]
            self.stdout.write('Processing latest stock message')
            
        else:
            # Default: process recent unprocessed stock messages
            messages = WhatsAppMessage.objects.filter(
                message_type='stock',
                processed=False,
                timestamp__gte=datetime.now() - timedelta(days=7)
            ).order_by('-timestamp')
            self.stdout.write('Processing recent unprocessed stock messages')
        
        if not messages.exists():
            self.stdout.write(self.style.WARNING('No stock messages found matching criteria'))
            return
        
        self.stdout.write(f'Found {messages.count()} stock message(s) to process')
        
        # Process each message and combine into complete stock take
        all_stock_items = {}
        parsing_summary = {
            'total_messages': 0,
            'successful_parses': 0,
            'total_items': 0,
            'parsing_failures': []
        }
        
        for message in messages:
            self.stdout.write(f'\\nProcessing message: {message.message_id}')
            self.stdout.write(f'Timestamp: {message.timestamp}')
            self.stdout.write(f'Sender: {message.sender_name}')
            
            # Parse the message
            parsed_data = parse_stock_message(message)
            parsing_summary['total_messages'] += 1
            
            if parsed_data:
                parsing_summary['successful_parses'] += 1
                parsing_summary['total_items'] += len(parsed_data['items'])
                
                self.stdout.write(f'  ✅ Parsed {len(parsed_data["items"])} items')
                self.stdout.write(f'  📊 Success rate: {parsed_data["parsing_success_rate"]}%')
                
                # Add items to combined stock take
                for name, data in parsed_data['items'].items():
                    if name in all_stock_items:
                        self.stdout.write(f'  ⚠️  Duplicate item: {name} (keeping latest)')
                    all_stock_items[name] = data
                
                # Track parsing failures
                if parsed_data['parsing_failures']:
                    parsing_summary['parsing_failures'].extend(parsed_data['parsing_failures'])
                    self.stdout.write(f'  ❌ {len(parsed_data["parsing_failures"])} parsing failures')
            else:
                self.stdout.write(f'  ❌ Failed to parse message')
        
        if not all_stock_items:
            self.stdout.write(self.style.ERROR('No stock items found in any message'))
            return
        
        self.stdout.write(f'\\n=== COMPLETE STOCK TAKE SUMMARY ===')
        self.stdout.write(f'Messages processed: {parsing_summary["total_messages"]}')
        self.stdout.write(f'Successfully parsed: {parsing_summary["successful_parses"]}')
        self.stdout.write(f'Total unique items: {len(all_stock_items)}')
        self.stdout.write(f'Total parsing failures: {len(parsing_summary["parsing_failures"])}')
        
        if parsing_summary['parsing_failures']:
            self.stdout.write(f'\\n=== PARSING FAILURES ===')
            for failure in parsing_summary['parsing_failures'][:10]:
                self.stdout.write(f'❌ "{failure["original_line"]}" - {failure["failure_reason"]}')
            if len(parsing_summary['parsing_failures']) > 10:
                self.stdout.write(f'... and {len(parsing_summary["parsing_failures"]) - 10} more')
        
        if not dry_run:
            # Create a single comprehensive stock update
            with transaction.atomic():
                # Use the latest message's date and details
                latest_message = messages.first()
                
                stock_update, created = StockUpdate.objects.get_or_create(
                    message=latest_message,
                    defaults={
                        'stock_date': latest_message.timestamp.date(),
                        'order_day': 'Monday' if latest_message.timestamp.weekday() <= 0 else 'Thursday',
                        'items': all_stock_items,
                        'processed': False
                    }
                )
                
                if created:
                    self.stdout.write(f'✅ Created comprehensive stock update (ID: {stock_update.id})')
                else:
                    # Update existing with combined data
                    stock_update.items = all_stock_items
                    stock_update.processed = False
                    stock_update.save()
                    self.stdout.write(f'✅ Updated existing stock update (ID: {stock_update.id})')
                
                # Mark messages as processed
                for message in messages:
                    message.processed = True
                    message.save()
                
                # Now apply the complete stock take with reset
                self.stdout.write(f'\\n=== APPLYING COMPLETE STOCK TAKE ===')
                self.stdout.write('⚠️  This will RESET all stock to 0 first, then apply new levels')
                
                result = apply_stock_updates_to_inventory(reset_before_processing=True)
                
                self.stdout.write(f'\\n=== PROCESSING RESULTS ===')
                self.stdout.write(f'Applied Updates: {result["applied_updates"]}')
                self.stdout.write(f'Products Updated: {result["products_updated"]}')
                self.stdout.write(f'Success Rate: {result["success_rate"]}%')
                self.stdout.write(f'Total Items: {result["total_items_processed"]}')
                self.stdout.write(f'Successful: {result["successful_items"]}')
                self.stdout.write(f'Failed: {result["failed_items_count"]}')
                
                if result['failed_items']:
                    self.stdout.write(f'\\n=== FAILED ITEMS ===')
                    for item in result['failed_items']:
                        self.stdout.write(f'❌ {item["original_name"]}: {item["failure_reason"]}')
                
                if result['processing_warnings']:
                    self.stdout.write(f'\\n=== WARNINGS ===')
                    for warning in result['processing_warnings']:
                        self.stdout.write(f'⚠️  {warning}')
                
                self.stdout.write(f'\\n🎉 Complete stock take processed successfully!')
                
        else:
            self.stdout.write(f'\\n=== DRY RUN SUMMARY ===')
            self.stdout.write(f'Would create stock update with {len(all_stock_items)} items')
            self.stdout.write(f'Would reset all existing stock to 0')
            self.stdout.write(f'Would apply new stock levels from complete stock take')
            self.stdout.write(f'\\nSample items that would be processed:')
            for name, data in list(all_stock_items.items())[:10]:
                self.stdout.write(f'  {name}: {data["quantity"]} {data["unit"]}')
            if len(all_stock_items) > 10:
                self.stdout.write(f'  ... and {len(all_stock_items) - 10} more')

"""
Django management command to run WhatsApp message background processing
Preserves valuable business logic while maintaining performance
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
import time
import logging

from whatsapp.processors.background_processor import get_background_processor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process WhatsApp messages with preserved business logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of messages to process in each batch (default: 50)'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously, processing messages every interval'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=300,  # 5 minutes
            help='Interval in seconds between processing runs (default: 300)'
        )
        parser.add_argument(
            '--max-runs',
            type=int,
            default=0,
            help='Maximum number of processing runs (0 = unlimited, default: 0)'
        )
        parser.add_argument(
            '--message-ids',
            nargs='+',
            type=int,
            help='Process specific message IDs only'
        )
        parser.add_argument(
            '--stats-only',
            action='store_true',
            help='Show processing statistics only, do not process messages'
        )

    def handle(self, *args, **options):
        processor = get_background_processor()
        
        # Show stats only
        if options['stats_only']:
            self.show_processing_stats(processor)
            return
        
        # Process specific messages
        if options['message_ids']:
            self.process_specific_messages(processor, options['message_ids'])
            return
        
        # Single run or continuous processing
        if options['continuous']:
            self.run_continuous_processing(processor, options)
        else:
            self.run_single_processing(processor, options['batch_size'])

    def run_single_processing(self, processor, batch_size):
        """Run a single batch of message processing"""
        self.stdout.write(
            self.style.SUCCESS(f'🚀 Starting WhatsApp message processing (batch_size={batch_size})')
        )
        
        start_time = timezone.now()
        
        try:
            stats = processor.process_unprocessed_messages(batch_size=batch_size)
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Processing complete in {duration:.2f}s')
            )
            self.display_stats(stats)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Processing failed: {e}')
            )
            raise CommandError(f'Processing failed: {e}')

    def run_continuous_processing(self, processor, options):
        """Run continuous message processing"""
        batch_size = options['batch_size']
        interval = options['interval']
        max_runs = options['max_runs']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🔄 Starting continuous WhatsApp processing '
                f'(batch_size={batch_size}, interval={interval}s, max_runs={max_runs or "unlimited"})'
            )
        )
        
        run_count = 0
        
        try:
            while True:
                run_count += 1
                
                self.stdout.write(f'\n📋 Processing run #{run_count} at {timezone.now()}')
                
                start_time = timezone.now()
                stats = processor.process_unprocessed_messages(batch_size=batch_size)
                end_time = timezone.now()
                
                duration = (end_time - start_time).total_seconds()
                
                if stats['processed'] > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Run #{run_count} complete in {duration:.2f}s')
                    )
                    self.display_stats(stats)
                else:
                    self.stdout.write(f'📭 No messages to process (duration: {duration:.2f}s)')
                
                # Check if we've reached max runs
                if max_runs > 0 and run_count >= max_runs:
                    self.stdout.write(
                        self.style.SUCCESS(f'🏁 Reached maximum runs ({max_runs}), stopping')
                    )
                    break
                
                # Wait for next interval
                self.stdout.write(f'⏳ Waiting {interval}s until next run...')
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING(f'\n🛑 Interrupted after {run_count} runs')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Continuous processing failed: {e}')
            )
            raise CommandError(f'Continuous processing failed: {e}')

    def process_specific_messages(self, processor, message_ids):
        """Process specific messages by ID"""
        self.stdout.write(
            self.style.SUCCESS(f'🎯 Processing specific messages: {message_ids}')
        )
        
        try:
            stats = processor.process_specific_messages(message_ids)
            
            self.stdout.write(
                self.style.SUCCESS('✅ Specific message processing complete')
            )
            self.display_stats(stats)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Specific message processing failed: {e}')
            )
            raise CommandError(f'Specific message processing failed: {e}')

    def show_processing_stats(self, processor):
        """Show processing statistics"""
        self.stdout.write(
            self.style.SUCCESS('📊 WhatsApp Message Processing Statistics')
        )
        
        try:
            stats = processor.get_processing_stats()
            
            self.stdout.write('\n🔢 Overall Statistics:')
            self.stdout.write(f'  Total Messages: {stats["total_messages"]}')
            self.stdout.write(f'  Processed Messages: {stats["processed_messages"]}')
            self.stdout.write(f'  Processing Rate: {stats["processing_rate"]:.1f}%')
            self.stdout.write(f'  Messages with Companies: {stats["messages_with_companies"]}')
            self.stdout.write(f'  Company Extraction Rate: {stats["company_extraction_rate"]:.1f}%')
            
            self.stdout.write('\n📋 Message Classification:')
            for msg_type, count in stats["classification_counts"].items():
                self.stdout.write(f'  {msg_type.title()}: {count}')
            
            # Component stats
            from whatsapp.processors.company_extractor import get_company_extractor
            from whatsapp.processors.order_item_parser import get_order_item_parser
            from whatsapp.processors.message_classifier import get_message_classifier
            
            company_stats = get_company_extractor().get_extraction_stats()
            item_stats = get_order_item_parser().get_parsing_stats()
            classifier_stats = get_message_classifier().get_classification_stats()
            
            self.stdout.write('\n🏢 Company Extractor:')
            self.stdout.write(f'  Total Aliases: {company_stats["total_aliases"]}')
            self.stdout.write(f'  Unique Companies: {company_stats["unique_companies"]}')
            self.stdout.write(f'  Restaurant Customers: {company_stats["restaurant_customers"]}')
            
            self.stdout.write('\n📦 Order Item Parser:')
            self.stdout.write(f'  Quantity Patterns: {item_stats["quantity_patterns"]}')
            self.stdout.write(f'  Product Keywords: {item_stats["product_keywords"]}')
            
            self.stdout.write('\n🎯 Message Classifier:')
            for msg_type, type_stats in classifier_stats.items():
                self.stdout.write(f'  {msg_type.title()}: {type_stats["keywords"]} keywords, {type_stats["patterns"]} patterns')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to get statistics: {e}')
            )

    def display_stats(self, stats):
        """Display processing statistics"""
        self.stdout.write('\n📊 Processing Results:')
        self.stdout.write(f'  📝 Processed: {stats["processed"]} messages')
        self.stdout.write(f'  ✨ Enhanced: {stats["enhanced"]} messages')
        
        if 'companies_extracted' in stats:
            self.stdout.write(f'  🏢 Companies Extracted: {stats["companies_extracted"]}')
        if 'items_parsed' in stats:
            self.stdout.write(f'  📦 Items Parsed: {stats["items_parsed"]}')
        if 'reclassified' in stats:
            self.stdout.write(f'  🎯 Reclassified: {stats["reclassified"]}')
        if 'orders_created' in stats:
            self.stdout.write(f'  📋 Orders Created: {stats["orders_created"]}')
        if 'errors' in stats and stats['errors'] > 0:
            self.stdout.write(f'  ❌ Errors: {stats["errors"]}')
        
        if stats['processed'] > 0:
            enhancement_rate = (stats['enhanced'] / stats['processed']) * 100
            self.stdout.write(f'  📈 Enhancement Rate: {enhancement_rate:.1f}%')


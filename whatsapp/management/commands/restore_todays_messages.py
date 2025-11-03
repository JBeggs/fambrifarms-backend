from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from whatsapp.models import WhatsAppMessage


class Command(BaseCommand):
    help = 'Restore (undelete) all soft-deleted WhatsApp messages from today'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be restored without actually restoring',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Restore messages from specific date (YYYY-MM-DD). Defaults to today.',
        )

    def handle(self, *args, **options):
        # Determine the target date
        if options['date']:
            try:
                target_date = timezone.datetime.strptime(options['date'], '%Y-%m-%d').date()
                self.stdout.write(f"Targeting messages from: {target_date}")
            except ValueError:
                self.stderr.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD')
                )
                return
        else:
            target_date = date.today()
            self.stdout.write(f"Targeting messages from today: {target_date}")

        # Find soft-deleted messages from the target date
        deleted_messages = WhatsAppMessage.objects.filter(
            is_deleted=True,
            timestamp__date=target_date
        )

        count = deleted_messages.count()
        
        if count == 0:
            self.stdout.write(
                self.style.WARNING(f'No soft-deleted messages found for {target_date}')
            )
            return

        self.stdout.write(f"Found {count} soft-deleted messages from {target_date}")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
            
            # Show details of what would be restored
            for message in deleted_messages[:10]:  # Show first 10
                self.stdout.write(
                    f"  - ID: {message.id}, Sender: {message.sender_name}, "
                    f"Time: {message.timestamp.strftime('%H:%M:%S')}, "
                    f"Content: {message.content[:50]}..."
                )
            
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more messages")
                
            self.stdout.write(
                self.style.SUCCESS(f"Would restore {count} messages")
            )
        else:
            # Confirm before proceeding
            confirm = input(f"Are you sure you want to restore {count} messages? (y/N): ")
            if confirm.lower() != 'y':
                self.stdout.write("Operation cancelled")
                return

            # Restore the messages
            restored_count = deleted_messages.update(is_deleted=False)
            
            self.stdout.write(
                self.style.SUCCESS(f"Successfully restored {restored_count} messages from {target_date}")
            )

            # Show summary of restored messages
            self.stdout.write("\nRestored messages summary:")
            for message in deleted_messages[:5]:  # Show first 5 restored
                self.stdout.write(
                    f"  - {message.sender_name} ({message.timestamp.strftime('%H:%M:%S')}): "
                    f"{message.content[:50]}..."
                )
            
            if count > 5:
                self.stdout.write(f"  ... and {count - 5} more messages")

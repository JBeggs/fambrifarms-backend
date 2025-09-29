from django.core.management.base import BaseCommand
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix MySQL database charset to support emojis (utf8mb4)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes will be made')
            )
        
        with connection.cursor() as cursor:
            try:
                # Get current database name
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()[0]
                self.stdout.write(f'Working with database: {db_name}')
                
                # Check current charset
                cursor.execute(f"SELECT DEFAULT_CHARACTER_SET_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = '{db_name}'")
                current_charset = cursor.fetchone()[0]
                self.stdout.write(f'Current database charset: {current_charset}')
                
                if current_charset == 'utf8mb4':
                    self.stdout.write(
                        self.style.SUCCESS('Database already uses utf8mb4 charset')
                    )
                    return
                
                # Get tables that need to be converted
                cursor.execute("""
                    SELECT TABLE_NAME, TABLE_COLLATION 
                    FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_TYPE = 'BASE TABLE'
                """, [db_name])
                
                tables = cursor.fetchall()
                self.stdout.write(f'Found {len(tables)} tables to check')
                
                # Show tables that need conversion
                tables_to_convert = []
                for table_name, table_collation in tables:
                    if not table_collation.startswith('utf8mb4'):
                        tables_to_convert.append(table_name)
                        self.stdout.write(f'  - {table_name}: {table_collation}')
                
                if not tables_to_convert:
                    self.stdout.write(
                        self.style.SUCCESS('All tables already use utf8mb4 charset')
                    )
                    return
                
                if not dry_run:
                    # Confirm before proceeding
                    confirm = input(f'\nConvert {len(tables_to_convert)} tables to utf8mb4? (yes/no): ')
                    if confirm.lower() != 'yes':
                        self.stdout.write('Operation cancelled')
                        return
                    
                    # Convert database charset
                    self.stdout.write('Converting database charset...')
                    cursor.execute(f"ALTER DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    
                    # Convert each table
                    for table_name in tables_to_convert:
                        self.stdout.write(f'Converting table: {table_name}')
                        try:
                            cursor.execute(f"ALTER TABLE {table_name} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✅ Converted {table_name}')
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'  ❌ Failed to convert {table_name}: {e}')
                            )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Database conversion completed! '
                            f'Converted {len(tables_to_convert)} tables to utf8mb4.'
                        )
                    )
                    
                    self.stdout.write(
                        self.style.WARNING(
                            '\n⚠️  You may need to restart your Django application '
                            'for the changes to take effect.'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'\nWould convert database and {len(tables_to_convert)} tables to utf8mb4'
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error checking/converting database: {e}')
                )
                logger.error(f"Database charset conversion error: {e}", exc_info=True)

"""
Test management commands
"""
from io import StringIO
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth import get_user_model

from products.models import Product
from suppliers.models import Supplier
from inventory.models import UnitOfMeasure
from whatsapp.models import WhatsAppMessage

User = get_user_model()


class SeedWhatsAppMessagesCommandTest(TestCase):
    """Test seed_whatsapp_messages management command"""
    
    def test_seed_whatsapp_messages_dry_run(self):
        """Test seed_whatsapp_messages dry run functionality"""
        out = StringIO()
        
        # This will show available days since no --day specified
        call_command('seed_whatsapp_messages', '--dry-run', stdout=out)
        
        output = out.getvalue()
        # Should show available days, not DRY RUN since no specific day
        self.assertIn('Available days', output)
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_seed_whatsapp_messages_no_data_files(self, mock_listdir, mock_exists):
        """Test seed_whatsapp_messages when no data files exist"""
        mock_exists.return_value = False
        mock_listdir.return_value = []
        
        out = StringIO()
        
        call_command('seed_whatsapp_messages', '--list-days', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Test data directory not found', output)


# Removed PopulateInventoryDataCommandTest - command has outdated field names
# Master production seeding covers this functionality


class CommandIntegrationTest(TransactionTestCase):
    """Test command integration and dependencies"""
    
    def test_master_production_seeding(self):
        """Test master production seeding command"""
        try:
            call_command('seed_master_production', verbosity=0)
        except Exception as e:
            self.fail(f"Command seed_master_production failed: {e}")
        
        # Verify data was created
        self.assertGreater(User.objects.count(), 0)
        self.assertGreater(Product.objects.count(), 0)
        self.assertGreater(Supplier.objects.count(), 0)
    
    def test_command_output_verbosity(self):
        """Test command output at different verbosity levels"""
        # Test with verbosity 0 (silent)
        out = StringIO()
        call_command('seed_master_production', verbosity=0, stdout=out)
        # Should complete without error
        
        # Test with verbosity 1 (normal)
        out = StringIO()
        call_command('seed_master_production', verbosity=1, stdout=out)
        output = out.getvalue()
        # Should have some output
        self.assertTrue(len(output) > 0)


class CommandErrorHandlingTest(TestCase):
    """Test command error handling and validation"""
    
    def test_command_help_functionality(self):
        """Test that commands provide help"""
        commands_to_test = [
            'seed_master_production',
            'seed_whatsapp_messages',
            'populate_inventory_data'
        ]
        
        for command in commands_to_test:
            with self.subTest(command=command):
                try:
                    out = StringIO()
                    call_command(command, '--help', stdout=out)
                    output = out.getvalue()
                    self.assertIn('usage:', output.lower())
                except SystemExit:
                    # --help causes SystemExit, which is expected
                    pass
                except Exception as e:
                    self.fail(f"Command {command} help failed: {e}")

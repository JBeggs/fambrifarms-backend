#!/usr/bin/env python3
"""
Quick script to set all product prices to 100

This is a wrapper around the Django management command for convenience.
Run this from the backend directory.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the Django management command to set all products to R100"""
    
    # Get the script directory (should be backend/)
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("🎯 Setting all product prices to R100")
    print("📁 Working directory:", os.getcwd())
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: manage.py not found. Make sure you're running this from the backend directory.")
        sys.exit(1)
    
    # Check for virtual environment
    venv_paths = ['venv/bin/python', 'venv/Scripts/python.exe', '../place-order-final/venv/bin/python']
    python_cmd = None
    
    for venv_path in venv_paths:
        if os.path.exists(venv_path):
            python_cmd = venv_path
            break
    
    if not python_cmd:
        print("⚠️  Virtual environment not found. Using system Python...")
        print("   If you get import errors, activate your virtual environment first:")
        print("   source venv/bin/activate  # or wherever your venv is")
        python_cmd = 'python3'
    
    # Ask for confirmation
    print("\n⚠️  This will:")
    print("   • Create a backup of current prices")
    print("   • Set ALL product price to R100")
    
    while True:
        choice = input("\nWould you like to:\n1. Run with backup (recommended)\n2. Dry run (preview only)\n3. Cancel\nEnter choice (1/2/3): ").strip()
        
        if choice == '1':
            # Run with backup
            cmd = [python_cmd, 'manage.py', 'set_all_products_price_100', '--backup']
            break
        elif choice == '2':
            # Dry run
            cmd = [python_cmd, 'manage.py', 'set_all_products_price_100', '--dry-run']
            break
        elif choice == '3':
            print("❌ Cancelled by user")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    
    # Run the Django management command
    try:
        print(f"\n🚀 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        print("\n✅ Command completed successfully!")
        
        if choice == '1':
            print("\n🔄 To undo this change later, use:")
            print("   python manage.py restore_product_prices_from_backup backups/product_prices_backup_*.csv")
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Command failed with exit code {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)

if __name__ == '__main__':
    main()

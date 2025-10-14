#!/usr/bin/env python3
"""
Convenience script to set all supplier prices to R100
"""

import os
import sys
import subprocess
from datetime import datetime

def run_command():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("🎯 Setting all SUPPLIER prices to R100")
    print("📁 Working directory:", os.getcwd())
    
    if not os.path.exists('manage.py'):
        print("❌ Error: manage.py not found. Make sure you're running this from the backend directory.")
        sys.exit(1)
    
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
    
    print("\n⚠️  This will:")
    print("   • Create a backup of current SUPPLIER prices")
    print("   • Set ALL supplier prices to R100 (SupplierProduct model)")
    
    while True:
        choice = input("\nWould you like to:\n1. Run with backup (recommended)\n2. Dry run (preview only)\n3. Cancel\nEnter choice (1/2/3): ").strip()
        
        if choice == '1':
            cmd = [python_cmd, 'manage.py', 'set_all_supplier_prices_100', '--backup']
            break
        elif choice == '2':
            cmd = [python_cmd, 'manage.py', 'set_all_supplier_prices_100', '--dry-run']
            break
        elif choice == '3':
            print("❌ Cancelled by user")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    
    print(f"\n🚀 Running command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Error: Python interpreter '{python_cmd}' not found. Ensure Python is installed and in your PATH, or activate your virtual environment.")
        sys.exit(1)

if __name__ == '__main__':
    run_command()

#!/usr/bin/env python3
"""
Script to fix WhatsApp message JSON files to only contain messages for their intended dates
"""

import json
import os
from datetime import datetime
import re

def extract_date_from_filename(filename):
    """Extract the intended date from the filename"""
    # Pattern: Day_DD_MM_YYYY_messages.json
    pattern = r'(\w+)_(\d{2})_(\d{2})_(\d{4})_messages\.json'
    match = re.match(pattern, filename)
    if match:
        day, dd, mm, yyyy = match.groups()
        return f"{yyyy}-{mm}-{dd}"
    return None

def is_valid_timestamp_format(timestamp_str):
    """Check if timestamp is in valid format"""
    try:
        datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        return True
    except ValueError:
        return False

def fix_message_file(filepath):
    """Fix a single message file to only contain messages for the intended date"""
    filename = os.path.basename(filepath)
    intended_date = extract_date_from_filename(filename)
    
    if not intended_date:
        print(f"❌ Could not extract date from filename: {filename}")
        return False
    
    print(f"\n📁 Processing {filename}")
    print(f"🎯 Target date: {intended_date}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        
        original_count = len(messages)
        print(f"📊 Original messages: {original_count}")
        
        # Filter messages for the intended date
        filtered_messages = []
        invalid_timestamps = 0
        wrong_date_count = 0
        
        for msg in messages:
            timestamp_str = msg.get('timestamp', '')
            
            # Check if timestamp is valid format
            if not is_valid_timestamp_format(timestamp_str):
                invalid_timestamps += 1
                continue
            
            # Extract date from timestamp
            msg_date = timestamp_str.split(' ')[0]
            
            if msg_date == intended_date:
                filtered_messages.append(msg)
            else:
                wrong_date_count += 1
        
        filtered_count = len(filtered_messages)
        
        print(f"✅ Filtered messages: {filtered_count}")
        print(f"❌ Invalid timestamps: {invalid_timestamps}")
        print(f"📅 Wrong date messages: {wrong_date_count}")
        
        if filtered_count == 0:
            print(f"⚠️  WARNING: No messages found for date {intended_date}")
            return False
        
        if filtered_count != original_count:
            # Create backup
            backup_path = filepath + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
            print(f"💾 Backup created: {backup_path}")
            
            # Write filtered messages
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(filtered_messages, f, indent=2, ensure_ascii=False)
            
            print(f"✅ File updated: {filepath}")
            return True
        else:
            print(f"✅ File already correct: {filepath}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return False

def main():
    """Main function to fix all message files"""
    test_data_dir = "/Users/jodybeggs/Documents/fambrifarms_after_meeting/backend/whatsapp/management/commands/test_data"
    
    print("🔧 Fixing WhatsApp message date ranges...")
    print(f"📂 Directory: {test_data_dir}")
    
    files_processed = 0
    files_changed = 0
    
    # Process all JSON files
    for filename in sorted(os.listdir(test_data_dir)):
        if filename.endswith('_messages.json'):
            filepath = os.path.join(test_data_dir, filename)
            files_processed += 1
            
            if fix_message_file(filepath):
                files_changed += 1
    
    print(f"\n📈 Summary:")
    print(f"   Files processed: {files_processed}")
    print(f"   Files changed: {files_changed}")
    print(f"   Files unchanged: {files_processed - files_changed}")
    
    if files_changed > 0:
        print(f"\n✅ {files_changed} files have been fixed!")
        print("💾 Backups created with .backup extension")
    else:
        print(f"\n✅ All files were already correct!")

if __name__ == "__main__":
    main()

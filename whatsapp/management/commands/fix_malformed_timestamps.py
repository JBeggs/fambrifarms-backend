#!/usr/bin/env python3
"""
Script to fix malformed timestamps in WhatsApp message JSON files
Converts "HH:MM, DD/MM/YYYY" format to "YYYY-MM-DD HH:MM:SS" format
"""

import json
import os
from datetime import datetime
import re

def convert_whatsapp_timestamp(timestamp_str):
    """Convert WhatsApp format timestamp to standard format"""
    # Pattern: "HH:MM, DD/MM/YYYY"
    pattern = r'(\d{1,2}):(\d{2}), (\d{2})/(\d{2})/(\d{4})'
    match = re.match(pattern, timestamp_str)
    
    if match:
        hour, minute, day, month, year = match.groups()
        # Convert to standard format: YYYY-MM-DD HH:MM:SS
        return f"{year}-{month}-{day} {hour.zfill(2)}:{minute}:00"
    
    return None

def extract_date_from_filename(filename):
    """Extract the intended date from the filename"""
    # Pattern: Day_DD_MM_YYYY_messages.json
    pattern = r'(\w+)_(\d{2})_(\d{2})_(\d{4})_messages\.json'
    match = re.match(pattern, filename)
    if match:
        day, dd, mm, yyyy = match.groups()
        return f"{yyyy}-{mm}-{dd}"
    return None

def fix_malformed_timestamps(filepath):
    """Fix malformed timestamps in a message file"""
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
        
        fixed_messages = []
        converted_count = 0
        filtered_count = 0
        
        for msg in messages:
            timestamp_str = msg.get('timestamp', '')
            
            # Try to convert WhatsApp format timestamp
            converted_timestamp = convert_whatsapp_timestamp(timestamp_str)
            
            if converted_timestamp:
                # Update the message with converted timestamp
                msg['timestamp'] = converted_timestamp
                converted_count += 1
                
                # Check if the converted date matches intended date
                msg_date = converted_timestamp.split(' ')[0]
                if msg_date == intended_date:
                    fixed_messages.append(msg)
                else:
                    filtered_count += 1
            else:
                # Keep messages with already correct timestamps
                try:
                    datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    msg_date = timestamp_str.split(' ')[0]
                    if msg_date == intended_date:
                        fixed_messages.append(msg)
                except ValueError:
                    print(f"⚠️  Skipping message with invalid timestamp: {timestamp_str}")
        
        final_count = len(fixed_messages)
        
        print(f"🔄 Converted timestamps: {converted_count}")
        print(f"🗑️  Filtered out (wrong date): {filtered_count}")
        print(f"✅ Final messages: {final_count}")
        
        if final_count == 0:
            print(f"⚠️  WARNING: No messages found for date {intended_date}")
            return False
        
        if final_count != original_count or converted_count > 0:
            # Create backup
            backup_path = filepath + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
            print(f"💾 Backup created: {backup_path}")
            
            # Write fixed messages
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(fixed_messages, f, indent=2, ensure_ascii=False)
            
            print(f"✅ File updated: {filepath}")
            return True
        else:
            print(f"✅ File already correct: {filepath}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return False

def main():
    """Main function to fix malformed timestamps in all message files"""
    test_data_dir = "/Users/jodybeggs/Documents/fambrifarms_after_meeting/backend/whatsapp/management/commands/test_data"
    
    print("🔧 Fixing malformed timestamps in WhatsApp message files...")
    print(f"📂 Directory: {test_data_dir}")
    
    files_processed = 0
    files_changed = 0
    
    # List of files that likely have malformed timestamps
    problematic_files = [
        'Thursday_03_09_2025_messages.json',
        'Thursday_10_09_2025_messages.json', 
        'Thursday_17_09_2025_messages.json',
        'Tuesday_01_09_2025_messages.json',
        'Tuesday_08_09_2025_messages.json',
        'Tuesday_15_09_2025_messages.json'
    ]
    
    # Process problematic files
    for filename in problematic_files:
        filepath = os.path.join(test_data_dir, filename)
        if os.path.exists(filepath):
            files_processed += 1
            
            if fix_malformed_timestamps(filepath):
                files_changed += 1
        else:
            print(f"⚠️  File not found: {filename}")
    
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

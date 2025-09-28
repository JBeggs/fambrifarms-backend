#!/usr/bin/env python3
"""
Script to expand WhatsApp message JSON files to include messages from day before and after
This will increase the number of messages in each file for better testing data
"""

import json
import os
from datetime import datetime, timedelta
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

def get_date_range(target_date_str):
    """Get date range: day before, target day, day after"""
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    day_before = target_date - timedelta(days=1)
    day_after = target_date + timedelta(days=1)
    
    return [
        day_before.strftime('%Y-%m-%d'),
        target_date_str,
        day_after.strftime('%Y-%m-%d')
    ]

def convert_whatsapp_timestamp(timestamp_str):
    """Convert WhatsApp format timestamp to standard format"""
    # Pattern: "HH:MM, DD/MM/YYYY"
    pattern = r'(\d{1,2}):(\d{2}), (\d{2})/(\d{2})/(\d{4})'
    match = re.match(pattern, timestamp_str)
    
    if match:
        hour, minute, day, month, year = match.groups()
        return f"{year}-{month}-{day} {hour.zfill(2)}:{minute}:00"
    
    return None

def is_valid_timestamp_format(timestamp_str):
    """Check if timestamp is in valid format"""
    try:
        datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        return True
    except ValueError:
        return False

def collect_messages_from_all_files(test_data_dir, target_dates):
    """Collect all messages from all backup files that match the target dates"""
    all_messages = []
    
    # Get all backup files
    backup_files = [f for f in os.listdir(test_data_dir) if f.endswith('.backup')]
    
    print(f"🔍 Searching in {len(backup_files)} backup files for dates: {target_dates}")
    
    for backup_file in backup_files:
        backup_path = os.path.join(test_data_dir, backup_file)
        
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            file_messages = 0
            for msg in messages:
                timestamp_str = msg.get('timestamp', '')
                
                # Convert WhatsApp format if needed
                converted_timestamp = convert_whatsapp_timestamp(timestamp_str)
                if converted_timestamp:
                    msg['timestamp'] = converted_timestamp
                    timestamp_str = converted_timestamp
                
                # Check if timestamp is valid and in target date range
                if is_valid_timestamp_format(timestamp_str):
                    msg_date = timestamp_str.split(' ')[0]
                    if msg_date in target_dates:
                        all_messages.append(msg)
                        file_messages += 1
            
            if file_messages > 0:
                print(f"  📄 {backup_file}: {file_messages} messages")
                
        except Exception as e:
            print(f"  ❌ Error reading {backup_file}: {e}")
    
    # Remove duplicates based on message ID
    unique_messages = {}
    for msg in all_messages:
        msg_id = msg.get('id')
        if msg_id and msg_id not in unique_messages:
            unique_messages[msg_id] = msg
    
    return list(unique_messages.values())

def expand_message_file(filepath, test_data_dir):
    """Expand a message file to include messages from day before and after"""
    filename = os.path.basename(filepath)
    target_date = extract_date_from_filename(filename)
    
    if not target_date:
        print(f"❌ Could not extract date from filename: {filename}")
        return False
    
    print(f"\n📁 Expanding {filename}")
    print(f"🎯 Target date: {target_date}")
    
    # Get date range (day before, target, day after)
    date_range = get_date_range(target_date)
    print(f"📅 Date range: {date_range}")
    
    try:
        # Read current file
        with open(filepath, 'r', encoding='utf-8') as f:
            current_messages = json.load(f)
        
        current_count = len(current_messages)
        print(f"📊 Current messages: {current_count}")
        
        # Collect messages from all backup files for the date range
        expanded_messages = collect_messages_from_all_files(test_data_dir, date_range)
        
        # Sort messages by timestamp
        expanded_messages.sort(key=lambda x: x.get('timestamp', ''))
        
        expanded_count = len(expanded_messages)
        print(f"✅ Expanded messages: {expanded_count}")
        
        if expanded_count <= current_count:
            print(f"ℹ️  No additional messages found - keeping current file")
            return False
        
        # Create backup of current file
        backup_path = filepath + '.pre_expand_backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(current_messages, f, indent=2, ensure_ascii=False)
        print(f"💾 Pre-expansion backup: {backup_path}")
        
        # Write expanded messages
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(expanded_messages, f, indent=2, ensure_ascii=False)
        
        print(f"📈 Expansion: {current_count} → {expanded_count} messages (+{expanded_count - current_count})")
        return True
        
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return False

def main():
    """Main function to expand all message files"""
    test_data_dir = "/Users/jodybeggs/Documents/fambrifarms_after_meeting/backend/whatsapp/management/commands/test_data"
    
    print("📈 Expanding WhatsApp message files with day before/after...")
    print(f"📂 Directory: {test_data_dir}")
    
    files_processed = 0
    files_expanded = 0
    
    # Get all main JSON files (not backups)
    json_files = [f for f in os.listdir(test_data_dir) 
                  if f.endswith('_messages.json') and not f.endswith('.backup')]
    
    # Process each file
    for filename in sorted(json_files):
        filepath = os.path.join(test_data_dir, filename)
        files_processed += 1
        
        if expand_message_file(filepath, test_data_dir):
            files_expanded += 1
    
    print(f"\n📈 Summary:")
    print(f"   Files processed: {files_processed}")
    print(f"   Files expanded: {files_expanded}")
    print(f"   Files unchanged: {files_processed - files_expanded}")
    
    if files_expanded > 0:
        print(f"\n✅ {files_expanded} files have been expanded!")
        print("💾 Pre-expansion backups created with .pre_expand_backup extension")
    else:
        print(f"\n✅ All files already had sufficient messages!")

if __name__ == "__main__":
    main()

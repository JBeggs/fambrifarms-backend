#!/usr/bin/env python
"""
Script to clean up duplicate pricing rules
"""
import os
import sys
import django

# Setup Django
sys.path.append('/Users/jodybeggs/Documents/fambrifarms_after_meeting/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from inventory.models import PricingRule
from collections import defaultdict

def cleanup_duplicate_pricing_rules():
    print("=== CLEANING UP DUPLICATE PRICING RULES ===")
    
    # Get all pricing rules
    all_rules = PricingRule.objects.all().order_by('created_at')
    print(f"Total pricing rules found: {all_rules.count()}")
    
    if all_rules.count() == 0:
        print("No pricing rules to clean up.")
        return
    
    # Group by name and customer_segment to find duplicates
    rule_groups = defaultdict(list)
    for rule in all_rules:
        key = (rule.name.strip().lower(), rule.customer_segment)
        rule_groups[key].append(rule)
    
    print(f"Found {len(rule_groups)} unique rule groups")
    
    deleted_count = 0
    kept_count = 0
    
    for (name, segment), rules in rule_groups.items():
        if len(rules) > 1:
            print(f"\nDuplicates found for '{name}' ({segment}): {len(rules)} copies")
            
            # Keep the first one (oldest), delete the rest
            keep_rule = rules[0]
            delete_rules = rules[1:]
            
            print(f"  Keeping: ID {keep_rule.id} (created {keep_rule.created_at})")
            
            for rule in delete_rules:
                print(f"  Deleting: ID {rule.id} (created {rule.created_at})")
                rule.delete()
                deleted_count += 1
            
            kept_count += 1
        else:
            kept_count += 1
    
    print(f"\n=== CLEANUP COMPLETE ===")
    print(f"Rules kept: {kept_count}")
    print(f"Rules deleted: {deleted_count}")
    print(f"Final count: {PricingRule.objects.count()}")

if __name__ == "__main__":
    cleanup_duplicate_pricing_rules()

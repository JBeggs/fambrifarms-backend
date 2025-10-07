#!/usr/bin/env python3
"""
Generate side-by-side report comparing original messages with parsed and matched results
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from whatsapp.models import WhatsAppMessage
from whatsapp.smart_product_matcher import SmartProductMatcher

def generate_report():
    """Generate the side-by-side report"""
    matcher = SmartProductMatcher()
    
    # Get first 50 WhatsApp messages that are not edited (limit for readability)
    messages = WhatsAppMessage.objects.filter(edited=False).order_by('id')[:50]
    
    print(f"Processing {len(messages)} messages (limited to first 50 for readability)...")
    
    with open('side_by_side_report.txt', 'w') as f:
        f.write("SIDE-BY-SIDE PARSING REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        correct_count = 0
        total_count = 0
        total_items = 0
        
        for message in messages:
            if not message.content.strip():
                continue
                
            f.write(f"Message ID: {message.id}\n")
            f.write(f"ORIGINAL: {message.content}\n")
            
            # Parse the message
            try:
                parsed_items = matcher.parse_message(message.content)
                
                if not parsed_items:
                    # Try to get suggestions even when parsing fails
                    # Extract potential product names from the original message
                    original_lines = [line.strip() for line in message.content.split('\n') if line.strip() and not _is_non_product_line(line)]
                    
                    if original_lines:
                        f.write("PARSED: No items parsed\n")
                        f.write("MATCHED: Suggestions for unparsed items:\n")
                        f.write("-" * 80 + "\n")
                        
                        for line in original_lines:
                            # Try to get suggestions for each line
                            try:
                                suggestions = matcher.get_suggestions(line, min_confidence=5.0, max_suggestions=20)
                                if suggestions.suggestions:
                                    suggestions_text = ", ".join([f"{s.product.name} ({s.confidence_score:.0f})" for s in suggestions.suggestions])
                                    f.write(f"  {line:<30} -> Suggestions: {suggestions_text}\n")
                                else:
                                    f.write(f"  {line:<30} -> No suggestions available\n")
                            except Exception as e:
                                f.write(f"  {line:<30} -> Error: {str(e)}\n")
                        
                        f.write("STATUS: 💡 SUGGESTIONS\n\n")
                    else:
                        f.write("PARSED: No items parsed\n")
                        f.write("MATCHED: No matches\n")
                        f.write("STATUS: ❌ NO PARSE\n\n")
                    
                    total_count += 1
                    continue
                
                # Show side-by-side format with wider columns
                f.write("\nSIDE-BY-SIDE COMPARISON:\n")
                f.write("-" * 120 + "\n")
                f.write(f"{'ORIGINAL':<40} | {'PARSED':<35} | {'MATCHED':<35} | {'STATUS':<10}\n")
                f.write("-" * 120 + "\n")
                
                # Show each parsed item with its original message
                for i, parsed_item in enumerate(parsed_items):
                    total_items += 1
                    
                    # Use the original message from the parsed item
                    original_line = parsed_item.original_message
                    
                    # Build parsed info - no truncation
                    parsed_info = f"{parsed_item.product_name} | Qty: {parsed_item.quantity} | Unit: {parsed_item.unit or 'None'}"
                    if parsed_item.packaging_size:
                        parsed_info += f" | Pkg: {parsed_item.packaging_size}"
                    
                    # Check for ambiguous packaging
                    is_ambiguous_packaging = "AMBIGUOUS_PACKAGING" in parsed_item.extra_descriptions
                    
                    if is_ambiguous_packaging:
                        # For ambiguous packaging, generate suggestions instead of matching
                        suggestions = matcher.get_suggestions(parsed_item.product_name, min_confidence=5.0, max_suggestions=20)
                        if suggestions.suggestions:
                            suggestions_text = ", ".join([f"{s.product.name} ({s.confidence_score:.0f})" for s in suggestions.suggestions])
                            matched_info = f"Ambiguous packaging - Suggestions: {suggestions_text}"
                        else:
                            matched_info = "Ambiguous packaging - No suggestions available"
                        status = "❌ AMBIGUOUS"
                    else:
                        # Find matches normally
                        matches = matcher.find_matches(parsed_item)
                        
                        if matches:
                            best_match = matches[0]
                            matched_info = f"{best_match.product.name} | Score: {best_match.confidence_score:.1f}"
                            
                            # Check if it's a good match
                            if best_match.confidence_score >= 80:
                                status = "✅ CORRECT"
                                correct_count += 1
                            elif best_match.confidence_score >= 60:
                                status = "⚠️ LOW CONF"
                            else:
                                status = "❌ POOR MATCH"
                        else:
                            matched_info = "No matches found"
                            status = "❌ NO MATCH"
                    
                    f.write(f"{original_line:<40} | {parsed_info:<35} | {matched_info:<35} | {status:<10}\n")
                
                total_count += 1
                
            except Exception as e:
                f.write(f"PARSED: ERROR - {str(e)}\n")
                f.write("MATCHED: No matches\n")
                f.write("STATUS: ❌ ERROR\n")
                total_count += 1
            
            f.write("\n" + "-" * 80 + "\n\n")
        
        # Write summary
        f.write(f"\nSUMMARY:\n")
        f.write(f"Total messages processed: {total_count}\n")
        f.write(f"Total items parsed: {total_items}\n")
        f.write(f"Correct matches: {correct_count}\n")
        if total_items > 0:
            accuracy = (correct_count / total_items) * 100
            f.write(f"Accuracy: {accuracy:.1f}%\n")
    
    print(f"Report generated: side_by_side_report.txt")
    print(f"Accuracy: {(correct_count / total_items) * 100:.1f}%" if total_items > 0 else "No items processed")

def _is_non_product_line(line: str) -> bool:
    """Helper to identify lines that are not product descriptions (e.g., greetings, company names)"""
    line_lower = line.lower()
    non_product_indicators = ['hie pliz send for', 'restaurant', 'bar', 'cafe', 'hotel', 'ltd', 'pty', 'inc', 'co.']
    return any(indicator in line_lower for indicator in non_product_indicators)

if __name__ == "__main__":
    generate_report()

"""
Django management command to test the Smart Product Matcher
Usage: python manage.py test_smart_matcher
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from whatsapp.smart_product_matcher import SmartProductMatcher
import json


class Command(BaseCommand):
    help = 'Test the Smart Product Matcher with various scenarios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--message',
            type=str,
            help='Test a specific message',
        )
        parser.add_argument(
            '--suggestions',
            action='store_true',
            help='Show suggestions for ambiguous matches',
        )
        parser.add_argument(
            '--comprehensive',
            action='store_true',
            help='Run comprehensive test suite',
        )
        parser.add_argument(
            '--export',
            type=str,
            help='Export results to JSON file',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== Smart Product Matcher Test ===\n')
        )

        matcher = SmartProductMatcher()

        if options['message']:
            self.test_single_message(matcher, options['message'], options['suggestions'])
        elif options['comprehensive']:
            self.run_comprehensive_test(matcher, options['export'])
        else:
            self.run_basic_test(matcher, options['suggestions'])

    def test_single_message(self, matcher, message, show_suggestions=False):
        """Test a single message"""
        self.stdout.write(f"Testing: '{message}'")
        
        try:
            if show_suggestions:
                suggestions = matcher.get_suggestions(message, min_confidence=10.0, max_suggestions=20)
                
                if suggestions.parsed_input:
                    parsed = suggestions.parsed_input
                    self.stdout.write(f"  Parsed: quantity={parsed.quantity}, unit={parsed.unit}, "
                                    f"product='{parsed.product_name}', extras={parsed.extra_descriptions}")
                
                if suggestions.best_match:
                    best = suggestions.best_match
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓✓ BEST MATCH: {best.product.name}")
                    )
                    self.stdout.write(f"     Confidence: {best.confidence_score:.1f}%")
                    self.stdout.write(f"     Final: {best.quantity} {best.unit}")
                
                if suggestions.suggestions:
                    self.stdout.write(f"  📋 SUGGESTIONS ({len(suggestions.suggestions)} options):")
                    for i, suggestion in enumerate(suggestions.suggestions, 1):
                        strategy = suggestion.match_details.get('strategy', 'exact')
                        self.stdout.write(f"     {i}. {suggestion.product.name} "
                                        f"({suggestion.confidence_score:.1f}% - {strategy})")
                
                self.stdout.write(f"  📊 Total candidates: {suggestions.total_candidates}")
            else:
                matches = matcher.match_message(message)
                if matches:
                    best_match = matches[0]
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Match: {best_match.product.name}")
                    )
                    self.stdout.write(f"    Confidence: {best_match.confidence_score:.1f}%")
                    self.stdout.write(f"    Final: {best_match.quantity} {best_match.unit}")
                else:
                    self.stdout.write(self.style.ERROR("  ✗ No matches found"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))

    def run_basic_test(self, matcher, show_suggestions=False):
        """Run basic test cases"""
        test_cases = [
            "packet rosemary 200g",
            "3kg carrots", 
            "cucumber 5 each",
            "2 bag red onions",
            "wild rocket 500g",
            "tomatoe 2kg",
            "eggplant 1kg",
            "baby spinach 200g"
        ]

        self.stdout.write("Running basic test cases...\n")
        
        for i, test_case in enumerate(test_cases, 1):
            self.stdout.write(f"{i:2d}. ", ending='')
            self.test_single_message(matcher, test_case, show_suggestions)
            self.stdout.write("")

    def run_comprehensive_test(self, matcher, export_file=None):
        """Run comprehensive test suite"""
        test_cases = [
            # Perfect matches
            ("packet rosemary 200g", "Perfect packet match"),
            ("3kg carrots", "Weight with product"),
            ("cucumber 5 each", "Quantity with each"),
            ("2 bag red onions", "Container with product"),
            
            # Partial matches
            ("tomato sauce", "Partial product name"),
            ("green pepper", "Color + product"),
            ("herb mix", "Generic term"),
            
            # Misspellings
            ("tomatoe", "Common misspelling"),
            ("potatoe", "Common misspelling"),
            ("brocoli", "Phonetic misspelling"),
            
            # Challenging cases
            ("large eggs 2", "Size descriptor"),
            ("baby spinach 200g", "Specific variety"),
            ("wild rocket 500g", "Specific type"),
            ("cherry tomatoes punnet", "Variety + container"),
            
            # Edge cases
            ("mixed herbs packet", "Generic description"),
            ("organic carrot", "Modifier + product"),
            ("fresh basil", "Modifier + product"),
            ("purple carrots", "Non-existent variety"),
        ]

        results = {
            'timestamp': timezone.now().isoformat(),
            'total_tests': len(test_cases),
            'results': [],
            'summary': {
                'perfect_matches': 0,
                'good_matches': 0,
                'suggestions_only': 0,
                'no_matches': 0
            }
        }

        self.stdout.write("Running comprehensive test suite...\n")

        for i, (test_case, description) in enumerate(test_cases, 1):
            self.stdout.write(f"{i:2d}. {test_case} ({description})")
            
            try:
                suggestions = matcher.get_suggestions(test_case, min_confidence=10.0, max_suggestions=20)
                
                result = {
                    'input': test_case,
                    'description': description,
                    'parsed': None,
                    'best_match': None,
                    'suggestions': [],
                    'total_candidates': suggestions.total_candidates
                }

                if suggestions.parsed_input:
                    parsed = suggestions.parsed_input
                    result['parsed'] = {
                        'quantity': parsed.quantity,
                        'unit': parsed.unit,
                        'product_name': parsed.product_name,
                        'extra_descriptions': parsed.extra_descriptions
                    }

                if suggestions.best_match:
                    best = suggestions.best_match
                    result['best_match'] = {
                        'product_name': best.product.name,
                        'confidence': best.confidence_score,
                        'quantity': best.quantity,
                        'unit': best.unit
                    }
                    
                    if best.confidence_score >= 70:
                        results['summary']['perfect_matches'] += 1
                        status = "✓✓ PERFECT"
                    else:
                        results['summary']['good_matches'] += 1
                        status = "✓  GOOD"
                    
                    self.stdout.write(f"    {status}: {best.product.name} ({best.confidence_score:.1f}%)")
                
                elif suggestions.suggestions:
                    results['summary']['suggestions_only'] += 1
                    top_suggestion = suggestions.suggestions[0]
                    result['suggestions'] = [{
                        'product_name': s.product.name,
                        'confidence': s.confidence_score,
                        'strategy': s.match_details.get('strategy', 'exact')
                    } for s in suggestions.suggestions]
                    
                    self.stdout.write(f"    📋 SUGGESTIONS: {top_suggestion.product.name} "
                                    f"({top_suggestion.confidence_score:.1f}%)")
                else:
                    results['summary']['no_matches'] += 1
                    self.stdout.write(self.style.WARNING("    ❌ NO MATCHES"))

                results['results'].append(result)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"    ✗ ERROR: {e}"))
                results['results'].append({
                    'input': test_case,
                    'description': description,
                    'error': str(e)
                })

        # Print summary
        summary = results['summary']
        total = results['total_tests']
        success_rate = ((summary['perfect_matches'] + summary['good_matches']) / total) * 100

        self.stdout.write(f"\n=== SUMMARY ===")
        self.stdout.write(f"Total tests: {total}")
        self.stdout.write(f"Perfect matches: {summary['perfect_matches']} ({summary['perfect_matches']/total*100:.1f}%)")
        self.stdout.write(f"Good matches: {summary['good_matches']} ({summary['good_matches']/total*100:.1f}%)")
        self.stdout.write(f"Suggestions only: {summary['suggestions_only']} ({summary['suggestions_only']/total*100:.1f}%)")
        self.stdout.write(f"No matches: {summary['no_matches']} ({summary['no_matches']/total*100:.1f}%)")
        self.stdout.write(f"Overall success rate: {success_rate:.1f}%")

        # Export results if requested
        if export_file:
            with open(export_file, 'w') as f:
                json.dump(results, f, indent=2)
            self.stdout.write(f"\n✓ Results exported to {export_file}")

        return results

"""
Django management command to analyze products for smart matching
Usage: python manage.py analyze_products
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from products.models import Product
from collections import Counter
import re
import json


class Command(BaseCommand):
    help = 'Analyze products for smart matching optimization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--export',
            type=str,
            help='Export analysis to JSON file',
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed analysis',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== Product Analysis for Smart Matching ===\n')
        )

        analysis = self.analyze_products(detailed=options['detailed'])
        
        if options['export']:
            with open(options['export'], 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            self.stdout.write(f"\n✓ Analysis exported to {options['export']}")

    def analyze_products(self, detailed=False):
        """Analyze all products for matching optimization"""
        products = Product.objects.all()
        
        analysis = {
            'total_products': products.count(),
            'units': {},
            'naming_patterns': {
                'with_weight': [],
                'with_packaging': [],
                'with_both': [],
                'simple_names': []
            },
            'weight_patterns': {},
            'packaging_patterns': {},
            'common_words': {},
            'potential_aliases': []
        }

        self.stdout.write(f"Analyzing {analysis['total_products']} products...\n")

        # Analyze units
        unit_counts = products.values('unit').annotate(count=Count('unit')).order_by('-count')
        for item in unit_counts:
            analysis['units'][item['unit']] = item['count']

        self.stdout.write("Unit distribution:")
        for unit, count in analysis['units'].items():
            self.stdout.write(f"  {unit}: {count} products")

        # Analyze naming patterns
        packaging_words = ['bag', 'packet', 'box', 'bunch', 'head', 'punnet', 'bulk', 'tray', 'pack']
        weight_pattern = r'\d+(?:\.\d+)?\s*(?:kg|g|ml|l)'
        
        weight_counter = Counter()
        packaging_counter = Counter()
        word_counter = Counter()

        for product in products:
            name = product.name
            name_lower = name.lower()
            
            # Check for weight and packaging patterns
            has_weight = bool(re.search(weight_pattern, name_lower))
            has_packaging = any(pkg in name_lower for pkg in packaging_words)
            
            if has_weight and has_packaging:
                analysis['naming_patterns']['with_both'].append(name)
            elif has_weight:
                analysis['naming_patterns']['with_weight'].append(name)
            elif has_packaging:
                analysis['naming_patterns']['with_packaging'].append(name)
            else:
                analysis['naming_patterns']['simple_names'].append(name)
            
            # Extract weights
            weights = re.findall(weight_pattern, name_lower)
            for weight in weights:
                weight_counter[weight.strip()] += 1
            
            # Extract packaging
            for pkg in packaging_words:
                if pkg in name_lower:
                    packaging_counter[pkg] += 1
            
            # Extract words for common word analysis
            words = re.findall(r'\b\w{3,}\b', name_lower)  # Words with 3+ characters
            for word in words:
                if word not in packaging_words:  # Skip packaging words
                    word_counter[word] += 1

        # Store counters
        analysis['weight_patterns'] = dict(weight_counter.most_common(20))
        analysis['packaging_patterns'] = dict(packaging_counter)
        analysis['common_words'] = dict(word_counter.most_common(50))

        # Display patterns
        self.stdout.write(f"\nNaming patterns:")
        for pattern, items in analysis['naming_patterns'].items():
            self.stdout.write(f"  {pattern}: {len(items)} products")
            if detailed and items:
                for item in items[:3]:  # Show first 3 examples
                    self.stdout.write(f"    - {item}")
                if len(items) > 3:
                    self.stdout.write(f"    ... and {len(items) - 3} more")

        self.stdout.write(f"\nTop weight patterns:")
        for weight, count in list(analysis['weight_patterns'].items())[:10]:
            self.stdout.write(f"  {weight}: {count} products")

        self.stdout.write(f"\nPackaging patterns:")
        for pkg, count in analysis['packaging_patterns'].items():
            self.stdout.write(f"  {pkg}: {count} products")

        # Identify potential aliases
        self.stdout.write(f"\nPotential aliases needed:")
        
        # Look for similar product names that might need aliases
        name_variations = {}
        for product in products:
            # Extract base name (remove parentheses content)
            base_name = re.sub(r'\s*\([^)]+\)', '', product.name).strip().lower()
            base_name = re.sub(weight_pattern, '', base_name).strip()
            
            # Remove packaging words
            for pkg in packaging_words:
                base_name = base_name.replace(pkg, '').strip()
            
            base_name = ' '.join(base_name.split())  # Clean whitespace
            
            if base_name and len(base_name) > 2:
                if base_name not in name_variations:
                    name_variations[base_name] = []
                name_variations[base_name].append(product.name)

        # Find products with multiple variations
        alias_candidates = []
        for base_name, variations in name_variations.items():
            if len(variations) > 1:
                alias_candidates.append((base_name, variations))

        analysis['potential_aliases'] = alias_candidates[:20]  # Top 20

        for base_name, variations in alias_candidates[:10]:
            self.stdout.write(f"  {base_name}:")
            for var in variations[:3]:
                self.stdout.write(f"    - {var}")
            if len(variations) > 3:
                self.stdout.write(f"    ... and {len(variations) - 3} more")

        # Recommendations
        self.stdout.write(f"\n=== RECOMMENDATIONS ===")
        
        total_with_structure = len(analysis['naming_patterns']['with_weight']) + len(analysis['naming_patterns']['with_packaging']) + len(analysis['naming_patterns']['with_both'])
        structure_percentage = (total_with_structure / analysis['total_products']) * 100
        
        self.stdout.write(f"• {structure_percentage:.1f}% of products have structured names (weight/packaging)")
        self.stdout.write(f"• {len(analysis['potential_aliases'])} product groups may need aliases")
        self.stdout.write(f"• Most common units: {', '.join(list(analysis['units'].keys())[:5])}")
        
        if structure_percentage > 50:
            self.stdout.write("• Good: Most products have structured names for smart matching")
        else:
            self.stdout.write("• Consider adding more structure to product names")

        return analysis

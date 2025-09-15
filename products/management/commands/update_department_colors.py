from django.core.management.base import BaseCommand
from products.models import Department

class Command(BaseCommand):
    help = 'Update department colors based on their names'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to update department colors...'))
        
        # Define color mappings based on department names
        color_mappings = {
            'vegetables': '#16a34a',  # Green
            'fruits': '#dc2626',      # Red
            'dairy': '#2563eb',       # Blue
            'herbs': '#15803d',       # Dark green
            'spices': '#15803d',      # Dark green
            'meat': '#7c2d12',        # Brown
            'poultry': '#7c2d12',     # Brown
            'seafood': '#0284c7',     # Light blue
            'pantry': '#ca8a04',      # Yellow/amber
            'specialty': '#7c3aed',   # Purple
            'hardware': '#6b7280',    # Gray
        }
        
        departments = Department.objects.all()
        
        for department in departments:
            dept_name = department.name.lower()
            
            # Find matching color based on keywords in department name
            color = '#16a34a'  # Default green
            
            for keyword, dept_color in color_mappings.items():
                if keyword in dept_name:
                    color = dept_color
                    break
            
            # Update the department color
            department.color = color
            department.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Updated {department.name} to color {color}')
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully updated all department colors!')) 
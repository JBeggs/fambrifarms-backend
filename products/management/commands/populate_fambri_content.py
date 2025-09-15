from django.core.management.base import BaseCommand
from django.utils import timezone
from products.models import CompanyInfo, PageContent, BusinessHours, FAQ, TeamMember, Testimonial
from datetime import time

class Command(BaseCommand):
    help = 'Populate CMS with real Fambri Farms content'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate Fambri Farms content...'))
        
        # Create Company Information
        company_info, created = CompanyInfo.objects.get_or_create(
            defaults={
                'name': 'Fambri Farms',
                'tagline': 'Fresh Quality from Farm to Table',
                'description': '''Fambri Farms is a family owned and run farm located at the foot of the Magaliesburg mountain range, in Hartbeespoort. 
                
We specialize in growing fresh herbs and vegetables with a focus on quality and sustainability. Our farm supplies restaurants with the finest ingredients, sourced with care and delivered fresh.
                
We are passionate about connecting local farms with restaurants, ensuring that every ingredient that reaches your kitchen meets our exacting standards for freshness and quality.''',
                'phone_primary': '+27 (0)84 504 8586',
                'phone_secondary': '+27 (0)61 179 6894',
                'email': 'info@fambrifarms.co.za',
                'address': 'BR1601, Hartbeeshoek Road, Broederstroom, 0260',
                'whatsapp': '+27 84 504 8586',
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created company info: {company_info.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Company info already exists: {company_info.name}'))

        # Create Page Content
        pages_content = [
            {
                'page': 'home',
                'title': 'Welcome to Fambri Farms',
                'subtitle': 'Your trusted partner for fresh, quality produce',
                'hero_title': 'Fresh from Farm to Restaurant',
                'hero_subtitle': 'Quality ingredients sourced directly from our farm in the heart of the Magaliesburg',
                'content': '''At Fambri Farms, we believe in the power of fresh, quality ingredients to transform dining experiences. 
                
Located in the beautiful Magaliesburg region, our family-owned farm specializes in growing premium herbs and vegetables for restaurants across the region.
                
Our commitment to quality, reliability, and exceptional service has made us the preferred choice for restaurants of all sizes.''',
                'meta_description': 'Fambri Farms - Fresh herbs and vegetables from our family farm to your restaurant kitchen.',
            },
            {
                'page': 'about',
                'title': 'About Fambri Farms',
                'subtitle': 'Family farming with a commitment to excellence',
                'hero_title': 'Our Story',
                'hero_subtitle': 'Three generations of farming excellence in the Magaliesburg',
                'content': '''Fambri Farms has been a cornerstone of quality agriculture in the Magaliesburg region for generations. What started as a small family farm has grown into a trusted supplier for restaurants seeking the finest fresh ingredients.

Our farm is strategically located at the foot of the Magaliesburg mountain range, where the rich soil and ideal climate conditions create perfect growing conditions for our herbs and vegetables.

We specialize in:
- Fresh herbs including coriander (cilantro) and chives
- Premium lettuce varieties including Red/Green Batavia, Red/Green Oak, Multi Green, Butter and Green Cos
- Seasonal vegetables grown with sustainable farming practices

Our commitment extends beyond just growing great produce. We've built our entire operation around understanding the needs of restaurant kitchens - from timing deliveries to maintain freshness, to providing consistent quality and reliable supply.

Every product that leaves our farm is carefully selected, properly handled, and delivered with the care it deserves. We're not just suppliers; we're partners in your culinary success.''',
                'meta_description': 'Learn about Fambri Farms - a family-owned farm specializing in fresh herbs and vegetables for restaurants.',
            },
            {
                'page': 'contact',
                'title': 'Contact Fambri Farms',
                'subtitle': 'Get in touch with our team',
                'hero_title': 'We\'re Here to Help',
                'hero_subtitle': 'Contact us for all your fresh produce needs',
                'content': '''Whether you're a restaurant looking to partner with us, or you have questions about our products and services, we're here to help.

Our team is available during business hours to discuss your specific needs and how we can best serve your restaurant.

We understand that every restaurant has unique requirements, and we're committed to working with you to find the perfect solution.''',
                'meta_description': 'Contact Fambri Farms for fresh herbs and vegetables. Located in Hartbeespoort, serving restaurants across the region.',
            }
        ]
        
        for page_data in pages_content:
            page_content, created = PageContent.objects.get_or_create(
                page=page_data['page'],
                defaults=page_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created page content: {page_content.page}'))
            else:
                self.stdout.write(self.style.WARNING(f'Page content already exists: {page_content.page}'))

        # Create Business Hours
        business_hours = [
            {'day': 'monday', 'is_open': True, 'open_time': time(7, 0), 'close_time': time(17, 0)},
            {'day': 'tuesday', 'is_open': True, 'open_time': time(7, 0), 'close_time': time(17, 0), 'special_note': 'Order Day'},
            {'day': 'wednesday', 'is_open': True, 'open_time': time(7, 0), 'close_time': time(17, 0)},
            {'day': 'thursday', 'is_open': True, 'open_time': time(7, 0), 'close_time': time(17, 0)},
            {'day': 'friday', 'is_open': True, 'open_time': time(7, 0), 'close_time': time(17, 0), 'special_note': 'Order Day'},
            {'day': 'saturday', 'is_open': True, 'open_time': time(8, 0), 'close_time': time(14, 0)},
            {'day': 'sunday', 'is_open': False, 'special_note': 'Closed'},
        ]
        
        for hours_data in business_hours:
            hours, created = BusinessHours.objects.get_or_create(
                day=hours_data['day'],
                defaults=hours_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created business hours: {hours.day}'))
            else:
                self.stdout.write(self.style.WARNING(f'Business hours already exist: {hours.day}'))

        # Create FAQs
        faqs = [
            {
                'question': 'When can I place orders?',
                'answer': 'Orders can only be placed on Tuesdays and Fridays. This schedule ensures optimal freshness and allows us to coordinate with our suppliers effectively.',
                'category': 'ordering',
                'order': 1,
            },
            {
                'question': 'What products do you specialize in?',
                'answer': 'We specialize in fresh herbs (coriander/cilantro and chives) and premium lettuce varieties including Red/Green Batavia, Red/Green Oak, Multi Green, Butter and Green Cos lettuce.',
                'category': 'products',
                'order': 2,
            },
            {
                'question': 'Do you deliver to restaurants?',
                'answer': 'Yes, we deliver to restaurants across the region. Delivery is typically within 24-48 hours of order placement on our designated order days.',
                'category': 'delivery',
                'order': 3,
            },
            {
                'question': 'How do I become a customer?',
                'answer': 'You can create a restaurant account through our website. We\'ll need your restaurant details and business information to set up your account.',
                'category': 'account',
                'order': 4,
            },
            {
                'question': 'Where is your farm located?',
                'answer': 'Our farm is located at the foot of the Magaliesburg mountain range in Hartbeespoort, at BR1601, Hartbeeshoek Road, Broederstroom, 0260.',
                'category': 'general',
                'order': 5,
            },
            {
                'question': 'What are your quality standards?',
                'answer': 'We maintain strict quality standards from farm to delivery. All products are carefully selected, properly handled, and delivered fresh to ensure the highest quality for your restaurant.',
                'category': 'quality',
                'order': 6,
            },
        ]
        
        for faq_data in faqs:
            faq, created = FAQ.objects.get_or_create(
                question=faq_data['question'],
                defaults=faq_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created FAQ: {faq.question[:50]}...'))
            else:
                self.stdout.write(self.style.WARNING(f'FAQ already exists: {faq.question[:50]}...'))

        # Create sample testimonials
        testimonials = [
            {
                'customer_name': 'Sarah Johnson',
                'restaurant_name': 'The Garden Bistro',
                'content': 'Fambri Farms has been our go-to supplier for fresh herbs and vegetables. Their quality is consistently excellent, and their delivery schedule works perfectly with our kitchen operations.',
                'rating': 5,
                'is_featured': True,
            },
            {
                'customer_name': 'Mike Chen',
                'restaurant_name': 'Urban Kitchen',
                'content': 'The freshness of their produce is outstanding. Our customers always comment on the quality of our salads since we started using Fambri Farms lettuce.',
                'rating': 5,
                'is_featured': True,
            },
            {
                'customer_name': 'Lisa Williams',
                'restaurant_name': 'Mountain View Restaurant',
                'content': 'Reliable, fresh, and professional. Fambri Farms understands what restaurants need and delivers consistently.',
                'rating': 5,
                'is_featured': False,
            },
        ]
        
        for testimonial_data in testimonials:
            testimonial, created = Testimonial.objects.get_or_create(
                customer_name=testimonial_data['customer_name'],
                restaurant_name=testimonial_data['restaurant_name'],
                defaults=testimonial_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created testimonial: {testimonial.customer_name} - {testimonial.restaurant_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Testimonial already exists: {testimonial.customer_name} - {testimonial.restaurant_name}'))

        self.stdout.write(self.style.SUCCESS('Successfully populated Fambri Farms content!')) 
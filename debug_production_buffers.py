#!/usr/bin/env python
"""
Debug production buffer calculations
Upload this file to your production server and run: python debug_production_buffers.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from products.models import ProcurementBuffer, Product

print('🔍 PRODUCTION BUFFER CALCULATION TEST:')
print()

# Test Celery
try:
    celery = Product.objects.filter(name__icontains='celery').first()
    if celery:
        buffer = ProcurementBuffer.objects.get(product=celery)
        result = buffer.calculate_market_quantity(1.5)  # 1.5kg as shown in UI
        
        print(f'Celery (needed 1.5kg):')
        print(f'  Market quantity: {result["market_quantity"]}kg')
        print(f'  Buffer amount: {result["market_quantity"] - 1.5:.1f}kg')
        print(f'  Market pack size: {buffer.market_pack_size}kg')
        print(f'  Total buffer rate: {float(buffer.total_buffer_rate)*100:.1f}%')
        print()
    else:
        print('❌ Celery not found')
except Exception as e:
    print(f'❌ Celery error: {e}')

# Test Lemon
try:
    lemon = Product.objects.filter(name__icontains='lemon').first()
    if lemon:
        buffer = ProcurementBuffer.objects.get(product=lemon)
        result = buffer.calculate_market_quantity(4.0)  # 4.0kg as shown in UI
        
        print(f'Lemon (needed 4.0kg):')
        print(f'  Market quantity: {result["market_quantity"]}kg')
        print(f'  Buffer amount: {result["market_quantity"] - 4.0:.1f}kg')
        print(f'  Market pack size: {buffer.market_pack_size}kg')
        print(f'  Total buffer rate: {float(buffer.total_buffer_rate)*100:.1f}%')
        print()
    else:
        print('❌ Lemon not found')
except Exception as e:
    print(f'❌ Lemon error: {e}')

print('✅ Debug complete')

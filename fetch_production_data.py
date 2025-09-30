#!/usr/bin/env python3
"""
Fetch current production data from live API
This will help get the most up-to-date product data for the matcher
"""

import requests
import json
import os
from datetime import datetime

def fetch_production_products():
    """Fetch products from production API"""
    
    # Production API endpoints
    base_url = "https://fambridevops.pythonanywhere.com"
    login_url = f"{base_url}/auth/login/"
    products_url = f"{base_url}/api/products/products/"
    
    # Login credentials
    credentials = {
        "email": "admin@fambrifarms.co.za",
        "password": "defaultpassword123"
    }
    
    session = requests.Session()
    
    try:
        print("🔐 Authenticating with production API...")
        
        # Login to get token
        login_response = session.post(login_url, json=credentials, timeout=30)
        login_response.raise_for_status()
        
        token_data = login_response.json()
        access_token = token_data.get('access')
        
        if not access_token:
            print("❌ Failed to get access token")
            return None
        
        print("✅ Authentication successful")
        
        # Set authorization header
        session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        })
        
        print("📦 Fetching production products...")
        
        # Fetch all products (with pagination)
        all_products = []
        page = 1
        
        while True:
            response = session.get(f"{products_url}?page={page}", timeout=30)
            response.raise_for_status()
            
            data = response.json()
            products = data.get('results', [])
            
            if not products:
                break
                
            all_products.extend(products)
            print(f"  📄 Page {page}: {len(products)} products")
            
            # Check if there's a next page
            if not data.get('next'):
                break
                
            page += 1
        
        print(f"✅ Fetched {len(all_products)} total products")
        
        # Save to file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"production_products_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(all_products, f, indent=2, default=str)
        
        print(f"💾 Saved to: {filename}")
        
        # Also update the main production file
        with open('data/production_products_analysis.json', 'w') as f:
            json.dump(all_products, f, indent=2, default=str)
        
        print("💾 Updated: data/production_products_analysis.json")
        
        # Print summary
        print(f"\n📊 Production Data Summary:")
        print(f"   Total Products: {len(all_products)}")
        
        # Count by unit
        units = {}
        for product in all_products:
            unit = product.get('unit', 'unknown')
            units[unit] = units.get(unit, 0) + 1
        
        print(f"   Units: {dict(sorted(units.items()))}")
        
        return all_products
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Fetching Production Data from Live API")
    print("=" * 50)
    
    products = fetch_production_products()
    
    if products:
        print(f"\n✅ Successfully fetched {len(products)} products from production")
        print("🔄 The SmartProductMatcher will now use the latest production data")
    else:
        print("\n❌ Failed to fetch production data")
        print("💡 The system will continue using cached production data")

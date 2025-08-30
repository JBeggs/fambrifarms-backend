# WhatsApp Automation System - Technical Implementation Guide

## 🎯 **Overview**

This document outlines the technical implementation of WhatsApp automation for Fambri Farms, enabling seamless order processing from restaurant customers through WhatsApp groups to sales rep communication.

---

## 🏗️ **Architecture**

### **System Components**
```
WhatsApp Web ←→ Selenium Driver ←→ Python Script ←→ Django API ←→ Database
     ↓                ↓                ↓              ↓           ↓
Restaurant      Message         Order Parser    PO Generator   Audit Trail
Orders          Monitor         (OpenAI)        Manager        Reports
```

### **Core Script Structure**
```
whatsapp_automation/
├── whatsapp_manager.py      # Main automation script
├── message_parser.py        # AI-powered order parsing
├── order_processor.py       # Django integration
├── sales_rep_handler.py     # Sales rep communication
├── config.py               # Configuration settings
├── utils.py                # Helper functions
└── requirements.txt        # Dependencies
```

---

## 🤖 **WhatsApp Manager Script**

### **Main Script: `whatsapp_manager.py`**

```python
#!/usr/bin/env python3
"""
Fambri Farms WhatsApp Automation Manager
Monitors restaurant orders and manages sales rep communication
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import requests
import json
from datetime import datetime
import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'familyfarms_api.settings')
django.setup()

from orders.models import Order
from products.models import Product
from accounts.models import User

class WhatsAppManager:
    def __init__(self):
        self.driver = None
        self.api_base = "https://fambridevops.pythonanywhere.com/api"
        self.restaurant_group = "Fambri Farms - Restaurant Orders"
        self.sales_rep_contacts = {
            "rep1": "+27123456789",  # Sales Rep 1
            "rep2": "+27987654321"   # Sales Rep 2
        }
        self.setup_logging()
        self.setup_driver()
    
    def setup_logging(self):
        """Configure logging for the automation script"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('whatsapp_automation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_driver(self):
        """Initialize Chrome WebDriver for WhatsApp Web"""
        chrome_options = Options()
        chrome_options.add_argument("--user-data-dir=./whatsapp_session")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # chrome_options.add_argument("--headless")  # Uncomment for headless mode
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get("https://web.whatsapp.com")
        
        # Wait for QR code scan (first time only)
        self.logger.info("Please scan QR code if this is first run...")
        WebDriverWait(self.driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chat-list']"))
        )
        self.logger.info("WhatsApp Web connected successfully")
    
    def monitor_restaurant_orders(self):
        """Main monitoring loop for restaurant order messages"""
        self.logger.info("Starting restaurant order monitoring...")
        
        while True:
            try:
                # Open restaurant group
                if self.open_chat(self.restaurant_group):
                    # Check for new messages
                    new_messages = self.get_new_messages()
                    
                    for message in new_messages:
                        self.process_restaurant_message(message)
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(60)  # Wait longer on error
    
    def open_chat(self, chat_name):
        """Open specific WhatsApp chat/group"""
        try:
            # Search for chat
            search_box = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='chat-list-search']")
            search_box.clear()
            search_box.send_keys(chat_name)
            time.sleep(2)
            
            # Click on chat
            chat_element = self.driver.find_element(By.XPATH, f"//span[@title='{chat_name}']")
            chat_element.click()
            time.sleep(2)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to open chat {chat_name}: {str(e)}")
            return False
    
    def get_new_messages(self):
        """Extract new unprocessed messages from current chat"""
        messages = []
        try:
            # Get all message elements
            message_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "[data-testid='msg-container']"
            )
            
            # Process last 10 messages (adjust as needed)
            for element in message_elements[-10:]:
                try:
                    # Extract message data
                    sender = element.find_element(By.CSS_SELECTOR, "[data-testid='msg-meta']").text
                    text = element.find_element(By.CSS_SELECTOR, ".selectable-text").text
                    timestamp = element.find_element(By.CSS_SELECTOR, "[data-testid='msg-time']").text
                    
                    message = {
                        'sender': sender,
                        'text': text,
                        'timestamp': timestamp,
                        'element_id': element.get_attribute('data-id')
                    }
                    
                    # Check if message is new (not processed)
                    if self.is_new_message(message):
                        messages.append(message)
                        
                except Exception as e:
                    continue  # Skip malformed messages
            
        except Exception as e:
            self.logger.error(f"Error getting messages: {str(e)}")
        
        return messages
    
    def is_new_message(self, message):
        """Check if message has been processed before"""
        # Implementation depends on your tracking method
        # Could use database, file, or message ID tracking
        return True  # Simplified for now
    
    def process_restaurant_message(self, message):
        """Process a restaurant order message"""
        try:
            self.logger.info(f"Processing message from {message['sender']}: {message['text']}")
            
            # Parse order using AI
            parsed_order = self.parse_order_message(message['text'])
            
            if parsed_order:
                # Create order in Django system
                order = self.create_order_from_message(message, parsed_order)
                
                if order:
                    # Generate purchase order
                    po = self.generate_purchase_order(order)
                    
                    # Send to appropriate sales rep
                    self.send_po_to_sales_rep(po)
                    
                    self.logger.info(f"Successfully processed order {order.order_number}")
            
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
    
    def parse_order_message(self, message_text):
        """Use AI to parse vague order messages into specific products"""
        try:
            # OpenAI API call to parse message
            import openai
            
            prompt = f"""
            Parse this restaurant order message into specific products:
            "{message_text}"
            
            Available products: {self.get_available_products()}
            
            Return JSON format:
            {{
                "items": [
                    {{"product_name": "Red Onions", "quantity": 5, "unit": "kg"}},
                    {{"product_name": "Tomatoes", "quantity": 3, "unit": "kg"}}
                ],
                "confidence": 0.95,
                "notes": "Interpreted '1 x onions' as 5kg Red Onions based on typical restaurant order"
            }}
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            parsed_data = json.loads(response.choices[0].message.content)
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Error parsing message: {str(e)}")
            return None
    
    def get_available_products(self):
        """Get list of available products from Django API"""
        try:
            response = requests.get(f"{self.api_base}/products/")
            if response.status_code == 200:
                products = response.json()
                return [p['name'] for p in products['results']]
        except Exception as e:
            self.logger.error(f"Error getting products: {str(e)}")
        return []
    
    def create_order_from_message(self, message, parsed_order):
        """Create Django order from parsed WhatsApp message"""
        try:
            # Create order via API
            order_data = {
                'restaurant_name': message['sender'],
                'source': 'whatsapp',
                'original_message': message['text'],
                'parsed_data': parsed_order,
                'items': parsed_order['items']
            }
            
            response = requests.post(
                f"{self.api_base}/orders/create-from-whatsapp/",
                json=order_data
            )
            
            if response.status_code == 201:
                return response.json()
            
        except Exception as e:
            self.logger.error(f"Error creating order: {str(e)}")
        return None
    
    def generate_purchase_order(self, order):
        """Generate purchase order for sales rep"""
        try:
            po_data = {
                'order_id': order['id'],
                'sales_rep': self.assign_sales_rep(order),
                'items': order['items']
            }
            
            response = requests.post(
                f"{self.api_base}/procurement/generate-po-from-order/",
                json=po_data
            )
            
            if response.status_code == 201:
                return response.json()
                
        except Exception as e:
            self.logger.error(f"Error generating PO: {str(e)}")
        return None
    
    def assign_sales_rep(self, order):
        """Assign appropriate sales rep based on order contents"""
        # Simple round-robin or product-based assignment
        # Can be enhanced with more sophisticated logic
        return "rep1"  # Simplified
    
    def send_po_to_sales_rep(self, po):
        """Send purchase order to sales rep via WhatsApp"""
        try:
            sales_rep = po['sales_rep']
            rep_phone = self.sales_rep_contacts[sales_rep]
            
            # Format PO message
            po_message = self.format_po_message(po)
            
            # Send via WhatsApp
            if self.send_whatsapp_message(rep_phone, po_message):
                self.logger.info(f"PO sent to {sales_rep}: {po['po_number']}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error sending PO: {str(e)}")
        return False
    
    def format_po_message(self, po):
        """Format purchase order for WhatsApp message"""
        message = f"""
🛒 *Purchase Order: {po['po_number']}*

📅 Date: {po['created_at']}
🏪 Customer: {po['customer_name']}

📦 *Items Needed:*
"""
        
        for item in po['items']:
            message += f"• {item['product_name']}: {item['quantity']}{item['unit']}\n"
        
        message += f"""
💰 Budget: R{po['estimated_total']}
⏰ Needed by: {po['delivery_date']}

Please confirm availability and pricing.
Reply with: CONFIRM {po['po_number']} [your response]
        """
        
        return message
    
    def send_whatsapp_message(self, phone_number, message):
        """Send message to specific WhatsApp contact"""
        try:
            # Open chat with phone number
            self.driver.get(f"https://web.whatsapp.com/send?phone={phone_number}")
            time.sleep(3)
            
            # Wait for chat to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='msg-input']"))
            )
            
            # Type and send message
            message_box = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='msg-input']")
            message_box.send_keys(message)
            
            send_button = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='send']")
            send_button.click()
            
            time.sleep(2)
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()

# Main execution
if __name__ == "__main__":
    manager = WhatsAppManager()
    
    try:
        manager.monitor_restaurant_orders()
    except KeyboardInterrupt:
        print("\nShutting down WhatsApp automation...")
    finally:
        manager.cleanup()
```

---

## 🔧 **Configuration & Setup**

### **Requirements: `requirements.txt`**
```
selenium==4.15.0
webdriver-manager==4.0.1
openai==1.3.0
requests==2.31.0
django==5.0.9
python-decouple==3.8
```

### **Configuration: `config.py`**
```python
import os
from decouple import config

# WhatsApp Settings
WHATSAPP_SESSION_PATH = config('WHATSAPP_SESSION_PATH', default='./whatsapp_session')
RESTAURANT_GROUP_NAME = config('RESTAURANT_GROUP_NAME', default='Fambri Farms - Restaurant Orders')

# Sales Rep Contacts
SALES_REP_1_PHONE = config('SALES_REP_1_PHONE')
SALES_REP_2_PHONE = config('SALES_REP_2_PHONE')

# API Settings
DJANGO_API_BASE = config('DJANGO_API_BASE', default='https://fambridevops.pythonanywhere.com/api')
API_TOKEN = config('API_TOKEN')

# OpenAI Settings
OPENAI_API_KEY = config('OPENAI_API_KEY')

# Monitoring Settings
MESSAGE_CHECK_INTERVAL = config('MESSAGE_CHECK_INTERVAL', default=30, cast=int)
MAX_MESSAGES_PER_CHECK = config('MAX_MESSAGES_PER_CHECK', default=10, cast=int)
```

### **Environment Variables: `.env`**
```env
# WhatsApp Automation Settings
WHATSAPP_SESSION_PATH=./whatsapp_session
RESTAURANT_GROUP_NAME=Fambri Farms - Restaurant Orders
SALES_REP_1_PHONE=+27123456789
SALES_REP_2_PHONE=+27987654321

# API Configuration
DJANGO_API_BASE=https://fambridevops.pythonanywhere.com/api
API_TOKEN=your-api-token-here

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Monitoring Configuration
MESSAGE_CHECK_INTERVAL=30
MAX_MESSAGES_PER_CHECK=10
```

---

## 🚀 **Deployment & Running**

### **Installation Steps**
```bash
# 1. Clone repository
git clone https://github.com/JBeggs/fambrifarms-backend.git
cd fambrifarms-backend

# 2. Create automation directory
mkdir whatsapp_automation
cd whatsapp_automation

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Chrome WebDriver
# Download ChromeDriver from https://chromedriver.chromium.org/
# Or use webdriver-manager (included in requirements)

# 5. Configure environment
cp .env.example .env
nano .env  # Add your API keys and phone numbers

# 6. First run (QR code scan)
python whatsapp_manager.py
```

### **Running as Service**
```bash
# Create systemd service file
sudo nano /etc/systemd/system/whatsapp-automation.service
```

```ini
[Unit]
Description=Fambri Farms WhatsApp Automation
After=network.target

[Service]
Type=simple
User=fambridevops
WorkingDirectory=/home/fambridevops/whatsapp_automation
ExecStart=/home/fambridevops/venv/bin/python whatsapp_manager.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable whatsapp-automation
sudo systemctl start whatsapp-automation
sudo systemctl status whatsapp-automation
```

---

## 📊 **Monitoring & Logging**

### **Log Files**
- `whatsapp_automation.log` - Main application log
- `message_processing.log` - Order parsing details
- `sales_rep_communication.log` - PO sending/receiving

### **Health Checks**
```python
def health_check():
    """Check if automation is running properly"""
    checks = {
        'whatsapp_connected': check_whatsapp_connection(),
        'django_api_accessible': check_django_api(),
        'openai_api_working': check_openai_api(),
        'last_message_processed': get_last_message_time()
    }
    return checks
```

### **Error Handling**
- **Connection Loss**: Auto-reconnect to WhatsApp Web
- **API Failures**: Retry with exponential backoff
- **Parsing Errors**: Log and flag for manual review
- **Message Duplication**: Track processed messages

---

## 🔒 **Security Considerations**

### **Authentication**
- **WhatsApp Session**: Secure session storage
- **API Tokens**: Encrypted environment variables
- **Phone Numbers**: Validated and sanitized

### **Data Protection**
- **Message Encryption**: End-to-end encrypted storage
- **PII Handling**: Anonymize customer data where possible
- **Audit Logging**: Complete trail of all actions

### **Access Control**
- **Script Permissions**: Limited system access
- **API Endpoints**: Authenticated requests only
- **File Permissions**: Restricted session and log files

---

## 🧪 **Testing Strategy**

### **Unit Tests**
```python
def test_message_parsing():
    """Test AI message parsing accuracy"""
    test_messages = [
        "1 x onions, 2 x tomatoes",
        "Need 5kg potatoes for tomorrow",
        "Can I get some lettuce and carrots?"
    ]
    # Test parsing accuracy
```

### **Integration Tests**
- **WhatsApp Connection**: Automated browser testing
- **API Integration**: Django endpoint testing
- **End-to-End**: Full order processing workflow

### **Performance Tests**
- **Message Processing Speed**: Target <5 seconds per message
- **Concurrent Handling**: Multiple messages simultaneously
- **Memory Usage**: Monitor for memory leaks

---

This WhatsApp automation system provides the technical foundation for seamless order processing while maintaining the familiar WhatsApp interface that users prefer. The system is designed to be robust, scalable, and easily maintainable.

"""
Company Extractor - Preserved from original WhatsApp processing system
Handles company name extraction and alias mapping with real customer data
"""

import re
from typing import Optional, Dict, List
from django.conf import settings


class CompanyExtractor:
    """
    Extract and normalize company names from WhatsApp messages
    Preserves all original business logic and customer mappings
    """
    
    def __init__(self):
        self.company_aliases = self._load_company_aliases()
        
    def _load_company_aliases(self) -> Dict[str, str]:
        """
        Load company aliases mapping - PRESERVED from original system
        Enhanced with real customer data from seeded database + dynamic database companies
        """
        # PRESERVED: All original company aliases with enhancements
        hardcoded_aliases = {
            # Restaurant customers from seeded data
            "mugg and bean": "Mugg and Bean",
            "mugg bean": "Mugg and Bean", 
            "mugg": "Mugg and Bean",
            "maltos": "Maltos",
            "valley": "Valley",
            "order valley": "Valley",  # Common variation
            "barchef": "Barchef Entertainment",
            "barchef entertainment": "Barchef Entertainment",
            "casa bella": "Casa Bella",
            "casabella": "Casa Bella",
            "debonairs": "Debonairs Pizza",
            "debonair": "Debonairs Pizza",
            "debonair pizza": "Debonairs Pizza",
            "wimpy": "Wimpy Mooikloof",
            "wimpy mooikloof": "Wimpy Mooikloof",
            "wimpy mooinooi": "Wimpy Mooikloof",  # Common misspelling - PRESERVED
            "t-junction": "T-junction",
            "t junction": "T-junction",
            "tjunction": "T-junction",
            "venue": "Venue",
            "revue": "Revue Bar",
            "revue bar": "Revue Bar",
            
            # Hospitality & Institutions
            "pecanwood": "Pecanwood Golf Estate",
            "pecanwood golf": "Pecanwood Golf Estate",
            "culinary": "Culinary Institute",
            "culinary institute": "Culinary Institute",
            
            # Private customers
            "marco": "Marco",
            "sylvia": "Sylvia",
            "arthur": "Arthur",
            
            # Internal/Stock
            "shallome": "SHALLOME",
            "hazvinei": "SHALLOME",  # Stock taker name - PRESERVED
            
            # Legacy aliases (for backward compatibility) - PRESERVED
            "luma": "Luma",
            "shebeen": "Shebeen"
        }
        
        # DYNAMIC: Load companies from database
        try:
            from accounts.models import RestaurantProfile, PrivateCustomerProfile
            
            # Add restaurant profiles
            restaurant_profiles = RestaurantProfile.objects.all()
            for profile in restaurant_profiles:
                business_name = profile.business_name.strip()
                if business_name:
                    # Add exact match
                    hardcoded_aliases[business_name.lower()] = business_name
                    
                    # Add branch variation if exists
                    if profile.branch_name:
                        full_name = f"{business_name} - {profile.branch_name}".strip()
                        hardcoded_aliases[full_name.lower()] = full_name
                        hardcoded_aliases[profile.branch_name.lower()] = full_name
                    
                    # Add common variations (first word, without common suffixes)
                    first_word = business_name.split()[0].lower()
                    if len(first_word) > 2:  # Avoid very short words
                        hardcoded_aliases[first_word] = business_name
            
            # Add private customer profiles  
            private_profiles = PrivateCustomerProfile.objects.select_related('user').all()
            for profile in private_profiles:
                if hasattr(profile.user, 'first_name') and profile.user.first_name:
                    customer_name = profile.user.first_name.strip()
                    if customer_name:
                        hardcoded_aliases[customer_name.lower()] = customer_name
                
                if hasattr(profile.user, 'last_name') and profile.user.last_name:
                    last_name = profile.user.last_name.strip()
                    if last_name and hasattr(profile.user, 'first_name') and profile.user.first_name:
                        full_name = f"{profile.user.first_name} {last_name}".strip()
                        hardcoded_aliases[full_name.lower()] = full_name
                        
        except Exception as e:
            print(f"⚠️ [COMPANY_EXTRACTOR] Error loading database companies: {e}")
            # Continue with hardcoded aliases if database loading fails
        
        return hardcoded_aliases
    
    def extract_company(self, text: str) -> Optional[str]:
        """
        Extract company name from message text
        PRESERVED: Original logic with enhancements + timestamp cleaning
        """
        if not text:
            return None
            
        # Clean and normalize text
        text_clean = text.strip()
        
        # ENHANCED: Remove timestamps from end of text (e.g., "10:15", "14:30")
        text_clean = self._remove_timestamps(text_clean)
        
        text_lower = text_clean.lower()
        
        # PRESERVED: Direct alias match (highest priority)
        if text_lower in self.company_aliases:
            return self.company_aliases[text_lower]
        
        # PRESERVED: Partial match logic
        for alias, canonical in self.company_aliases.items():
            if self._is_partial_match(alias, text_lower):
                return canonical
        
        # PRESERVED: Multi-line company extraction
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for line in lines:
            line_lower = line.lower()
            
            # Check each line for company matches
            if line_lower in self.company_aliases:
                return self.company_aliases[line_lower]
            
            # Partial match on individual lines
            for alias, canonical in self.company_aliases.items():
                if self._is_partial_match(alias, line_lower):
                    return canonical
        
        # ENHANCED: Check for company-like patterns
        company_candidate = self._extract_company_candidate(text_clean)
        if company_candidate:
            return company_candidate
            
        return None
    
    def _is_partial_match(self, alias: str, text: str) -> bool:
        """
        PRESERVED: Partial matching logic from original system
        Handles flexible company name recognition
        """
        # Exact substring match
        if alias in text or text in alias:
            return True
        
        # Word boundary matching for better accuracy
        alias_words = alias.split()
        text_words = text.split()
        
        # Check if all alias words are present in text
        if len(alias_words) > 1:
            alias_word_matches = sum(1 for word in alias_words if word in text_words)
            if alias_word_matches >= len(alias_words) * 0.8:  # 80% word match threshold
                return True
        
        return False
    
    def _remove_timestamps(self, text: str) -> str:
        """
        Remove timestamps from text that interfere with company extraction
        Handles patterns like: "10:15", "14:30", "9:45" at end of text
        """
        # Remove timestamps at the end of text (most common case)
        # Pattern: digits:digits at end of string, optionally preceded by whitespace
        text = re.sub(r'\s*\d{1,2}:\d{2}\s*$', '', text)
        
        # Remove timestamps at the end of individual lines
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove timestamp from end of each line
            cleaned_line = re.sub(r'\s*\d{1,2}:\d{2}\s*$', '', line)
            if cleaned_line.strip():  # Only keep non-empty lines
                cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)
    
    def _extract_company_candidate(self, text: str) -> Optional[str]:
        """
        ENHANCED: Extract potential company names from unrecognized text
        Looks for company-like patterns for future learning
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Collect potential company candidates, skip generic terms
        candidates = []
        
        for line in lines:
            # Skip lines that look like order items
            if self._looks_like_order_item(line):
                continue
            
            # Skip lines that look like instructions
            if self._looks_like_instruction(line):
                continue
            
            # Skip generic terms that aren't actual company names
            if self._is_generic_term(line):
                continue
            
            # Check if line could be a company name
            if self._looks_like_company_name(line):
                candidates.append(line.title())  # Capitalize for consistency
        
        # Return the first non-generic candidate
        return candidates[0] if candidates else None
    
    def _looks_like_order_item(self, line: str) -> bool:
        """Check if line looks like an order item rather than company name"""
        line_upper = line.upper()
        
        # PRESERVED: Quantity indicators from original system
        quantity_patterns = [
            r'\d+\s*KG', r'\d+\s*X', r'X\d+', r'\d+\s*BOX', r'\d+\s*HEADS',
            r'\d+\s*BUNCHES', r'\d+\s*PCS', r'\d+\s*PIECES'
        ]
        
        for pattern in quantity_patterns:
            if re.search(pattern, line_upper):
                return True
        
        # Common vegetable/product keywords
        product_keywords = [
            'CARROT', 'LETTUCE', 'ONION', 'POTATO', 'TOMATO', 'CABBAGE',
            'SPINACH', 'BEETROOT', 'CUCUMBER', 'PEPPER', 'BROCCOLI'
        ]
        
        for keyword in product_keywords:
            if keyword in line_upper:
                return True
                
        return False
    
    def _is_generic_term(self, line: str) -> bool:
        """Check if line is a generic term rather than actual company name"""
        line_lower = line.lower().strip()
        
        # Generic terms that appear in messages but aren't company names
        generic_terms = [
            'new customer',
            'customer',
            'order',
            'good morning',
            'good afternoon', 
            'good evening',
            'hi all',
            'hello',
            'please',
            'thank you',
            'thanks',
            'order for tomorrow',
            'order for today',
            'morning order',
            'afternoon order',
            'delivery',
            'urgent',
            'asap'
        ]
        
        # Check exact matches
        if line_lower in generic_terms:
            return True
        
        # Check if line starts with generic terms
        for term in generic_terms:
            if line_lower.startswith(term):
                return True
        
        return False
    
    def _looks_like_instruction(self, line: str) -> bool:
        """Check if line looks like an instruction rather than company name"""
        line_upper = line.upper()
        
        # PRESERVED: Instruction keywords from original system
        instruction_keywords = [
            'GOOD MORNING', 'HELLO', 'HI', 'THANKS', 'PLEASE', 'NOTE',
            'REMEMBER', 'SEPARATE INVOICE', 'THAT\'S ALL', 'TNX', 'CHEERS'
        ]
        
        for keyword in instruction_keywords:
            if keyword in line_upper:
                return True
                
        return False
    
    def _looks_like_company_name(self, line: str) -> bool:
        """Check if line could plausibly be a company name"""
        # Skip very short or very long lines
        if len(line.strip()) < 2 or len(line.strip()) > 50:
            return False
        
        # Skip lines with too many numbers (likely order items)
        digit_count = sum(1 for char in line if char.isdigit())
        if digit_count > len(line) * 0.3:  # More than 30% digits
            return False
        
        # Must contain at least one letter
        if not any(char.isalpha() for char in line):
            return False
        
        # Looks reasonable as a company name
        return True
    
    def get_all_known_companies(self) -> List[str]:
        """Get list of all known canonical company names"""
        return list(set(self.company_aliases.values()))
    
    def add_company_alias(self, alias: str, canonical: str) -> None:
        """
        Add new company alias (for learning/adaptation)
        This allows the system to learn new customer variations
        """
        self.company_aliases[alias.lower()] = canonical
        print(f"[CompanyExtractor] Added new alias: '{alias}' → '{canonical}'")
    
    def get_extraction_stats(self) -> Dict[str, int]:
        """Get statistics about company extraction"""
        return {
            'total_aliases': len(self.company_aliases),
            'unique_companies': len(set(self.company_aliases.values())),
            'restaurant_customers': len([c for c in self.company_aliases.values() 
                                       if c in ['Mugg and Bean', 'Maltos', 'Valley', 'Debonairs Pizza']]),
            'private_customers': len([c for c in self.company_aliases.values() 
                                    if c in ['Marco', 'Sylvia', 'Arthur']])
        }


# Singleton instance for efficient reuse
_company_extractor_instance = None

def get_company_extractor() -> CompanyExtractor:
    """Get singleton CompanyExtractor instance"""
    global _company_extractor_instance
    if _company_extractor_instance is None:
        _company_extractor_instance = CompanyExtractor()
    return _company_extractor_instance


import re
import logging

logger = logging.getLogger(__name__)

def clean_emoji_for_mysql(text):
    """
    Remove or replace 4-byte UTF-8 characters (emojis) that cause MySQL encoding issues.
    This is a temporary fix until the database charset is properly configured.
    """
    if not text:
        return text
    
    try:
        # Remove 4-byte UTF-8 characters (emojis)
        # This regex matches characters outside the Basic Multilingual Plane
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"
            "]+", 
            flags=re.UNICODE
        )
        
        # Replace emojis with a placeholder or remove them
        cleaned_text = emoji_pattern.sub('[emoji]', text)
        
        # Also handle other 4-byte characters
        cleaned_text = cleaned_text.encode('utf-8', errors='ignore').decode('utf-8')
        
        if cleaned_text != text:
            logger.warning(f"Cleaned emojis from text: {len(text)} -> {len(cleaned_text)} chars")
        
        return cleaned_text
        
    except Exception as e:
        logger.error(f"Error cleaning emojis: {e}")
        # Fallback: encode/decode to remove problematic characters
        try:
            return text.encode('utf-8', errors='ignore').decode('utf-8')
        except:
            return text


def safe_html_content(html_content):
    """
    Safely process HTML content to avoid MySQL encoding issues.
    """
    if not html_content:
        return html_content
    
    try:
        # Clean emojis that cause encoding issues
        cleaned_html = clean_emoji_for_mysql(html_content)
        
        # Additional safety: ensure the content is not too long
        max_length = 65535  # TEXT field limit in MySQL
        if len(cleaned_html) > max_length:
            cleaned_html = cleaned_html[:max_length] + "... [truncated]"
            logger.warning(f"Truncated HTML content from {len(html_content)} to {len(cleaned_html)} chars")
        
        return cleaned_html
        
    except Exception as e:
        logger.error(f"Error processing HTML content: {e}")
        return html_content[:1000] + "... [error processing]" if len(html_content) > 1000 else html_content

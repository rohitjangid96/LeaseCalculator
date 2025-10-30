"""
AI-Assisted Lease Data Extraction using Google Gemini API
Extracts lease information from text using AI
"""

import json
import re
import os
from typing import Dict, Optional
from datetime import datetime

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


# Configuration
MAX_TEXT_LENGTH = 80000  # Limit text length for AI processing


def extract_lease_info_from_text(text: str, api_key: Optional[str] = None) -> Dict:
    """
    Extract lease information from text using Google Gemini AI
    
    Args:
        text: Extracted text from PDF
        api_key: Google Gemini API key (if None, tries env var)
        
    Returns:
        Dictionary with extracted lease fields
    """
    if not HAS_GEMINI:
        return {"error": "Google Gemini API not installed. Install with: pip install google-generativeai"}
    
    if not api_key:
        api_key = os.getenv('GOOGLE_AI_API_KEY')
    
    if not api_key:
        return {"error": "Google Gemini API key not provided"}
    
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # List models and print them for debugging
        try:
            models = list(genai.list_models())
            print('Available Gemini models:')
            for m in models:
                print(f'- {m.name}')
        except Exception as e:
            print(f'Could not list models: {e}')
            models = []

        # Official model names to try, in recommended order (updated for Gemini 2.x API)
        model_names = [
            'models/gemini-2.5-flash',      # Latest stable Flash model
            'models/gemini-2.0-flash',      # Stable Flash model
            'models/gemini-2.5-pro',        # Latest stable Pro model
            'models/gemini-2.0-flash-001',  # Flash 001 variant
            'models/gemini-flash-latest',   # Latest flash (fallback)
        ]
        model = None
        model_success = None
        errors = {}
        for model_name in model_names:
            try:
                print(f'Trying Gemini model: {model_name}')
                m = genai.GenerativeModel(model_name)
                _ = m.generate_content('test')  # dummy call
                print(f'✅ Successfully using: {model_name}')
                model = m
                model_success = model_name
                break
            except Exception as e:
                print(f'❌ {model_name} failed: {e}')
                errors[model_name] = str(e)
        if not model:
            return {
                'error': 'No valid Gemini model found for your API key. See model list.',
                'model_attempts': model_names,
                'errors': errors,
                'available_models': [m.name for m in models],
            }
        
        # Truncate text if too long
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH]
        
        # Create extraction prompt
        prompt = _create_extraction_prompt(text)
        
        # Generate response
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Parse JSON from response
        return _parse_ai_response(response_text)
        
    except Exception as e:
        return {"error": f"AI extraction failed: {str(e)}"}


def _create_extraction_prompt(text: str) -> str:
    """Create the AI prompt for extracting lease information"""
    return f"""Extract lease information from this document and return ONLY a JSON object with the following fields:

{{
  "description": "lease description or title (string)",
  "asset_class": "asset category/type (string)",
  "asset_id_code": "asset identifier/code (string or null)",
  "lease_start_date": "start date in YYYY-MM-DD format (string or null)",
  "end_date": "end date in YYYY-MM-DD format (string or null)",
  "agreement_date": "agreement date in YYYY-MM-DD format (string or null)",
  "termination_date": "termination date in YYYY-MM-DD format (string or null)",
  "first_payment_date": "first payment date in YYYY-MM-DD format (string or null)",
  "tenure": "lease term in months (integer or null)",
  "frequency_months": "payment frequency in months (integer, default 1)",
  "day_of_month": "payment day of month (string, default '1')",
  "rental_1": "first rental amount (number or null)",
  "rental_2": "second rental amount (number or null)",
  "currency": "currency code like USD, INR (string or null)",
  "borrowing_rate": "interest rate as percentage (number or null)",
  "compound_months": "compounding frequency in months (integer, default 12)",
  "security_deposit": "security deposit amount (number or null)",
  "esc_freq_months": "escalation frequency in months (integer or null)",
  "escalation_percent": "escalation percentage (number or null)",
  "escalation_start_date": "escalation start date in YYYY-MM-DD format (string or null)",
  "lease_incentive": "lease incentive amount (number or null)",
  "initial_direct_expenditure": "initial direct costs (number or null)",
  "finance_lease": "Yes or No (string, default 'No')",
  "sublease": "Yes or No (string, default 'No')",
  "bargain_purchase": "Yes or No (string, default 'No')",
  "title_transfer": "Yes or No (string, default 'No')",
  "practical_expedient": "Yes or No (string, default 'No')",
  "short_term_ifrs": "Yes or No (string, default 'No')",
  "manual_adj": "Yes or No (string, default 'No')",
  "additional_info": "any extra information (string or null)"
}}

Document Text:
{text}

Important: Return ONLY the JSON object, no explanation or markdown formatting."""


def _parse_ai_response(response_text: str) -> Dict:
    """Parse AI response and extract JSON"""
    try:
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without markdown
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text
        
        # Parse JSON
        extracted_data = json.loads(json_str)
        
        # Validate and clean up the data
        return _clean_extracted_data(extracted_data)
        
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse AI response as JSON: {e}", "raw_response": response_text}
    except Exception as e:
        return {"error": f"Failed to process AI response: {e}"}


def _clean_extracted_data(data: Dict) -> Dict:
    """Clean and validate extracted data"""
    cleaned = {}
    
    # String fields
    string_fields = [
        'description', 'asset_class', 'asset_id_code', 'currency', 'day_of_month',
        'finance_lease', 'sublease', 'bargain_purchase', 'title_transfer',
        'practical_expedient', 'short_term_ifrs', 'manual_adj', 'additional_info'
    ]
    
    for field in string_fields:
        value = data.get(field)
        if isinstance(value, str) and value.strip():
            cleaned[field] = value.strip()
        elif field in ['finance_lease', 'sublease', 'bargain_purchase', 'title_transfer',
                       'practical_expedient', 'short_term_ifrs', 'manual_adj']:
            # Ensure Yes/No fields have proper values
            cleaned[field] = 'Yes' if str(value).lower() in ['yes', 'true', '1', 'on'] else 'No'
        else:
            cleaned[field] = None
    
    # Number fields
    number_fields = [
        'tenure', 'frequency_months', 'rental_1', 'rental_2', 'borrowing_rate',
        'compound_months', 'security_deposit', 'esc_freq_months', 'escalation_percent',
        'lease_incentive', 'initial_direct_expenditure'
    ]
    
    for field in number_fields:
        value = data.get(field)
        try:
            if value is not None:
                cleaned[field] = float(value)
            else:
                cleaned[field] = None
        except (ValueError, TypeError):
            cleaned[field] = None
    
    # Date fields
    date_fields = [
        'lease_start_date', 'end_date', 'agreement_date', 'termination_date',
        'first_payment_date', 'escalation_start_date'
    ]
    
    for field in date_fields:
        value = data.get(field)
        if value:
            cleaned[field] = _parse_date_field(value)
        else:
            cleaned[field] = None
    
    return cleaned


def _parse_date_field(value) -> Optional[str]:
    """Parse date field to YYYY-MM-DD format"""
    if not value:
        return None
    
    # Try various date formats
    date_formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%m-%d-%Y',
        '%d-%m-%Y',
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(str(value).strip(), fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None


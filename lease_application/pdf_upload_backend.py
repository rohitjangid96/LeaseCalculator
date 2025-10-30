"""
PDF Upload and AI Extraction Backend
Handles PDF upload and AI-assisted data extraction
"""

from flask import Blueprint, request, jsonify
import os
import tempfile
import logging
from pathlib import Path

try:
    from lease_accounting.utils.pdf_extractor import extract_text_from_pdf, has_selectable_text
    from lease_accounting.utils.ai_extractor import extract_lease_info_from_text, HAS_GEMINI
except ImportError as e:
    print(f"Warning: AI extraction modules not fully available: {e}")
    HAS_GEMINI = False

# Create blueprint
pdf_bp = Blueprint('pdf', __name__, url_prefix='/api')

logger = logging.getLogger(__name__)


@pdf_bp.route('/extract_lease_pdf', methods=['POST'])
def extract_lease_pdf():
    """
    Extract lease data from uploaded PDF using AI
    
    Expected request:
    - PDF file upload
    - Optional: Google AI API key (or use env var)
    
    Returns:
    - Extracted lease fields if successful
    - Error message if failed
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Check if it's a PDF
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                'success': False,
                'error': 'File must be a PDF'
            }), 400
        
        # Get API key from request or environment
        api_key = request.form.get('api_key') or os.getenv('GOOGLE_AI_API_KEY')
        
        if not api_key and HAS_GEMINI:
            return jsonify({
                'success': False,
                'error': 'Google AI API key required. Set GOOGLE_AI_API_KEY environment variable or provide in request.',
                'help': 'Get your free API key at: https://makersuite.google.com/app/apikey'
            }), 400
        
        if not HAS_GEMINI:
            return jsonify({
                'success': False,
                'error': 'Google Gemini AI not installed',
                'install_instructions': 'Install with: pip install google-generativeai'
            }), 400
        
        # Save uploaded file temporarily
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"upload_{file.filename}")
        
        try:
            file.save(temp_path)
            
            # Extract text from PDF
            logger.info(f"📄 Extracting text from PDF: {file.filename}")
            text, status_msg = extract_text_from_pdf(temp_path)
            
            if not text:
                return jsonify({
                    'success': False,
                    'error': status_msg or 'Failed to extract text from PDF'
                }), 400
            
            logger.info(f"✅ Extracted {len(text)} characters from PDF")
            
            # Extract lease info using AI
            logger.info("🤖 Extracting lease information using AI...")
            extracted_data = extract_lease_info_from_text(text, api_key)
            
            # Log any extra debug info from extraction
            if 'model_attempts' in extracted_data:
                logger.error(f"Model attempts: {extracted_data.get('model_attempts')}")
                logger.error(f"Available models: {extracted_data.get('available_models')}")
                logger.error(f"Errors: {extracted_data.get('errors')}")
            
            if 'error' in extracted_data:
                return jsonify({
                    'success': False,
                    'error': extracted_data['error'],
                    'extracted_text_length': len(text),
                    'has_api_key': bool(api_key),
                    'debug_info': {
                        'model_attempts': extracted_data.get('model_attempts'),
                        'available_models': extracted_data.get('available_models'),
                        'errors': extracted_data.get('errors')
                    }
                }), 400
            
            logger.info(f"✅ AI extraction successful: {len(extracted_data)} fields extracted")
            
            return jsonify({
                'success': True,
                'data': extracted_data,
                'metadata': {
                    'filename': file.filename,
                    'text_length': len(text),
                    'extraction_method': 'text-based' if has_selectable_text(temp_path) else 'OCR'
                }
            })
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        logger.error(f"❌ PDF extraction error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }), 500


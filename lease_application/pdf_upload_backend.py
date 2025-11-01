"""
PDF Upload and AI Extraction Backend
Handles PDF upload and AI-assisted data extraction
"""

from flask import Blueprint, request, jsonify, session
import os
import tempfile
import logging
import uuid
import json  # For JSON encoding/decoding
import re  # Add regex for robust text cleaning
from pathlib import Path
from typing import Optional
from werkzeug.utils import secure_filename

try:
    from lease_accounting.utils.pdf_extractor import extract_text_from_pdf, has_selectable_text, find_text_positions, HAS_PYMUPDF
    from lease_accounting.utils.ai_extractor import (
        extract_lease_info_from_text,
        extract_lease_info_from_pdf,
        HAS_GEMINI
    )
    from database import save_extraction_metadata, save_document
except ImportError as e:
    print(f"Warning: AI extraction modules not fully available: {e}")
    HAS_GEMINI = False
    HAS_PYMUPDF = False
    extract_lease_info_from_pdf = None
    extract_lease_info_from_text = None

# File upload directory (same as document_backend)
UPLOAD_FOLDER = 'uploaded_documents'
PENDING_PDF_FOLDER = 'pending_pdfs'  # Temporary storage for PDFs without lease_id
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)
Path(PENDING_PDF_FOLDER).mkdir(exist_ok=True)

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
        
        # Get API key from: request -> database -> environment
        api_key = request.form.get('api_key')
        
        if not api_key:
            # Try database settings
            try:
                from database import get_google_ai_settings
                settings = get_google_ai_settings()
                if settings:
                    api_key = settings.get('api_key')
            except Exception as e:
                logger.warning(f"Could not load Google AI settings from database: {e}")
        
        if not api_key:
            # Try environment variable
            api_key = os.getenv('GOOGLE_AI_API_KEY')
        
        # Check if Gemini is available (try to use extract_lease_info_from_pdf if available)
        gemini_available = HAS_GEMINI or extract_lease_info_from_pdf is not None
        
        if not api_key and gemini_available:
            return jsonify({
                'success': False,
                'error': 'Google AI API key required. Configure in Admin Settings.',
                'help': 'Get your free API key at: https://makersuite.google.com/app/apikey'
            }), 400
        
        # Only return error if both Gemini is not available AND extract_lease_info_from_text also won't work
        # This allows fallback to text-based extraction even if PDF extraction isn't available
        if not gemini_available and extract_lease_info_from_text is None:
            return jsonify({
                'success': False,
                'error': 'Google Gemini AI not installed',
                'install_instructions': 'Install with: pip install google-generativeai'
            }), 400
        
        # Save uploaded file temporarily
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"upload_{file.filename}")
        
        # Initialize variables before use (for finally block)
        lease_id = None
        saved_doc_id = None
        pending_pdf_id = None
        
        try:
            file.save(temp_path)
            
            # Extract text from PDF
            logger.info(f"📄 Extracting text from PDF: {file.filename}")
            try:
                result = extract_text_from_pdf(temp_path)
                if isinstance(result, tuple):
                    text, status_msg = result
                else:
                    text = result
                    status_msg = ""
                logger.info(f"📄 Text extraction result: status_msg={status_msg}, text_length={len(text) if text else 0}")
            except Exception as e:
                logger.error(f"❌ Error extracting text from PDF: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': f'Failed to extract text from PDF: {str(e)}',
                    'status': 'extraction_error'
                }), 400
            
            if not text:
                logger.warning(f"⚠️ No text extracted from PDF: {status_msg}")
                return jsonify({
                    'success': False,
                    'error': status_msg or 'Failed to extract text from PDF. The PDF may be scanned or password-protected.',
                    'status': 'no_text_extracted',
                    'status_msg': status_msg
                }), 400
            
            logger.info(f"✅ Extracted {len(text)} characters from PDF")
            
            # Extract lease info using AI
            # Use text-based extraction first (more reliable), then enhance with PDF extraction if available
            logger.info("🤖 Extracting lease information using AI...")
            try:
                # Start with text-based extraction (more reliable, was working before)
                if extract_lease_info_from_text is not None:
                    logger.info("   - Using text-based extraction (reliable method)")
                    extracted_data = extract_lease_info_from_text(text, api_key)
                    
                    # Check if text extraction succeeded
                    if 'error' in extracted_data:
                        raise Exception(extracted_data.get('error', 'Text extraction failed'))
                    
                    logger.info(f"✅ Text extraction successful: {len([k for k in extracted_data.keys() if k != '_metadata'])} fields extracted")
                    
                    # Try to enhance with PDF extraction for bounding boxes (optional, doesn't block if fails)
                    if extract_lease_info_from_pdf is not None:
                        try:
                            logger.info("   - Attempting PDF extraction for bounding boxes (optional enhancement)")
                            pdf_extracted_data = extract_lease_info_from_pdf(temp_path, api_key)
                            
                            # If PDF extraction succeeded and has metadata, merge it
                            if 'error' not in pdf_extracted_data and '_metadata' in pdf_extracted_data:
                                extracted_data['_metadata'] = pdf_extracted_data['_metadata']
                                logger.info("   - ✅ PDF bounding boxes added to extraction")
                            else:
                                logger.debug("   - PDF extraction didn't provide metadata, continuing with text extraction")
                        except Exception as pdf_error:
                            logger.debug(f"   - PDF extraction failed (non-critical): {pdf_error}")
                            # Continue with text extraction - PDF extraction is optional
                else:
                    # Neither extraction method available
                    raise Exception("Neither PDF nor text-based extraction is available. Please install google-generativeai.")
                
                logger.info("🤖 AI extraction completed")
            except Exception as ai_error:
                logger.error(f"❌ AI extraction failed: {ai_error}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': f'AI extraction failed: {str(ai_error)}',
                    'extracted_text_length': len(text),
                    'has_api_key': bool(api_key)
                }), 500
            
            # Validate extracted_data is a dict
            if not isinstance(extracted_data, dict):
                logger.error(f"❌ AI extraction returned invalid data type: {type(extracted_data)}")
                return jsonify({
                    'success': False,
                    'error': 'AI extraction returned invalid data',
                    'extracted_text_length': len(text),
                    'has_api_key': bool(api_key)
                }), 500
            
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
            
            # Get lease_id and user_id if provided
            lease_id_str = request.form.get('lease_id')
            user_id = session.get('user_id')  # Get from session if available
            
            logger.info(f"📋 PDF Upload Debug:")
            logger.info(f"   - lease_id from form: {lease_id_str}")
            logger.info(f"   - user_id from session: {user_id}")
            logger.info(f"   - filename: {file.filename}")
            
            # If lease_id is provided, save the PDF permanently to documents table
            
            if lease_id_str:
                try:
                    lease_id = int(lease_id_str)
                    logger.info(f"   - Processing lease_id: {lease_id}")
                    
                    # Save extraction metadata with coordinates
                    logger.info(f"   - Saving extraction metadata...")
                    _save_extraction_metadata(lease_id, extracted_data, temp_path)
                    logger.info(f"   - ✅ Extraction metadata saved")
                    
                    # Create highlighted PDF with annotations
                    try:
                        from database import get_extraction_metadata
                        metadata = get_extraction_metadata(lease_id)
                        if metadata:
                            highlighted_pdf_path = create_highlighted_pdf(lease_id, temp_path, metadata)
                            if highlighted_pdf_path:
                                logger.info(f"   - ✅ Highlighted PDF created: {highlighted_pdf_path}")
                    except Exception as e:
                        logger.warning(f"Could not create highlighted PDF: {e}")
                    
                    # Save the PDF to documents table permanently
                    if user_id:
                        logger.info(f"   - User ID found: {user_id}, saving PDF to documents table...")
                        try:
                            saved_doc_id = _save_pdf_document(lease_id, user_id, file, temp_path)
                            logger.info(f"✅ PDF saved to documents table with doc_id: {saved_doc_id}")
                        except Exception as e:
                            logger.error(f"❌ Failed to save PDF to documents table: {e}", exc_info=True)
                            # Continue even if document save fails
                    else:
                        logger.warning(f"   - ⚠️ No user_id in session, cannot save PDF to documents table")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not save PDF/document metadata: {e}", exc_info=True)
            else:
                # No lease_id yet - save PDF temporarily for later association
                if user_id:
                    logger.info(f"   - No lease_id yet, saving PDF temporarily...")
                    try:
                        # Store extraction_data so we can save metadata when lease is created
                        pending_pdf_id = _save_pending_pdf(user_id, file, temp_path, extracted_data)
                        logger.info(f"✅ PDF saved temporarily with pending_id: {pending_pdf_id}")
                    except Exception as e:
                        logger.error(f"❌ Failed to save pending PDF: {e}", exc_info=True)
                else:
                    logger.warning(f"   - ⚠️ No lease_id and no user_id in session, PDF will not be saved")
            
            response_data = {
                'success': True,
                'data': extracted_data,
                'metadata': {
                    'filename': file.filename,
                    'text_length': len(text),
                    'extraction_method': 'text-based' if has_selectable_text(temp_path) else 'OCR'
                }
            }
            
            # Add document ID if PDF was saved
            if saved_doc_id:
                response_data['doc_id'] = saved_doc_id
                response_data['message'] = 'PDF extracted and saved successfully'
                logger.info(f"✅ PDF extraction complete - document saved with doc_id: {saved_doc_id}")
            elif pending_pdf_id:
                # PDF saved temporarily - will be associated when lease is created
                response_data['pending_pdf_id'] = pending_pdf_id
                response_data['message'] = 'PDF extracted and saved temporarily. It will be automatically associated when you save the lease.'
                logger.info(f"✅ PDF extraction complete - PDF saved temporarily with pending_id: {pending_pdf_id}")
            else:
                if not user_id:
                    response_data['warning'] = 'PDF was not saved because user session is missing. Please log in and try again.'
                    logger.warning(f"⚠️ PDF extraction complete but not saved - no user_id in session")
                else:
                    response_data['warning'] = 'PDF was not saved. Please try again.'
                    logger.warning(f"⚠️ PDF extraction complete but not saved - unknown error")
            
            return jsonify(response_data)
            
        finally:
            # Clean up temp file only if it wasn't moved to permanent storage
            # (If saved to documents or pending, the file is already moved)
            try:
                if os.path.exists(temp_path) and not lease_id and not pending_pdf_id:
                    os.remove(temp_path)
            except Exception as cleanup_error:
                logger.warning(f"Could not cleanup temp file: {cleanup_error}")
        
    except Exception as e:
        logger.error(f"❌ PDF extraction error: {e}", exc_info=True)
        # Make sure we always return a response, even on error
        try:
            return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }), 500
        except Exception as response_error:
            logger.error(f"❌ Failed to send error response: {response_error}", exc_info=True)
            # Last resort - return a simple response
            from flask import Response
            return Response(
                '{"success": false, "error": "Internal server error"}',
                status=500,
                mimetype='application/json'
            )


def create_highlighted_pdf(lease_id: int, pdf_path: str, extraction_metadata: list) -> Optional[str]:
    """
    Create a PDF with highlight annotations for all extracted fields using pypdf.
    
    Args:
        lease_id: Lease ID
        pdf_path: Path to original PDF
        extraction_metadata: List of extraction metadata with bounding boxes
        
    Returns:
        Path to highlighted PDF file, or None if failed
    """
    try:
        from pypdf import PdfReader, PdfWriter
        from pathlib import Path
        import shutil
        import json
        
        logger.info(f"📝 Creating highlighted PDF for lease_id={lease_id} using pypdf")
        
        # Open the PDF
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # Colors for different fields (cycle through pypdf color format: R, G, B values 0-255)
        # pypdf uses RGB values as integers 0-255 or floats 0-1
        highlight_colors_rgb = [
            (255, 255, 0),   # Yellow
            (0, 255, 0),     # Green
            (0, 255, 255),   # Cyan
            (255, 0, 255),   # Magenta
        ]
        
        # Process each page and add to writer
        for page_idx, page in enumerate(reader.pages):
            writer.add_page(page)
            
            # Get the page object for the writer (needed for annotation)
            writer_page = writer.pages[page_idx]
            page_height = float(writer_page.mediabox.height)  # CRITICAL: Get page height for conversion
            page_width = float(writer_page.mediabox.width)
            
            # Add highlights for fields matching this page (1-indexed)
            current_page_num = page_idx + 1
            
            for idx, meta in enumerate(extraction_metadata):
                field_name = meta.get('field_name')
                page_number = meta.get('page_number')
                bounding_boxes = meta.get('bounding_boxes', [])

                if page_number != current_page_num or not bounding_boxes:
                    continue
                
                # Ensure bounding_boxes is a list of dicts (parsed from JSON in get_extraction_metadata)
                if isinstance(bounding_boxes, str):
                    bounding_boxes = json.loads(bounding_boxes)
                
                if not isinstance(bounding_boxes, list):
                    bounding_boxes = [bounding_boxes] if bounding_boxes else []
                
                color_rgb = highlight_colors_rgb[idx % len(highlight_colors_rgb)]
                
                # Add highlight annotation for each bounding box
                for bbox in bounding_boxes:
                    if not isinstance(bbox, dict) or 'x' not in bbox:
                        # Try list format: [x0, y0, x1, y1]
                        if isinstance(bbox, list) and len(bbox) >= 4:
                            x_tl = bbox[0]
                            y_tl = bbox[1]
                            width = bbox[2] - bbox[0] if len(bbox) > 2 else 0
                            height = bbox[3] - bbox[1] if len(bbox) > 3 else 0
                        else:
                            continue
                    else:
                        x_tl = bbox.get('x', 0)
                        y_tl = bbox.get('y', 0)
                        width = bbox.get('width', 0)
                        height = bbox.get('height', 0)
                    
                    # --- CRITICAL COORDINATE CONVERSION (Top-Left Origin to Bottom-Left Origin) ---
                    # Bounding box in pypdf (bottom-left origin): (x_bl, y_bl, x_tr, y_tr)
                    
                    x_bl = x_tl
                    # y_bl is the bottom edge, measured from the page's bottom
                    y_bl = page_height - (y_tl + height)
                    
                    x_tr = x_tl + width
                    # y_tr is the top edge, measured from the page's bottom
                    y_tr = page_height - y_tl
                    
                    # Ensure coordinates are within page bounds
                    x_bl = max(0, min(x_bl, page_width))
                    y_bl = max(0, min(y_bl, page_height))
                    x_tr = max(0, min(x_tr, page_width))
                    y_tr = max(0, min(y_tr, page_height))
                    
                    if x_tr <= x_bl or y_tr <= y_bl:
                        continue
                    
                    rect_pypdf = [x_bl, y_bl, x_tr, y_tr]

                    # Add highlight annotation using pypdf's annotation API
                    try:
                        # Try using pypdf's annotation methods (if available)
                        from pypdf.generic import DictionaryObject, ArrayObject
                        
                        # Create annotation dictionary
                        annot_dict = DictionaryObject({
                            '/Type': '/Annot',
                            '/Subtype': '/Highlight',
                            '/Rect': ArrayObject(rect_pypdf),
                            '/QuadPoints': ArrayObject([
                                x_bl, y_tr,  # Top-left
                                x_tr, y_tr,  # Top-right
                                x_bl, y_bl,  # Bottom-left
                                x_tr, y_bl   # Bottom-right
                            ]),
                            '/C': ArrayObject([c / 255.0 for c in color_rgb]),  # Normalize to 0-1
                            '/CA': 0.4,  # Opacity
                            '/Border': ArrayObject([0, 0, 1])  # Border style
                        })
                        
                        # Add annotation to page
                        if '/Annots' not in writer_page:
                            writer_page['/Annots'] = ArrayObject()
                        writer_page['/Annots'].append(annot_dict)
                        
                        logger.info(f"   ✓ Highlighted {field_name} on page {current_page_num}")
                    except Exception as annot_error:
                        logger.warning(f"Could not add highlight annotation for {field_name}: {annot_error}")

        # Save highlighted PDF
        Path(UPLOAD_FOLDER).mkdir(exist_ok=True)
        highlighted_filename = f"highlighted_lease_{lease_id}.pdf"
        highlighted_path = os.path.join(UPLOAD_FOLDER, highlighted_filename)
        
        with open(highlighted_path, "wb") as output_stream:
            writer.write(output_stream)
        
        logger.info(f"✅ Highlighted PDF saved: {highlighted_path}")
        return highlighted_path
        
    except ImportError as e:
        logger.error(f"❌ pypdf not available: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error creating highlighted PDF with pypdf: {e}", exc_info=True)
        return None


def _save_extraction_metadata(lease_id: int, extracted_data: dict, pdf_path: str):
    """
    Save extraction metadata with coordinates for review interface
    
    Args:
        lease_id: Lease ID to associate metadata with
        extracted_data: Dictionary of extracted field values
        pdf_path: Path to PDF file for finding coordinates
    """
    if not HAS_GEMINI:
        return
    
    # Field mapping from extraction keys to database field names
    field_mapping = {
        'description': 'description',
        'asset_class': 'asset_class',
        'asset_id_code': 'asset_id_code',
        'lease_start_date': 'lease_start_date',
        'end_date': 'end_date',
        'agreement_date': 'agreement_date',
        'termination_date': 'termination_date',
        'first_payment_date': 'first_payment_date',
        'tenure': 'tenure',
        'frequency_months': 'frequency_months',
        'day_of_month': 'day_of_month',
        'rental_1': 'rental_1',
        'rental_2': 'rental_2',
        'currency': 'currency',
        'borrowing_rate': 'borrowing_rate',
        'compound_months': 'compound_months',
        'security_deposit': 'security_deposit',
        'esc_freq_months': 'esc_freq_months',
        'escalation_percent': 'escalation_percent',
        'escalation_start_date': 'escalation_start_date',
        'lease_incentive': 'lease_incentive',
        'initial_direct_expenditure': 'initial_direct_expenditure',
        'counterparty': 'counterparty',
        'group_entity_name': 'group_entity_name',
    }
    
    # Check if extraction includes metadata with bounding boxes (from new PDF-based extraction)
    ai_metadata = extracted_data.get('_metadata', {})
    use_ai_coordinates = bool(ai_metadata)
    
    if use_ai_coordinates:
        logger.info("✅ Using AI-provided bounding boxes from Gemini extraction")
    
    # Save metadata for each extracted field
    for extract_key, value in extracted_data.items():
        # Skip metadata key
        if extract_key == '_metadata':
            continue
            
        if value is None or value == '':
            continue
        
        field_name = field_mapping.get(extract_key)
        if not field_name:
            continue
        
        # Get bounding boxes from AI metadata if available
        bounding_boxes = []
        page_number = None
        
        if use_ai_coordinates and extract_key in ai_metadata:
            # Use bounding boxes from AI extraction
            field_meta = ai_metadata[extract_key]
            page_number = field_meta.get('page_number')
            ai_bboxes = field_meta.get('bounding_boxes', [])
            
            for bbox in ai_bboxes:
                if isinstance(bbox, list) and len(bbox) >= 4:
                    # bbox is [x0, y0, x1, y1] in PDF points (top-left origin)
                    x0, y0, x1, y1 = bbox[:4]
                    bounding_boxes.append([x0, y0, x1, y1])
                    logger.debug(f"Using AI coordinates for {field_name}: page={page_number}, bbox=[{x0}, {y0}, {x1}, {y1}]")
        
        # Fallback: Search for text positions if AI coordinates not available
        if not bounding_boxes:
            # --- START Robustness Fix ---
            # 1. Convert value to string and strip whitespace for searching
            search_text = str(value).strip()
            
            # 2. Normalize: replace multiple spaces/newlines with a single space
            search_text = re.sub(r'\s+', ' ', search_text)
            
            # For dates, try multiple formats
            date_search_variants = []
            if field_name in ['lease_start_date', 'end_date', 'first_payment_date', 'agreement_date', 
                            'termination_date', 'escalation_start_date']:
                # Try to find date in various formats in PDF
                # Original format might be YYYY-MM-DD, but PDF might have DD/MM/YYYY or MM/DD/YYYY
                try:
                    from datetime import datetime
                    if len(search_text) == 10 and '-' in search_text:
                        date_obj = datetime.strptime(search_text, '%Y-%m-%d')
                        date_search_variants = [
                            date_obj.strftime('%d/%m/%Y'),
                            date_obj.strftime('%m/%d/%Y'),
                            date_obj.strftime('%d-%m-%Y'),
                            date_obj.strftime('%m-%d-%Y'),
                            date_obj.strftime('%d %m %Y'),
                            date_obj.strftime('%B %d, %Y'),  # "January 15, 2024"
                            date_obj.strftime('%b %d, %Y'),   # "Jan 15, 2024"
                        ]
                except:
                    pass
            
            # Try original search text first, then variants
            search_texts_to_try = [search_text] + date_search_variants
            
            # Skip empty values after normalization
            if not search_text or len(search_text) == 0:
                continue
            
            # Limit search text length for better matching
            if len(search_text) > 100:
                # For long text, try multiple shorter snippets
                words = search_text.split()
                if len(words) > 10:
                    # Try first 5 words and last 5 words
                    search_texts_to_try = [' '.join(words[:5]), ' '.join(words[-5:])] + search_texts_to_try
                else:
                    search_texts_to_try = [search_text[:100]] + search_texts_to_try
            
            try:
                matches = None
                # Strategy 1: Try each search text variant with exact matching
                for search_variant in search_texts_to_try:
                    if not search_variant or len(search_variant) < 2:
                        continue
                    try:
                        matches = find_text_positions(pdf_path, search_variant, case_sensitive=False, fuzzy=False)
                        if matches:
                            logger.debug(f"Found coordinates for {field_name} using search variant: '{search_variant[:50]}...'")
                            break
                    except Exception as search_error:
                        logger.debug(f"Search variant '{search_variant[:30]}...' failed for {field_name}: {search_error}")
                        continue
                
                # Strategy 2: Try fuzzy matching (word-by-word) if exact match failed
                if not matches and search_text and len(search_text.split()) > 1:
                    try:
                        matches = find_text_positions(pdf_path, search_text, case_sensitive=False, fuzzy=True)
                        if matches:
                            logger.debug(f"Found coordinates for {field_name} using fuzzy matching")
                    except Exception as fuzzy_error:
                        logger.debug(f"Fuzzy matching failed for {field_name}: {fuzzy_error}")
                
                # Strategy 3: For numbers/amounts, try different formats
                if not matches:
                    # Try to extract numeric value and search with different formatting
                    try:
                        import re
                        # Extract numbers from text (handles decimals, commas, etc.)
                        numbers = re.findall(r'[\d,]+\.?\d*', search_text)
                        if numbers:
                            for num_str in numbers[:3]:  # Try first 3 numbers found
                                # Remove commas and try different formats
                                clean_num = num_str.replace(',', '')
                                num_variants = [
                                    clean_num,
                                    num_str,  # Original with commas
                                    f"{float(clean_num):,.2f}",  # With commas and 2 decimals
                                    f"{float(clean_num):.2f}",   # With 2 decimals
                                ]
                                for num_variant in num_variants:
                                    try:
                                        num_matches = find_text_positions(pdf_path, num_variant, case_sensitive=False)
                                        if num_matches:
                                            matches = num_matches
                                            logger.debug(f"Found coordinates for {field_name} using number variant: '{num_variant}'")
                                            break
                                    except:
                                        continue
                                if matches:
                                    break
                    except Exception as num_error:
                        logger.debug(f"Number extraction failed for {field_name}: {num_error}")
                
                # Strategy 4: Try matching individual significant words (for multi-word values)
                if not matches and len(search_text.split()) > 1:
                    words = search_text.split()
                    significant_words = [w for w in words if len(w) > 3]  # Words longer than 3 chars
                    if significant_words:
                        # Try first significant word
                        try:
                            word_matches = find_text_positions(pdf_path, significant_words[0], case_sensitive=False)
                            if word_matches:
                                matches = word_matches
                                logger.debug(f"Found coordinates for {field_name} using significant word: '{significant_words[0]}'")
                        except:
                            pass
                
                if matches:
                    # Use first match
                    match = matches[0]
                    page_number = match['page']
                    bbox = match['bbox']
                    
                    # Convert to format [x0, y0, x1, y1]
                    # bbox from find_text_positions is [x0, y0, x1, y1] with top-left origin
                    if len(bbox) >= 4:
                        bounding_boxes.append([bbox[0], bbox[1], bbox[2], bbox[3]])
                        logger.info(f"✅ Found coordinates via text search for {field_name}: page={page_number}, bbox={bbox}")
                else:
                    logger.debug(f"⚠️ Could not find text '{search_text[:50]}...' in PDF for field {field_name} (tried exact, fuzzy, number variants, and word matching)")
            except Exception as e:
                logger.warning(f"Could not find coordinates for field {field_name} (search_text='{search_text[:50]}...'): {e}")
        
        # Save metadata (with default confidence if not available)
        # Convert bounding_boxes to list of dicts format for database
        bboxes_formatted = None
        if bounding_boxes:
            bboxes_formatted = []
            for bbox in bounding_boxes:
                if isinstance(bbox, list) and len(bbox) >= 4:
                    # Convert [x0, y0, x1, y1] to dict format if needed
                    # Database expects list format, so keep as is
                    bboxes_formatted.append(bbox)
        
        # Get extracted value for snippet
        extracted_value_str = str(value).strip()
        snippet = extracted_value_str[:200] if len(extracted_value_str) > 200 else extracted_value_str
        
        # Always save metadata, even if bounding boxes weren't found
        # Set default page_number if not found (for fields without bounding boxes)
        if page_number is None:
            page_number = 1  # Default to page 1 if not found
        
        try:
            save_extraction_metadata(
                lease_id=lease_id,
                field_name=field_name,
                extracted_value=extracted_value_str,
                ai_confidence=0.85,  # Default confidence (could be enhanced with actual AI confidence)
                page_number=page_number if page_number else 1,  # Ensure page_number is always set
                bounding_boxes=bboxes_formatted if bboxes_formatted else None,
                snippet=snippet
            )
        except Exception as e:
            logger.warning(f"Could not save extraction metadata for {field_name}: {e}")


def _save_pdf_document(lease_id: int, user_id: int, file, temp_path: str) -> int:
    """
    Save the PDF file permanently to documents table
    
    Args:
        lease_id: Lease ID to associate document with
        user_id: User ID uploading the document
        file: Flask file object
        temp_path: Path to temporary file
        
    Returns:
        Document ID if successful
    """
    try:
        logger.info(f"📄 _save_pdf_document called:")
        logger.info(f"   - lease_id: {lease_id}")
        logger.info(f"   - user_id: {user_id}")
        logger.info(f"   - temp_path: {temp_path}")
        logger.info(f"   - temp_path exists: {os.path.exists(temp_path)}")
        
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'pdf'
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        permanent_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        logger.info(f"   - original_filename: {original_filename}")
        logger.info(f"   - unique_filename: {unique_filename}")
        logger.info(f"   - permanent_path: {permanent_path}")
        logger.info(f"   - UPLOAD_FOLDER: {UPLOAD_FOLDER}")
        logger.info(f"   - UPLOAD_FOLDER exists: {os.path.exists(UPLOAD_FOLDER)}")
        
        # Ensure upload folder exists
        Path(UPLOAD_FOLDER).mkdir(exist_ok=True)
        
        # Copy temp file to permanent location
        import shutil
        logger.info(f"   - Copying file from {temp_path} to {permanent_path}...")
        shutil.copy2(temp_path, permanent_path)
        logger.info(f"   - ✅ File copied successfully")
        
        # Get file size
        file_size = os.path.getsize(permanent_path)
        file_type = f'application/{file_ext}'
        logger.info(f"   - file_size: {file_size} bytes")
        logger.info(f"   - file_type: {file_type}")
        
        # Save document metadata to database
        logger.info(f"   - Saving to database...")
        doc_id = save_document(
            lease_id=lease_id,
            user_id=user_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_path=permanent_path,
            file_size=file_size,
            file_type=file_type,
            document_type='contract',  # PDFs uploaded for extraction are typically contracts
            uploaded_by=user_id
        )
        
        logger.info(f"✅ PDF document saved successfully:")
        logger.info(f"   - doc_id: {doc_id}")
        logger.info(f"   - original_filename: {original_filename}")
        logger.info(f"   - permanent_path: {permanent_path}")
        
        return doc_id
        
    except Exception as e:
        logger.error(f"❌ Error saving PDF document: {e}", exc_info=True)
        # Clean up permanent file if database save failed
        if 'permanent_path' in locals() and os.path.exists(permanent_path):
            try:
                os.remove(permanent_path)
                logger.info(f"   - Cleaned up permanent file after error")
            except:
                pass
        raise


def _save_pending_pdf(user_id: int, file, temp_path: str, extracted_data: dict = None) -> str:
    """
    Save PDF temporarily when lease_id is not available yet
    Will be associated with lease when lease is created
    
    Args:
        user_id: User ID uploading the document
        file: Flask file object
        temp_path: Path to temporary file
        extracted_data: Optional extracted data to store for later metadata creation
        
    Returns:
        Pending PDF ID (UUID string)
    """
    try:
        logger.info(f"📄 _save_pending_pdf called:")
        logger.info(f"   - user_id: {user_id}")
        logger.info(f"   - temp_path: {temp_path}")
        logger.info(f"   - temp_path exists: {os.path.exists(temp_path)}")
        
        # Generate unique ID for pending PDF
        pending_pdf_id = str(uuid.uuid4())
        
        # Generate filename
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'pdf'
        pending_filename = f"{pending_pdf_id}.{file_ext}"
        pending_path = os.path.join(PENDING_PDF_FOLDER, pending_filename)
        
        logger.info(f"   - original_filename: {original_filename}")
        logger.info(f"   - pending_filename: {pending_filename}")
        logger.info(f"   - pending_path: {pending_path}")
        
        # Ensure pending folder exists
        Path(PENDING_PDF_FOLDER).mkdir(exist_ok=True)
        
        # Copy temp file to pending location
        import shutil
        logger.info(f"   - Copying file from {temp_path} to {pending_path}...")
        shutil.copy2(temp_path, pending_path)
        logger.info(f"   - ✅ File copied successfully")
        
        # Store pending PDF info in database (including extraction data)
        import json
        from database import get_db_connection
        extraction_json = json.dumps(extracted_data) if extracted_data else None
        
        with get_db_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO pending_pdfs 
                (pending_pdf_id, user_id, original_filename, pending_filename, pending_path, file_size, file_type, extraction_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                pending_pdf_id,
                user_id,
                original_filename,
                pending_filename,
                pending_path,
                os.path.getsize(pending_path),
                f'application/{file_ext}',
                extraction_json,
            ))
        
        logger.info(f"✅ Pending PDF saved successfully:")
        logger.info(f"   - pending_pdf_id: {pending_pdf_id}")
        logger.info(f"   - original_filename: {original_filename}")
        logger.info(f"   - pending_path: {pending_path}")
        
        return pending_pdf_id
        
    except Exception as e:
        logger.error(f"❌ Error saving pending PDF: {e}", exc_info=True)
        # Clean up pending file if database save failed
        if 'pending_path' in locals() and os.path.exists(pending_path):
            try:
                os.remove(pending_path)
                logger.info(f"   - Cleaned up pending file after error")
            except:
                pass
        raise

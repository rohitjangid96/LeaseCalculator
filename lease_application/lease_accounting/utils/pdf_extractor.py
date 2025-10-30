"""
PDF Text Extraction Utilities
Extracts text from PDF files (text-based or scanned images)
"""

import os
import tempfile
from typing import Optional, Tuple

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from pdf2image import convert_from_path
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


def extract_text_from_pdf(pdf_path: str) -> Tuple[Optional[str], str]:
    """
    Extract text from PDF file
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Tuple of (extracted_text, status_message)
    """
    if not os.path.exists(pdf_path):
        return None, "PDF file not found"
    
    # Try text-based extraction first (faster)
    if HAS_PYMUPDF:
        try:
            text = _extract_text_pymupdf(pdf_path)
            if text and text.strip():
                return text, "Text extracted successfully from text-based PDF"
        except Exception as e:
            print(f"PyMuPDF extraction failed: {e}")
    
    # Fall back to OCR for scanned PDFs
    if HAS_OCR:
        try:
            text = _extract_text_ocr(pdf_path)
            if text and text.strip():
                return text, "Text extracted successfully from scanned PDF (OCR)"
        except Exception as e:
            print(f"OCR extraction failed: {e}")
    
    return None, "Failed to extract text from PDF"


def _extract_text_pymupdf(pdf_path: str) -> Optional[str]:
    """Extract text from text-based PDF using PyMuPDF"""
    doc = fitz.open(pdf_path)
    text_parts = []
    
    for page in doc:
        page_text = page.get_text()
        if page_text.strip():
            text_parts.append(page_text)
    
    doc.close()
    return "\n".join(text_parts)


def _extract_text_ocr(pdf_path: str) -> Optional[str]:
    """Extract text from scanned PDF using OCR"""
    images = convert_from_path(pdf_path)
    
    if not images:
        return None
    
    text_parts = []
    for img in images:
        text = pytesseract.image_to_string(img, config="--psm 6")
        if text.strip():
            text_parts.append(text)
    
    return "\n".join(text_parts)


def has_selectable_text(pdf_path: str) -> bool:
    """Check if PDF has selectable text"""
    if not HAS_PYMUPDF:
        return False
    
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            if page.get_text().strip():
                doc.close()
                return True
        doc.close()
    except Exception:
        pass
    
    return False


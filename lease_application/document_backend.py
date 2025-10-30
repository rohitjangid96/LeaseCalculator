"""
Document Management Backend
Handles document upload, storage, and retrieval for leases
"""

from flask import Blueprint, request, jsonify, send_file, session
from auth.auth import require_login
from database import (save_document, get_lease_documents, get_document, 
                      delete_document, get_document_count)
import os
import uuid
from werkzeug.utils import secure_filename
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Create blueprint
doc_bp = Blueprint('documents', __name__, url_prefix='/api')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'png', 'jpg', 'jpeg'}

# File upload directory
UPLOAD_FOLDER = 'uploaded_documents'
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Ensure upload directory exists
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


@doc_bp.route('/documents/upload', methods=['POST'])
@require_login
def upload_document():
    """
    Upload a document for a specific lease
    
    Expected request:
    - lease_id (required)
    - file (required) - Uploaded file
    - document_type (optional) - Type of document (contract, amendment, etc.)
    
    Returns:
    - Success with document metadata
    - Error message if failed
    """
    try:
        # Get lease_id
        lease_id = request.form.get('lease_id')
        if not lease_id:
            return jsonify({
                'success': False,
                'error': 'Lease ID is required'
            }), 400
        
        try:
            lease_id = int(lease_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid lease ID'
            }), 400
        
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
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Get user_id from session
        user_id = session.get('user_id')
        
        # Read file to check size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'File too large. Maximum size: {format_file_size(MAX_FILE_SIZE)}'
            }), 400
        
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Get document type
        document_type = request.form.get('document_type', 'contract')
        
        # Get file type
        file_type = file.content_type or f'application/{file_ext}'
        
        # Save document metadata to database
        doc_id = save_document(
            lease_id=lease_id,
            user_id=user_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            document_type=document_type,
            uploaded_by=user_id
        )
        
        logger.info(f"✅ Document uploaded: {original_filename} for lease {lease_id}")
        
        return jsonify({
            'success': True,
            'doc_id': doc_id,
            'filename': original_filename,
            'file_size': file_size,
            'file_size_formatted': format_file_size(file_size),
            'document_type': document_type,
            'message': f'Document uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"❌ Document upload error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Upload failed: {str(e)}'
        }), 500


@doc_bp.route('/documents/<int:lease_id>', methods=['GET'])
@require_login
def get_documents(lease_id):
    """
    Get all documents for a specific lease
    
    Returns:
    - List of documents with metadata
    """
    try:
        user_id = session.get('user_id')
        documents = get_lease_documents(lease_id, user_id)
        
        # Format documents
        for doc in documents:
            doc['file_size_formatted'] = format_file_size(doc['file_size'])
            doc['uploaded_at'] = doc['uploaded_at'] if isinstance(doc['uploaded_at'], str) else str(doc['uploaded_at'])
        
        return jsonify({
            'success': True,
            'count': len(documents),
            'documents': documents
        })
        
    except Exception as e:
        logger.error(f"❌ Get documents error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@doc_bp.route('/documents/<int:lease_id>/count', methods=['GET'])
@require_login
def get_document_count_for_lease(lease_id):
    """
    Get count of documents for a specific lease
    
    Returns:
    - Document count
    """
    try:
        count = get_document_count(lease_id)
        return jsonify({
            'success': True,
            'lease_id': lease_id,
            'count': count
        })
        
    except Exception as e:
        logger.error(f"❌ Get document count error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@doc_bp.route('/document/download/<int:doc_id>', methods=['GET'])
@require_login
def download_document(doc_id):
    """
    Download a specific document
    
    Returns:
    - File download
    """
    try:
        user_id = session.get('user_id')
        doc = get_document(doc_id, user_id)
        
        if not doc:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404
        
        # Check if file exists
        if not os.path.exists(doc['file_path']):
            return jsonify({
                'success': False,
                'error': 'File not found on server'
            }), 404
        
        return send_file(
            doc['file_path'],
            as_attachment=True,
            download_name=doc['original_filename'],
            mimetype=doc['file_type']
        )
        
    except Exception as e:
        logger.error(f"❌ Download error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@doc_bp.route('/document/delete/<int:doc_id>', methods=['DELETE'])
@require_login
def remove_document(doc_id):
    """
    Delete a document
    
    Returns:
    - Success or error message
    """
    try:
        user_id = session.get('user_id')
        doc = get_document(doc_id, user_id)
        
        if not doc:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404
        
        # Delete file
        if os.path.exists(doc['file_path']):
            os.remove(doc['file_path'])
        
        # Delete from database
        deleted = delete_document(doc_id, user_id)
        
        if deleted:
            logger.info(f"✅ Document deleted: {doc['original_filename']}")
            return jsonify({
                'success': True,
                'message': 'Document deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete document'
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Delete error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


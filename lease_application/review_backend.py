"""
Review Interface Backend
Handles review interface with side-by-side PDF viewing and field highlighting
"""

from flask import Blueprint, request, jsonify, send_file, session
from auth.auth import require_login, require_reviewer
from database import (get_lease, get_extraction_metadata, get_field_edit_history,
                     get_reviewer_modifications_summary, save_field_edit, get_lease_documents,
                     get_document, get_user)
import os
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

review_bp = Blueprint('review', __name__, url_prefix='/api')


@review_bp.route('/review/<int:lease_id>/metadata', methods=['GET'])
@require_login
def get_review_metadata(lease_id):
    """Get extraction metadata and review data for a lease"""
    try:
        user_id = session.get('user_id')
        
        # Get lease data
        lease = get_lease(lease_id, user_id)
        if not lease:
            # Check if user is admin/reviewer and has access
            from database import get_user
            user = get_user(user_id)
            is_admin = user and user.get('role') == 'admin'
            is_reviewer = user and user.get('role') == 'reviewer'
            
            if not (is_admin or is_reviewer):
                return jsonify({'success': False, 'error': 'Lease not found'}), 404
            
            # Get lease without user_id check for admin/reviewer
            from database import get_all_leases_admin
            all_leases = get_all_leases_admin()
            lease = next((l for l in all_leases if l['lease_id'] == lease_id), None)
            if not lease:
                return jsonify({'success': False, 'error': 'Lease not found'}), 404
        
        # Get extraction metadata
        extraction_metadata = get_extraction_metadata(lease_id)
        
        # Get field edit history
        edit_history = get_field_edit_history(lease_id)
        
        # Get modification summary
        modifications_summary = get_reviewer_modifications_summary(lease_id)
        
        # Get PDF documents for this lease
        # For reviewers/admins, allow access to any lease's documents (don't check ownership)
        user = get_user(user_id)
        is_admin = user and user.get('role') == 'admin'
        is_reviewer = user and user.get('role') == 'reviewer'
        
        logger.info(f"📋 Review Metadata Debug for lease_id={lease_id}:")
        logger.info(f"   - user_id: {user_id}")
        logger.info(f"   - user: {user}")
        logger.info(f"   - is_admin: {is_admin}")
        logger.info(f"   - is_reviewer: {is_reviewer}")
        
        if is_admin or is_reviewer:
            # Admin/reviewer can see all documents without ownership check
            logger.info(f"   - Admin/Reviewer: Fetching documents without ownership check...")
            documents = get_lease_documents(lease_id, user_id, check_ownership=False)
        else:
            # Regular user must own the lease to see documents
            logger.info(f"   - Regular user: Fetching documents with ownership check...")
            documents = get_lease_documents(lease_id, user_id, check_ownership=True)
        
        logger.info(f"   - Total documents found: {len(documents)}")
        for i, doc in enumerate(documents):
            logger.info(f"   - Document {i+1}: doc_id={doc.get('doc_id')}, filename={doc.get('filename')}, file_type={doc.get('file_type')}, lease_id={doc.get('lease_id')}, user_id={doc.get('user_id')}")
        
        # Filter PDF documents - be more lenient with file_type checking
        pdf_documents = []
        for doc in documents:
            file_type = doc.get('file_type', '') or ''
            if isinstance(file_type, str):
                file_type = file_type.lower()
            filename = doc.get('filename', '') or doc.get('original_filename', '') or ''
            file_path = doc.get('file_path', '') or ''
            
            # Include if:
            # 1. file_type is application/pdf OR
            # 2. filename ends with .pdf OR
            # 3. file_path ends with .pdf OR
            # 4. No file_type/filename but document exists (assume PDF)
            is_pdf = (
                file_type == 'application/pdf' or
                (isinstance(filename, str) and filename.lower().endswith('.pdf')) or
                (isinstance(file_path, str) and file_path.lower().endswith('.pdf'))
            )
            
            if is_pdf:
                pdf_documents.append(doc)
                logger.info(f"   - ✅ Included PDF doc: doc_id={doc.get('doc_id')}, filename={filename}, file_type={file_type}, file_path={file_path}")
            else:
                logger.info(f"   - ⚠️ Skipped non-PDF doc: doc_id={doc.get('doc_id')}, filename={filename}, file_type={file_type}")
        
        logger.info(f"   - PDF documents found: {len(pdf_documents)} (from {len(documents)} total documents)")
        
        # Get the application root directory - resolve relative to this file's location
        # This file is in lease_application/, so parent is lease_application/ itself
        current_file = Path(__file__).resolve()
        if 'lease_application' in str(current_file):
            # We're in lease_application/ directory
            app_root = current_file.parent  # lease_application/
            uploaded_docs_dir = app_root / 'uploaded_documents'
        else:
            # Fallback - try to find lease_application directory
            app_root = Path('.')
            uploaded_docs_dir = app_root / 'lease_application' / 'uploaded_documents'
            if not uploaded_docs_dir.exists():
                uploaded_docs_dir = app_root / 'uploaded_documents'
        
        logger.info(f"   - App root: {app_root}")
        logger.info(f"   - Uploaded docs dir: {uploaded_docs_dir}")
        logger.info(f"   - Uploaded docs dir exists: {uploaded_docs_dir.exists()}")
        logger.info(f"   - Current working directory: {os.getcwd()}")
        
        for i, pdf_doc in enumerate(pdf_documents):
            file_path = pdf_doc.get('file_path', '')
            filename = Path(file_path).name if file_path else pdf_doc.get('filename', '')
            
            # Try multiple path combinations - more comprehensive search
            possible_paths = [
                file_path,  # Original path from DB
                os.path.join('lease_application', file_path) if file_path and not file_path.startswith('lease_application') else file_path,  # With lease_application prefix
                str(uploaded_docs_dir / filename) if filename else None,  # Just filename in uploaded_documents
                str(uploaded_docs_dir / Path(file_path).name) if file_path else None,  # Filename from path
                os.path.join(str(uploaded_docs_dir), filename) if filename else None,  # Explicit join
            ]
            
            # Also try absolute paths and current working directory variations
            if file_path:
                possible_paths.extend([
                    os.path.abspath(file_path),  # Absolute path
                    os.path.join(os.getcwd(), file_path),  # With cwd
                    os.path.join(os.getcwd(), 'lease_application', file_path) if not file_path.startswith('lease_application') else os.path.join(os.getcwd(), file_path),
                ])
            
            if filename:
                possible_paths.extend([
                    os.path.join(os.getcwd(), 'lease_application', 'uploaded_documents', filename),
                    os.path.join(os.getcwd(), 'uploaded_documents', filename),
                ])
            
            # Filter out None values and normalize paths
            possible_paths = [os.path.normpath(p) for p in possible_paths if p]
            # Remove duplicates while preserving order
            seen = set()
            unique_paths = []
            for p in possible_paths:
                if p not in seen:
                    seen.add(p)
                    unique_paths.append(p)
            possible_paths = unique_paths
            
            file_exists = any(os.path.exists(p) for p in possible_paths)
            existing_path = next((p for p in possible_paths if os.path.exists(p)), None)
            
            logger.info(f"   - PDF {i+1}: doc_id={pdf_doc.get('doc_id')}, filename={pdf_doc.get('filename')}, file_path={file_path}")
            logger.info(f"   - PDF file exists: {file_exists}, existing_path: {existing_path}")
            logger.info(f"   - Checked paths: {possible_paths}")
            
            # Update file_path to the existing path if found
            if existing_path:
                pdf_doc['file_path'] = existing_path
                logger.info(f"   - ✅ Updated file_path to: {existing_path}")
            else:
                logger.warning(f"   - ⚠️ PDF file not found for doc_id={pdf_doc.get('doc_id')}")
                logger.warning(f"   - ⚠️ Original file_path: {file_path}")
                logger.warning(f"   - ⚠️ Checked all paths: {possible_paths}")
                # Still include the document, even if file not found (might exist but path issue)
                logger.warning(f"   - ⚠️ Keeping document in list but file may not be accessible")
        
        # Add highlighted PDF as a virtual document entry if it exists
        # Try multiple path combinations using the resolved uploaded_docs_dir
        highlighted_pdf_paths = [
            os.path.join('uploaded_documents', f'highlighted_lease_{lease_id}.pdf'),
            os.path.join('lease_application', 'uploaded_documents', f'highlighted_lease_{lease_id}.pdf'),
            str(uploaded_docs_dir / f'highlighted_lease_{lease_id}.pdf'),
        ]
        
        logger.info(f"   - Checking for highlighted PDF at: {highlighted_pdf_paths}")
        
        pdf_path = None
        for hp_path in highlighted_pdf_paths:
            if os.path.exists(hp_path):
                pdf_path = hp_path
                logger.info(f"   - Highlighted PDF found: {hp_path}")
                break
        
        if pdf_path:
            # Add highlighted PDF as virtual document with doc_id = -1
            pdf_documents.insert(0, {
                'doc_id': -1,  # Special ID for highlighted PDF
                'lease_id': lease_id,
                'filename': f'highlighted_lease_{lease_id}.pdf',
                'original_filename': f'highlighted_lease_{lease_id}.pdf',
                'file_path': pdf_path,
                'file_type': 'application/pdf',
                'file_size': os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
                'uploaded_at': None,
                'user_id': None,
                'is_highlighted': True
            })
            logger.info(f"   - Added highlighted PDF to documents list")
        else:
            logger.info(f"   - Highlighted PDF not found (checked: {highlighted_pdf_paths})")
        
        # If no PDF documents at all, log this
        if len(pdf_documents) == 0:
            logger.warning(f"⚠️ No PDF documents found for lease_id={lease_id}")
        
        return jsonify({
            'success': True,
            'lease': lease,
            'extraction_metadata': extraction_metadata,
            'edit_history': edit_history,
            'modifications_summary': modifications_summary,
            'pdf_documents': pdf_documents,
            'is_ai_populated': len(extraction_metadata) > 0
        })
        
    except Exception as e:
        logger.error(f"Error getting review metadata: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@review_bp.route('/review/<int:lease_id>/field-metadata/<field_name>', methods=['GET'])
@require_login
def get_field_metadata(lease_id, field_name):
    """Get extraction metadata for a specific field"""
    try:
        user_id = session.get('user_id')
        
        # Verify access to lease
        lease = get_lease(lease_id, user_id)
        if not lease:
            # Check if user is admin/reviewer
            from database import get_user
            user = get_user(user_id)
            is_admin = user and user.get('role') == 'admin'
            is_reviewer = user and user.get('role') == 'reviewer'
            
            if not (is_admin or is_reviewer):
                return jsonify({'success': False, 'error': 'Lease not found'}), 404
        
        # Get field extraction metadata
        from database import get_field_extraction_metadata
        metadata = get_field_extraction_metadata(lease_id, field_name)
        
        if not metadata:
            return jsonify({
                'success': True,
                'metadata': None,
                'message': 'No extraction metadata found for this field'
            })
        
        return jsonify({
            'success': True,
            'metadata': metadata
        })
        
    except Exception as e:
        logger.error(f"Error getting field metadata: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@review_bp.route('/review/<int:lease_id>/pdf/<int:doc_id>', methods=['GET'])
@require_login
def get_review_pdf(lease_id, doc_id):
    """Serve PDF file for review interface
    
    Special handling:
    - doc_id = -1: Serve highlighted PDF if available, otherwise original
    - doc_id > 0: Serve specific document
    """
    try:
        user_id = session.get('user_id')
        
        # Verify access - check if user owns lease or is admin/reviewer
        user = get_user(user_id)
        is_admin = user and user.get('role') == 'admin'
        is_reviewer = user and user.get('role') == 'reviewer'
        
        # Special case: doc_id = -1 means use highlighted PDF if available
        if doc_id == -1:
            # Get the application root directory - resolve relative to this file
            current_file = Path(__file__).resolve()
            if 'lease_application' in str(current_file):
                app_root = current_file.parent  # lease_application/
            else:
                app_root = Path('.')
            uploaded_docs_dir = app_root / 'uploaded_documents'
            
            # Try multiple path combinations
            highlighted_pdf_paths = [
                os.path.join('uploaded_documents', f'highlighted_lease_{lease_id}.pdf'),
                os.path.join('lease_application', 'uploaded_documents', f'highlighted_lease_{lease_id}.pdf'),
                str(uploaded_docs_dir / f'highlighted_lease_{lease_id}.pdf'),
            ]
            
            pdf_path = None
            for hp_path in highlighted_pdf_paths:
                if os.path.exists(hp_path):
                    pdf_path = hp_path
                    logger.info(f"📄 Serving highlighted PDF: {hp_path}")
                    break
            
            if pdf_path:
                return send_file(pdf_path, mimetype='application/pdf', as_attachment=False)
            else:
                # Fall back to original PDF
                logger.info(f"⚠️ Highlighted PDF not found, falling back to original")
                # Get the first PDF document for this lease
                documents = get_lease_documents(lease_id, user_id, check_ownership=not (is_admin or is_reviewer))
                pdf_docs = [d for d in documents if d.get('file_type', '').lower() == 'application/pdf']
                if pdf_docs:
                    # Get the application root directory
                    app_root = Path(__file__).parent
                    uploaded_docs_dir = app_root / 'uploaded_documents'
                    
                    # Try to find a valid file path
                    for pdf_doc in pdf_docs:
                        file_path = pdf_doc.get('file_path', '')
                        filename = Path(file_path).name if file_path else pdf_doc.get('filename', '')
                        
                        # Try multiple path combinations
                        possible_paths = [
                            file_path,  # Original path from DB
                            os.path.join('lease_application', file_path) if not file_path.startswith('lease_application') else file_path,
                            str(uploaded_docs_dir / filename) if filename else None,
                            str(uploaded_docs_dir / Path(file_path).name) if file_path else None,
                        ]
                        
                        possible_paths = [p for p in possible_paths if p]
                        
                        for path in possible_paths:
                            if os.path.exists(path):
                                logger.info(f"📄 Serving original PDF: {path}")
                                return send_file(path, mimetype='application/pdf', as_attachment=False)
                        
                    logger.warning(f"⚠️ PDF documents found but files don't exist. Checked paths: {possible_paths if 'possible_paths' in locals() else 'unknown'}")
                
                return jsonify({'success': False, 'error': 'PDF not found'}), 404
        
        # Try to get document
        doc = get_document(doc_id, user_id)
        
        # If not found and user is admin/reviewer, try with lease owner's user_id
        if not doc and (is_admin or is_reviewer):
            # Get document without user check
            from database import get_db_connection
            with get_db_connection() as conn:
                row = conn.execute("""
                    SELECT d.* FROM lease_documents d
                    WHERE d.doc_id = ? AND d.lease_id = ?
                """, (doc_id, lease_id)).fetchone()
                if row:
                    doc = dict(row)
                    logger.info(f"📄 Found document for admin/reviewer: doc_id={doc_id}, file_path={doc.get('file_path')}")
        
        # If still not found, try to get any document for this lease (admin/reviewer can see all)
        if not doc and (is_admin or is_reviewer):
            all_docs = get_lease_documents(lease_id, user_id, check_ownership=False)
            for d in all_docs:
                if d.get('doc_id') == doc_id:
                    doc = d
                    logger.info(f"📄 Found document from lease_documents: doc_id={doc_id}")
                    break
        
        if not doc:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        # Verify document belongs to lease
        if doc['lease_id'] != lease_id:
            return jsonify({'success': False, 'error': 'Document does not belong to this lease'}), 400
        
        # Check if file exists - try multiple path combinations
        file_path = doc.get('file_path', '')
        filename = doc.get('filename', '') or (Path(file_path).name if file_path else '')
        
        logger.info(f"📄 Resolving PDF path: doc_id={doc_id}, filename={filename}, file_path={file_path}")
        
        # Get the application root directory
        current_file = Path(__file__).resolve()
        if 'lease_application' in str(current_file):
            app_root = current_file.parent  # lease_application/
        else:
            app_root = Path('.')
        uploaded_docs_dir = app_root / 'uploaded_documents'
        
        logger.info(f"   App root: {app_root}")
        logger.info(f"   Uploaded docs dir: {uploaded_docs_dir}")
        logger.info(f"   Uploaded docs dir exists: {uploaded_docs_dir.exists()}")
        
        # Try multiple path combinations - comprehensive search
        possible_paths = []
        
        if file_path:
            possible_paths.extend([
                file_path,  # Original path from DB
                os.path.abspath(file_path),  # Absolute path
                os.path.join(os.getcwd(), file_path),  # With cwd
                os.path.join('lease_application', file_path) if not file_path.startswith('lease_application') else file_path,
            ])
        
        if filename:
            possible_paths.extend([
                str(uploaded_docs_dir / filename),
                os.path.join(str(uploaded_docs_dir), filename),
                os.path.join(os.getcwd(), 'lease_application', 'uploaded_documents', filename),
                os.path.join(os.getcwd(), 'uploaded_documents', filename),
            ])
        
        if file_path:
            possible_paths.extend([
                str(uploaded_docs_dir / Path(file_path).name),
            ])
        
        # Filter and normalize paths
        possible_paths = [os.path.normpath(p) for p in possible_paths if p]
        # Remove duplicates
        seen = set()
        unique_paths = []
        for p in possible_paths:
            if p not in seen:
                seen.add(p)
                unique_paths.append(p)
        possible_paths = unique_paths
        
        logger.info(f"   Checking {len(possible_paths)} possible paths: {possible_paths[:5]}...")
        
        actual_path = None
        for path in possible_paths:
            if os.path.exists(path):
                actual_path = path
                logger.info(f"📄 Serving document: {path}")
                break
        
        if not actual_path:
            logger.error(f"❌ Document file not found. Checked paths: {possible_paths}")
            return jsonify({'success': False, 'error': 'File not found on server'}), 404
        
        # Serve PDF file
        return send_file(
            actual_path,
            mimetype='application/pdf',
            download_name=doc['original_filename']
        )
        
    except Exception as e:
        logger.error(f"Error serving PDF: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@review_bp.route('/review/<int:lease_id>/save-edit', methods=['POST'])
@require_login
def save_field_edit_api(lease_id):
    """Save a field edit made by reviewer"""
    try:
        user_id = session.get('user_id')
        data = request.json
        
        field_name = data.get('field_name')
        original_ai_value = data.get('original_ai_value', '')
        reviewer_value = data.get('reviewer_value', '')
        
        if not field_name:
            return jsonify({'success': False, 'error': 'Field name is required'}), 400
        
        # Verify access to lease
        lease = get_lease(lease_id, user_id)
        if not lease:
            # Check if user is admin/reviewer
            from database import get_user
            user = get_user(user_id)
            is_admin = user and user.get('role') == 'admin'
            is_reviewer = user and user.get('role') == 'reviewer'
            
            if not (is_admin or is_reviewer):
                return jsonify({'success': False, 'error': 'Lease not found'}), 404
        
        # Save the edit
        audit_id = save_field_edit(
            lease_id=lease_id,
            field_name=field_name,
            original_ai_value=str(original_ai_value),
            reviewer_value=str(reviewer_value),
            reviewer_user_id=user_id
        )
        
        logger.info(f"✅ Field edit saved: {field_name} for lease {lease_id} by user {user_id}")
        
        return jsonify({
            'success': True,
            'audit_id': audit_id,
            'message': 'Field edit saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving field edit: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@review_bp.route('/review/<int:lease_id>/modifications', methods=['GET'])
@require_login
def get_modifications(lease_id):
    """Get summary of reviewer modifications"""
    try:
        user_id = session.get('user_id')
        
        # Verify access
        lease = get_lease(lease_id, user_id)
        if not lease:
            # Check if user is admin/reviewer
            from database import get_user
            user = get_user(user_id)
            is_admin = user and user.get('role') == 'admin'
            is_reviewer = user and user.get('role') == 'reviewer'
            
            if not (is_admin or is_reviewer):
                return jsonify({'success': False, 'error': 'Lease not found'}), 404
        
        summary = get_reviewer_modifications_summary(lease_id)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Error getting modifications: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


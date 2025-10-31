"""
Approval Workflow Backend
Handles maker-checker approval workflow for lease management
"""

from flask import Blueprint, request, jsonify, session
from auth.auth import require_login, require_admin, require_reviewer
import database
import logging

logger = logging.getLogger(__name__)

approval_bp = Blueprint('approval', __name__, url_prefix='/api')


@approval_bp.route('/approvals/submit', methods=['POST'])
@require_login
def submit_for_approval_api():
    """Submit a lease for approval"""
    try:
        user_id = session.get('user_id')
        data = request.json
        
        lease_id = data.get('lease_id')
        request_type = data.get('request_type', 'creation')  # creation, edit, deletion
        comments = data.get('comments', '')
        
        if not lease_id:
            return jsonify({'success': False, 'error': 'Lease ID is required'}), 400
        
        # Verify lease exists and belongs to user (or admin)
        user = database.get_user(user_id)
        is_admin = user and user.get('role') == 'admin'
        is_reviewer = user and user.get('role') == 'reviewer'
        
        # Admin and reviewer don't need to submit for approval - their changes are auto-approved
        if is_admin or is_reviewer:
            return jsonify({'success': False, 'error': 'Admin and reviewer changes are automatically approved. No approval submission needed.'}), 400
        
        if is_admin:
            all_leases = database.get_all_leases_admin()
            lease = next((l for l in all_leases if l['lease_id'] == lease_id), None)
        else:
            lease = database.get_lease(lease_id, user_id)
        
        if not lease:
            return jsonify({'success': False, 'error': 'Lease not found'}), 404
        
        # Submit for approval
        approval_id = database.submit_for_approval(lease_id, user_id, request_type, comments)
        
        logger.info(f"✅ Lease {lease_id} submitted for approval by user {user_id}")
        
        return jsonify({
            'success': True,
            'approval_id': approval_id,
            'message': 'Lease submitted for approval'
        })
        
    except Exception as e:
        logger.error(f"Error submitting for approval: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@approval_bp.route('/approvals/pending', methods=['GET'])
@require_login
@require_reviewer
def get_pending_approvals_api():
    """Get all pending approvals"""
    try:
        user_id = session.get('user_id')
        
        # Get pending approvals
        approvals = database.get_pending_approvals(user_id)
        
        return jsonify({
            'success': True,
            'approvals': approvals
        })
        
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@approval_bp.route('/approvals/<int:approval_id>/approve', methods=['POST'])
@require_login
@require_reviewer
def approve_lease_api(approval_id):
    """Approve a lease request"""
    try:
        user_id = session.get('user_id')
        data = request.json
        comments = data.get('comments', '')
        
        # Approve the lease
        success = database.approve_lease(approval_id, user_id, comments)
        
        if not success:
            return jsonify({'success': False, 'error': 'Approval not found'}), 404
        
        logger.info(f"✅ Approval {approval_id} approved by user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Lease approved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error approving lease: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@approval_bp.route('/approvals/<int:approval_id>/reject', methods=['POST'])
@require_login
@require_reviewer
def reject_lease_api(approval_id):
    """Reject a lease request"""
    try:
        user_id = session.get('user_id')
        data = request.json
        comments = data.get('comments', '')
        
        # Reject the lease
        success = database.reject_lease(approval_id, user_id, comments)
        
        if not success:
            return jsonify({'success': False, 'error': 'Approval not found'}), 404
        
        logger.info(f"❌ Approval {approval_id} rejected by user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Lease rejected'
        })
        
    except Exception as e:
        logger.error(f"Error rejecting lease: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@approval_bp.route('/approvals/history/<int:lease_id>', methods=['GET'])
@require_login
def get_approval_history_api(lease_id):
    """Get approval history for a lease"""
    try:
        user_id = session.get('user_id')
        
        # Verify user has access to this lease
        user = database.get_user(user_id)
        is_admin = user and user.get('role') == 'admin'
        
        if is_admin:
            all_leases = database.get_all_leases_admin()
            lease = next((l for l in all_leases if l['lease_id'] == lease_id), None)
        else:
            lease = database.get_lease(lease_id, user_id)
        
        if not lease:
            return jsonify({'success': False, 'error': 'Lease not found'}), 404
        
        # Get approval history
        history = database.get_approval_history(lease_id)
        
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        logger.error(f"Error getting approval history: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@approval_bp.route('/reviewers', methods=['GET'])
@require_login
@require_admin
def get_reviewers_api():
    """Get all users with reviewer role (admin only)"""
    try:
        reviewers = database.get_users_by_role('reviewer')
        return jsonify({
            'success': True,
            'reviewers': reviewers
        })
    except Exception as e:
        logger.error(f"Error getting reviewers: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


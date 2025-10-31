"""
Admin Backend
Handles admin operations including user management and system statistics
"""

from flask import Blueprint, request, jsonify, session
from auth.auth import require_login, require_admin
import database
import logging

logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/check', methods=['GET'])
@require_login
def check_admin():
    """Check if the current user is an admin"""
    try:
        user_id = session.get('user_id')
        user = database.get_user(user_id)
        is_admin = user and user.get('role') == 'admin'
        
        return jsonify({'success': True, 'is_admin': is_admin})
    except Exception as e:
        logger.error(f"Error checking admin status: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/stats', methods=['GET'])
@require_login
@require_admin
def get_stats():
    """Get system statistics (admin only)"""
    try:
        # Get total users
        users = database.get_all_users()
        
        # Get total leases
        all_leases = database.get_all_leases_admin()
        
        # Calculate statistics
        active_users = sum(1 for u in users if u.get('is_active'))
        
        stats = {
            'total_users': len(users),
            'active_users': active_users,
            'total_leases': len(all_leases),
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/users', methods=['GET'])
@require_login
@require_admin
def get_all_users_api():
    """Get all users (admin only)"""
    try:
        users = database.get_all_users()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        logger.error(f"Error getting all users: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_login
@require_admin
def update_user_api(user_id):
    """Update user role or status (admin only)"""
    try:
        data = request.json
        
        # Update role if provided
        if 'role' in data:
            database.update_user_role(user_id, data['role'])
        
        # Update active status if provided
        if 'is_active' in data:
            database.set_user_active(user_id, bool(data['is_active']))
        
        logger.info(f"✅ User {user_id} updated by admin")
        
        return jsonify({'success': True, 'message': 'User updated successfully'})
        
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/leases', methods=['GET'])
@require_login
@require_admin
def get_all_leases_admin_api():
    """Get all leases for admin (admin only)"""
    try:
        # Optional filter by user_id
        user_id = request.args.get('user_id')
        user_id = int(user_id) if user_id else None
        
        all_leases = database.get_all_leases_admin(user_id)
        
        return jsonify({'success': True, 'leases': all_leases})
        
    except Exception as e:
        logger.error(f"Error getting all leases: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/leases/create', methods=['POST'])
@require_login
@require_admin
def create_lease_for_user():
    """Create a lease on behalf of any user (admin only)"""
    try:
        data = request.json
        
        # Get target user_id
        target_user_id = data.get('user_id')
        if not target_user_id:
            return jsonify({'success': False, 'error': 'user_id is required'}), 400
        
        # Verify target user exists
        target_user = database.get_user(target_user_id)
        if not target_user:
            return jsonify({'success': False, 'error': 'Target user not found'}), 404
        
        # Create the lease (remove user_id from data, add it separately)
        lease_data = {k: v for k, v in data.items() if k != 'user_id'}
        
        from api import create_lease
        
        # Call create_lease with target_user_id
        lease_id = create_lease(lease_data, target_user_id)
        
        logger.info(f"✅ Admin created lease {lease_id} for user {target_user_id}")
        
        return jsonify({
            'success': True,
            'lease_id': lease_id,
            'message': f'Lease created for user {target_user.get("username")}'
        })
        
    except Exception as e:
        logger.error(f"Error creating lease for user: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/google-ai-settings', methods=['GET'])
@require_login
@require_admin
def get_google_ai_settings_api():
    """Get Google AI API settings (admin only)"""
    try:
        settings = database.get_google_ai_settings()
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error(f"Error getting Google AI settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/google-ai-settings', methods=['POST'])
@require_login
@require_admin
def save_google_ai_settings_api():
    """Save Google AI API settings (admin only)"""
    try:
        data = request.json
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({'success': False, 'error': 'API key is required'}), 400
        
        setting_id = database.save_google_ai_settings(api_key)
        
        logger.info(f"✅ Google AI API settings saved by admin")
        
        return jsonify({
            'success': True,
            'setting_id': setting_id,
            'message': 'Google AI API settings saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving Google AI settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


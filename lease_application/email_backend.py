"""
Email Management Backend
Handles email configuration and sending
"""

from flask import Blueprint, request, jsonify, session
from auth.auth import require_login
import database
import logging

logger = logging.getLogger(__name__)

# Create blueprint
email_bp = Blueprint('email', __name__, url_prefix='/api')

# Import email service (will fail gracefully if not available)
try:
    from utils.email_service import (send_email, send_lease_expiration_alert, 
                                    send_lease_report, send_bulk_alert, HAS_EMAIL_AVAILABLE)
except ImportError as e:
    logger.warning(f"Email service not available: {e}")
    HAS_EMAIL_AVAILABLE = False
    def send_email(*args, **kwargs):
        return False


@email_bp.route('/email/settings', methods=['GET'])
@require_login
def get_email_settings_api():
    """Get current email settings"""
    try:
        settings = database.get_email_settings()
        
        if settings:
            # Don't return password
            settings_safe = {
                'smtp_host': settings['smtp_host'],
                'smtp_port': settings['smtp_port'],
                'smtp_username': settings['smtp_username'],
                'from_email': settings['from_email'],
                'from_name': settings['from_name'],
                'use_tls': bool(settings['use_tls'])
            }
            return jsonify({'success': True, 'settings': settings_safe})
        else:
            return jsonify({'success': True, 'settings': None})
    except Exception as e:
        logger.error(f"Error getting email settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@email_bp.route('/email/settings', methods=['POST'])
@require_login
def save_email_settings_api():
    """Save email settings"""
    try:
        if not HAS_EMAIL_AVAILABLE:
            return jsonify({'success': False, 'error': 'Email service not available'}), 400
        
        data = request.json
        
        # Validate required fields
        required = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'from_email', 'from_name']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        setting_id = database.save_email_settings(
            host=data['smtp_host'],
            port=data['smtp_port'],
            username=data['smtp_username'],
            password=data['smtp_password'],
            from_email=data['from_email'],
            from_name=data['from_name'],
            use_tls=data.get('use_tls', True)
        )
        
        logger.info(f"✅ Email settings saved successfully")
        
        return jsonify({
            'success': True,
            'setting_id': setting_id,
            'message': 'Email settings saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving email settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@email_bp.route('/email/test', methods=['POST'])
@require_login
def test_email():
    """Send a test email"""
    try:
        if not HAS_EMAIL_AVAILABLE:
            return jsonify({'success': False, 'error': 'Email service not available'}), 400
        
        user_id = session.get('user_id')
        user = database.get_user(user_id)
        
        if not user or not user.get('email'):
            return jsonify({'success': False, 'error': 'User email not configured'}), 400
        
        test_subject = "Test Email from Lease Management System"
        test_body_html = """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #667eea;">✅ Email Configuration Test</h2>
            <p>This is a test email to verify your email settings are configured correctly.</p>
            <p>If you received this email, your configuration is working properly!</p>
            <hr>
            <p style="color: #6c757d; font-size: 0.9em;">
                Lease Management System<br>
                Automated Test Email
            </p>
        </body>
        </html>
        """
        
        success = send_email(
            to_email=user['email'],
            subject=test_subject,
            body_html=test_body_html
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Test email sent to {user["email"]}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to send test email. Please check your settings.'
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending test email: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@email_bp.route('/email/notifications', methods=['GET'])
@require_login
def get_notifications():
    """Get user's email notification preferences"""
    try:
        user_id = session.get('user_id')
        notifications = database.get_user_email_notifications(user_id)
        
        return jsonify({
            'success': True,
            'notifications': notifications
        })
    except Exception as e:
        logger.error(f"Error getting notifications: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@email_bp.route('/email/notifications', methods=['POST'])
@require_login
def update_notifications():
    """Update user's email notification preferences"""
    try:
        user_id = session.get('user_id')
        data = request.json
        
        notification_type = data.get('notification_type')
        is_enabled = data.get('is_enabled', True)
        reminder_days = data.get('reminder_days', 30)
        
        if not notification_type:
            return jsonify({'success': False, 'error': 'Missing notification_type'}), 400
        
        database.update_user_notification(user_id, notification_type, is_enabled, reminder_days)
        
        return jsonify({
            'success': True,
            'message': 'Notification preferences updated'
        })
    except Exception as e:
        logger.error(f"Error updating notifications: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@email_bp.route('/email/send-report', methods=['POST'])
@require_login
def send_report_email():
    """Send lease calculation report via email"""
    try:
        if not HAS_EMAIL_AVAILABLE:
            return jsonify({'success': False, 'error': 'Email service not available'}), 400
        
        data = request.json
        
        to_email = data.get('to_email')
        report_data = data.get('report_data', {})
        attachment_path = data.get('attachment_path')
        
        if not to_email:
            return jsonify({'success': False, 'error': 'Missing recipient email'}), 400
        
        success = send_lease_report(to_email, report_data, attachment_path)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Report sent to {to_email}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to send email. Please check your settings.'
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending report email: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


"""
Email Service for Lease Management System
Handles sending emails for notifications and reports
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Flag to check if email service is available
HAS_EMAIL_AVAILABLE = True
try:
    # Check if email libraries are available
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
except ImportError:
    HAS_EMAIL_AVAILABLE = False
    logger.warning("Email libraries not available")


def send_email(to_email: str, subject: str, body_html: str, body_text: str = None,
               attachments: List[Dict] = None, settings: Dict = None) -> bool:
    """
    Send an email using SMTP
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body_html: HTML body content
        body_text: Plain text body (optional, generated from HTML if not provided)
        attachments: List of files to attach [{'filename': 'file.pdf', 'path': '/path/to/file'}]
        settings: SMTP settings dict (or will fetch from database)
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not HAS_EMAIL_AVAILABLE:
        logger.error("Email service not available")
        return False
    
    try:
        # Import database here to avoid circular imports
        from database import get_email_settings
        
        # Get settings if not provided
        if not settings:
            settings = get_email_settings()
        
        if not settings:
            logger.error("No email settings configured")
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{settings['from_name']} <{settings['from_email']}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add text and HTML parts
        if body_text:
            text_part = MIMEText(body_text, 'plain')
            msg.attach(text_part)
        
        html_part = MIMEText(body_html, 'html')
        msg.attach(html_part)
        
        # Add attachments
        if attachments:
            for attachment in attachments:
                try:
                    with open(attachment['path'], 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', 
                                      f'attachment; filename="{attachment["filename"]}"')
                        msg.attach(part)
                except Exception as e:
                    logger.error(f"Failed to attach file {attachment['path']}: {e}")
        
        # Connect to SMTP server and send
        if settings['use_tls']:
            server = smtplib.SMTP(settings['smtp_host'], settings['smtp_port'])
            server.starttls()
        else:
            server = smtplib.SMTP(settings['smtp_host'], settings['smtp_port'])
        
        server.login(settings['smtp_username'], settings['smtp_password'])
        server.send_message(msg)
        server.quit()
        
        logger.info(f"✅ Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {e}", exc_info=True)
        return False


def send_lease_expiration_alert(to_email: str, lease_info: Dict, days_remaining: int) -> bool:
    """Send lease expiration alert email"""
    
    subject = f"⚠️ Lease Expiring Soon: {lease_info.get('lease_name', 'Untitled Lease')}"
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                      color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
            .alert {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
            .lease-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #dee2e6; }}
            .detail-label {{ font-weight: 600; color: #6c757d; }}
            .detail-value {{ color: #495057; }}
            .button {{ display: inline-block; padding: 12px 24px; background: #667eea; 
                      color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🏢 Lease Management System</h2>
                <h3>Lease Expiration Alert</h3>
            </div>
            <div class="content">
                <div class="alert">
                    <strong>⚠️ Important:</strong> Your lease will expire in {days_remaining} days!
                </div>
                
                <div class="lease-details">
                    <h3>Lease Information</h3>
                    <div class="detail-row">
                        <span class="detail-label">Lease Name:</span>
                        <span class="detail-value">{lease_info.get('lease_name', 'N/A')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Description:</span>
                        <span class="detail-value">{lease_info.get('description', 'N/A')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Expiry Date:</span>
                        <span class="detail-value">{lease_info.get('end_date', 'N/A')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Monthly Rent:</span>
                        <span class="detail-value">${lease_info.get('rental_1', 0):,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Days Remaining:</span>
                        <span class="detail-value"><strong>{days_remaining} days</strong></span>
                    </div>
                </div>
                
                <p><strong>Action Required:</strong></p>
                <ul>
                    <li>Review lease terms before expiration</li>
                    <li>Contact landlord for renewal terms</li>
                    <li>Update system with new lease if renewed</li>
                    <li>Mark as terminated if not renewing</li>
                </ul>
                
                <a href="http://localhost:5001/dashboard.html" class="button">View Lease Details</a>
                
                <div class="footer">
                    <p>This is an automated notification from Lease Management System</p>
                    <p>© 2025 Lease Management System</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    body_text = f"""
    Lease Management System - Lease Expiration Alert
    
    Your lease will expire in {days_remaining} days!
    
    Lease Name: {lease_info.get('lease_name', 'N/A')}
    Expiry Date: {lease_info.get('end_date', 'N/A')}
    Days Remaining: {days_remaining} days
    
    View lease details: http://localhost:5001/dashboard.html
    """
    
    return send_email(to_email, subject, body_html, body_text)


def send_lease_report(to_email: str, report_data: Dict, attachment_path: Optional[str] = None) -> bool:
    """Send lease calculation report via email"""
    
    subject = f"📊 Lease Report: {report_data.get('period', 'Calculation')}"
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                      color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
            .summary {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .summary-item {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6; }}
            .button {{ display: inline-block; padding: 12px 24px; background: #667eea; 
                      color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📊 Lease Calculation Report</h2>
                <p>Period: {report_data.get('period', 'N/A')}</p>
            </div>
            <div class="content">
                <div class="summary">
                    <h3>Financial Summary</h3>
                    <div class="summary-item">
                        <span>Opening Liability:</span>
                        <span><strong>${report_data.get('opening_liability', 0):,.2f}</strong></span>
                    </div>
                    <div class="summary-item">
                        <span>Closing Liability:</span>
                        <span><strong>${report_data.get('closing_liability', 0):,.2f}</strong></span>
                    </div>
                    <div class="summary-item">
                        <span>Total Interest:</span>
                        <span><strong>${report_data.get('total_interest', 0):,.2f}</strong></span>
                    </div>
                    <div class="summary-item">
                        <span>Total Depreciation:</span>
                        <span><strong>${report_data.get('total_depreciation', 0):,.2f}</strong></span>
                    </div>
                    <div class="summary-item">
                        <span>Total Rent Paid:</span>
                        <span><strong>${report_data.get('total_rent_paid', 0):,.2f}</strong></span>
                    </div>
                </div>
                
                {f'<p><strong>Report attachment included:</strong> Complete Excel workbook with amortization schedule and journal entries.</p>' if attachment_path else ''}
                
                <a href="http://localhost:5001/dashboard.html" class="button">View Full Details</a>
                
                <div class="footer">
                    <p>This is an automated report from Lease Management System</p>
                    <p>© 2025 Lease Management System</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    body_text = f"""
    Lease Calculation Report
    
    Period: {report_data.get('period', 'N/A')}
    
    Financial Summary:
    - Opening Liability: ${report_data.get('opening_liability', 0):,.2f}
    - Closing Liability: ${report_data.get('closing_liability', 0):,.2f}
    - Total Interest: ${report_data.get('total_interest', 0):,.2f}
    - Total Depreciation: ${report_data.get('total_depreciation', 0):,.2f}
    - Total Rent Paid: ${report_data.get('total_rent_paid', 0):,.2f}
    
    View full details: http://localhost:5001/dashboard.html
    """
    
    # Attach file if provided
    attachments = []
    if attachment_path and os.path.exists(attachment_path):
        attachments = [{
            'filename': os.path.basename(attachment_path),
            'path': attachment_path
        }]
    
    return send_email(to_email, subject, body_html, body_text, attachments)


def send_bulk_alert(to_email: str, alert_message: str, alert_type: str = 'info') -> bool:
    """Send a general alert/notification email"""
    
    subject_map = {
        'info': 'ℹ️ Lease Management Alert',
        'warning': '⚠️ Lease Management Warning',
        'error': '❌ Lease Management Error',
        'success': '✅ Lease Management Update'
    }
    
    subject = subject_map.get(alert_type, 'Lease Management Alert')
    
    icon_map = {
        'info': 'ℹ️',
        'warning': '⚠️',
        'error': '❌',
        'success': '✅'
    }
    
    icon = icon_map.get(alert_type, 'ℹ️')
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                      color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
            .alert {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>{icon} Lease Management System</h2>
            </div>
            <div class="content">
                <div class="alert">
                    {alert_message.replace(chr(10), '<br>')}
                </div>
                
                <a href="http://localhost:5001/dashboard.html" class="button">View Dashboard</a>
                
                <div class="footer">
                    <p>This is an automated notification from Lease Management System</p>
                    <p>© 2025 Lease Management System</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, body_html)


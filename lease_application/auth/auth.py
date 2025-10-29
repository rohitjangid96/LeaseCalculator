"""
Authentication Utilities
Helper functions for authentication
"""

from functools import wraps
from flask import session, jsonify
import logging

logger = logging.getLogger(__name__)


def require_login(f):
    """
    Decorator to require authentication
    Use this decorator on routes that need authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("❌ Unauthorized access attempt")
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


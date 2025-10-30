"""
Utility script to make a user an admin
Usage: python make_admin.py <username>
"""

import sys
import os
import sqlite3

# Database path
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'lease_application', 'lease_management.db')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    
    # Connect to database
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Find user
        cursor = conn.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if not row:
            print(f"❌ User '{username}' not found!")
            sys.exit(1)
        
        user_id = row['user_id']
        
        # Update role to admin
        conn.execute("UPDATE users SET role = 'admin' WHERE user_id = ?", (user_id,))
        conn.commit()
        
        print(f"✅ User '{username}' (ID: {user_id}) is now an admin!")
        
    finally:
        conn.close()


"""
Database layer for Lease Management System
"""
import sqlite3
from datetime import date, datetime
from typing import List, Dict, Optional
import bcrypt
from contextlib import contextmanager
import base64
import hashlib
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

# Encryption setup for sensitive data
def _get_encryption_key():
    """Generate encryption key from SECRET_KEY"""
    from config import Config
    secret = Config.SECRET_KEY.encode('utf-8')
    key = hashlib.sha256(secret).digest()
    return base64.urlsafe_b64encode(key)

def _encrypt_text(text: str) -> str:
    """Encrypt sensitive text"""
    if not text:
        return text
    f = Fernet(_get_encryption_key())
    return f.encrypt(text.encode('utf-8')).decode('utf-8')

def _decrypt_text(encrypted_text: str) -> str:
    """Decrypt sensitive text"""
    if not encrypted_text:
        return encrypted_text
    try:
        f = Fernet(_get_encryption_key())
        return f.decrypt(encrypted_text.encode('utf-8')).decode('utf-8')
    except Exception:
        # If decryption fails, return as-is (might be plain text from older versions)
        return encrypted_text

DATABASE_PATH = "lease_management.db"


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database tables"""
    with get_db_connection() as conn:
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'user',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add role and is_active columns if they don't exist (migration for existing databases)
        try:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Leases table - stores all lease data
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leases (
                lease_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lease_name TEXT NOT NULL,
                description TEXT,
                asset_class TEXT,
                asset_id_code TEXT,
                counterparty TEXT,
                group_entity_name TEXT,
                region TEXT,
                segment TEXT,
                cost_element TEXT,
                vendor_code TEXT,
                agreement_type TEXT,
                responsible_person_operations TEXT,
                responsible_person_accounts TEXT,
                
                -- Dates
                lease_start_date DATE,
                first_payment_date DATE,
                end_date DATE,
                agreement_date DATE,
                termination_date DATE,
                
                -- Terms
                tenure REAL,
                frequency_months INTEGER,
                day_of_month TEXT,
                accrual_day INTEGER,
                
                -- Rentals
                auto_rentals TEXT,
                rental_1 REAL,
                rental_2 REAL,
                
                -- Escalation
                escalation_percent REAL,
                esc_freq_months INTEGER,
                escalation_start_date DATE,
                index_rate_table TEXT,
                
                -- Financial
                borrowing_rate REAL,
                currency TEXT,
                compound_months INTEGER,
                fv_of_rou REAL,
                initial_direct_expenditure REAL,
                lease_incentive REAL,
                
                -- ARO
                aro REAL,
                aro_table INTEGER,
                
                -- Security Deposit
                security_deposit REAL,
                security_discount REAL,
                
                -- Cost Centers
                cost_centre TEXT,
                profit_center TEXT,
                
                -- Flags
                finance_lease_usgaap TEXT,
                shortterm_lease_ifrs_indas TEXT,
                manual_adj TEXT,
                
                -- Transition
                transition_date DATE,
                transition_option TEXT,
                
                -- Impairments
                impairment1 REAL,
                impairment_date_1 DATE,
                
                -- Other
                intragroup_lease TEXT,
                sublease TEXT,
                sublease_rou REAL,
                modifies_this_id INTEGER,
                modified_by_this_id INTEGER,
                date_modified DATE,
                head_lease_id TEXT,
                scope_reduction REAL,
                scope_date DATE,
                practical_expedient TEXT,
                entered_by TEXT,
                last_modified_by TEXT,
                last_reviewed_by TEXT,
                
                -- Approval workflow
                approval_status TEXT DEFAULT 'draft',  -- draft, pending, approved, rejected
                approved_lease_id INTEGER,  -- For versioning: points to the approved version
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (approved_lease_id) REFERENCES leases(lease_id) ON DELETE SET NULL
            )
        """)
        
        # Add approved_lease_id column if not exists (migration)
        try:
            conn.execute("ALTER TABLE leases ADD COLUMN approved_lease_id INTEGER")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_approved_lease_id ON leases(approved_lease_id)")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Leases calculations - stores calculated schedules and journal entries
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lease_calculations (
                calc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                lease_id INTEGER NOT NULL,
                from_date DATE NOT NULL,
                to_date DATE NOT NULL,
                calculation_data TEXT,  -- JSON stored results
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lease_id) REFERENCES leases(lease_id)
            )
        """)
        
        # Results summary - stores bulk calculation results
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results_summary (
                summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                from_date DATE NOT NULL,
                to_date DATE NOT NULL,
                filters_applied TEXT,  -- JSON of filters
                results_data TEXT,  -- JSON of all lease results
                aggregated_totals TEXT,  -- JSON of aggregated totals
                consolidated_journals TEXT,  -- JSON of consolidated journal entries
                processed_count INTEGER DEFAULT 0,
                skipped_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Lease documents table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lease_documents (
                doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                lease_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                file_type TEXT,
                document_type TEXT DEFAULT 'contract',
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploaded_by INTEGER,
                version INTEGER DEFAULT 1,
                FOREIGN KEY (lease_id) REFERENCES leases(lease_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
            )
        """)
        
        # Email settings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_settings (
                setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                smtp_host TEXT NOT NULL,
                smtp_port INTEGER NOT NULL,
                smtp_username TEXT NOT NULL,
                smtp_password TEXT NOT NULL,
                use_tls INTEGER DEFAULT 1,
                from_email TEXT NOT NULL,
                from_name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Google AI API settings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS google_ai_settings (
                setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Email notifications table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_notifications (
                notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                is_enabled INTEGER DEFAULT 1,
                reminder_days INTEGER DEFAULT 30,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Lease approvals table - tracks approval workflow
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lease_approvals (
                approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                lease_id INTEGER NOT NULL,
                requester_user_id INTEGER NOT NULL,
                approver_user_id INTEGER,
                approval_status TEXT NOT NULL DEFAULT 'pending',
                request_type TEXT NOT NULL,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                FOREIGN KEY (lease_id) REFERENCES leases(lease_id) ON DELETE CASCADE,
                FOREIGN KEY (requester_user_id) REFERENCES users(user_id),
                FOREIGN KEY (approver_user_id) REFERENCES users(user_id)
            )
        """)
        
        # Migration: Add approval_status column to existing leases table if not exists
        try:
            conn.execute("ALTER TABLE leases ADD COLUMN approval_status TEXT DEFAULT 'draft'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        print("✅ Database initialized")


# ============ USER MANAGEMENT ============

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_user(username: str, password: str, email: Optional[str] = None) -> int:
    """Create a new user"""
    password_hash = hash_password(password)
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
            (username, password_hash, email)
        )
        return cursor.lastrowid


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authenticate user and return user data if valid"""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        
        if row and verify_password(password, row['password_hash']):
            return dict(row)
        return None


def get_user(user_id: int) -> Optional[Dict]:
    """Get user by ID"""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, email, role, is_active, created_at FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None


# ============ LEASE MANAGEMENT ============

def save_lease(user_id: int, lease_data: Dict) -> int:
    """Save or update a lease"""
    lease_id = lease_data.get('lease_id')
    
    # Normalize field names from form to database schema (camelCase -> snake_case)
    field_mapping = {
        'asset_name': 'lease_name',  # Use asset_name as lease_name if not set
        'asset_id_code': 'asset_id_code',
        'asset_class': 'asset_class',
        'lease_start_date': 'lease_start_date',
        'first_payment_date': 'first_payment_date',
        'end_date': 'end_date',
        # Add more mappings as needed
    }
    
    # Only keep fields that exist in database schema
    lease_data['user_id'] = user_id
    
    # Convert dates to strings
    date_fields = ['lease_start_date', 'first_payment_date', 'end_date', 'agreement_date',
                   'termination_date', 'escalation_start_date', 'transition_date',
                   'impairment_date_1', 'scope_date', 'date_modified']
    
    for field in date_fields:
        if lease_data.get(field):
            if isinstance(lease_data[field], date):
                lease_data[field] = lease_data[field].isoformat()
            elif isinstance(lease_data[field], str) and '/' in lease_data[field]:
                # Handle MM/DD/YYYY format
                try:
                    d = datetime.strptime(lease_data[field], '%m/%d/%Y')
                    lease_data[field] = d.date().isoformat()
                except:
                    pass
    
    # Check user role for auto-approval
    user = get_user(user_id)
    is_admin = user.get('role') == 'admin' if user else False
    is_checker = user.get('role') == 'reviewer' if user else False
    
    if lease_id:
        # Update existing lease
        # First, check if the lease is currently approved
        with get_db_connection() as conn:
            current_lease = conn.execute(
                "SELECT approval_status FROM leases WHERE lease_id = ? AND user_id = ?",
                (lease_id, user_id)
            ).fetchone()
        
        # Filter to only valid database columns
        valid_columns = [
            'lease_name', 'description', 'asset_class', 'asset_id_code', 'counterparty',
            'group_entity_name', 'region', 'segment', 'cost_element', 'vendor_code',
            'agreement_type', 'responsible_person_operations', 'responsible_person_accounts',
            'lease_start_date', 'first_payment_date', 'end_date', 'agreement_date', 'termination_date',
            'tenure', 'frequency_months', 'day_of_month', 'accrual_day',
            'auto_rentals', 'rental_1', 'rental_2',
            'escalation_percent', 'esc_freq_months', 'escalation_start_date', 'index_rate_table',
            'borrowing_rate', 'currency', 'compound_months', 'fv_of_rou',
            'initial_direct_expenditure', 'lease_incentive',
            'aro', 'aro_table', 'security_deposit', 'security_discount',
            'cost_centre', 'profit_center', 'finance_lease_usgaap', 'shortterm_lease_ifrs_indas',
            'manual_adj', 'transition_date', 'transition_option', 'impairment1', 'impairment_date_1',
            'intragroup_lease', 'sublease', 'sublease_rou', 'modifies_this_id', 'modified_by_this_id',
            'date_modified', 'head_lease_id', 'scope_reduction', 'scope_date',
            'practical_expedient', 'entered_by', 'last_modified_by', 'last_reviewed_by'
        ]
        
        # Filter lease_data to only valid columns
        # Allow None/empty values to be updated (for clearing fields)
        filtered_data = {}
        for k, v in lease_data.items():
            if k in valid_columns and k not in ['lease_id', 'user_id', 'created_at']:
                # Handle empty strings - convert to None for date fields, keep for others
                if k in ['lease_start_date', 'first_payment_date', 'end_date', 'agreement_date', 
                        'termination_date', 'escalation_start_date', 'transition_date', 
                        'impairment_date_1', 'scope_date', 'date_modified']:
                    filtered_data[k] = v if v and v != '' else None
                else:
                    # Keep empty strings for non-date fields (they'll be stored as empty or None)
                    filtered_data[k] = v
        
        # If editing an approved lease, set status to pending (unless user is admin or checker)
        # If editing a rejected lease, set status to draft so user can rework and resubmit
        needs_approval = False
        if not is_admin and not is_checker and current_lease:
            if current_lease['approval_status'] == 'approved':
                # Add approval_status to filtered_data even though it's not in valid_columns
                filtered_data['approval_status'] = 'pending'
                needs_approval = True
            elif current_lease['approval_status'] == 'rejected':
                # Reset rejected lease to draft so user can fix issues and resubmit
                filtered_data['approval_status'] = 'draft'
        
        if not filtered_data:
            return lease_id  # Nothing to update
        
        update_fields = list(filtered_data.keys())
        set_clause = ', '.join([f"{f} = ?" for f in update_fields])
        set_clause += ", updated_at = CURRENT_TIMESTAMP"
        
        values = [filtered_data[f] for f in update_fields]
        values.extend([lease_id, user_id])
        
        with get_db_connection() as conn:
            conn.execute(
                f"UPDATE leases SET {set_clause} WHERE lease_id = ? AND user_id = ?",
                values
            )
            
            # Auto-create approval request if needed
            if needs_approval:
                conn.execute("""
                    INSERT INTO lease_approvals 
                    (lease_id, requester_user_id, approval_status, request_type, comments)
                    VALUES (?, ?, 'pending', 'edit', 'Auto-submitted for approval after editing approved lease')
                """, (lease_id, user_id))
            
            # Auto-approve if edited by admin or checker
            if (is_admin or is_checker) and current_lease and current_lease['approval_status'] != 'approved':
                conn.execute(
                    "UPDATE leases SET approval_status = 'approved' WHERE lease_id = ?",
                    (lease_id,)
                )
        
        return lease_id
    else:
        # Create new lease
        fields = list(lease_data.keys())
        placeholders = ', '.join(['?' for _ in fields])
        values = list(lease_data.values())
        
        with get_db_connection() as conn:
            cursor = conn.execute(
                f"INSERT INTO leases ({', '.join(fields)}) VALUES ({placeholders})",
                values
            )
            lease_id = cursor.lastrowid
            
            # Auto-approve if created by admin or checker
            if is_admin or is_checker:
                conn.execute(
                    "UPDATE leases SET approval_status = 'approved' WHERE lease_id = ?",
                    (lease_id,)
                )
            
            return lease_id


def get_lease(lease_id: int, user_id: int) -> Optional[Dict]:
    """Get lease by ID (only if owned by user)"""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM leases WHERE lease_id = ? AND user_id = ?",
            (lease_id, user_id)
        ).fetchone()
        if not row:
            return None
        
        lease_dict = dict(row)
        # Ensure None values are returned as None (not 'N/A')
        # CRITICAL: Convert numeric fields to proper types (SQLite returns floats as float)
        numeric_fields = ['rental_1', 'rental_2', 'borrowing_rate', 'escalation_percent', 
                         'tenure', 'frequency_months', 'compound_months', 'esc_freq_months',
                         'security_deposit', 'aro', 'initial_direct_expenditure', 'lease_incentive']
        for field in numeric_fields:
            if field in lease_dict and lease_dict[field] is not None:
                try:
                    lease_dict[field] = float(lease_dict[field])
                except (ValueError, TypeError):
                    lease_dict[field] = None
        # The frontend will handle displaying 'N/A' if needed
        return lease_dict


def get_all_leases(user_id: int) -> List[Dict]:
    """Get all leases for a user (includes rejected with rejection reason)"""
    with get_db_connection() as conn:
        # Get column names to verify what's available
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        cursor = conn.execute(
            """
            SELECT l.lease_id, l.lease_name, l.description,
                   COALESCE(l.asset_class, 'N/A') as asset_class, 
                   COALESCE(l.asset_id_code, 'N/A') as asset_id_code,
                   l.lease_start_date, l.end_date,
                   l.rental_1, l.rental_2,
                   l.currency, l.cost_centre, l.profit_center, l.group_entity_name,
                   l.auto_rentals, l.frequency_months,
                   l.approval_status,
                   l.created_at, l.updated_at,
                   (SELECT comments FROM lease_approvals WHERE lease_id = l.lease_id AND approval_status = 'rejected' ORDER BY reviewed_at DESC LIMIT 1) as rejection_reason
            FROM leases l
            WHERE l.user_id = ? 
              AND (l.approval_status IN ('draft', 'pending', 'approved', 'rejected') OR l.approval_status IS NULL)
            ORDER BY l.created_at DESC
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        
        leases = []
        for row in rows:
            lease_dict = dict(row)
            # Format dates or show 'N/A'
            lease_dict['asset_class'] = lease_dict.get('asset_class') or 'N/A'
            lease_dict['asset_id_code'] = lease_dict.get('asset_id_code') or 'N/A'
            lease_dict['lease_start_date'] = lease_dict.get('lease_start_date') or 'N/A'
            lease_dict['end_date'] = lease_dict.get('end_date') or 'N/A'
            lease_dict['description'] = lease_dict.get('description') or ''
            
            # Ensure approval_status has a default
            if not lease_dict.get('approval_status'):
                lease_dict['approval_status'] = 'draft'
            
            # Ensure numeric fields are properly typed
            numeric_fields = ['rental_1', 'rental_2']
            for field in numeric_fields:
                if field in lease_dict and lease_dict[field] is not None:
                    try:
                        lease_dict[field] = float(lease_dict[field])
                    except (ValueError, TypeError):
                        lease_dict[field] = None
                else:
                    lease_dict[field] = None
            
            leases.append(lease_dict)
        
        return leases


def delete_lease(lease_id: int, user_id: int) -> bool:
    """Delete a lease (only if owned by user)"""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM leases WHERE lease_id = ? AND user_id = ?",
            (lease_id, user_id)
        )
        return cursor.rowcount > 0


def save_calculation(lease_id: int, from_date: date, to_date: date, calculation_data: Dict) -> int:
    """Save a calculation result"""
    import json
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO lease_calculations (lease_id, from_date, to_date, calculation_data) VALUES (?, ?, ?, ?)",
            (lease_id, from_date.isoformat(), to_date.isoformat(), json.dumps(calculation_data))
        )
        return cursor.lastrowid


def get_calculation(calc_id: int) -> Optional[Dict]:
    """Get a saved calculation"""
    import json
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM lease_calculations WHERE calc_id = ?",
            (calc_id,)
        ).fetchone()
        if row:
            result = dict(row)
            result['calculation_data'] = json.loads(result['calculation_data'])
            return result
    return None


# ============ ADMIN MANAGEMENT ============

def get_all_users() -> List[Dict]:
    """Get all users (admin only)"""
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT user_id, username, email, role, is_active, created_at 
            FROM users 
            ORDER BY created_at DESC
        """).fetchall()
        return [dict(row) for row in rows]


def update_user_role(user_id: int, role: str) -> bool:
    """Update user's role"""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET role = ? WHERE user_id = ?",
            (role, user_id)
        )
        return cursor.rowcount > 0


def set_user_active(user_id: int, is_active: bool) -> bool:
    """Set user active/inactive status"""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET is_active = ? WHERE user_id = ?",
            (1 if is_active else 0, user_id)
        )
        return cursor.rowcount > 0


def get_all_leases_admin(user_id: Optional[int] = None) -> List[Dict]:
    """Get all leases (admin only) - optionally filtered by user"""
    with get_db_connection() as conn:
        if user_id:
            rows = conn.execute("""
                SELECT * FROM leases WHERE user_id = ? ORDER BY created_at DESC
            """, (user_id,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM leases ORDER BY created_at DESC
            """).fetchall()
        
        leases = []
        for row in rows:
            lease_dict = dict(row)
            # Get username separately
            user_row = conn.execute(
                "SELECT username FROM users WHERE user_id = ?",
                (lease_dict['user_id'],)
            ).fetchone()
            lease_dict['username'] = user_row['username'] if user_row else 'Unknown'
            leases.append(lease_dict)
        
        return leases


# ============ DOCUMENT MANAGEMENT ============

def save_document(lease_id: int, user_id: int, filename: str, original_filename: str, 
                  file_path: str, file_size: int, file_type: str, 
                  document_type: str = 'contract', uploaded_by: Optional[int] = None) -> int:
    """Save document metadata to database"""
    with get_db_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO lease_documents 
            (lease_id, user_id, filename, original_filename, file_path, file_size, 
             file_type, document_type, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (lease_id, user_id, filename, original_filename, file_path, 
              file_size, file_type, document_type, uploaded_by or user_id))
        return cursor.lastrowid


def get_lease_documents(lease_id: int, user_id: int) -> List[Dict]:
    """Get all documents for a lease"""
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM lease_documents 
            WHERE lease_id = ? AND user_id = ?
            ORDER BY uploaded_at DESC
        """, (lease_id, user_id)).fetchall()
        return [dict(row) for row in rows]


def get_document(doc_id: int, user_id: int) -> Optional[Dict]:
    """Get a specific document"""
    with get_db_connection() as conn:
        row = conn.execute("""
            SELECT * FROM lease_documents 
            WHERE doc_id = ? AND user_id = ?
        """, (doc_id, user_id)).fetchone()
        return dict(row) if row else None


def delete_document(doc_id: int, user_id: int) -> bool:
    """Delete a document"""
    with get_db_connection() as conn:
        cursor = conn.execute("""
            DELETE FROM lease_documents 
            WHERE doc_id = ? AND user_id = ?
        """, (doc_id, user_id))
        return cursor.rowcount > 0


def get_document_count(lease_id: int) -> int:
    """Get count of documents for a lease"""
    with get_db_connection() as conn:
        row = conn.execute("""
            SELECT COUNT(*) as count FROM lease_documents WHERE lease_id = ?
        """, (lease_id,)).fetchone()
        return row['count'] if row else 0


# ============ EMAIL MANAGEMENT ============

def get_email_settings() -> Optional[Dict]:
    """Get current active email settings"""
    with get_db_connection() as conn:
        row = conn.execute("""
            SELECT * FROM email_settings WHERE is_active = 1 ORDER BY setting_id DESC LIMIT 1
        """).fetchone()
        return dict(row) if row else None


def save_email_settings(host: str, port: int, username: str, password: str, 
                        from_email: str, from_name: str, use_tls: bool = True) -> int:
    """Save or update email settings"""
    with get_db_connection() as conn:
        # Deactivate old settings
        conn.execute("UPDATE email_settings SET is_active = 0")
        
        # Insert new settings
        cursor = conn.execute("""
            INSERT INTO email_settings 
            (smtp_host, smtp_port, smtp_username, smtp_password, from_email, from_name, use_tls, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (host, port, username, password, from_email, from_name, 1 if use_tls else 0))
        return cursor.lastrowid


def get_user_email_notifications(user_id: int) -> List[Dict]:
    """Get user's email notification preferences"""
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM email_notifications WHERE user_id = ?
        """, (user_id,)).fetchall()
        return [dict(row) for row in rows]


def update_user_notification(user_id: int, notification_type: str, 
                             is_enabled: bool, reminder_days: int = 30) -> None:
    """Update user's notification preference"""
    with get_db_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO email_notifications 
            (user_id, notification_type, is_enabled, reminder_days)
            VALUES (?, ?, ?, ?)
        """, (user_id, notification_type, 1 if is_enabled else 0, reminder_days))


# ============ GOOGLE AI API SETTINGS ============

def get_google_ai_settings() -> Optional[Dict]:
    """Get current Google AI API settings (decrypted)"""
    with get_db_connection() as conn:
        row = conn.execute("""
            SELECT * FROM google_ai_settings WHERE is_active = 1 ORDER BY setting_id DESC LIMIT 1
        """).fetchone()
        if row:
            settings = dict(row)
            # Decrypt the API key before returning
            if 'api_key' in settings:
                settings['api_key'] = _decrypt_text(settings['api_key'])
            return settings
        return None


def save_google_ai_settings(api_key: str) -> int:
    """Save or update Google AI API settings (encrypted)"""
    with get_db_connection() as conn:
        # Deactivate old settings
        conn.execute("UPDATE google_ai_settings SET is_active = 0")
        
        # Encrypt the API key before storing
        encrypted_key = _encrypt_text(api_key)
        
        # Insert new settings
        cursor = conn.execute("""
            INSERT INTO google_ai_settings 
            (api_key, is_active)
            VALUES (?, 1)
        """, (encrypted_key,))
        return cursor.lastrowid


# ============ APPROVAL WORKFLOW ============

def submit_for_approval(lease_id: int, requester_user_id: int, request_type: str, comments: str = None) -> int:
    """Submit a lease for approval"""
    with get_db_connection() as conn:
        # Check if there's already a pending approval for this lease
        existing = conn.execute("""
            SELECT approval_id FROM lease_approvals 
            WHERE lease_id = ? AND approval_status = 'pending'
        """, (lease_id,)).fetchone()
        
        if existing:
            # Return existing approval_id instead of creating duplicate
            logger.info(f"⚠️ Lease {lease_id} already has pending approval, returning existing approval_id {existing['approval_id']}")
            return existing['approval_id']
        
        # Create approval request
        cursor = conn.execute("""
            INSERT INTO lease_approvals 
            (lease_id, requester_user_id, approval_status, request_type, comments)
            VALUES (?, ?, 'pending', ?, ?)
        """, (lease_id, requester_user_id, request_type, comments))
        approval_id = cursor.lastrowid
        
        # Update lease status to pending
        conn.execute("""
            UPDATE leases 
            SET approval_status = 'pending', updated_at = CURRENT_TIMESTAMP
            WHERE lease_id = ?
        """, (lease_id,))
        
        return approval_id


def get_pending_approvals(approver_user_id: int = None) -> List[Dict]:
    """Get all pending approvals (or for a specific approver)"""
    with get_db_connection() as conn:
        if approver_user_id:
            # For specific approver - get pending approvals where they haven't reviewed yet
            rows = conn.execute("""
                SELECT la.*, l.lease_name, l.description, l.asset_class,
                       l.created_at as lease_created, l.updated_at as lease_updated,
                       u.username as requester_name
                FROM lease_approvals la
                JOIN leases l ON la.lease_id = l.lease_id
                JOIN users u ON la.requester_user_id = u.user_id
                WHERE la.approval_status = 'pending'
                  AND l.approval_status = 'pending'
                  AND (la.approver_user_id IS NULL OR la.approver_user_id = ?)
                ORDER BY la.created_at DESC
            """, (approver_user_id,)).fetchall()
        else:
            # All pending approvals
            rows = conn.execute("""
                SELECT la.*, l.lease_name, l.description, l.asset_class,
                       l.created_at as lease_created, l.updated_at as lease_updated,
                       u.username as requester_name
                FROM lease_approvals la
                JOIN leases l ON la.lease_id = l.lease_id
                JOIN users u ON la.requester_user_id = u.user_id
                WHERE la.approval_status = 'pending'
                  AND l.approval_status = 'pending'
                ORDER BY la.created_at DESC
            """).fetchall()
        return [dict(row) for row in rows]


def approve_lease(approval_id: int, approver_user_id: int, comments: str = None) -> bool:
    """Approve a lease request"""
    with get_db_connection() as conn:
        # Get the approval record
        approval = conn.execute("""
            SELECT * FROM lease_approvals WHERE approval_id = ?
        """, (approval_id,)).fetchone()
        
        if not approval:
            return False
        
        # Update approval record
        conn.execute("""
            UPDATE lease_approvals 
            SET approval_status = 'approved',
                approver_user_id = ?,
                reviewed_at = CURRENT_TIMESTAMP,
                comments = ?
            WHERE approval_id = ?
        """, (approver_user_id, comments, approval_id))
        
        # Update lease status
        conn.execute("""
            UPDATE leases 
            SET approval_status = 'approved',
                updated_at = CURRENT_TIMESTAMP
            WHERE lease_id = ?
        """, (approval['lease_id'],))
        
        return True


def reject_lease(approval_id: int, approver_user_id: int, comments: str = None) -> bool:
    """Reject a lease request"""
    with get_db_connection() as conn:
        # Get the approval record
        approval = conn.execute("""
            SELECT * FROM lease_approvals WHERE approval_id = ?
        """, (approval_id,)).fetchone()
        
        if not approval:
            return False
        
        # Update approval record
        conn.execute("""
            UPDATE lease_approvals 
            SET approval_status = 'rejected',
                approver_user_id = ?,
                reviewed_at = CURRENT_TIMESTAMP,
                comments = ?
            WHERE approval_id = ?
        """, (approver_user_id, comments, approval_id))
        
        # Update lease status
        conn.execute("""
            UPDATE leases 
            SET approval_status = 'rejected',
                updated_at = CURRENT_TIMESTAMP
            WHERE lease_id = ?
        """, (approval['lease_id'],))
        
        return True


def get_approval_history(lease_id: int) -> List[Dict]:
    """Get approval history for a lease"""
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT la.*, u1.username as requester_name, u2.username as approver_name
            FROM lease_approvals la
            LEFT JOIN users u1 ON la.requester_user_id = u1.user_id
            LEFT JOIN users u2 ON la.approver_user_id = u2.user_id
            WHERE la.lease_id = ?
            ORDER BY la.created_at DESC
        """, (lease_id,)).fetchall()
        return [dict(row) for row in rows]


def get_users_by_role(role: str) -> List[Dict]:
    """Get all users with a specific role"""
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT user_id, username, email, role, is_active, created_at
            FROM users
            WHERE role = ? AND is_active = 1
            ORDER BY username
        """, (role,)).fetchall()
        return [dict(row) for row in rows]


# Initialize database on import
init_database()


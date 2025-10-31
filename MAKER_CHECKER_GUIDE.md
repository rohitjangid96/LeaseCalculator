# Maker-Checker Approval Workflow Guide

## Overview

The Lease Management System now includes a **maker-checker approval workflow** for enhanced governance and control over lease data creation, modifications, and deletions.

## Roles

### 1. **Admin** 
- **Full access** to all features
- Can approve/reject lease requests
- Can access admin dashboard
- Can manage all users and system settings

### 2. **Reviewer** ✅ NEW
- **Review and approve/reject** lease requests
- Can access the Approvals dashboard
- **Cannot create or edit leases directly**
- Focused on quality control and compliance

### 3. **User** (Maker)
- **Can create and edit** lease records
- **Must submit** for approval before changes go live
- Can only see their own pending requests

## How It Works

### For Makers (Regular Users):

1. **Create or Edit Lease**: Fill out the lease form as usual
2. **Save Lease**: Click "💾 Save Lease" - lease is saved as **draft**
3. **Submit for Approval**: Click "✅ Submit for Approval" button
4. **Add Comments** (optional): Provide context for your request
5. **Wait for Review**: Your request appears in the reviewer's queue

### For Reviewers:

1. **Access Approvals**: Click "✅ Approvals" button in dashboard
2. **Review Requests**: See all pending lease requests with details
3. **View Details**: Click "👁️ View Details" to see full lease information
4. **Make Decision**:
   - **✅ Approve**: Lease becomes active and visible
   - **❌ Reject**: Lease remains in rejected state
5. **Add Comments**: Provide feedback to the maker

### For Admins:

- **Everything reviewers can do**
- **Plus**: Full access to admin dashboard
- **Plus**: Can bypass approval (leases created by admins are auto-approved)

## Setup Instructions

### 1. Create a Reviewer User

```bash
# Option 1: Create a new user first
python lease_application/create_user.py reviewer1 password123 reviewer@company.com

# Option 2: Make an existing user a reviewer
python make_reviewer.py reviewer1
```

### 2. Create an Admin User

```bash
# Make an existing user an admin
python make_admin.py username
```

### 3. Test the Workflow

**As a Maker:**
1. Login as a regular user
2. Go to "Create New Lease"
3. Fill out the form
4. Click "💾 Save Lease"
5. Click "✅ Submit for Approval"

**As a Reviewer:**
1. Login as reviewer/admin
2. Click "✅ Approvals" button in dashboard
3. You'll see the pending request
4. Review and approve/reject

## Database Schema

### New Table: `lease_approvals`

```sql
CREATE TABLE lease_approvals (
    approval_id INTEGER PRIMARY KEY,
    lease_id INTEGER NOT NULL,
    requester_user_id INTEGER NOT NULL,
    approver_user_id INTEGER,
    approval_status TEXT NOT NULL,  -- pending, approved, rejected
    request_type TEXT NOT NULL,      -- creation, edit, deletion
    comments TEXT,
    created_at TIMESTAMP,
    reviewed_at TIMESTAMP
)
```

### New Column in `leases` table:

```sql
ALTER TABLE leases ADD COLUMN approval_status TEXT DEFAULT 'draft';
-- Values: draft, pending, approved, rejected
```

## API Endpoints

- `POST /api/approvals/submit` - Submit lease for approval
- `GET /api/approvals/pending` - Get all pending approvals (reviewer/admin only)
- `POST /api/approvals/{id}/approve` - Approve a lease (reviewer/admin only)
- `POST /api/approvals/{id}/reject` - Reject a lease (reviewer/admin only)
- `GET /api/approvals/history/{lease_id}` - Get approval history for a lease

## Approval Status Flow

```
draft → pending → approved ✅
                  ↓
                  rejected ❌
```

1. **draft**: Lease saved but not submitted
2. **pending**: Submitted and waiting for review
3. **approved**: Review passed, lease is active
4. **rejected**: Review failed, needs correction

## UI Components

### Dashboard
- **✅ Approvals** button: Visible to reviewers and admins
- Shows pending count badge (future enhancement)

### Lease Form
- **✅ Submit for Approval** button: Available after saving
- Submission modal with request type and comments

### Approvals Page
- List of all pending requests
- Approve/Reject actions
- Request details and comments
- View full lease details

## Security

- **Role-based access control**: Only reviewers/admins can approve
- **Audit trail**: All approval actions are logged
- **Comments required**: Optional but recommended for transparency

## Future Enhancements

1. Email notifications for approval requests
2. Multi-level approvals (junior/senior reviewer)
3. Expiry time for pending approvals
4. Dashboard badge showing pending count
5. Approver assignment workflows
6. Bulk approval operations

## Troubleshooting

### "Reviewer access required" error
- **Solution**: User must have `role = 'reviewer'` or `role = 'admin'` in database

### No approvals showing
- **Solution**: Check that leases have `approval_status = 'pending'`

### Can't submit for approval
- **Solution**: Lease must be saved first (have a lease_id)

## Database Utilities

```bash
# Make user a reviewer
python make_reviewer.py username

# Make user an admin  
python make_admin.py username

# Create new user
python lease_application/create_user.py username password email@example.com
```

## Example Workflow

**Alice (Maker):**
1. Creates lease "Office Space - NYC"
2. Saves draft
3. Submits for approval with comment: "Annual escalation 3%"
4. Status: `pending`

**Bob (Reviewer):**
1. Logs in, sees "✅ Approvals" button
2. Clicks and sees Alice's request
3. Reviews details
4. Approves with comment: "Approved. Good terms."
5. Status: `approved`

**Alice:**
1. Refreshes dashboard
2. Sees "Office Space - NYC" is now active ✅


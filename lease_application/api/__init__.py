"""
API Routes Module
Handles lease management API endpoints

VBA Source: None (new functionality - replaces direct Flask routes)
"""

from flask import Blueprint, request, jsonify, session
import logging
import database

logger = logging.getLogger(__name__)

# Import require_login decorator
from auth import require_login

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/leases', methods=['GET'])
@require_login
def get_leases():
    """Get all leases for current user (or all leases if admin)"""
    user_id = session['user_id']
    
    # Check if user is admin
    user = database.get_user(user_id)
    is_admin = user and user.get('role') == 'admin'
    
    logger.info(f"📋 GET /api/leases - User {user_id} {'(Admin)' if is_admin else ''} fetching leases")
    
    if is_admin:
        leases = database.get_all_leases_admin()
    else:
        leases = database.get_all_leases(user_id)
    
    logger.info(f"Found {len(leases)} leases for user {user_id}")
    return jsonify({'success': True, 'leases': leases})


@api_bp.route('/leases/<int:lease_id>', methods=['GET'])
@require_login
def get_lease(lease_id):
    """Get a specific lease"""
    user_id = session['user_id']
    
    # Check if user is admin
    user = database.get_user(user_id)
    is_admin = user and user.get('role') == 'admin'
    
    logger.info(f"🔍 GET /api/leases/{lease_id} - User {user_id} {'(Admin)' if is_admin else ''} fetching lease")
    
    if is_admin:
        # Admin can access any lease
        all_leases = database.get_all_leases_admin()
        lease = next((l for l in all_leases if l['lease_id'] == lease_id), None)
    else:
        # Regular user can only access their own leases
        lease = database.get_lease(lease_id, user_id)
    
    if lease:
        logger.info(f"Lease {lease_id} found")
        return jsonify({'success': True, 'lease': dict(lease)})
    logger.warning(f"Lease {lease_id} not found for user {user_id}")
    return jsonify({'error': 'Lease not found'}), 404


@api_bp.route('/leases', methods=['POST'])
@require_login
def create_lease():
    """Create a new lease"""
    user_id = session['user_id']
    logger.info(f"➕ POST /api/leases - User {user_id} creating lease")
    data = request.json
    logger.debug(f"Request data keys: {list(data.keys()) if data else 'No data'}")
    
    # Filter only valid database columns
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
    
    # Handle both update and create
    lease_id_param = data.get('lease_id')
    is_update = lease_id_param and str(lease_id_param).isdigit()
    logger.info(f"Operation: {'UPDATE' if is_update else 'CREATE'}")
    
    # Create filtered data with only valid columns
    filtered_data = {k: v for k, v in data.items() if k in valid_columns or k == 'user_id'}
    
    # Set lease_name to Lease_XXX format
    if 'lease_name' not in filtered_data or not filtered_data['lease_name']:
        user_leases = database.get_all_leases(user_id)
        next_num = len(user_leases) + 1
        filtered_data['lease_name'] = f"Lease_{str(next_num).zfill(3)}"
        logger.info(f"Generated lease_name: {filtered_data['lease_name']}")
    
    # Add lease_id if updating
    if is_update:
        filtered_data['lease_id'] = int(lease_id_param)
        logger.info(f"Updating lease_id: {lease_id_param}")
    
    lease_id = database.save_lease(user_id, filtered_data)
    logger.info(f"✅ Lease saved: lease_id={lease_id}")
    return jsonify({
        'success': True,
        'lease_id': lease_id,
        'message': 'Lease saved successfully'
    }), 201


@api_bp.route('/leases/<int:lease_id>', methods=['PUT'])
@require_login
def update_lease(lease_id):
    """Update an existing lease"""
    user_id = session['user_id']
    
    # Check if user is admin
    user = database.get_user(user_id)
    is_admin = user and user.get('role') == 'admin'
    
    logger.info(f"✏️ PUT /api/leases/{lease_id} - User {user_id} {'(Admin)' if is_admin else ''} updating lease")
    data = request.json
    
    # Filter only valid database columns (same as create)
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
    
    filtered_data = {k: v for k, v in data.items() if k in valid_columns}
    filtered_data['lease_id'] = lease_id
    filtered_data['user_id'] = user_id
    
    # For admin, use save_lease_admin; for regular users, use regular save_lease
    if is_admin:
        # Admin can update any lease - need to find original user_id
        all_leases = database.get_all_leases_admin()
        original_lease = next((l for l in all_leases if l['lease_id'] == lease_id), None)
        if original_lease:
            updated_id = database.save_lease(original_lease['user_id'], filtered_data)
        else:
            return jsonify({'error': 'Lease not found'}), 404
    else:
        updated_id = database.save_lease(user_id, filtered_data)
    
    logger.info(f"✅ Lease updated: lease_id={updated_id}")
    return jsonify({
        'success': True,
        'lease_id': updated_id,
        'message': 'Lease updated successfully'
    })


@api_bp.route('/leases/bulk', methods=['GET'])
@require_login
def get_leases_for_bulk():
    """Get leases with filters for bulk processing"""
    user_id = session['user_id']
    
    # Check if user is admin
    user = database.get_user(user_id)
    is_admin = user and user.get('role') == 'admin'
    
    logger.info(f"📋 GET /api/leases/bulk - User {user_id} {'(Admin)' if is_admin else ''} fetching leases for bulk processing")
    
    # Get optional filters from query parameters
    cost_center = request.args.get('cost_center')
    entity = request.args.get('entity')
    asset_class = request.args.get('asset_class')
    profit_center = request.args.get('profit_center')
    
    # Get all leases - admin gets all, regular user gets their own
    if is_admin:
        leases = database.get_all_leases_admin()
    else:
        leases = database.get_all_leases(user_id)
    
    # Apply filters if provided
    filtered_leases = leases
    if cost_center:
        filtered_leases = [l for l in filtered_leases if l.get('cost_centre') == cost_center]
    if entity:
        filtered_leases = [l for l in filtered_leases if l.get('group_entity_name') == entity]
    if asset_class:
        filtered_leases = [l for l in filtered_leases if l.get('asset_class') == asset_class]
    if profit_center:
        filtered_leases = [l for l in filtered_leases if l.get('profit_center') == profit_center]
    
    logger.info(f"Found {len(filtered_leases)} leases (filtered from {len(leases)})")
    return jsonify({'success': True, 'leases': filtered_leases})


@api_bp.route('/leases/<int:lease_id>', methods=['DELETE'])
@require_login
def delete_lease(lease_id):
    """Delete a lease"""
    user_id = session['user_id']
    
    # Check if user is admin
    user = database.get_user(user_id)
    is_admin = user and user.get('role') == 'admin'
    
    logger.info(f"🗑️ DELETE /api/leases/{lease_id} - User {user_id} {'(Admin)' if is_admin else ''} deleting lease")
    
    if is_admin:
        # Admin can delete any lease - need to find original user_id
        all_leases = database.get_all_leases_admin()
        original_lease = next((l for l in all_leases if l['lease_id'] == lease_id), None)
        if original_lease:
            success = database.delete_lease(lease_id, original_lease['user_id'])
        else:
            return jsonify({'error': 'Lease not found'}), 404
    else:
        success = database.delete_lease(lease_id, user_id)
    
    if success:
        logger.info(f"✅ Lease {lease_id} deleted")
        return jsonify({'success': True, 'message': 'Lease deleted'})
    logger.warning(f"❌ Lease {lease_id} not found or not owned by user {user_id}")
    return jsonify({'error': 'Lease not found'}), 404


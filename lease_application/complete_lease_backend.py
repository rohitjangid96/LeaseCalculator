"""
Lease Calculation Backend API
Handles lease calculation requests and returns schedules, journal entries, and results

VBA Source: VB script/Code, compu() Sub
"""

from flask import Blueprint, request, jsonify, session
from datetime import date, datetime
from typing import Optional, List
import logging
from lease_accounting.core.models import LeaseData, ProcessingFilters
from lease_accounting.core.results_processor import ResultsProcessor
import database
from auth import require_login

# Create blueprint
calc_bp = Blueprint('calc', __name__, url_prefix='/api')

logger = logging.getLogger(__name__)


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string to date object"""
    if not date_str:
        return None
    try:
        if isinstance(date_str, str):
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        return date_str
    except (ValueError, TypeError):
        return None


@calc_bp.route('/calculate_lease', methods=['POST'])
def calculate_lease():
    """
    Main endpoint for lease calculation
    Returns complete schedule, journal entries, and results
    """
    try:
        data = request.json
        
        # DEBUG: Log incoming data
        logger.info(f"📥 Received calculation request:")
        logger.info(f"   rental_1: {data.get('rental_1', 'NOT PROVIDED')}")
        logger.info(f"   lease_start: {data.get('lease_start_date')}, end: {data.get('end_date')}")
        logger.info(f"   from_date: {data.get('from_date')}, to_date: {data.get('to_date')}")
        
        # Validation: Check for common issues
        rental_1_val = float(data.get('rental_1', 0) or 0)
        lease_start = _parse_date(data.get('lease_start_date'))
        end_date = _parse_date(data.get('end_date'))
        
        if rental_1_val == 0:
            logger.warning(f"⚠️  rental_1 is 0 - no payments will be generated!")
        
        if lease_start and end_date and lease_start >= end_date:
            logger.warning(f"⚠️  Lease end date ({end_date}) must be AFTER start date ({lease_start})!")
        
        # Parse lease data from form
        lease_data = LeaseData(
            auto_id=data.get('auto_id', 1),
            description=data.get('description', ''),
            asset_class=data.get('asset_class', ''),
            asset_id_code=data.get('asset_id_code', ''),
            
            # Dates
            lease_start_date=_parse_date(data.get('lease_start_date')),
            first_payment_date=_parse_date(data.get('first_payment_date')),
            end_date=_parse_date(data.get('end_date')),
            agreement_date=_parse_date(data.get('agreement_date')),
            termination_date=_parse_date(data.get('termination_date')),
            
            # Financial Terms
            tenure=float(data.get('tenure', 0) or 0),
            frequency_months=int(data.get('frequency_months', 1)),
            day_of_month=str(data.get('day_of_month', '1')),
            
            # Payments
            auto_rentals=data.get('auto_rentals', 'Yes'),
            manual_adj="Yes" if str(data.get('manual_adj', '')).lower() in ['yes', 'on', 'true', '1'] else "No",
            rental_1=float(data.get('rental_1', 0) or 0),
            rental_2=float(data.get('rental_2', 0) or 0),
            
            # Escalation
            escalation_start=_parse_date(data.get('escalation_start_date') or data.get('Escalation_Start')),
            escalation_percent=float(data.get('escalation_percent', 0) or 0),
            esc_freq_months=int(data.get('esc_freq_months', 12) or data.get('Esc_Freq_months', 12) or 12),
            accrual_day=int(data.get('accrual_day', 1) or 1),
            index_rate_table=data.get('index_rate_table'),
            
            # Rates
            borrowing_rate=float(data.get('borrowing_rate', 8) or 8),
            compound_months=int(data.get('compound_months')) if data.get('compound_months') else None,
            fv_of_rou=float(data.get('fv_of_rou', 0) or 0),
            
            # Residual
            bargain_purchase=data.get('bargain_purchase', 'No'),
            purchase_option_price=float(data.get('purchase_option_price', 0) or 0),
            title_transfer=data.get('title_transfer', 'No'),
            useful_life=_parse_date(data.get('useful_life_end_date')),
            
            # Entity
            currency=data.get('currency', 'USD'),
            cost_centre=data.get('cost_centre', ''),
            counterparty=data.get('counterparty', ''),
            
            # Security - With increases
            security_deposit=float(data.get('security_deposit', 0) or 0),
            security_discount=float(data.get('security_discount', 0) or 0),
            increase_security_1=float(data.get('increase_security_1', 0) or 0),
            increase_security_2=float(data.get('increase_security_2', 0) or 0),
            increase_security_3=float(data.get('increase_security_3', 0) or 0),
            increase_security_4=float(data.get('increase_security_4', 0) or 0),
            security_dates=[
                _parse_date(data.get('security_date_1')),
                _parse_date(data.get('security_date_2')),
                _parse_date(data.get('security_date_3')),
                _parse_date(data.get('security_date_4')),
            ],
            
            # ARO
            aro=float(data.get('aro', 0) or 0),
            aro_table=int(data.get('aro_table', 0) or 0),
            aro_revisions=[
                float(data.get('aro_revision_1', 0) or 0),
                float(data.get('aro_revision_2', 0) or 0),
                float(data.get('aro_revision_3', 0) or 0),
                float(data.get('aro_revision_4', 0) or 0),
            ],
            aro_dates=[
                _parse_date(data.get('aro_date_1')),
                _parse_date(data.get('aro_date_2')),
                _parse_date(data.get('aro_date_3')),
                _parse_date(data.get('aro_date_4')),
            ],
            
            # Initial Costs
            initial_direct_expenditure=float(data.get('initial_direct_expenditure', 0) or 0),
            lease_incentive=float(data.get('lease_incentive', 0) or 0),
            
            # Modifications
            modifies_this_id=int(data.get('modifies_this_id', 0) or 0) if data.get('modifies_this_id') else None,
            modified_by_this_id=int(data.get('modified_by_this_id', 0) or 0) if data.get('modified_by_this_id') else None,
            date_modified=_parse_date(data.get('date_modified')),
            
            # Sublease
            sublease=data.get('sublease', 'No'),
            sublease_rou=float(data.get('sublease_rou', 0) or 0),
            
            # Other
            profit_center=data.get('profit_center', ''),
            group_entity_name=data.get('group_entity_name', ''),
            short_term_lease_ifrs=data.get('short_term_ifrs', 'No'),
            short_term_lease_usgaap=data.get('finance_lease', 'No'),  # Simplified mapping
        )
        
        # Parse manual rental dates and amounts (rental_date_2, rental_date_3, ... rental_date_20)
        # and corresponding rental amounts (rental_2, rental_3, ... rental_20)
        rental_dates = []
        rental_amounts = []
        for i in range(2, 21):  # rental_date_2 through rental_date_20
            rental_date_key = f'Rental_date_{i}' if i >= 2 else f'rental_date_{i}'
            rental_amount_key = f'Rental_{i}' if i >= 2 else f'rental_{i}'
            
            # Try both capitalized and lowercase field names
            rental_date = _parse_date(data.get(rental_date_key) or data.get(rental_date_key.lower()) or data.get(f'rental_date_{i}'))
            rental_amount = float(data.get(rental_amount_key, 0) or data.get(rental_amount_key.lower(), 0) or data.get(f'rental_{i}', 0) or 0)
            
            if rental_date and rental_amount:
                rental_dates.append(rental_date)
                rental_amounts.append(rental_amount)
        
        # Set rental_dates and rental_amounts on lease_data
        if rental_dates:
            lease_data.rental_dates = rental_dates
            # Store rental amounts in a way we can access them
            # VBA uses rental_2, rental_3, etc. by index
            # We'll store them as a dictionary indexed by rental date
            if not hasattr(lease_data, 'rental_amounts_by_date'):
                lease_data.rental_amounts_by_date = {}
            for i, (rdate, ramount) in enumerate(zip(rental_dates, rental_amounts)):
                lease_data.rental_amounts_by_date[rdate] = ramount
        
        # Parse date range filters
        from_date = _parse_date(data.get('from_date'))
        to_date = _parse_date(data.get('to_date'))
        
        if not from_date:
            from_date = lease_data.lease_start_date or date.today()
        if not to_date:
            to_date = lease_data.end_date or date.today()
        
        # Create filters
        filters = ProcessingFilters(
            start_date=from_date,
            end_date=to_date,
            gaap_standard=data.get('gaap_standard', 'IFRS')
        )
        
        # Set gaap_standard on lease_data so it's available for schedule generation
        lease_data.gaap_standard = filters.gaap_standard
        
        # Import here to avoid circular imports
        from lease_accounting.schedule.generator_vba_complete import generate_complete_schedule
        from lease_accounting.core.processor import LeaseProcessor
        from lease_accounting.utils.journal_generator import JournalGenerator
        
        # Generate full schedule (VBA: datessrent + basic_calc)
        logger.info("📅 Generating payment schedule...")
        full_schedule = generate_complete_schedule(lease_data)
        
        if not full_schedule:
            return jsonify({'error': 'Failed to generate schedule - check lease parameters'}), 400
        
        logger.info(f"✅ Generated {len(full_schedule)} schedule rows")
        
        # Process lease (VBA: compu() main logic)
        logger.info("🔄 Processing lease...")
        processor = LeaseProcessor(filters)
        result = processor.process_single_lease(lease_data)
        
        if not result:
            return jsonify({'error': 'Failed to process lease'}), 400
        
        logger.info(f"✅ Lease processed: Opening Liability={result.opening_lease_liability:,.2f}, Closing={result.closing_lease_liability_current + result.closing_lease_liability_non_current:,.2f}")
        
        # Filter schedule by date range if provided (VBA: Only summary changes, schedule always full)
        # Note: VBA always shows full schedule, only opening/closing balances change with date range
        schedule = list(full_schedule)
        
        # VBA: If to_date is not a payment date, INSERT row and COPY values from previous row
        if to_date:
            # Check if to_date exists in schedule
            to_date_exists = any(row.date == to_date for row in schedule)
            
            if not to_date_exists:
                # Find where to insert
                for i, row in enumerate(schedule):
                    if row.date > to_date:
                        # Insert new row before this one, copying previous row values
                        prev_row = schedule[i-1] if i > 0 else row
                        from lease_accounting.core.models import PaymentScheduleRow
                        new_row = PaymentScheduleRow(
                            date=to_date,
                            rental_amount=0.0,  # No payment on interpolated row
                            pv_factor=prev_row.pv_factor,
                            interest=0.0,
                            lease_liability=prev_row.lease_liability,
                            pv_of_rent=0.0,
                            rou_asset=prev_row.rou_asset,
                            depreciation=0.0,
                            change_in_rou=0.0,
                            security_deposit_pv=prev_row.security_deposit_pv,
                            aro_gross=prev_row.aro_gross,
                            aro_interest=0.0,
                            aro_provision=prev_row.aro_provision,
                            principal=0.0,
                            remaining_balance=None
                        )
                        schedule.insert(i, new_row)
                        break
        
        # Generate journal entries
        logger.info("📝 Generating journal entries...")
        journal_gen = JournalGenerator(gaap_standard=filters.gaap_standard)  # Use GAAP from filters
        journals = journal_gen.generate_journals(result, schedule, None)
        
        # Prepare response
        response = {
            'lease_result': result.to_dict(),
            'schedule': [row.to_dict() for row in schedule],
            'journal_entries': [j.to_dict() for j in journals],
            'date_range': {
                'filtered': bool(from_date or to_date),
                'from_date': from_date.isoformat() if from_date else None,
                'to_date': to_date.isoformat() if to_date else None,
            }
        }
        
        logger.info("✅ Calculation complete")
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"❌ Error in calculate_lease: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@calc_bp.route('/calculate_leases', methods=['POST'])
@require_login
def calculate_leases():
    """
    Bulk lease processing endpoint
    Processes multiple leases and returns consolidated results
    
    VBA Source: VB script/Code, compu() Sub (Lines 316-605)
    Main loop: For ai = G2 To G3
    """
    try:
        user_id = session['user_id']
        data = request.json
        
        logger.info(f"📥 Received bulk calculation request from user {user_id}")
        
        # Parse filters
        from_date = _parse_date(data.get('from_date'))
        to_date = _parse_date(data.get('to_date'))
        
        if not from_date or not to_date:
            return jsonify({'error': 'from_date and to_date are required'}), 400
        
        # Get lease IDs to process
        lease_ids = data.get('lease_ids', [])
        
        # Check if user is admin
        from database import get_user
        user = get_user(user_id)
        is_admin = user and user.get('role') == 'admin'
        
        if not lease_ids:
            # Get all leases - admin gets all, regular user gets their own
            if is_admin:
                all_leases = database.get_all_leases_admin()
            else:
                all_leases = database.get_all_leases(user_id)
            # Filter to only approved leases for calculations
            approved_leases = [lease for lease in all_leases if lease.get('approval_status') == 'approved' or lease.get('approval_status') is None]
            lease_ids = [lease['lease_id'] for lease in approved_leases]
        
        logger.info(f"   Processing {len(lease_ids)} leases from {from_date} to {to_date}")
        
        # Parse additional filters
        filters = ProcessingFilters(
            start_date=from_date,
            end_date=to_date,
            start_lease_id=data.get('start_lease_id'),
            end_lease_id=data.get('end_lease_id'),
            cost_center_filter=data.get('cost_center'),
            entity_filter=data.get('entity'),
            asset_class_filter=data.get('asset_class'),
            profit_center_filter=data.get('profit_center'),
            gaap_standard=data.get('gaap_standard', 'IFRS')
        )
        
        # Load lease data from database
        lease_data_list = []
        for lease_id in lease_ids:
            # Admin can load any lease, regular user only their own
            if is_admin:
                all_leases_admin = database.get_all_leases_admin()
                lease_dict = next((l for l in all_leases_admin if l['lease_id'] == lease_id), None)
            else:
                lease_dict = database.get_lease(lease_id, user_id)
            
            if not lease_dict:
                logger.warning(f"⚠️  Lease {lease_id} not found")
                continue
            
            # Convert dict to LeaseData
            lease_data = _dict_to_lease_data(lease_dict)
            lease_data.auto_id = lease_id
            # Set gaap_standard from filters so it's available for schedule generation
            lease_data.gaap_standard = filters.gaap_standard
            lease_data_list.append(lease_data)
        
        if not lease_data_list:
            return jsonify({'error': 'No valid leases found to process'}), 400
        
        logger.info(f"   Loaded {len(lease_data_list)} leases")
        
        # Check if GAAP comparison is requested
        include_gaap_comparison = data.get('include_gaap_comparison', False)
        gaap_comparison_results = {}
        
        if include_gaap_comparison:
            # Calculate for all GAAP standards
            for gaap_std in ['IFRS', 'IndAS', 'US-GAAP']:
                logger.info(f"   Computing results for {gaap_std}...")
                gaap_filters = ProcessingFilters(
                    start_date=from_date,
                    end_date=to_date,
                    start_lease_id=data.get('start_lease_id'),
                    end_lease_id=data.get('end_lease_id'),
                    cost_center_filter=data.get('cost_center'),
                    entity_filter=data.get('entity'),
                    asset_class_filter=data.get('asset_class'),
                    profit_center_filter=data.get('profit_center'),
                    gaap_standard=gaap_std
                )
                
                # Set GAAP standard on each lease data
                for lease_data in lease_data_list:
                    lease_data.gaap_standard = gaap_std
                
                # Process with this GAAP standard
                gaap_results_processor = ResultsProcessor(gaap_filters)
                gaap_bulk_results = gaap_results_processor.process_bulk_leases(lease_data_list)
                gaap_comparison_results[gaap_std] = {
                    'results': gaap_bulk_results['results'],
                    'aggregated_totals': gaap_bulk_results['aggregated_totals'],
                    'stats': {
                        'processed_count': gaap_bulk_results['processed_count'],
                        'skipped_count': gaap_bulk_results['skipped_count'],
                        'total_count': gaap_bulk_results['total_count']
                    }
                }
        
        # Process bulk leases for the selected GAAP standard
        results_processor = ResultsProcessor(filters)
        bulk_results = results_processor.process_bulk_leases(lease_data_list)
        
        # Save results summary to database
        import json
        summary_data = {
            'summary_id': None,
            'user_id': user_id,
            'calculation_date': datetime.now().isoformat(),
            'from_date': from_date.isoformat(),
            'to_date': to_date.isoformat(),
            'filters_applied': json.dumps({
                'cost_center': filters.cost_center_filter,
                'entity': filters.entity_filter,
                'asset_class': filters.asset_class_filter,
                'profit_center': filters.profit_center_filter,
                'gaap_standard': filters.gaap_standard
            }),
            'results_data': json.dumps(bulk_results['results']),
            'aggregated_totals': json.dumps(bulk_results['aggregated_totals']),
            'consolidated_journals': json.dumps(bulk_results['consolidated_journals']),
            'processed_count': bulk_results['processed_count'],
            'skipped_count': bulk_results['skipped_count']
        }
        
        # Save to database  
        with database.get_db_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO results_summary 
                (user_id, from_date, to_date, filters_applied, results_data, 
                 aggregated_totals, consolidated_journals, processed_count, skipped_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                summary_data['user_id'],
                summary_data['from_date'],
                summary_data['to_date'],
                summary_data['filters_applied'],
                summary_data['results_data'],
                summary_data['aggregated_totals'],
                summary_data['consolidated_journals'],
                summary_data['processed_count'],
                summary_data['skipped_count']
            ))
            summary_id = cursor.lastrowid
            summary_data['summary_id'] = summary_id
        
        logger.info(f"✅ Bulk processing complete: {bulk_results['processed_count']} processed, {bulk_results['skipped_count']} skipped")
        
        # Generate disclosures if requested
        disclosures = None
        if data.get('include_disclosures', False):
            from lease_accounting.utils.disclosures_generator import DisclosuresGenerator
            from lease_accounting.schedule.generator_vba_complete import generate_complete_schedule
            
            # Generate schedules for all leases
            schedule_list = []
            for lease_data in lease_data_list:
                schedule = generate_complete_schedule(lease_data)
                schedule_list.append(schedule or [])
            
            # Get results for disclosures
            disclosures_gen = DisclosuresGenerator()
            disclosures = disclosures_gen.generate_disclosures(
                lease_results=[r for r in bulk_results['results'] if r],  # Convert dict results
                lease_data_list=lease_data_list,
                schedule_list=schedule_list,
                balance_date=to_date,
                gaap_standard=filters.gaap_standard
            )
        
        response_data = {
            'success': True,
            'summary_id': summary_id,
            'results': bulk_results['results'],
            'aggregated_totals': bulk_results['aggregated_totals'],
            'consolidated_journals': bulk_results['consolidated_journals'],
            'disclosures': disclosures,  # Include disclosures if generated
            'filters': {
                'from_date': from_date.isoformat(),
                'to_date': to_date.isoformat(),
                'gaap_standard': filters.gaap_standard
            },
            'stats': {
                'processed_count': bulk_results['processed_count'],
                'skipped_count': bulk_results['skipped_count'],
                'total_count': bulk_results['total_count']
            }
        }
        
        # Add GAAP comparison results if requested
        if include_gaap_comparison and gaap_comparison_results:
            response_data['gaap_comparison'] = gaap_comparison_results
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"❌ Error in calculate_leases: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def _dict_to_lease_data(lease_dict: dict) -> LeaseData:
    """Convert database lease dict to LeaseData object"""
    manual_adj_value = lease_dict.get('manual_adj', 'No')
    manual_adj = "Yes" if str(manual_adj_value).lower() in ['yes', 'on', 'true', '1'] else "No"
    
    lease_data = LeaseData(
        auto_id=lease_dict.get('lease_id', 0),
        description=lease_dict.get('description', ''),
        asset_class=lease_dict.get('asset_class', ''),
        asset_id_code=lease_dict.get('asset_id_code', ''),
        lease_start_date=_parse_date(lease_dict.get('lease_start_date')),
        first_payment_date=_parse_date(lease_dict.get('first_payment_date')),
        end_date=_parse_date(lease_dict.get('end_date')),
        agreement_date=_parse_date(lease_dict.get('agreement_date')),
        termination_date=_parse_date(lease_dict.get('termination_date')),
        tenure=float(lease_dict.get('tenure', 0) or 0),
        frequency_months=int(lease_dict.get('frequency_months', 1) or 1),
        day_of_month=str(lease_dict.get('day_of_month', '1')),
        auto_rentals=lease_dict.get('auto_rentals', 'Yes'),
        manual_adj=manual_adj,
        rental_1=float(lease_dict.get('rental_1', 0) or 0),
        rental_2=float(lease_dict.get('rental_2', 0) or 0),
        escalation_start=_parse_date(lease_dict.get('escalation_start_date')),
        escalation_percent=float(lease_dict.get('escalation_percent', 0) or 0),
        esc_freq_months=int(lease_dict.get('esc_freq_months', 12) or 12),
        accrual_day=int(lease_dict.get('accrual_day', 1) or 1),
        borrowing_rate=float(lease_dict.get('borrowing_rate', 0) or 0),
        compound_months=int(lease_dict.get('compound_months')) if lease_dict.get('compound_months') else None,
        currency=lease_dict.get('currency', 'USD'),
        cost_centre=lease_dict.get('cost_centre', ''),
        counterparty=lease_dict.get('counterparty', ''),
        security_deposit=float(lease_dict.get('security_deposit', 0) or 0),
        security_discount=float(lease_dict.get('security_discount', 0) or 0),
        aro=float(lease_dict.get('aro', 0) or 0),
        aro_table=int(lease_dict.get('aro_table', 0) or 0),
        initial_direct_expenditure=float(lease_dict.get('initial_direct_expenditure', 0) or 0),
        lease_incentive=float(lease_dict.get('lease_incentive', 0) or 0),
        sublease=lease_dict.get('sublease', 'No'),
        date_modified=_parse_date(lease_dict.get('date_modified')),
        profit_center=lease_dict.get('profit_center', ''),
        group_entity_name=lease_dict.get('group_entity_name', ''),
        short_term_lease_ifrs=lease_dict.get('shortterm_lease_ifrs_indas', 'No'),
        short_term_lease_usgaap=lease_dict.get('finance_lease_usgaap', 'No'),
    )
    
    # Parse manual rental dates and amounts from database if stored as JSON
    # Note: Database doesn't store rental_dates directly, so we'll need to reconstruct
    # from rental_date_2, rental_date_3, etc. if they're stored separately
    # For now, rental_dates will be empty and populated from payload when calculating
    
    return lease_data

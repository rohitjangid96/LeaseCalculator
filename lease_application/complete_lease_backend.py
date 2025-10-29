"""
Complete Lease Accounting Backend
Integrates all components for end-to-end processing
"""

from flask import Flask, Blueprint, request, jsonify
from flask_cors import CORS
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import sys
import os

# Add lease_accounting to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lease_accounting'))

from core.models import LeaseData, LeaseResult, PaymentScheduleRow, ProcessingFilters
from core.processor import LeaseProcessor
from schedule.generator_vba_complete import generate_complete_schedule
from utils.journal_generator import generate_lease_journal
from utils.rfr_rates import RFRRateTable

# Create blueprint for route registration
calc_bp = Blueprint('calc', __name__, url_prefix='/api')


@calc_bp.route('/calculate_lease', methods=['POST'])
def calculate_lease():
    """
    Main endpoint for lease calculation
    Returns complete schedule, journal entries, and results
    """
    try:
        data = request.json
        
        # DEBUG: Log incoming data
        import logging
        logger = logging.getLogger(__name__)
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
            compound_months=int(data.get('compound_months', 12) or 12),
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
            security_dates=_parse_date_array(data, 'security_date', 4),
            
            # ARO - With revisions
            aro=float(data.get('aro_initial', 0) or data.get('aro', 0) or 0),
            aro_table=int(data.get('aro_table', 0) or 0),
            aro_revisions=_parse_float_array(data, 'aro_revision', 8),
            aro_dates=_parse_date_array(data, 'aro_date', 8),
            
            # Manual Rentals
            manual_adj=data.get('manual_adj', 'No'),
            rental_dates=_parse_date_array(data, 'rental_date', 20),  # Up to 20 manual rentals
            
            # Costs
            initial_direct_expenditure=float(data.get('initial_direct_costs', 0) or data.get('initial_direct_expenditure', 0) or 0),
            lease_incentive=float(data.get('lease_incentive', 0) or 0),
            prepaid_accrual=float(data.get('prepaid_accrual', 0) or 0),
            
            # Sublease
            sublease=data.get('is_sublease', 'No'),
            sublease_rou=float(data.get('sublease_rou', 0) or 0),
            
            # Lease Modifications
            modifies_this_id=int(data.get('modifies_this_id', 0) or 0) or None,
            modified_by_this_id=int(data.get('modified_by_this_id', 0) or 0) or None,
            date_modified=_parse_date(data.get('date_modified')),
            
            # Impairments
            impairment1=float(data.get('impairment1', 0) or 0),
            impairment2=float(data.get('impairment2', 0) or 0),
            impairment3=float(data.get('impairment3', 0) or 0),
            impairment4=float(data.get('impairment4', 0) or 0),
            impairment5=float(data.get('impairment5', 0) or 0),
            impairment_dates=_parse_date_array(data, 'impairment_date', 5),
            
            # Transition
            transition_option=data.get('transition_option'),
            transition_date=_parse_date(data.get('transition_date')),
            
            # Termination
            termination_penalty=float(data.get('termination_penalty', 0) or 0),
            
            # Special Classifications
            finance_lease_usgaap=data.get('finance_lease', 'No'),
            short_term_lease_ifrs=data.get('short_term_ifrs', 'No'),
            practical_expedient=data.get('practical_expedient', 'No'),
        )
        
        # Get date range filters if provided (matching VBA: opendate = D2-1, baldate = D3)
        from_date_str = data.get('from_date')
        to_date_str = data.get('to_date')
        from_date = _parse_date(from_date_str) if from_date_str else None
        to_date = _parse_date(to_date_str) if to_date_str else None
        
        # Import logging
        import logging
        logger = logging.getLogger(__name__)
        
        # Generate COMPLETE schedule (full lease period) - VBA logic: never filter schedule
        # Schedule is generated for entire lease, then we calculate opening/closing/activity
        full_schedule = generate_complete_schedule(lease_data)
        
        if not full_schedule:
            logger.warning(f"⚠️  No schedule generated. lease_start={lease_data.lease_start_date}, end={lease_data.end_date}, rental_1={lease_data.rental_1}")
            return jsonify({'error': 'Failed to generate schedule'}), 400
        
        logger.info(f"📊 Generated full schedule: {len(full_schedule)} rows")
        if full_schedule:
            first_row = full_schedule[0]
            logger.info(f"   First row: date={first_row.date}, rental={first_row.rental_amount}, liability={first_row.lease_liability}, ROU={first_row.rou_asset}")
            if len(full_schedule) > 1:
                logger.info(f"   Last row: date={full_schedule[-1].date}, rental={full_schedule[-1].rental_amount}, liability={full_schedule[-1].lease_liability}")
            
            # Check if all values are zero (indicates data issue)
            if first_row.lease_liability == 0 and first_row.rental_amount == 0:
                warning_msg = f"⚠️  All values are zero! Possible issues: "
                issues = []
                if lease_data.rental_1 == 0:
                    issues.append("rental_1=0 (no payments)")
                if lease_data.lease_start_date == lease_data.end_date:
                    issues.append(f"start_date=end_date ({lease_data.lease_start_date})")
                if lease_data.lease_start_date > lease_data.end_date:
                    issues.append(f"end_date before start_date")
                warning_msg += ", ".join(issues)
                logger.warning(warning_msg)
        
        # Use LeaseProcessor if date range provided (matches VBA compu() logic)
        if from_date and to_date:
            logger.info(f"📅 Date range filtering: from {from_date} to {to_date}")
            logger.info(f"   VBA: opendate = from_date - 1 = {from_date - timedelta(days=1)}")
            logger.info(f"   VBA: baldate = to_date = {to_date}")
            
            from lease_accounting.core.processor import LeaseProcessor, ProcessingFilters
            
            # VBA: opendate = D2 - 1, baldate = D3
            opening_date = from_date - timedelta(days=1)
            closing_date = to_date
            
            # Create filters
            filters = ProcessingFilters(
                start_date=opening_date,  # Opening date (from_date - 1)
                end_date=closing_date,    # Closing date (to_date)
                gaap_standard="IFRS"
            )
            
            processor = LeaseProcessor(filters)
            result = processor.process_single_lease(lease_data)
            
            if not result:
                return jsonify({
                    'success': True,
                    'message': f'No lease activity in date range ({from_date_str} to {to_date_str})',
                    'schedule': [],
                    'journal_entries': [],
                    'summary': {'total_payments': 0, 'total_interest': 0, 'total_depreciation': 0, 
                              'total_rent_paid': 0, 'opening_liability': 0, 'closing_liability': 0}
                })
            
            # CRITICAL FIX: If opening_date is before lease start OR before first payment date, use first schedule row's liability
            first_payment_date = lease_data.first_payment_date if lease_data.first_payment_date else lease_data.lease_start_date
            if full_schedule and (opening_date < lease_data.lease_start_date or opening_date < first_payment_date):
                first_row = full_schedule[0]
                # Use first row if opening_date is before any payment occurs
                result.opening_lease_liability = first_row.lease_liability or 0.0
                result.opening_rou_asset = first_row.rou_asset or 0.0
                result.opening_aro_liability = first_row.aro_provision or 0.0
                result.opening_security_deposit = first_row.security_deposit_pv or 0.0
                logger.info(f"   Adjusted opening balances (opening_date={opening_date} < first_payment={first_payment_date}): liability={result.opening_lease_liability}")
            elif full_schedule and result.opening_lease_liability == 0:
                # Fallback: If LeaseProcessor returned 0, check if it's because opening_date is before first payment
                first_row_date = full_schedule[0].date
                if opening_date < first_row_date:
                    first_row = full_schedule[0]
                    result.opening_lease_liability = first_row.lease_liability or 0.0
                    result.opening_rou_asset = first_row.rou_asset or 0.0
                    result.opening_aro_liability = first_row.aro_provision or 0.0
                    result.opening_security_deposit = first_row.security_deposit_pv or 0.0
                    logger.info(f"   Fallback: Used first row (opening_date={opening_date} < first_row_date={first_row_date}): liability={result.opening_lease_liability}")
            
            # CRITICAL: Update closing balances to use the interpolated row at to_date
            # The result from processor may have calculated closing at last payment date
            # We need to ensure closing balances reflect the interpolated row at to_date
            from lease_accounting.core.processor import LeaseProcessor
            # Re-get closing balances at to_date to ensure they're correct
            closing_liab, closing_rou, closing_aro, closing_sec = processor.get_closing_balances(full_schedule, to_date)
            
            # Update result with correct closing balances
            closing_total = abs(closing_liab) if closing_liab > 0 else 0
            result.closing_lease_liability_current = closing_total * 0.3
            result.closing_lease_liability_non_current = closing_total * 0.7
            result.closing_rou_asset = closing_rou
            result.closing_aro_liability = closing_aro
            result.closing_security_deposit = closing_sec
            
            logger.info(f"   Closing balances at {to_date}: liability={closing_total:,.2f}, ROU={closing_rou:,.2f}")
            
            # VBA LOGIC: Schedule is NEVER filtered - always show full schedule
            # Only SUMMARY (opening/closing balances, period activity) changes with from_date/to_date
            # VBA Lines 404-419: If to_date (baldate) is not a payment date, insert row and copy values
            schedule = list(full_schedule)  # Copy for potential modification
            
            # VBA: If to_date is not a payment date, INSERT row and COPY values from previous row
            interpolated_inserted = False
            if to_date:
                # Check if to_date exists in schedule
                to_date_exists = any(row.date == to_date for row in schedule)
                if not to_date_exists:
                    # Find the row just before to_date (VBA Line 413-418)
                    for i, row in enumerate(schedule):
                        row_date = row.date
                        next_row_date = schedule[i + 1].date if i + 1 < len(schedule) else None
                        
                        # VBA: If cell.Value < baldate And cell.Offset(1, 0).Value > baldate
                        if next_row_date and row_date < to_date < next_row_date:
                            # Insert interpolated row at to_date (VBA copies previous row values E-O)
                            from copy import deepcopy
                            from lease_accounting.core.models import PaymentScheduleRow
                            interpolated_row = PaymentScheduleRow(
                                date=to_date,
                                rental_amount=0.0,  # No payment on interpolated date
                                pv_factor=row.pv_factor,
                                interest=row.interest,
                                lease_liability=closing_liab,  # Use calculated closing balance
                                pv_of_rent=row.pv_of_rent,
                                rou_asset=closing_rou,  # Use calculated closing balance
                                depreciation=row.depreciation,
                                change_in_rou=row.change_in_rou,
                                security_deposit_pv=closing_sec,
                                aro_gross=row.aro_gross,
                                aro_interest=row.aro_interest,
                                aro_provision=closing_aro,  # Use calculated closing balance
                                is_opening=False
                            )
                            schedule.insert(i + 1, interpolated_row)
                            interpolated_inserted = True
                            logger.info(f"   ✅ Inserted interpolated row at to_date={to_date} (copied values from row {i})")
                            break
                    if not interpolated_inserted:
                        # If to_date is after all schedule rows, use last row values
                        if schedule and schedule[-1].date < to_date:
                            logger.info(f"   ℹ️  to_date={to_date} is after all schedule rows, using last row values for closing")
            
            # Generate journal entries - CRITICAL: Pass None for previous_result to show incremental adjustments
            # Journal entries should show period activity (incremental changes), not full balances
            journal_entries = generate_lease_journal(result, full_schedule, None, "IFRS")
            
            logger.info(f"📊 Schedule: {len(schedule)} rows (FULL schedule - never filtered per VBA logic)")
            logger.info(f"   Interpolated row inserted: {interpolated_inserted}")
            logger.info(f"   Opening liability: {result.opening_lease_liability}")
        else:
            # No date filtering - calculate full lease
            # Use LeaseProcessor for consistency, but with full date range
            from lease_accounting.core.processor import LeaseProcessor, ProcessingFilters
            filters = ProcessingFilters(
                start_date=lease_data.lease_start_date,
                end_date=lease_data.end_date,
                gaap_standard="IFRS"
            )
            processor = LeaseProcessor(filters)
            result = processor.process_single_lease(lease_data)
            
            if not result:
                result = _calculate_lease_results(lease_data, full_schedule)
            
            schedule = full_schedule
            journal_entries = generate_lease_journal(result, full_schedule, None, "IFRS")
        
        # Format response
        response = {
            'success': True,
            'lease_result': result.to_dict(),
            'schedule': [row.to_dict() for row in schedule],
            'journal_entries': [entry.to_dict() for entry in journal_entries],
            'date_range': {
                'from_date': from_date_str,
                'to_date': to_date_str,
                'filtered': from_date is not None and to_date is not None
            },
            'summary': {
                'total_payments': len([r for r in schedule if r.rental_amount > 0]),
                'total_interest': result.interest_expense,
                'total_depreciation': result.depreciation_expense,
                'total_rent_paid': result.rent_paid,
                'opening_liability': result.opening_lease_liability,
                'closing_liability': result.closing_lease_liability_non_current + result.closing_lease_liability_current,
            }
        }
        
        logger.info("✅ Calculation completed successfully")
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string to date object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        return None

def _parse_date_array(data: Dict, prefix: str, max_count: int = 8) -> List[Optional[date]]:
    """Parse date array from form data (e.g., aro_date_1, aro_date_2, ...)"""
    dates = []
    for i in range(1, max_count + 1):
        date_key = f"{prefix}_{i}"
        date_val = data.get(date_key) or data.get(f"{prefix}{i}")  # Support both formats
        dates.append(_parse_date(date_val))
    return dates

def _parse_float_array(data: Dict, prefix: str, max_count: int = 8) -> List[Optional[float]]:
    """Parse float array from form data (e.g., aro_revision_1, aro_revision_2, ...)"""
    values = []
    for i in range(1, max_count + 1):
        val_key = f"{prefix}_{i}"
        val = data.get(val_key) or data.get(f"{prefix}{i}")  # Support both formats
        try:
            values.append(float(val) if val else None)
        except (ValueError, TypeError):
            values.append(None)
    return values


def _calculate_lease_results(lease_data: LeaseData, schedule: List[PaymentScheduleRow], 
                             from_date: Optional[date] = None, to_date: Optional[date] = None) -> LeaseResult:
    """
    Calculate lease results from schedule - VBA compu() logic
    Includes: Termination gain/loss, Force end date, COVID PE, Sublease gains, etc.
    """
    if not schedule:
        return LeaseResult(lease_id=lease_data.auto_id)
    
    # VBA Line 386: Force end date logic
    forceenddate = None
    if lease_data.date_modified or lease_data.termination_date:
        dates = [d for d in [lease_data.date_modified, lease_data.termination_date] if d]
        if dates:
            forceenddate = max(dates)
    
    # VBA Line 353, 401: closedate calculation
    if forceenddate and to_date and forceenddate <= to_date:
        closedate = forceenddate
    else:
        closedate = to_date if to_date else lease_data.end_date
    
    # Get opening row - should be the first row in schedule (lease start date)
    # If schedule is empty or filtered, use the first row available
    if not schedule:
        return None
    
    opening_row = schedule[0]
    closing_row = schedule[-1]
    
    # Find closing row based on closedate
    if closedate:
        for row in schedule:
            # payment_date is a property that returns row.date (already a date object)
            row_date = row.date
            if isinstance(row_date, datetime):
                row_date = row_date.date()
            
            if row_date and row_date <= closedate:
                closing_row = row
    
    # Get period activity (VBA findPL section)
    activity_rows = [r for r in schedule if not r.is_opening]
    opendate = (from_date - timedelta(days=1)) if from_date else None
    
    # VBA Line 454-460: Special gains/losses
    covid_pe_gain = 0.0
    modi_gain = 0.0
    sublease_gainloss = 0.0
    sublease_modi_gainloss = 0.0
    
    if opendate and to_date:
        lease_start = lease_data.lease_start_date
        if lease_start and opendate < lease_start <= to_date:
            # Find opening row for sublease calculations
            opening_row = schedule[0] if schedule else None
            
            # COVID Practical Expedient (VBA Line 454)
            if lease_data.practical_expedient == "Yes" and opening_row:
                # K7 = Gain on COVID practical expedient
                # Would need to calculate new liability vs old liability
                # Simplified: would be calculated during modification processing
                pass
            
            # Gain on modification (VBA Line 456)
            # K6 = Gain on modification of lease
            # Calculated in modification processor
            
            # Sublease gain/loss (VBA Line 458)
            if lease_data.sublease == "Yes" and opening_row:
                if not lease_data.modifies_this_id:
                    # Initial sublease gain/loss
                    # sublease_gainloss = I9 - G9 (ROU - Liability)
                    sublease_gainloss = (opening_row.rou_asset or 0.0) - (opening_row.lease_liability or 0.0)
                else:
                    # Sublease modification gain/loss (VBA Line 460)
                    # K5 = Gain/Loss on modification of sublease
                    # Calculated in modification processor
                    pass
    
    # VBA Line 462-468: Termination gain/loss
    termination_gain_loss = 0.0
    if lease_data.termination_date and closing_row:
        # Find termination row
        term_row = None
        for row in schedule:
            row_date = row.date  # payment_date property returns date
            if isinstance(row_date, datetime):
                row_date = row_date.date()
            if row_date == lease_data.termination_date:
                term_row = row
                break
        
        if term_row:
            # Calculate security_grossT (VBA Line 464-467)
            sec_grossT = lease_data.security_deposit or 0.0
            if hasattr(lease_data, 'security_dates'):
                for qqq in range(1, 5):
                    if (qqq <= len(lease_data.security_dates) and 
                        lease_data.security_dates[qqq - 1] and
                        lease_data.security_dates[qqq - 1] <= lease_data.termination_date):
                        if qqq == 1:
                            sec_grossT += lease_data.increase_security_1 or 0.0
                        elif qqq == 2:
                            sec_grossT += lease_data.increase_security_2 or 0.0
                        elif qqq == 3:
                            sec_grossT += lease_data.increase_security_3 or 0.0
                        elif qqq == 4:
                            sec_grossT += lease_data.increase_security_4 or 0.0
            
            # VBA Line 468: Termination gain/loss formula
            termination_gain_loss = (
                (lease_data.termination_penalty or 0.0) +
                (term_row.rou_asset or 0.0) -  # cell.Offset(0, 6)
                (term_row.lease_liability or 0.0) -  # cell.Offset(0, 4)
                sec_grossT +
                (term_row.security_deposit_pv or 0.0) -  # cell.Offset(0, 9)
                (term_row.aro_provision or 0.0) +  # cell.Offset(0, 12)
                covid_pe_gain + modi_gain + sublease_gainloss + sublease_modi_gainloss
            )
    
    # Calculate remaining ROU life (VBA Line 495-497)
    remaining_rou_life = 0.0
    if to_date:
        # Would need J6 (end of life) from schedule - simplified
        if lease_data.useful_life:
            days_remaining = (lease_data.useful_life - to_date).days
            if days_remaining > 0:
                remaining_rou_life = days_remaining / 365.0
        
        # Set to 0 if terminated or modified before baldate
        if lease_data.termination_date and lease_data.termination_date < to_date:
            remaining_rou_life = 0.0
        if lease_data.date_modified and lease_data.date_modified < to_date:
            remaining_rou_life = 0.0
    
    # Get period activity
    date_modified = lease_data.date_modified
    interest_expense = sum(r.interest for r in activity_rows)
    depreciation_expense = sum(r.depreciation for r in activity_rows)
    # CRITICAL: Exclude date_modified from rent_paid
    rent_paid = 0.0
    for r in activity_rows:
        r_date = r.date  # payment_date property returns date
        if not date_modified or r_date != date_modified:
            rent_paid += r.rental_amount
    aro_interest = sum(r.aro_interest or 0.0 for r in activity_rows)
    
    result = LeaseResult(
        lease_id=lease_data.auto_id,
        
        # Opening balances
        opening_lease_liability=opening_row.lease_liability,
        opening_rou_asset=opening_row.rou_asset,
        opening_aro_liability=opening_row.aro_provision or 0.0,
        opening_security_deposit=opening_row.security_deposit_pv,
        
        # Period activity
        interest_expense=interest_expense,
        depreciation_expense=depreciation_expense,
        rent_paid=rent_paid,
        aro_interest=aro_interest,
        security_deposit_change=0.0,  # Calculated in processor
        
        # Closing balances
        closing_lease_liability_non_current=abs(closing_row.lease_liability) * 0.7 if closing_row.lease_liability > 0 else 0,
        closing_lease_liability_current=abs(closing_row.lease_liability) * 0.3 if closing_row.lease_liability > 0 else 0,
        closing_rou_asset=closing_row.rou_asset,
        closing_aro_liability=closing_row.aro_provision or 0.0,
        closing_security_deposit=closing_row.security_deposit_pv,
        
        # Gain/Loss
        gain_loss_pnl=termination_gain_loss if lease_data.termination_date else (covid_pe_gain + modi_gain + sublease_gainloss + sublease_modi_gainloss),
        
        # Additional info
        asset_class=lease_data.asset_class,
        cost_center=lease_data.cost_centre,
        currency=lease_data.currency,
        description=lease_data.description,
        asset_code=lease_data.asset_id_code,
        borrowing_rate=lease_data.borrowing_rate,
        remaining_rou_life=remaining_rou_life,
    )
    
    return result


@calc_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'version': '1.0'})

# For standalone use
def create_calc_app():
    """Create standalone Flask app for testing"""
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(calc_bp)
    return app


if __name__ == '__main__':
    print("🚀 Starting Complete Lease Accounting Backend...")
    print("📍 API Endpoint: http://localhost:5001/api/calculate_lease")
    app = create_calc_app()
    app.run(debug=True, port=5001)


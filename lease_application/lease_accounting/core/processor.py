"""
Main Lease Processor
Ports compu() VBA function to Python
Handles multi-lease processing with filtering and results generation

VBA Source File: VB script/Code
VBA Function: compu() Sub (Lines 251-624)
  - Main loop: For ai = G2 To G3 (Lines 316-605)
  - Opening balances: Lines 364-381
  - Closing balances: Lines 384-427
  - Period activity: Lines 429-477 (findPL section)
  - Current/Non-current split: Lines 553-566
"""

from datetime import date, datetime
from typing import List, Optional
from lease_accounting.core.models import LeaseData, LeaseResult, ProcessingFilters, PaymentScheduleRow
from lease_accounting.schedule.generator_vba_complete import generate_complete_schedule


class LeaseProcessor:
    """
    Main lease accounting processor
    Ports Excel compu() function logic
    """
    
    def __init__(self, filters: ProcessingFilters):
        self.filters = filters
        self.lease_results = []
    
    def process_all_leases(self, lease_data_list: List[LeaseData]) -> List[LeaseResult]:
        """
        Process multiple leases
        Main loop equivalent to For ai = G2 To G3 in VBA
        """
        results = []
        
        for lease_data in lease_data_list:
            # Check filters
            if not self.should_process_lease(lease_data):
                continue
            
            # Skip short-term leases
            if self.is_short_term_lease(lease_data):
                continue
            
            # Process single lease
            result = self.process_single_lease(lease_data)
            if result:
                results.append(result)
        
        return results
    
    def should_process_lease(self, lease_data: LeaseData) -> bool:
        """Check if lease passes all filters"""
        
        # Cost center filter
        if self.filters.cost_center_filter and \
           lease_data.cost_centre != self.filters.cost_center_filter:
            return False
        
        # Entity filter
        if self.filters.entity_filter and \
           lease_data.group_entity_name != self.filters.entity_filter:
            return False
        
        # Asset class filter
        if self.filters.asset_class_filter and \
           lease_data.asset_class != self.filters.asset_class_filter:
            return False
        
        # Date filters
        if self.filters.end_date and lease_data.end_date and \
           lease_data.end_date < self.filters.end_date:
            return False
        
        if self.filters.start_date and lease_data.lease_start_date and \
           lease_data.lease_start_date > self.filters.start_date:
            return False
        
        return True
    
    def is_short_term_lease(self, lease_data: LeaseData) -> bool:
        """Check if lease is short-term (to be excluded)"""
        
        if self.filters.gaap_standard == "US-GAAP":
            return lease_data.short_term_lease_usgaap == "Yes"
        else:
            return lease_data.short_term_lease_ifrs == "Yes"
    
    def process_single_lease(self, lease_data: LeaseData) -> Optional[LeaseResult]:
        """
        Process a single lease - equivalent to main loop in compu()
        
        VBA Source: VB script/Code, compu() Sub (Lines 251-624)
        Main processing flow:
          1. Generate schedule (via generate_complete_schedule - VBA datessrent/basic_calc)
          2. Get opening balances (VBA Lines 367-381)
          3. Calculate period activity (VBA Lines 429-477)
          4. Get closing balances (VBA Lines 404-419)
          5. Split current/non-current liability (VBA Lines 553-566)
          6. Create LeaseResult object (VBA Results sheet)
        """
        if not self.filters.start_date or not self.filters.end_date:
            return None
        
        # Generate payment schedule
        schedule = generate_complete_schedule(lease_data)
        
        if not schedule:
            return None
        
        # VBA Line 361: Process lease modifications if applicable
        if lease_data.modifies_this_id and lease_data.modifies_this_id > 0:
            from lease_accounting.core.lease_modifications import process_lease_modifications
            schedule, mod_results = process_lease_modifications(
                lease_data, schedule, self.filters.end_date
            )
            # Store modification results in lease_data for use in results
            lease_data.calculated_fields.update(mod_results)
        
        # Calculate opening balances
        opening_liability, opening_rou, opening_aro, opening_security = self.get_opening_balances(
            schedule, self.filters.start_date
        )
        
        # Calculate period activity (depreciation, interest, rent paid)
        # Pass date_modified if available in lease_data
        date_modified = getattr(lease_data, 'date_modified', None)
        period_activity = self.calculate_period_activity(
            schedule, self.filters.start_date, self.filters.end_date, date_modified
        )
        
        # Calculate closing balances (VBA: baldate = D3)
        closing_liability, closing_rou, closing_aro, closing_security = self.get_closing_balances(
            schedule, self.filters.end_date
        )
        
        # Calculate Current vs Non-Current Liability
        # VBA Source: VB script/Code, compu() Sub (Lines 553-566)
        # Two methods (controlled by Sheets("A").Range("A5").Value):
        #   Method 0 (A5=0): Sum PV of payments due in next 12 months (Line 560)
        #   Method 1 (A5<>0): Max(D4 - AD4, 0) where AD4 = projected liability 12 months ahead (Line 563)
        # TODO: Implement full projection logic for Method 0 and Method 1
        # Simplified: Use 70/30 split for now (full implementation needs projections)
        closing_liability_total = abs(closing_liability) if closing_liability > 0 else 0
        closing_liability_current = closing_liability_total * 0.3
        closing_liability_non_current = closing_liability_total * 0.7
        
        # Create result object (matching VBA Results sheet)
        result = LeaseResult(
            lease_id=lease_data.auto_id,
            opening_lease_liability=opening_liability,
            opening_rou_asset=opening_rou,
            interest_expense=period_activity['interest'],
            depreciation_expense=period_activity['depreciation'],
            rent_paid=period_activity['rent_paid'],
            aro_interest=period_activity.get('aro_interest', 0.0),
            security_deposit_change=period_activity.get('security_change', 0.0),
            closing_lease_liability_non_current=closing_liability_non_current,
            closing_lease_liability_current=closing_liability_current,
            closing_rou_asset=closing_rou,
            closing_aro_liability=closing_aro,
            closing_security_deposit=closing_security,
            asset_class=lease_data.asset_class,
            cost_center=lease_data.cost_centre,
            currency=lease_data.currency,
            description=lease_data.description,
            asset_code=lease_data.asset_id_code,
            borrowing_rate=lease_data.borrowing_rate
        )
        
        return result
    
    def get_opening_balances(self, schedule: List[PaymentScheduleRow], 
                            balance_date: date) -> tuple:
        """
        Get opening balances at a specific date
        
        VBA Source: VB script/Code, compu() Sub (Lines 367-381)
        VBA Logic:
          1. If cell.Value = opendate: use that row (Line 367)
          2. If cell.Value < opendate And cell.Offset(1, 0).Value > opendate:
             INSERT row with opendate and COPY values from previous row (columns E-O) (Lines 374-380)
        Returns: (liability, rou, aro, security_deposit)
        """
        # VBA logic: find exact match or interpolate by inserting row
        for i, row in enumerate(schedule):
            # Get date from row
            row_date = row.payment_date
            if hasattr(row_date, 'date'):
                row_date = row_date.date()
            elif not isinstance(row_date, date):
                row_date = getattr(row, 'date', row_date)
            
            # Exact match (VBA: If cell.Value = opendate)
            if row_date == balance_date:
                return (row.lease_liability or 0.0, row.rou_asset or 0.0,
                       getattr(row, 'aro_provision', 0.0) or 0.0,
                       getattr(row, 'security_deposit_pv', 0.0) or 0.0)
            
            # Interpolation logic (VBA: If cell.Value < opendate And cell.Offset(1, 0).Value > opendate)
            # If balance_date falls between this row and next row
            if i < len(schedule) - 1:
                next_row = schedule[i + 1]
                next_date = next_row.payment_date
                if hasattr(next_date, 'date'):
                    next_date = next_date.date()
                elif not isinstance(next_date, date):
                    next_date = getattr(next_row, 'date', next_date)
                
                # VBA: inserts row and copies values from current row (columns E-O)
                # In Python: use current row's values (simulates copy)
                if row_date < balance_date < next_date:
                    return (row.lease_liability or 0.0, row.rou_asset or 0.0,
                           getattr(row, 'aro_provision', 0.0) or 0.0,
                           getattr(row, 'security_deposit_pv', 0.0) or 0.0)
        
        # If balance_date is before first row or after last row
        if schedule:
            first_row = schedule[0]
            first_date = first_row.date  # Use .date property directly
            if isinstance(first_date, datetime):
                first_date = first_date.date()
            
            if balance_date < first_date:
                # VBA Line 364: If lease_start_date > opendate, skip opening balance calculation
                # But if opendate is between lease_start and first payment, use first row values
                # For now, return first row's values (which represents opening balances at lease start)
                return (first_row.lease_liability or 0.0, first_row.rou_asset or 0.0,
                       getattr(first_row, 'aro_provision', 0.0) or 0.0,
                       getattr(first_row, 'security_deposit_pv', 0.0) or 0.0)
            else:
                # After lease end - use last row
                last_row = schedule[-1]
                return (last_row.lease_liability or 0.0, last_row.rou_asset or 0.0,
                       getattr(last_row, 'aro_provision', 0.0) or 0.0,
                       getattr(last_row, 'security_deposit_pv', 0.0) or 0.0)
        
        return (0.0, 0.0, 0.0, 0.0)
    
    def get_closing_balances(self, schedule: List[PaymentScheduleRow],
                            balance_date: date) -> tuple:
        """
        Get closing balances at a specific date
        
        VBA Source: VB script/Code, compu() Sub (Lines 404-419)
        VBA Logic:
          1. Force end date check (Line 386): Max(date_modified, termination_date)
          2. If cell.Value = baldate: use that row (Line 405)
          3. If cell.Value < baldate And cell.Offset(1, 0).Value > baldate:
             INSERT row with baldate and COPY values from previous row (columns E-O) (Lines 413-418)
        Returns: (liability, rou, aro, security_deposit)
        """
        closing_liability = 0.0
        closing_rou = 0.0
        closing_aro = 0.0
        closing_security = 0.0
        
        for i, row in enumerate(schedule):
            # Get date from row
            row_date = row.payment_date
            if hasattr(row_date, 'date'):
                row_date = row_date.date()
            elif not isinstance(row_date, date):
                row_date = getattr(row, 'date', row_date)
            
            # Exact match (VBA: If cell.Value = baldate)
            if row_date == balance_date:
                return (row.lease_liability, row.rou_asset, 
                       getattr(row, 'aro_provision', 0.0) or 0.0,
                       getattr(row, 'security_deposit_pv', 0.0) or 0.0)
            
            # Interpolation logic (VBA lines 413-418):
            # If cell.Value < baldate And cell.Offset(1, 0).Value > baldate
            # INSERT row with baldate and COPY values from current row
            if i < len(schedule) - 1:
                next_row = schedule[i + 1]
                next_date = next_row.payment_date
                if hasattr(next_date, 'date'):
                    next_date = next_date.date()
                elif not isinstance(next_date, date):
                    next_date = getattr(next_row, 'date', next_date)
                
                # Balance date falls between two payment dates
                # VBA copies values from current row (simulated here)
                if row_date < balance_date < next_date:
                    return (row.lease_liability, row.rou_asset,
                           getattr(row, 'aro_provision', 0.0) or 0.0,
                           getattr(row, 'security_deposit_pv', 0.0) or 0.0)
            
            # Track last row up to balance_date (for dates after lease end)
            if row_date <= balance_date:
                closing_liability = row.lease_liability or 0.0
                closing_rou = row.rou_asset or 0.0
                closing_aro = getattr(row, 'aro_provision', 0.0) or 0.0
                closing_security = getattr(row, 'security_deposit_pv', 0.0) or 0.0
        
        # Return last tracked values (if balance_date is after all rows)
        # If no values were set, return first row's values as fallback
        if closing_liability == 0 and closing_rou == 0 and schedule:
            first_row = schedule[0]
            closing_liability = first_row.lease_liability or 0.0
            closing_rou = first_row.rou_asset or 0.0
            closing_aro = getattr(first_row, 'aro_provision', 0.0) or 0.0
            closing_security = getattr(first_row, 'security_deposit_pv', 0.0) or 0.0
        
        return (closing_liability, closing_rou, closing_aro, closing_security)
    
    def calculate_period_activity(self, schedule: List[PaymentScheduleRow],
                                  start_date: date, end_date: date, 
                                  date_modified: Optional[date] = None) -> dict:
        """
        Calculate depreciation, interest, and rent paid for period
        
        VBA Source: VB script/Code, compu() Sub, findPL section (Lines 429-477)
        VBA Logic:
          - Line 438: If cell.Value > opendate And cell.Value <= closedate
          - Line 439: Not_modified flag (excludes date_modified from rent_paid)
          - Line 440-444: Accumulate depreciation, interest, changeROU, AROintt, RentPaid
          - Line 445: Security deposit interest (delta calculation)
          - Lines 454-460: Special gains/losses (COVID PE, modification, sublease)
          - Lines 462-474: Termination gain/loss calculation
        Returns: dict with 'depreciation', 'interest', 'rent_paid', 'aro_interest', 'security_change'
        """
        depreciation = 0.0
        interest = 0.0
        rent_paid = 0.0
        aro_interest = 0.0
        security_change = 0.0
        change_rou = 0.0
        
        prev_security_pv = 0.0
        
        for i, row in enumerate(schedule):
            # Skip opening row
            if row.is_opening:
                # Track opening security deposit for delta calculation
                prev_security_pv = row.security_deposit_pv or 0.0
                continue
                
            # Get date from row
            row_date = row.payment_date
            if hasattr(row_date, 'date'):
                row_date = row_date.date()
            elif not isinstance(row_date, date):
                row_date = getattr(row, 'date', row_date)
            
            # VBA Line 438: cell.Value > opendate And cell.Value <= closedate
            # start_date is already opendate (from_date - 1), end_date is closedate (to_date)
            # CRITICAL: VBA uses > (greater than) not >=, so opendate is EXCLUDED
            # Python condition must match: row_date > start_date AND row_date <= end_date
            if start_date < row_date <= end_date:  # Same as: row_date > start_date AND row_date <= end_date
                # VBA Line 432-437: If openinsert_Flag = 1, subtract values
                # (handled separately in get_opening_balances)
                
                # VBA Line 439: Not_modified flag
                Not_modified = 1
                if date_modified and row_date == date_modified:
                    Not_modified = 0
                
                # VBA Line 440-444: Accumulate period activity
                depreciation += abs(row.depreciation or 0.0)
                interest += abs(row.interest or 0.0)
                rent_paid += (row.rental_amount or 0.0) * Not_modified  # CRITICAL: Exclude date_modified
                change_rou += row.change_in_rou or 0.0
                
                if row.aro_interest:
                    aro_interest += row.aro_interest
                
                # VBA Line 445: Security deposit change (delta calculation)
                if i > 0:  # cell.Row > 9
                    curr_security_pv = row.security_deposit_pv or 0.0
                    security_change += curr_security_pv - prev_security_pv
                    
                    # VBA Line 446-450: Special handling for security increase formulas
                    # (Complex formula parsing - simplified here)
                
                prev_security_pv = row.security_deposit_pv or 0.0
        
        return {
            'depreciation': depreciation,
            'interest': interest,
            'rent_paid': rent_paid,
            'aro_interest': aro_interest,
            'security_change': security_change,
            'change_rou': change_rou
        }


"""
Results Processor for Bulk Lease Calculations
Handles batch processing and results summary generation

VBA Source: VB script/Code, compu() Sub (Lines 316-605)
VBA Results Sheet: Columns D4-AG4 (and beyond) for lease results
"""

from datetime import date
from typing import List, Dict, Optional
import logging
from lease_accounting.core.models import LeaseData, LeaseResult, ProcessingFilters
from lease_accounting.core.processor import LeaseProcessor
from lease_accounting.utils.journal_generator import JournalGenerator

logger = logging.getLogger(__name__)

# Import JournalEntry from journal_generator
try:
    from lease_accounting.utils.journal_generator import JournalEntry
except ImportError:
    # Fallback if JournalEntry is defined differently
    from dataclasses import dataclass
    
    @dataclass
    class JournalEntry:
        bs_pl: str
        account_code: str
        account_name: str
        result_period: float
        previous_period: float
        ifrs_adjustment: float = 0.0
        incremental_adjustment: float = 0.0
        usgaap_entry: float = 0.0
        
        def to_dict(self):
            return {
                'bs_pl': self.bs_pl,
                'account_code': self.account_code,
                'account_name': self.account_name,
                'result_period': self.result_period,
                'previous_period': self.previous_period,
                'ifrs_adjustment': self.ifrs_adjustment,
                'incremental_adjustment': self.incremental_adjustment,
                'usgaap_entry': self.usgaap_entry
            }


class ResultsProcessor:
    """
    Processes multiple leases and generates consolidated results
    Equivalent to VBA compu() loop: For ai = G2 To G3
    """
    
    def __init__(self, filters: ProcessingFilters):
        self.filters = filters
        self.lease_processor = LeaseProcessor(filters)
        self.results: List[Dict] = []
        self.aggregated_totals: Dict = {}
    
    def process_bulk_leases(self, lease_data_list: List[LeaseData]) -> Dict:
        """
        Process multiple leases and generate results summary
        
        Returns:
            {
                'results': List[Dict],  # Individual lease results (matching Excel Results D4-AG4)
                'aggregated_totals': Dict,  # Sum across all leases
                'consolidated_journals': List[JournalEntry],  # Combined journal entries
                'success': bool,
                'processed_count': int,
                'skipped_count': int
            }
        """
        logger.info(f"🔄 Starting bulk processing: {len(lease_data_list)} leases")
        
        processed_count = 0
        skipped_count = 0
        individual_results = []
        consolidated_journals_dict: Dict[str, JournalEntry] = {}
        
        # Process each lease (VBA: For ai = G2 To G3)
        for lease_data in lease_data_list:
            # Check if lease should be processed (VBA Lines 330-337: Filter checks)
            if not self._should_process_lease(lease_data):
                skipped_count += 1
                logger.debug(f"⏭️  Skipping lease {lease_data.auto_id}: Failed filters")
                continue
            
            # Skip short-term leases (VBA Lines 340-345)
            if self._is_short_term_lease(lease_data):
                skipped_count += 1
                logger.debug(f"⏭️  Skipping lease {lease_data.auto_id}: Short-term lease")
                continue
            
            try:
                # Process single lease (VBA: Calls modify_calc, then processes)
                result = self.lease_processor.process_single_lease(lease_data)
                
                if result:
                    processed_count += 1
                    
                    # Convert result to Results table row format (VBA Lines 485-499)
                    result_row = self._convert_to_results_row(lease_data, result)
                    individual_results.append(result_row)
                    
                    # Generate journals for this lease and consolidate
                    journal_gen = JournalGenerator(gaap_standard=self.filters.gaap_standard)
                    journals = journal_gen.generate_journals(result, [], None)  # No schedule needed for journals
                    
                    # Consolidate journal entries (sum by account)
                    for journal in journals:
                        account_key = f"{journal.account_code}_{journal.account_name}"
                        if account_key not in consolidated_journals_dict:
                            consolidated_journals_dict[account_key] = JournalEntry(
                                bs_pl=journal.bs_pl,
                                account_code=journal.account_code,
                                account_name=journal.account_name,
                                result_period=0.0,
                                previous_period=0.0,
                                ifrs_adjustment=0.0,
                                incremental_adjustment=0.0,
                                usgaap_entry=0.0
                            )
                        
                        consolidated_journals_dict[account_key].result_period += journal.result_period
                        consolidated_journals_dict[account_key].previous_period += journal.previous_period
                        consolidated_journals_dict[account_key].ifrs_adjustment += journal.ifrs_adjustment
                        consolidated_journals_dict[account_key].incremental_adjustment += journal.incremental_adjustment
                    
                    logger.info(f"✅ Processed lease {lease_data.auto_id}: {lease_data.description}")
                
            except Exception as e:
                logger.error(f"❌ Error processing lease {lease_data.auto_id}: {e}", exc_info=True)
                skipped_count += 1
        
        # Calculate aggregated totals (sum all results)
        aggregated_totals = self._calculate_aggregated_totals(individual_results)
        
        # Convert consolidated journals to list
        consolidated_journals = list(consolidated_journals_dict.values())
        
        logger.info(f"✅ Bulk processing complete: {processed_count} processed, {skipped_count} skipped")
        
        return {
            'results': individual_results,
            'aggregated_totals': aggregated_totals,
            'consolidated_journals': [j.to_dict() for j in consolidated_journals],
            'success': True,
            'processed_count': processed_count,
            'skipped_count': skipped_count,
            'total_count': len(lease_data_list)
        }
    
    def _should_process_lease(self, lease_data: LeaseData) -> bool:
        """
        Check if lease passes all filters
        VBA Lines 330-337: Filter validation
        """
        # Cost center filter (VBA Line 330)
        if self.filters.cost_center_filter and \
           lease_data.cost_centre != self.filters.cost_center_filter:
            return False
        
        # Entity filter (VBA Line 331)
        if self.filters.entity_filter and \
           lease_data.group_entity_name != self.filters.entity_filter:
            return False
        
        # Asset class filter (VBA Line 332)
        if self.filters.asset_class_filter and \
           lease_data.asset_class != self.filters.asset_class_filter:
            return False
        
        # Profit center filter (VBA Line 333)
        if self.filters.profit_center_filter and \
           lease_data.profit_center != self.filters.profit_center_filter:
            return False
        
        # Date modified filter (VBA Line 334)
        if self.filters.start_date and lease_data.date_modified and \
           lease_data.date_modified < self.filters.start_date:
            return False
        
        # Termination date filter (VBA Line 335)
        if self.filters.end_date and lease_data.termination_date and \
           lease_data.termination_date < self.filters.start_date:
            return False
        
        # End date filter (VBA Line 336)
        if self.filters.start_date and lease_data.end_date and \
           lease_data.end_date < self.filters.start_date:
            return False
        
        # Lease start date filter (VBA Line 337)
        if self.filters.end_date and lease_data.lease_start_date and \
           lease_data.lease_start_date > self.filters.end_date:
            return False
        
        return True
    
    def _is_short_term_lease(self, lease_data: LeaseData) -> bool:
        """
        Check if lease is short-term (to be excluded)
        VBA Lines 340-345: Short-term lease check
        """
        if self.filters.gaap_standard == "US-GAAP":
            return lease_data.short_term_lease_usgaap == "Yes"
        else:
            return lease_data.short_term_lease_ifrs == "Yes"
    
    def _convert_to_results_row(self, lease_data: LeaseData, result: LeaseResult) -> Dict:
        """
        Convert LeaseResult to Results table row format
        Matches Excel Results sheet columns D4-AG4 and beyond
        
        VBA Lines 485-499: Results table population
        """
        # Determine sublease multiplier (VBA Line 362)
        subl = -1 if lease_data.sublease == "Yes" else 1
        
        # Build results row matching Excel Results sheet columns
        # Column mapping based on VBA Lines 485-499 and Results sheet structure
        results_row = {
            # Identifiers
            'lease_id': lease_data.auto_id,
            'auto_id': lease_data.auto_id,
            'description': lease_data.description or '',
            'asset_class': lease_data.asset_class or '',
            'asset_id_code': lease_data.asset_id_code or '',
            
            # Closing Balances (D4, G4, M4, K4 in VBA)
            'closing_liability_total': abs(result.closing_lease_liability_non_current + result.closing_lease_liability_current) * subl,
            'closing_liability_current': result.closing_lease_liability_current * subl,
            'closing_liability_non_current': result.closing_lease_liability_non_current * subl,
            'closing_rou_asset': result.closing_rou_asset * subl,
            'closing_security_deposit': result.closing_security_deposit * subl,
            'closing_aro_liability': result.closing_aro_liability or 0.0,
            
            # Period Activity (F4, H4, J4, O4, R4 in VBA)
            'interest_expense': result.interest_expense * subl,
            'depreciation_expense': result.depreciation_expense * subl,
            'aro_interest': result.aro_interest or 0.0,
            'rent_paid': result.rent_paid * subl,
            'change_in_rou': 0.0,  # Would need schedule to calculate
            
            # Opening Balances (Q4, S4, T4, P4 in VBA)
            'opening_liability': result.opening_lease_liability * subl,
            'opening_rou_asset': result.opening_rou_asset * subl,
            'opening_security_deposit': result.opening_security_deposit or 0.0,
            'opening_aro_liability': result.opening_aro_liability or 0.0,
            
            # Gain/Loss (I4 in VBA)
            'gain_loss_pnl': result.gain_loss_pnl or 0.0,
            
            # Additional Fields
            'currency': lease_data.currency or 'USD',
            'cost_centre': lease_data.cost_centre or '',
            'profit_center': lease_data.profit_center or '',
            'group_entity_name': lease_data.group_entity_name or '',
            'counterparty': lease_data.counterparty or '',
            'borrowing_rate': lease_data.borrowing_rate or 0.0,
            'lease_start_date': lease_data.lease_start_date.isoformat() if lease_data.lease_start_date else '',
            'end_date': lease_data.end_date.isoformat() if lease_data.end_date else '',
            'termination_date': lease_data.termination_date.isoformat() if lease_data.termination_date else '',
            'date_modified': lease_data.date_modified.isoformat() if lease_data.date_modified else '',
            'sublease': lease_data.sublease or 'No',
            
            # Projections would go here (AD4-AG4 for each projection mode)
            # For now, we'll add placeholders
            'projection_1_liability': 0.0,
            'projection_1_rou': 0.0,
            'projection_1_depreciation': 0.0,
            'projection_1_interest': 0.0,
            'projection_1_rent': 0.0,
        }
        
        return results_row
    
    def _calculate_aggregated_totals(self, results: List[Dict]) -> Dict:
        """
        Calculate aggregated totals across all leases
        Equivalent to sum formulas in Excel Results sheet
        """
        if not results:
            return {}
        
        totals = {
            'total_leases': len(results),
            'total_closing_liability': sum(r.get('closing_liability_total', 0) for r in results),
            'total_closing_liability_current': sum(r.get('closing_liability_current', 0) for r in results),
            'total_closing_liability_non_current': sum(r.get('closing_liability_non_current', 0) for r in results),
            'total_closing_rou_asset': sum(r.get('closing_rou_asset', 0) for r in results),
            'total_closing_security_deposit': sum(r.get('closing_security_deposit', 0) for r in results),
            'total_closing_aro_liability': sum(r.get('closing_aro_liability', 0) for r in results),
            'total_interest_expense': sum(r.get('interest_expense', 0) for r in results),
            'total_depreciation_expense': sum(r.get('depreciation_expense', 0) for r in results),
            'total_aro_interest': sum(r.get('aro_interest', 0) for r in results),
            'total_rent_paid': sum(r.get('rent_paid', 0) for r in results),
            'total_opening_liability': sum(r.get('opening_liability', 0) for r in results),
            'total_opening_rou_asset': sum(r.get('opening_rou_asset', 0) for r in results),
            'total_gain_loss_pnl': sum(r.get('gain_loss_pnl', 0) for r in results),
        }
        
        return totals


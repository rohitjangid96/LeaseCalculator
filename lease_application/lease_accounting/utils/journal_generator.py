"""
Journal Entry Generator
Creates Excel-style journal entries (JournalD sheet)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from lease_accounting.core.models import PaymentScheduleRow, LeaseResult


@dataclass
class JournalEntry:
    """Single journal entry matching Excel JournalD sheet structure"""
    bs_pl: str  # "BS" or "PL"
    account_code: str = ""
    account_name: str = ""
    result_period: float = 0.0
    previous_period: float = 0.0
    incremental_adjustment: float = 0.0
    ifrs_adjustment: float = 0.0
    usgaap_entry: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'bs_pl': self.bs_pl,
            'account_code': self.account_code,
            'account_name': self.account_name,
            'result_period': self.result_period,
            'previous_period': self.previous_period,
            'incremental_adjustment': self.incremental_adjustment,
            'ifrs_adjustment': self.ifrs_adjustment,
            'usgaap_entry': self.usgaap_entry,
        }


class JournalGenerator:
    """
    Generate journal entries from lease schedule
    Ports Excel JournalD sheet logic
    """
    
    def __init__(self, gaap_standard: str = "IFRS"):
        self.gaap_standard = gaap_standard  # "IFRS", "IndAS", or "US-GAAP"
        self.journal_entries: List[JournalEntry] = []
    
    def generate_journals(
        self,
        lease_result: LeaseResult,
        schedule: List[PaymentScheduleRow],
        previous_result: Optional[LeaseResult] = None
    ) -> List[JournalEntry]:
        """
        Generate complete journal entries
        Matches Excel JournalD sheet structure
        """
        self.journal_entries = []
        
        # Opening balance entries - show CLOSING balances (not opening)
        # VBA JournalD: Column F = Result Period shows closing balances at to_date
        # Column E = Previous Period shows closing balances at from_date - 1
        # Column G = Incremental Adjustment shows the change during the period
        
        # For Liability: Show closing balance (not opening)
        opening_liab = lease_result.opening_lease_liability or 0.0
        closing_liab_total = (lease_result.closing_lease_liability_current or 0.0) + (lease_result.closing_lease_liability_non_current or 0.0)
        
        prev_opening_liab = previous_result.opening_lease_liability if previous_result else 0.0
        prev_closing_liab = ((previous_result.closing_lease_liability_current or 0.0) + (previous_result.closing_lease_liability_non_current or 0.0)) if previous_result else 0.0
        
        self._add_entry(
            bs_pl="BS",
            account_name="Lease Liability Non-current",
            result_period=-(lease_result.closing_lease_liability_non_current or 0.0),
            previous_period=-(previous_result.closing_lease_liability_non_current or 0.0) if previous_result else 0
        )
        
        self._add_entry(
            bs_pl="BS",
            account_name="Lease Liability Current",
            result_period=-(lease_result.closing_lease_liability_current or 0.0),
            previous_period=-(previous_result.closing_lease_liability_current or 0.0) if previous_result else 0
        )
        
        # Interest expense
        self._add_entry(
            bs_pl="PL",
            account_name="Interest Cost",
            result_period=lease_result.interest_expense,
            previous_period=previous_result.interest_expense if previous_result else 0
        )
        
        # ROU Asset
        self._add_entry(
            bs_pl="BS",
            account_name="RoU Asset (net)",
            result_period=lease_result.closing_rou_asset,
            previous_period=previous_result.closing_rou_asset if previous_result else 0
        )
        
        # Depreciation
        self._add_entry(
            bs_pl="PL",
            account_name="Depreciation",
            result_period=lease_result.depreciation_expense,
            previous_period=previous_result.depreciation_expense if previous_result else 0
        )
        
        # Gain/Loss
        if lease_result.gain_loss_pnl != 0:
            self._add_entry(
                bs_pl="PL",
                account_name="(Gain)/Loss in P&L",
                result_period=lease_result.gain_loss_pnl,
                previous_period=previous_result.gain_loss_pnl if previous_result else 0
            )
        
        # ARO Interest
        if lease_result.aro_interest != 0:
            self._add_entry(
                bs_pl="PL",
                account_name="ARO Interest",
                result_period=lease_result.aro_interest,
                previous_period=previous_result.aro_interest if previous_result else 0
            )
        
        # ARO Provision Closing
        if lease_result.closing_aro_liability != 0:
            self._add_entry(
                bs_pl="BS",
                account_name="ARO Provision Closing",
                result_period=lease_result.closing_aro_liability,
                previous_period=previous_result.closing_aro_liability if previous_result else 0
            )
        
        # Security Deposit Interest
        if lease_result.security_deposit_change != 0:
            self._add_entry(
                bs_pl="PL",
                account_name="Interest on Security Dep",
                result_period=lease_result.security_deposit_change,
                previous_period=previous_result.security_deposit_change if previous_result else 0
            )
        
        # Security Deposit - Show as single asset (not split into current/non-current)
        # VBA doesn't split security deposit in journal entries - it's shown as one line item
        if lease_result.closing_security_deposit > 0:
            self._add_entry(
                bs_pl="BS",
                account_name="Security Deposit",
                account_code="",  # No specific code for security deposit
                result_period=-lease_result.closing_security_deposit,
                previous_period=-previous_result.closing_security_deposit if previous_result else 0
            )
        
        # Rent Paid
        self._add_entry(
            bs_pl="PL",
            account_name="Rent Paid",
            result_period=-lease_result.rent_paid,
            previous_period=-previous_result.rent_paid if previous_result else 0
        )
        
        # Retained Earnings (balancing entry - should make debits equal credits)
        total_debits = sum(e.result_period for e in self.journal_entries if e.result_period > 0)
        total_credits = sum(e.result_period for e in self.journal_entries if e.result_period < 0)
        retained_earnings = total_credits + total_debits
        
        self._add_entry(
            bs_pl="BS",
            account_name="Retained Earnings",
            result_period=-retained_earnings,
            previous_period=-previous_result.gain_loss_pnl if previous_result else 0
        )
        
        # Calculate incremental adjustments
        for entry in self.journal_entries:
            entry.incremental_adjustment = entry.result_period - entry.previous_period
            
            # Calculate IFRS vs US-GAAP differences if applicable
            if self.gaap_standard == "IFRS":
                entry.ifrs_adjustment = entry.result_period
                entry.usgaap_entry = 0.0
            elif self.gaap_standard == "US-GAAP":
                entry.ifrs_adjustment = 0.0
                entry.usgaap_entry = entry.result_period
        
        return self.journal_entries
    
    def _get_account_code(self, account_name: str) -> str:
        """Map account name to account code (Chart of Accounts)"""
        account_code_map = {
            "Lease Liability Non-current": "2101",
            "Lease Liability Current": "2102",
            "RoU Asset (net)": "1200",
            "Interest Cost": "5101",
            "Depreciation": "5102",
            "Rent Paid": "5103",
            "ARO Interest": "5104",
            "Interest on Security Dep": "5105",
            "ARO Provision Closing": "2201",
            "Security Deposit - Non-current": "1201",
            "Security Deposit - Current": "1202",
            "Retained Earnings": "3100",
            "(Gain)/Loss in P&L": "5200",
        }
        return account_code_map.get(account_name, "")
    
    def _add_entry(self, bs_pl: str, account_name: str, 
                   account_code: str = "",
                   result_period: float = 0.0, previous_period: float = 0.0):
        """Add a journal entry"""
        # Auto-assign account code if not provided
        if not account_code:
            account_code = self._get_account_code(account_name)
        
        entry = JournalEntry(
            bs_pl=bs_pl,
            account_name=account_name,
            account_code=account_code,
            result_period=result_period,
            previous_period=previous_period
        )
        self.journal_entries.append(entry)
    
    def verify_balance(self) -> bool:
        """
        Verify that journal entries balance (debits = credits)
        Should sum to zero
        """
        total = sum(entry.result_period for entry in self.journal_entries)
        return abs(total) < 0.01  # Allow for rounding
    
    def get_debit_credit_summary(self) -> Dict[str, float]:
        """Get summary of debits and credits"""
        debits = sum(entry.result_period for entry in self.journal_entries if entry.result_period > 0)
        credits = abs(sum(entry.result_period for entry in self.journal_entries if entry.result_period < 0))
        difference = debits - credits
        
        return {
            'total_debits': debits,
            'total_credits': credits,
            'difference': difference,
            'is_balanced': abs(difference) < 0.01
        }


def generate_lease_journal(
    lease_result: LeaseResult,
    schedule: List[PaymentScheduleRow],
    previous_result: Optional[LeaseResult] = None,
    gaap_standard: str = "IFRS"
) -> List[JournalEntry]:
    """
    Convenience function to generate journal entries
    """
    generator = JournalGenerator(gaap_standard=gaap_standard)
    return generator.generate_journals(lease_result, schedule, previous_result)


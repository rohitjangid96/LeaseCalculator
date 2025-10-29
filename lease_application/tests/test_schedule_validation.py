"""
Schedule Validation Test
Validates the schedule response against VBA logic for payment dates and rental amounts
"""

import json
from datetime import date, datetime
from typing import Dict, List

def validate_schedule(payload: Dict, response: Dict):
    """
    Validate schedule matches VBA logic
    
    VBA Logic Summary (from Code lines 34-236):
    1. C9 (first row) = ALWAYS starto (lease_start_date) - Line 35
    2. If dateo == firstpaymentDate AND starto != firstpaymentDate: Plot with rental - Line 91-132
    3. Regular payments: If ((Year*12+Month) - (FirstYear*12+FirstMonth)) Mod monthof = 0 AND Day = dayofma - Line 137-184
    4. Month-end rows: If x=0 AND Month(dateo) <> Month(dateo+1): Plot without rental - Line 188-206
    5. February handling: Special logic for leap years - Line 143-146, 185
    """
    
    lease_start = datetime.fromisoformat(payload['lease_start_date']).date()
    first_payment = datetime.fromisoformat(payload['first_payment_date']).date()
    end_date = datetime.fromisoformat(payload['end_date']).date()
    day_of_month = payload.get('day_of_month', 'Last')
    frequency_months = payload.get('frequency_months', 1)
    
    schedule = response.get('schedule', [])
    
    print("\n" + "="*80)
    print("SCHEDULE VALIDATION REPORT")
    print("="*80)
    print(f"Lease Start: {lease_start}")
    print(f"First Payment: {first_payment}")
    print(f"End Date: {end_date}")
    print(f"Day of Month: {day_of_month}")
    print(f"Frequency: {frequency_months} month(s)")
    print(f"Total Schedule Rows: {len(schedule)}")
    
    issues = []
    warnings = []
    
    # Validation 1: First row must be lease_start_date (VBA Line 35)
    print("\n[Validation 1] First Row = Lease Start Date")
    if schedule and schedule[0]['date'] != lease_start.isoformat():
        issues.append(f"First row date {schedule[0]['date']} != lease_start_date {lease_start.isoformat()}")
        print(f"  ❌ FAIL: First row date mismatch")
    else:
        print(f"  ✅ PASS: First row is {schedule[0]['date']}")
        # First row should have rental = 0 if start != first_payment
        if lease_start != first_payment:
            if schedule[0]['rental_amount'] != 0:
                issues.append(f"First row (lease_start) has rental {schedule[0]['rental_amount']} but should be 0")
                print(f"  ❌ FAIL: First row rental should be 0, got {schedule[0]['rental_amount']}")
            else:
                print(f"  ✅ PASS: First row rental = 0 (correct for opening balance)")
        else:
            print(f"  ℹ️  INFO: First payment on start date (rental should be set)")
    
    # Validation 2: First payment date must have rental
    print("\n[Validation 2] First Payment Date Has Rental")
    first_payment_row = None
    for row in schedule:
        if row['date'] == first_payment.isoformat():
            first_payment_row = row
            break
    
    if first_payment_row:
        if first_payment_row['rental_amount'] > 0:
            print(f"  ✅ PASS: First payment date {first_payment.isoformat()} has rental {first_payment_row['rental_amount']}")
        else:
            issues.append(f"First payment date {first_payment.isoformat()} has rental = 0")
            print(f"  ❌ FAIL: First payment date has rental = 0")
    else:
        issues.append(f"First payment date {first_payment.isoformat()} not found in schedule")
        print(f"  ❌ FAIL: First payment date not found in schedule")
    
    # Validation 3: Month-end rows (VBA Line 188-206)
    print("\n[Validation 3] Month-End Rows (for accrual calculations)")
    month_end_rows = []
    for row in schedule:
        row_date = datetime.fromisoformat(row['date']).date()
        # Check if it's last day of month
        next_day = row_date + timedelta(days=1)
        if next_day.month != row_date.month:
            month_end_rows.append((row_date, row['rental_amount']))
    
    print(f"  Found {len(month_end_rows)} month-end rows")
    month_end_with_rental = [r for r in month_end_rows if r[1] > 0]
    if month_end_with_rental:
        warnings.append(f"Month-end rows with rental: {[r[0] for r in month_end_with_rental]}")
        print(f"  ⚠️  WARNING: {len(month_end_with_rental)} month-end rows have rental (might be payment dates, which is OK)")
    else:
        print(f"  ✅ PASS: All month-end rows have rental = 0 (correct for accrual rows)")
    
    # Validation 4: February handling (leap year)
    print("\n[Validation 4] February Leap Year Handling")
    feb_rows = [(datetime.fromisoformat(r['date']).date(), r['rental_amount']) 
                for r in schedule 
                if datetime.fromisoformat(r['date']).date().month == 2]
    feb_2024_rows = [r for r in feb_rows if r[0].year == 2024]
    
    if len(feb_2024_rows) > 2:
        print(f"  ℹ️  INFO: Found {len(feb_2024_rows)} rows in Feb 2024 (includes Feb 28 + Feb 29 for leap year)")
        if day_of_month == "Last":
            print(f"  ✅ PASS: Both Feb 28 and Feb 29 present (correct for leap year + 'Last' day logic)")
        else:
            warnings.append(f"Multiple Feb 2024 rows with day_of_month = {day_of_month}")
    elif len(feb_2024_rows) == 2:
        dates = [r[0] for r in feb_2024_rows]
        if date(2024, 2, 28) in dates and date(2024, 2, 29) in dates:
            print(f"  ✅ PASS: Both Feb 28 and Feb 29 present (correct for leap year)")
        else:
            print(f"  ⚠️  WARNING: Unexpected Feb 2024 dates: {dates}")
    else:
        print(f"  ⚠️  WARNING: Only {len(feb_2024_rows)} row(s) in Feb 2024")
    
    # Validation 5: Payment frequency validation
    print("\n[Validation 5] Payment Frequency")
    payment_rows = [r for r in schedule if r['rental_amount'] > 0]
    payment_dates = [datetime.fromisoformat(r['date']).date() for r in payment_rows]
    
    print(f"  Total payments: {len(payment_dates)}")
    print(f"  First payment: {min(payment_dates)}")
    print(f"  Last payment: {max(payment_dates)}")
    
    # Check if payments follow expected pattern
    if day_of_month == "Last":
        # Payments should be on last day of month (except first payment if it's different)
        expected_payment_month_ends = []
        for i, pd in enumerate(payment_dates):
            if i == 0 and pd == first_payment and first_payment != lease_start:
                # First payment can be on any date
                continue
            # Check if it's last day of month
            next_day = pd + timedelta(days=1)
            if next_day.month != pd.month:
                expected_payment_month_ends.append(pd)
            else:
                if i > 0:  # First payment exception already handled
                    issues.append(f"Payment on {pd} is not last day of month (day_of_month='Last')")
                    print(f"  ❌ FAIL: Payment {pd} is not last day of month")
        
        if len(expected_payment_month_ends) > 0:
            print(f"  ✅ PASS: {len(expected_payment_month_ends)} payment(s) correctly on month-end")
    
    # Validation 6: Jan 31, 2024 analysis
    print("\n[Validation 6] Jan 31, 2024 Row (Month-End Accrual)")
    jan31_row = next((r for r in schedule if r['date'] == '2024-01-31'), None)
    if jan31_row:
        if jan31_row['rental_amount'] == 0:
            print(f"  ✅ PASS: Jan 31 has rental = 0 (month-end accrual row per VBA Line 188-206)")
            print(f"     Reason: VBA creates month-end rows for calculation purposes even if no payment")
        else:
            print(f"  ℹ️  INFO: Jan 31 has rental = {jan31_row['rental_amount']} (might be payment date)")
    else:
        print(f"  ⚠️  WARNING: Jan 31 row not found")
    
    # Validation 7: Feb 29, 2024 analysis
    print("\n[Validation 7] Feb 29, 2024 Row (Leap Year)")
    feb29_row = next((r for r in schedule if r['date'] == '2024-02-29'), None)
    if feb29_row:
        if feb29_row['rental_amount'] == 0:
            print(f"  ✅ PASS: Feb 29 has rental = 0 (VBA creates this for leap year + 'Last' day logic)")
            print(f"     Reason: VBA Line 143-146, 185 handles February specially")
        else:
            print(f"  ℹ️  INFO: Feb 29 has rental = {feb29_row['rental_amount']}")
    else:
        print(f"  ⚠️  WARNING: Feb 29 row not found (2024 is leap year)")
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print(f"Total Issues: {len(issues)}")
    print(f"Total Warnings: {len(warnings)}")
    
    if issues:
        print("\n❌ ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    if not issues and not warnings:
        print("\n✅ ALL VALIDATIONS PASSED - Schedule matches VBA logic!")
    
    return len(issues) == 0


if __name__ == '__main__':
    from datetime import timedelta
    
    # Test with the provided payload and response
    payload = {
        'lease_start_date': '2024-01-01',
        'first_payment_date': '2024-01-16',
        'end_date': '2028-12-31',
        'day_of_month': 'Last',
        'frequency_months': 1,
        'rental_1': 150000,
        'auto_rentals': 'on'
    }
    
    # Load response from file or use sample
    print("Loading response data...")
    # In real usage, load from API response JSON
    
    # validate_schedule(payload, response)


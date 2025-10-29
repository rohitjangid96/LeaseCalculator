# Projection Logic Documentation

## Overview
Projections calculate future period balances and activity for lease accounting. This matches the VBA Excel logic from `VB script/Code` (Lines 510-568).

## When Projections Are Visible

### ✅ Projections ARE Calculated When:
1. **Balance Date (to_date) is BEFORE Lease End Date**
   - Example: `to_date = 2027-12-31` and `lease_end_date = 2028-12-31`
   - ✅ Projections will show future periods (e.g., 2028-03-31, 2028-06-30, 2028-09-30)

2. **Schedule Extends Beyond Balance Date**
   - Even if `termination_date` or `date_modified` exists BEFORE `to_date`
   - If schedule has data AFTER `to_date`, projections are calculated
   - Example: `termination_date = 2025-10-29`, `to_date = 2027-12-31`, but schedule extends to `2028-12-31`
   - ✅ Projections will show

3. **Projections Enabled**
   - `enable_projections = True` (default)
   - `projection_periods > 0` (default: 3)
   - `projection_period_months > 0` (default: 3)

### ❌ Projections are NOT Calculated When:

1. **Balance Date Equals or Exceeds Lease End**
   - Example: `to_date = 2028-12-31` and `lease_end_date = 2028-12-31`
   - ❌ No future periods to project

2. **All Schedule Data is At or Before Balance Date**
   - If `max_schedule_date <= to_date`
   - ❌ No future data to project from

3. **Future Modification/Termination After Balance Date**
   - If `forceenddate > balance_date` (where `forceenddate = max(date_modified, termination_date)`)
   - ❌ Can't project into a modified period

4. **Projections Disabled**
   - `enable_projections = False`
   - `projection_periods = 0`

## How Projections Are Calculated

### Input Parameters
- **balance_date**: The `to_date` from the calculation request (when balances are calculated)
- **projection_periods**: Number of periods to project (default: 3, max: 6)
- **period_months**: Months per period (default: 3)
- **enable_projections**: Boolean flag (default: True)

### Calculation Process (VBA Lines 510-568)

1. **Start from Balance Date**
   - `baldatep = balance_date` (to_date)

2. **For Each Projection Period** (max 6 periods):
   - `opendatep = baldatep` (opening date)
   - `baldatep = EoMonth(baldatep, period_months)` (add months, get end of month)
   - If `lease_end_date < baldatep`, clamp to `lease_end_date`

3. **Find Closing Balances** at `baldatep`:
   - Search schedule for row where `date = baldatep`
   - Extract: `closing_liability`, `closing_rou_asset`

4. **Calculate Period Activity** (between `opendatep` and `baldatep`):
   - Sum `depreciation` from schedule rows in period
   - Sum `interest` from schedule rows in period
   - Sum `rental_amount` (rent paid) from schedule rows in period

5. **Store Results**:
   ```python
   {
       'projection_mode': 1-6,
       'projection_date': 'YYYY-MM-DD',
       'closing_liability': float,
       'closing_rou_asset': float,
       'depreciation': float,
       'interest': float,
       'rent_paid': float
   }
   ```

### Example Calculation

**Input:**
- `balance_date` (to_date): `2027-12-31`
- `projection_periods`: `3`
- `period_months`: `3`
- `lease_end_date`: `2028-12-31`

**Output (3 periods):**
1. **Period 1**: `2028-03-31` (3 months from 2027-12-31)
   - Closing balances at 2028-03-31
   - Activity: Jan 1 - Mar 31, 2028

2. **Period 2**: `2028-06-30` (6 months from 2027-12-31)
   - Closing balances at 2028-06-30
   - Activity: Apr 1 - Jun 30, 2028

3. **Period 3**: `2028-09-30` (9 months from 2027-12-31)
   - Closing balances at 2028-09-30
   - Activity: Jul 1 - Sep 30, 2028

**Note**: If lease ends on 2028-12-31, Period 4 would be clamped to 2028-12-31.

## Date Range Logic

### Key Dates:
- **from_date** (start_date): Beginning of calculation period
- **to_date** (end_date, balance_date): End of calculation period (this is where projections start from)
- **lease_end_date**: Lease contract end date
- **termination_date**: Early termination date (if any)
- **date_modified**: Modification date (if lease was modified)

### Projection Dates:
- Projections start from `to_date + period_months`
- Each projection is `period_months` apart
- Maximum 6 projection periods (VBA limit)

## VBA Logic References

- **VBA Line 386**: `forceenddate = Max(date_modified, termination_date)`
- **VBA Line 511**: `If forceenddate <= baldate And forceenddate <> 0 Then GoTo skip_projections`
- **VBA Lines 512-568**: Projection calculation loop
- **VBA Line 522**: `baldatep = EoMonth(baldatep, A4.Value)` - Add months per period
- **VBA Line 525**: `If End_date < baldatep Then GoTo pfindPL` - Clamp to lease end

## Python Implementation

Location: `lease_application/lease_accounting/core/projection_calculator.py`

- **Class**: `ProjectionCalculator`
- **Method**: `calculate_projections()`
- **Usage**: Called from `LeaseProcessor.process_single_lease()`

The Python implementation matches VBA logic exactly, including:
- Handling of `forceenddate` (termination/modification dates)
- EoMonth calculation for projection dates
- Finding closing balances from schedule
- Summing period activity (depreciation, interest, rent)


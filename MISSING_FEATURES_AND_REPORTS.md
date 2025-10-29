# Missing Features and Reports - Excel/VBA vs Python Web App

## Comparison: Excel/VBA Application vs Python Web App

This document lists all features, reports, and displays that exist in the Excel/VBA application but are **NOT** currently implemented in the Python web app.

---

## 📊 **Reports & Displays Currently Missing**

### 1. **Results Summary Sheet (Bulk Lease Processing)**
**Excel/VBA:** `Sheets("Results")` - A comprehensive results table showing ALL leases processed
**Python App:** ❌ Missing

**Missing Fields/Columns in Results Sheet:**
- ✅ C4: Auto ID (Lease ID) - **EXISTS**
- ❌ D4: Opening Lease Liability (Non-current) - **PARTIAL** (only in lease result)
- ❌ E4: Opening Lease Liability (Current) - **PARTIAL** (only in lease result)  
- ✅ F4: Total Interest Expense - **EXISTS**
- ❌ G4: Opening ROU Asset - **EXISTS** but not in summary view
- ✅ H4: Total Depreciation - **EXISTS**
- ❌ I4: Gain/Loss in P&L (Termination, Modifications, COVID PE, Sublease) - **PARTIAL** (gain_loss_pnl exists but not detailed breakdown)
- ❌ J4: ARO Interest - **EXISTS** but not in summary view
- ❌ K4: Closing Security Deposit PV - **EXISTS** but not in summary view
- ❌ L4: Security Deposit Interest - **EXISTS** but not in summary view
- ❌ M4: Closing Security Deposit (Non-current) - **EXISTS** but not in summary view
- ❌ N4: Closing Security Deposit (Current) - **EXISTS** but not in summary view
- ✅ O4: Total Rent Paid - **EXISTS**
- ❌ P4: Opening ARO Liability - **EXISTS** but not in summary view
- ❌ Q4: Opening Lease Liability (for terminated leases) - **MISSING**
- ❌ R4: Change in ROU Asset - **EXISTS** but not in summary view
- ❌ S4: Opening ROU Asset (for terminated leases) - **MISSING**
- ❌ T4: Opening Security Deposit (for terminated leases) - **MISSING**
- ✅ U4: Asset Class - **EXISTS**
- ✅ V4: Cost Centre - **EXISTS**
- ✅ W4: Currency - **EXISTS**
- ✅ X4: Description - **EXISTS**
- ✅ Y4: Asset ID Code - **EXISTS**
- ❌ Z4: Original Lease ID (for modifications) - **MISSING**
- ❌ AA4: Modification Indicator ("Modifier") - **MISSING**
- ❌ AB4: Initial ROU Asset (for new leases) - **MISSING**
- ❌ AC4-AG4: **Projection Period 1-5** Closing Liability/ROU/Depreciation/Interest/Rent - **MISSING**
- ❌ BB4: Security Deposit Gross Amount - **MISSING**
- ❌ BC4: Accumulated Depreciation (from lease start) - **MISSING**
- ❌ BD4: Initial Direct Expenditure (on transition) - **MISSING**
- ❌ BE4: Prepaid Accrual - **MISSING**
- ❌ BG4: Borrowing Rate - **EXISTS** but not in summary
- ❌ BH4: Remaining ROU Life (in days) - **EXISTS** but not in summary
- ❌ BI4: COVID Practical Expedient Gain - **MISSING**

### 2. **Projections/Forecasting Report**
**Excel/VBA:** Multiple projection periods (up to 6) showing future liability, ROU, depreciation, interest, rent
**Python App:** ❌ Missing

**Missing Features:**
- Future period projections (1 month, 3 months, 6 months, 12 months ahead)
- Projection mode toggle (on/off)
- Projection date selection
- Current vs Non-current split in projections
- Full rent projection mode (projection mode 6)

### 3. **Journal & Disclosures Sheet**
**Excel/VBA:** `Sheets("JournalD")` - Detailed journal entries with disclosures
**Python App:** ✅ Basic Journal Entries exist, but missing:

**Missing Journal Entry Sections:**
- ❌ Opening Balance Section (Previous Period balances)
- ❌ IFRS vs US-GAAP Comparison Section
- ❌ Disclosures Section:
  - ❌ Total Lease Liability by entity/region
  - ❌ Total ROU Asset by category
  - ❌ Maturity Analysis (Lease payments due by year)
  - ❌ Variable Lease Payments
  - ❌ Short-term Leases (excluded from calculation)
  - ❌ Lease Incentives Received
  - ❌ Extension/Renewal Options
  - ❌ Purchase Options

### 4. **Summary Report Export**
**Excel/VBA:** `exporter("Summary")` function creates comprehensive Excel workbook
**Python App:** ✅ Basic export exists, but missing:

**Missing Export Features:**
- ❌ Multiple sheet workbook with:
  - ❌ Summary Sheet
  - ❌ Results Sheet (all leases)
  - ❌ Journal Sheet (consolidated)
  - ❌ Disclosures Sheet
  - ❌ Per-Lease Schedule Sheets
- ❌ Excel formatting (colors, borders, formulas)
- ❌ Pivot table ready data
- ❌ Chart/Graph generation

### 5. **Bulk Lease Processing**
**Excel/VBA:** Processes multiple leases (AutoID range: G2 to G3)
**Python App:** ❌ Missing

**Missing Features:**
- ❌ Batch calculation (multiple leases at once)
- ❌ Lease range selection (from ID to ID)
- ❌ Filtering by:
  - ❌ Cost Centre
  - ❌ Entity/Group
  - ❌ Asset Class
  - ❌ Profit Center
  - ❌ Date Modified range
  - ❌ Termination Date range
  - ❌ Lease Start Date range
- ❌ Aggregated results across leases
- ❌ Consolidated journal entries

---

## 🔧 **Functional Features Missing**

### 6. **Current/Non-Current Liability Split Logic**
**Excel/VBA:** Complex projection-based calculation
**Python App:** ⚠️ Placeholder (70/30 split) - **NEEDS VBA LOGIC PORT**

**Missing Logic:**
- Projection-based calculation (`projectionmode = 1`)
- Formula: `liacurrent = liacurrent + cell.Offset(0, 1).Value * cell.Offset(0, 2).Value / baldatepv`
- Alternative method when projection disabled (using closing balance method)
- Security deposit current/non-current split

### 7. **Lease Modifications Tracking**
**Excel/VBA:** Tracks original lease ID and modification relationships
**Python App:** ❌ Missing

**Missing Features:**
- ❌ Original Lease ID (Z4 in Results)
- ❌ Modification Indicator (AA4)
- ❌ Modification Gain/Loss calculation
- ❌ Modification relationship chain
- ❌ Modify-this-ID field

### 8. **Sublease Handling**
**Excel/VBA:** Complex sublease gain/loss calculations
**Python App:** ⚠️ Partial (sublease flag exists but calculations incomplete)

**Missing Calculations:**
- ❌ Sublease Gain/Loss on initial recognition
- ❌ Sublease Modification Gain/Loss
- ❌ Sublease ROU adjustment
- ❌ Sign multiplier (subl = -1 for subleases)

### 9. **Termination Penalty & Gain/Loss**
**Excel/VBA:** Calculates termination gain/loss including penalties
**Python App:** ⚠️ Partial (basic gain_loss_pnl exists)

**Missing Components:**
- ❌ Termination Penalty inclusion
- ❌ Security Deposit gross on termination
- ❌ Termination date handling
- ❌ Remaining ROU life = 0 on termination

### 10. **COVID Practical Expedient Gain**
**Excel/VBA:** Separate tracking of COVID-related gains
**Python App:** ❌ Missing

**Missing:**
- ❌ COVID Practical Expedient gain calculation
- ❌ COVID gain tracking (BI4 column)
- ❌ Separate disclosure

### 11. **Transition Accounting (IFRS 16)**
**Excel/VBA:** Handles transition options (2A, 2B)
**Python App:** ⚠️ Partial (field exists but logic incomplete)

**Missing:**
- ❌ Transition Option 2B handling
- ❌ Prepaid Accrual on transition (BE4)
- ❌ Initial Direct Expenditure on transition date (BD4)
- ❌ Transition date as Firstdate for Option 2B

### 12. **Asset Retirement Obligation (ARO) Details**
**Excel/VBA:** Multiple ARO dates and amounts with RFR rate tables
**Python App:** ⚠️ Partial (basic ARO exists)

**Missing:**
- ❌ ARO Table selection (0-10 tables)
- ❌ ARO Date arrays (ARO_date_1, ARO_date_2, etc.)
- ❌ ARO Rate Table lookup (RFR sheet)
- ❌ Multiple ARO provisions
- ❌ ARO Interest calculation with variable rates

### 13. **Security Deposit Details**
**Excel/VBA:** Multiple security deposits with dates
**Python App:** ⚠️ Partial (basic security deposit PV exists)

**Missing:**
- ❌ Security Deposit Date arrays (Security_date_1, Security_date_2, etc.)
- ❌ Multiple Security Deposit amounts
- ❌ Security Deposit Gross (BB4)
- ❌ Security Deposit Current/Non-current split
- ❌ Security Deposit on termination

### 14. **Purchase Option Handling**
**Excel/VBA:** Purchase option exercise date and price
**Python App:** ⚠️ Partial (fields exist but logic incomplete)

**Missing:**
- ❌ Purchase option exercise date handling
- ❌ Purchase option price application
- ❌ Remaining ROU life adjustment on purchase

### 15. **GAAP Standard Selection**
**Excel/VBA:** IFRS/Ind-AS vs US-GAAP toggle
**Python App:** ⚠️ Partial (field exists but limited application)

**Missing:**
- ❌ US-GAAP specific calculations
- ❌ IFRS vs US-GAAP comparison view
- ❌ Short-term lease exclusion by GAAP
- ❌ Finance lease classification by GAAP

---

## 📈 **UI/Display Features Missing**

### 16. **Dashboard Enhancements**
**Missing Displays:**
- ❌ Total Leases Count
- ❌ Total Lease Liability (aggregated)
- ❌ Total ROU Asset (aggregated)
- ❌ Total Monthly Rent Payments
- ❌ Upcoming Renewals
- ❌ Expiring Leases
- ❌ Lease Summary Cards
- ❌ Charts/Graphs (Liability trend, Payment schedule)

### 17. **Lease List/Table View**
**Missing Columns:**
- ❌ Opening Liability
- ❌ Closing Liability
- ❌ Monthly Rent
- ❌ Remaining Term
- ❌ Status (Active/Terminated/Expired)
- ❌ Modification Relationship
- ❌ Quick Actions (View, Edit, Calculate, Delete)

### 18. **Calculation Results Display**
**Missing Sections:**
- ❌ Gain/Loss Breakdown:
  - ❌ Termination Penalty
  - ❌ Modification Gain/Loss
  - ❌ COVID PE Gain
  - ❌ Sublease Gain/Loss
- ❌ Opening vs Closing Balance Comparison
- ❌ Period-over-Period Comparison
- ❌ Year-over-Year Trends
- ❌ Remaining ROU Life Days
- ❌ Cumulative Depreciation

### 19. **Schedule Table Enhancements**
**Missing Columns:**
- ❌ Principal Payment
- ❌ Remaining Balance (for each row)
- ❌ Cumulative Interest
- ❌ Cumulative Depreciation
- ❌ Change in ROU Asset
- ❌ ARO Provision (per row)
- ❌ Full detailed 13-column schedule display

### 20. **Filters & Search**
**Missing:**
- ❌ Search by Lease ID, Description, Asset Code
- ❌ Filter by Date Range
- ❌ Filter by Asset Class
- ❌ Filter by Cost Centre
- ❌ Filter by Currency
- ❌ Filter by Status
- ❌ Sort by various columns

---

## 🔐 **Enterprise Features Missing**

### 21. **Multi-Entity/Group Support**
**Excel/VBA:** Group Entity Name filtering
**Python App:** ❌ Missing

**Missing:**
- ❌ Entity/Group field in lease data
- ❌ Entity filtering
- ❌ Entity-specific reports
- ❌ Entity-level aggregation

### 22. **Profit Center Support**
**Excel/VBA:** Profit Center filtering
**Python App:** ❌ Missing

**Missing:**
- ❌ Profit Center field
- ❌ Profit Center filtering
- ❌ Profit Center reporting

### 23. **Region/Segment Support**
**Excel/VBA:** Region and Segment fields
**Python App:** ⚠️ Partial (fields exist but not utilized)

**Missing:**
- ❌ Region filtering
- ❌ Segment filtering
- ❌ Region/Segment reporting

### 24. **Online Data Download**
**Excel/VBA:** `OnlineDown()` function for external data sync
**Python App:** ❌ Missing

**Missing:**
- ❌ External data integration
- ❌ Online data pull
- ❌ Data synchronization

### 25. **Licensing/Authentication Matrix**
**Excel/VBA:** User authentication with domain checking
**Python App:** ✅ Basic auth exists, but missing:

**Missing:**
- ❌ License expiry date
- ❌ Domain-based authentication
- ❌ User permission matrix
- ❌ Entity access control

---

## 📊 **Data & Reporting Gaps**

### 26. **Date Range Calculation Options**
**Excel/VBA:** Multiple balance date options
**Python App:** ✅ Basic date range exists

**Missing Options:**
- ❌ Single date calculation (balance sheet date)
- ❌ Period-based calculation
- ❌ Fiscal year calculation
- ❌ Quarter-end calculation
- ❌ Month-end calculation

### 27. **Print/Export Formats**
**Missing Formats:**
- ❌ PDF Export
- ❌ CSV Export
- ❌ XML Export (for ERP integration)
- ❌ Print-friendly layouts
- ❌ Email report generation

### 28. **Audit Trail**
**Excel/VBA:** Implicit (Excel file versioning)
**Python App:** ❌ Missing

**Missing:**
- ❌ Calculation history
- ❌ User activity log
- ❌ Change tracking
- ❌ Version history
- ❌ Calculation audit report

### 29. **Validation & Error Reporting**
**Missing:**
- ❌ Data validation warnings
- ❌ Calculation error details
- ❌ Missing field indicators
- ❌ Inconsistency flags
- ❌ Formula error explanations

### 30. **Advanced Calculations Missing**
**Missing:**
- ❌ Interpolation for exact balance dates
- ❌ Leap year handling in projections
- ❌ Compound frequency variations
- ❌ Variable borrowing rates
- ❌ Index-linked rental escalation

---

## ✅ **What IS Currently Implemented**

1. ✅ **Basic Lease Calculation** - Single lease amortization schedule
2. ✅ **Journal Entries** - Basic journal entry generation
3. ✅ **User Authentication** - Login/logout system
4. ✅ **Lease CRUD** - Create, Read, Update, Delete leases
5. ✅ **Amortization Schedule** - Payment schedule with dates
6. ✅ **Basic Summary** - Opening/Closing balances
7. ✅ **Excel Export** - Simple Excel export
8. ✅ **Date Range Filtering** - From/To date calculation
9. ✅ **Escalation** - Rental escalation calculation
10. ✅ **Security Deposit PV** - Present value calculation
11. ✅ **ARO Provision** - Basic ARO calculation
12. ✅ **ROU Asset & Depreciation** - Basic calculations

---

## 📋 **Priority Recommendations**

### **High Priority (Core Functionality)**
1. Bulk lease processing with Results summary table
2. Proper Current/Non-Current liability split (VBA logic)
3. Projection periods (forecasting)
4. Complete journal entry sections (Opening, IFRS/US-GAAP)
5. Gain/Loss breakdown (Termination, Modifications, Sublease)

### **Medium Priority (Enhanced Reporting)**
6. Disclosures section
7. Export with multiple sheets
8. Dashboard with aggregated totals
9. Filters and search
10. Lease modification tracking

### **Low Priority (Nice to Have)**
11. Charts and graphs
12. PDF export
13. Audit trail
14. Advanced ARO with rate tables
15. Online data integration

---

**Last Updated:** Based on VBA code analysis from `VB script/Code` and current Python implementation
**Total Missing Features:** ~30 major features + multiple sub-features


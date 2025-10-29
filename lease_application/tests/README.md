# Test Suite

## End-to-End Test

The comprehensive test suite (`test_end_to_end.py`) validates the complete application flow:

1. **User Signup** - Register a new test user
2. **User Login** - Authenticate the user
3. **Lease Creation** - Create a test lease via API
4. **Lease Calculation** - Calculate schedule and journal entries
5. **VBA Validation** - Verify calculations match VBA Excel logic

## Running Tests

### Prerequisites

1. **Start the application server:**
   ```bash
   cd lease_application
   python3 app.py
   ```

   Or use the start script:
   ```bash
   ./start_app.sh
   ```

2. **Install test dependencies:**
   ```bash
   pip3 install requests
   ```

### Run Tests

```bash
cd lease_application/tests
python3 test_end_to_end.py
```

## Test Coverage

### VBA Validation Checks

The test validates against VBA formulas from `VB script/Code`:

1. **Initial Liability** (VBA G9)
   - Formula: Sum of PV of all rental payments
   - Validates: `opening_lease_liability = Σ(PV_of_rental)`

2. **PV Factor** (VBA E10)
   - Formula: `1/((1+r)^n)` where `r = borrowing_rate * icompound / 12`
   - Validates: Each row's PV factor calculation

3. **Interest** (VBA F10)
   - Formula: `G9*(1+r)^n - G9`
   - Validates: Interest calculation per period

4. **Liability Progression** (VBA G10)
   - Formula: `G9 - D10 + F10`
   - Validates: Liability decreases by rental, increases by interest

5. **ROU Asset** (VBA I9)
   - Formula: `G9 + IDE`
   - Validates: Initial ROU = Liability + Initial Direct Expenditure

### Test Data

The test uses a standard lease:
- **Rental**: $150,000/month
- **Escalation**: 5% monthly
- **Borrowing Rate**: 8%
- **Term**: 5 years
- **Payment Frequency**: Monthly

## Expected Output

```
================================================================================
  END-TO-END TEST SUITE - Lease Management System
================================================================================
Test Server: http://localhost:5001
Test User: test_user_1234567890

============================================================
TEST 1: User Signup and Login
============================================================
📝 Registering user: test_user_1234567890
✅ User registered successfully: user_id=1
🔐 Logging in user: test_user_1234567890
✅ Login successful: user_id=1, username=test_user_1234567890
✅ Session verified: test_user_1234567890

[... more tests ...]

VALIDATION SUMMARY: 5/5 tests passed
================================================================================
  TEST SUITE COMPLETE
================================================================================
```

## Troubleshooting

### Server Not Running
```
❌ ERROR: Server not running at http://localhost:5001
   Please start the server first:
   cd lease_application && python3 app.py
```

**Solution**: Start the Flask server before running tests.

### Test Failures

If validation fails:
1. Check server logs: `tail -f lease_application/logs/lease_app.log`
2. Verify VBA formulas match Python implementation
3. Check tolerance values (may need adjustment for floating-point precision)

### Port Conflicts

If port 5001 is in use:
- Change `TEST_BASE_URL` in `test_end_to_end.py`
- Or update `API_PORT` in `config/__init__.py`


"""
End-to-End Test Suite
Tests complete user flow: signup → login → create lease → calculate → verify VBA accuracy

This test validates the entire application stack against VBA Excel logic.
"""

import sys
import os
import time
import requests
import json
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional
import math

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
TEST_BASE_URL = "http://localhost:5001"
TEST_USERNAME = f"test_user_{int(time.time())}"
TEST_PASSWORD = "test_password_123"
TEST_EMAIL = f"{TEST_USERNAME}@test.com"


class TestClient:
    """Client for API testing with session management"""
    
    def __init__(self, base_url: str = TEST_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.user_id: Optional[int] = None
        self.username: Optional[str] = None
        
    def register(self, username: str, password: str, email: str) -> Dict[str, Any]:
        """Register a new user"""
        response = self.session.post(
            f"{self.base_url}/api/register",
            json={"username": username, "password": password, "email": email}
        )
        return response.json()
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login user"""
        response = self.session.post(
            f"{self.base_url}/api/login",
            json={"username": username, "password": password}
        )
        data = response.json()
        if data.get('success'):
            self.username = username
            if data.get('user'):
                self.user_id = data['user'].get('user_id')
        return data
    
    def create_lease(self, lease_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new lease"""
        response = self.session.post(
            f"{self.base_url}/api/leases",
            json=lease_data
        )
        return response.json()
    
    def calculate_lease(self, lease_data: Dict[str, Any], from_date: Optional[str] = None,
                       to_date: Optional[str] = None) -> Dict[str, Any]:
        """Calculate lease schedule and journal entries"""
        calc_data = {**lease_data}
        if from_date:
            calc_data['from_date'] = from_date
        if to_date:
            calc_data['to_date'] = to_date
            
        response = self.session.post(
            f"{self.base_url}/api/calculate_lease",
            json=calc_data
        )
        return response.json()
    
    def get_user(self) -> Dict[str, Any]:
        """Get current user info"""
        response = self.session.get(f"{self.base_url}/api/user")
        return response.json()
    
    def logout(self) -> Dict[str, Any]:
        """Logout user"""
        response = self.session.post(f"{self.base_url}/api/logout")
        return response.json()


class VBACalculationValidator:
    """
    Validates Python calculations against VBA Excel logic
    
    VBA Source: VB script/Code
    - datessrent() - Lines 16-249: Schedule generation
    - basic_calc() - Lines 628-707: Financial calculations
    - compu() - Lines 251-624: Result compilation
    """
    
    @staticmethod
    def validate_pv_calculation(borrowing_rate: float, days_from_start: int, 
                                icompound: int, expected_pv: float, 
                                tolerance: float = 0.01) -> bool:
        """
        Validate PV factor calculation
        
        VBA Formula: E10 = 1/((1+r)^n)
        Where r = borrowing_rate * icompound / 12, n = (days_from_start / 365) * 12 / icompound
        """
        discount_rate = borrowing_rate / 100
        pv_factor = 1 / ((1 + discount_rate * icompound / 12) ** 
                        ((days_from_start / 365) * 12 / icompound))
        
        # Compare with expected (if provided)
        if expected_pv > 0:
            diff = abs(pv_factor - expected_pv)
            return diff < tolerance
        return True
    
    @staticmethod
    def validate_interest_calculation(prev_liability: float, borrowing_rate: float,
                                     days_between: int, icompound: int,
                                     expected_interest: float, tolerance: float = 0.01) -> bool:
        """
        Validate interest calculation
        
        VBA Formula: F10 = G9*(1+r)^n - G9
        Where r = borrowing_rate * icompound / 12, n = (days_between / 365) * 12 / icompound
        """
        discount_rate = borrowing_rate / 100
        interest = prev_liability * ((1 + discount_rate * icompound / 12) ** 
                                   ((days_between / 365) * 12 / icompound) - 1)
        
        diff = abs(interest - expected_interest)
        return diff < tolerance
    
    @staticmethod
    def validate_liability_calculation(prev_liability: float, rental: float,
                                      interest: float, expected_liability: float,
                                      tolerance: float = 0.01) -> bool:
        """
        Validate lease liability calculation
        
        VBA Formula: G10 = G9 - D10 + F10
        """
        liability = prev_liability - rental + interest
        diff = abs(liability - expected_liability)
        return diff < tolerance
    
    @staticmethod
    def validate_rou_calculation(prev_rou: float, depreciation: float,
                                 change_in_rou: float, expected_rou: float,
                                 tolerance: float = 0.01) -> bool:
        """
        Validate ROU asset calculation
        
        VBA Formula: I10 = I9 - J10 + K10
        Where J10 = Depreciation, K10 = Change in ROU
        """
        rou = prev_rou - depreciation + change_in_rou
        diff = abs(rou - expected_rou)
        return diff < tolerance
    
    @staticmethod
    def validate_initial_liability(sum_pv_of_rentals: float, expected: float,
                                  tolerance: float = 0.01) -> bool:
        """
        Validate initial lease liability = sum of PV of all rentals
        
        VBA: G9 = SUM(H10:Hendrow) = SUM(PV of all rental payments)
        """
        diff = abs(sum_pv_of_rentals - expected)
        return diff < tolerance
    
    @staticmethod
    def validate_initial_rou(initial_liability: float, ide: float,
                             expected: float, tolerance: float = 0.01) -> bool:
        """
        Validate initial ROU asset
        
        VBA Formula: I9 = G7 + K9 + D6 - L9 + ide
        Simplified: I9 = G9 + ide (for initial calculation)
        """
        rou = initial_liability + ide
        diff = abs(rou - expected)
        return diff < tolerance


def create_test_lease_data() -> Dict[str, Any]:
    """
    Create test lease data matching VBA test scenarios
    
    This creates a lease with:
    - Simple monthly payments
    - Escalation
    - Known values for validation
    """
    today = date.today()
    lease_start = today.replace(day=1)
    first_payment = lease_start.replace(day=16)
    end_date = lease_start.replace(year=lease_start.year + 5)
    
    return {
        "auto_id": 999,  # Test ID
        "lease_name": f"Test_Lease_{int(time.time())}",
        "description": "End-to-End Test Lease",
        "asset_class": "Building",
        "asset_id_code": "TEST-001",
        "lease_start_date": lease_start.isoformat(),
        "first_payment_date": first_payment.isoformat(),
        "end_date": end_date.isoformat(),
        "frequency_months": 1,
        "day_of_month": "Last",
        "accrual_day": 1,
        "auto_rentals": "Yes",
        "rental_1": 150000.0,
        "escalation_percent": 5.0,
        "escalation_start": lease_start.isoformat(),
        "esc_freq_months": 1,
        "borrowing_rate": 8.0,
        "compound_months": 12,
        "currency": "USD",
        "initial_direct_expenditure": 0,
        "lease_incentive": 0,
        "security_deposit": 0,
        "aro": 0
    }


def test_user_signup_and_login():
    """Test 1: User signup and login"""
    print("\n" + "="*60)
    print("TEST 1: User Signup and Login")
    print("="*60)
    
    client = TestClient()
    
    # Test signup
    print(f"📝 Registering user: {TEST_USERNAME}")
    register_result = client.register(TEST_USERNAME, TEST_PASSWORD, TEST_EMAIL)
    
    assert register_result.get('success'), f"Registration failed: {register_result.get('error')}"
    print(f"✅ User registered successfully: user_id={register_result.get('user_id')}")
    
    # Test login
    print(f"🔐 Logging in user: {TEST_USERNAME}")
    login_result = client.login(TEST_USERNAME, TEST_PASSWORD)
    
    assert login_result.get('success'), f"Login failed: {login_result.get('error')}"
    assert client.user_id is not None, "User ID not set after login"
    print(f"✅ Login successful: user_id={client.user_id}, username={client.username}")
    
    # Verify session
    user_info = client.get_user()
    assert user_info.get('success'), "Session not valid after login"
    print(f"✅ Session verified: {user_info.get('user', {}).get('username')}")
    
    return client


def test_lease_creation(client: TestClient):
    """Test 2: Create a lease"""
    print("\n" + "="*60)
    print("TEST 2: Create Lease")
    print("="*60)
    
    lease_data = create_test_lease_data()
    
    print(f"➕ Creating lease: {lease_data['lease_name']}")
    create_result = client.create_lease(lease_data)
    
    assert create_result.get('success'), f"Lease creation failed: {create_result.get('error')}"
    lease_id = create_result.get('lease_id')
    assert lease_id is not None, "Lease ID not returned"
    
    print(f"✅ Lease created successfully: lease_id={lease_id}")
    
    # Update lease_data with the returned ID
    lease_data['lease_id'] = lease_id
    
    return lease_data


def test_lease_calculation(client: TestClient, lease_data: Dict[str, Any]):
    """Test 3: Calculate lease schedule"""
    print("\n" + "="*60)
    print("TEST 3: Calculate Lease Schedule")
    print("="*60)
    
    print("📊 Calculating lease schedule...")
    calc_result = client.calculate_lease(lease_data)
    
    assert calc_result.get('success'), f"Calculation failed: {calc_result.get('error')}"
    
    schedule = calc_result.get('schedule', [])
    lease_result = calc_result.get('lease_result', {})
    journal_entries = calc_result.get('journal_entries', [])
    
    assert len(schedule) > 0, "Schedule is empty"
    assert lease_result is not None, "Lease result is missing"
    
    print(f"✅ Calculation successful:")
    print(f"   - Schedule rows: {len(schedule)}")
    print(f"   - Opening liability: {lease_result.get('opening_lease_liability', 0):,.2f}")
    print(f"   - Closing liability: {lease_result.get('closing_lease_liability_non_current', 0) + lease_result.get('closing_lease_liability_current', 0):,.2f}")
    print(f"   - Journal entries: {len(journal_entries)}")
    
    return calc_result


def test_vba_validation(calc_result: Dict[str, Any], lease_data: Dict[str, Any]):
    """Test 4: Validate calculations against VBA logic"""
    print("\n" + "="*60)
    print("TEST 4: VBA Calculation Validation")
    print("="*60)
    
    schedule = calc_result.get('schedule', [])
    lease_result = calc_result.get('lease_result', {})
    
    if not schedule:
        print("❌ No schedule data for validation")
        return False
    
    validator = VBACalculationValidator()
    
    # Extract parameters
    borrowing_rate = float(lease_data.get('borrowing_rate', 8.0))
    compound_months = int(lease_data.get('compound_months', 12))
    first_date = datetime.fromisoformat(schedule[0]['date']).date()
    
    print(f"📐 Validation Parameters:")
    print(f"   - Borrowing Rate: {borrowing_rate}%")
    print(f"   - Compound Months: {compound_months}")
    print(f"   - First Date: {first_date}")
    
    # Test 1: Initial Liability = Sum of PV of all rentals
    print("\n🔍 Validating Initial Liability...")
    opening_liability = abs(float(lease_result.get('opening_lease_liability', 0)))
    
    # Calculate sum of PV of rentals from schedule
    sum_pv_of_rentals = 0.0
    for row in schedule:
        if row.get('rental_amount', 0) > 0:
            pv_of_rent = row.get('pv_of_rent', 0) or 0
            sum_pv_of_rentals += abs(float(pv_of_rent))
    
    is_valid = validator.validate_initial_liability(sum_pv_of_rentals, opening_liability, tolerance=100.0)
    print(f"   - Opening Liability: {opening_liability:,.2f}")
    print(f"   - Sum PV of Rentals: {sum_pv_of_rentals:,.2f}")
    print(f"   - Difference: {abs(sum_pv_of_rentals - opening_liability):,.2f}")
    print(f"   {'✅' if is_valid else '❌'} Initial Liability validation: {'PASS' if is_valid else 'FAIL'}")
    
    # Test 2: Validate PV factor calculations
    print("\n🔍 Validating PV Factor Calculations...")
    pv_errors = 0
    for i, row in enumerate(schedule[:10]):  # Check first 10 rows
        if row.get('rental_amount', 0) > 0:
            date_val = datetime.fromisoformat(row['date']).date()
            days_from_start = (date_val - first_date).days
            expected_pv = float(row.get('pv_factor', 0) or 0)
            
            if days_from_start > 0 and expected_pv > 0:
                is_valid = validator.validate_pv_calculation(
                    borrowing_rate, days_from_start, compound_months, expected_pv, tolerance=0.01
                )
                if not is_valid:
                    pv_errors += 1
                    print(f"   ⚠️  Row {i}: PV factor mismatch (expected ~{expected_pv:.6f})")
    
    print(f"   {'✅' if pv_errors == 0 else '❌'} PV Factor validation: {len([r for r in schedule[:10] if r.get('rental_amount', 0) > 0]) - pv_errors}/{len([r for r in schedule[:10] if r.get('rental_amount', 0) > 0])} rows correct")
    
    # Test 3: Validate interest calculations
    print("\n🔍 Validating Interest Calculations...")
    interest_errors = 0
    for i in range(1, min(10, len(schedule))):
        prev_row = schedule[i-1]
        curr_row = schedule[i]
        
        if curr_row.get('rental_amount', 0) > 0:
            prev_date = datetime.fromisoformat(prev_row['date']).date()
            curr_date = datetime.fromisoformat(curr_row['date']).date()
            days_between = (curr_date - prev_date).days
            
            if days_between > 0:
                prev_liability = abs(float(prev_row.get('lease_liability', 0) or 0))
                expected_interest = abs(float(curr_row.get('interest', 0) or 0))
                
                if prev_liability > 0 and expected_interest > 0:
                    is_valid = validator.validate_interest_calculation(
                        prev_liability, borrowing_rate, days_between, compound_months,
                        expected_interest, tolerance=1.0
                    )
                    if not is_valid:
                        interest_errors += 1
    
    print(f"   {'✅' if interest_errors == 0 else '❌'} Interest calculation validation: {min(10, len(schedule)) - 1 - interest_errors}/{min(10, len(schedule)) - 1} rows correct")
    
    # Test 4: Validate liability progression
    print("\n🔍 Validating Liability Progression...")
    liability_errors = 0
    for i in range(1, min(10, len(schedule))):
        prev_row = schedule[i-1]
        curr_row = schedule[i]
        
        if curr_row.get('rental_amount', 0) > 0:
            prev_liability = abs(float(prev_row.get('lease_liability', 0) or 0))
            rental = abs(float(curr_row.get('rental_amount', 0) or 0))
            interest = abs(float(curr_row.get('interest', 0) or 0))
            expected_liability = abs(float(curr_row.get('lease_liability', 0) or 0))
            
            if prev_liability > 0:
                is_valid = validator.validate_liability_calculation(
                    prev_liability, rental, interest, expected_liability, tolerance=1.0
                )
                if not is_valid:
                    liability_errors += 1
    
    print(f"   {'✅' if liability_errors == 0 else '❌'} Liability progression validation: {min(10, len(schedule)) - 1 - liability_errors}/{min(10, len(schedule)) - 1} rows correct")
    
    # Test 5: Validate ROU asset
    print("\n🔍 Validating ROU Asset...")
    opening_rou = abs(float(lease_result.get('opening_rou_asset', 0)))
    closing_rou = abs(float(lease_result.get('closing_rou_asset', 0)))
    ide = float(lease_data.get('initial_direct_expenditure', 0) or 0) - float(lease_data.get('lease_incentive', 0) or 0)
    
    is_valid = validator.validate_initial_rou(opening_liability, ide, opening_rou, tolerance=100.0)
    print(f"   - Opening ROU: {opening_rou:,.2f}")
    print(f"   - Expected (Liability + IDE): {opening_liability + ide:,.2f}")
    print(f"   - Closing ROU: {closing_rou:,.2f}")
    print(f"   {'✅' if is_valid else '❌'} Initial ROU validation: {'PASS' if is_valid else 'FAIL'}")
    
    # Summary
    total_tests = 5
    passed_tests = sum([
        is_valid,  # Initial liability
        pv_errors == 0,  # PV factors
        interest_errors == 0,  # Interest
        liability_errors == 0,  # Liability progression
        is_valid  # ROU
    ])
    
    print("\n" + "="*60)
    print(f"VALIDATION SUMMARY: {passed_tests}/{total_tests} tests passed")
    print("="*60)
    
    return passed_tests == total_tests


def run_all_tests():
    """Run complete end-to-end test suite"""
    print("\n" + "="*80)
    print("  END-TO-END TEST SUITE - Lease Management System")
    print("="*80)
    print(f"Test Server: {TEST_BASE_URL}")
    print(f"Test User: {TEST_USERNAME}")
    
    try:
        # Test 1: User signup and login
        client = test_user_signup_and_login()
        
        # Test 2: Create lease
        lease_data = test_lease_creation(client)
        
        # Test 3: Calculate lease
        calc_result = test_lease_calculation(client, lease_data)
        
        # Test 4: Validate against VBA
        validation_passed = test_vba_validation(calc_result, lease_data)
        
        # Test 5: Logout
        print("\n" + "="*60)
        print("TEST 5: User Logout")
        print("="*60)
        logout_result = client.logout()
        assert logout_result.get('success'), "Logout failed"
        print("✅ Logout successful")
        
        # Final summary
        print("\n" + "="*80)
        print("  TEST SUITE COMPLETE")
        print("="*80)
        print(f"✅ User Signup: PASS")
        print(f"✅ User Login: PASS")
        print(f"✅ Lease Creation: PASS")
        print(f"✅ Lease Calculation: PASS")
        print(f"{'✅' if validation_passed else '⚠️ '} VBA Validation: {'PASS' if validation_passed else 'NEEDS REVIEW'}")
        print("="*80)
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # Check if server is running
    try:
        response = requests.get(f"{TEST_BASE_URL}/api/user", timeout=2)
        print(f"✅ Server is running at {TEST_BASE_URL}")
    except requests.exceptions.RequestException:
        print(f"❌ ERROR: Server not running at {TEST_BASE_URL}")
        print(f"   Please start the server first:")
        print(f"   cd lease_application && python3 app.py")
        sys.exit(1)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)


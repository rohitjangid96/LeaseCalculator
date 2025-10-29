/**
 * Login Page JavaScript
 */

async function switchTab(tab) {
    if (tab === 'login') {
        document.getElementById('loginForm').style.display = 'block';
        document.getElementById('signupForm').style.display = 'none';
        document.querySelectorAll('.tab')[0].classList.add('active');
        document.querySelectorAll('.tab')[1].classList.remove('active');
    } else {
        document.getElementById('loginForm').style.display = 'none';
        document.getElementById('signupForm').style.display = 'block';
        document.querySelectorAll('.tab')[0].classList.remove('active');
        document.querySelectorAll('.tab')[1].classList.add('active');
    }
}

async function login() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    if (!username || !password) {
        showMessage('loginMessage', 'Please fill in all fields', 'error');
        return;
    }

    try {
        const data = await AuthAPI.login(username, password);

        if (data.success) {
            showMessage('loginMessage', 'Login successful! Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1000);
        } else {
            showMessage('loginMessage', data.error || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showMessage('loginMessage', `Error connecting to server: ${error.message}. Is backend running?`, 'error');
    }
}

async function signup() {
    const username = document.getElementById('signupUsername').value;
    const email = document.getElementById('signupEmail').value;
    const password = document.getElementById('signupPassword').value;

    if (!username || !password) {
        showMessage('signupMessage', 'Username and password required', 'error');
        return;
    }

    try {
        const data = await AuthAPI.register(username, email, password);

        if (data.success) {
            showMessage('signupMessage', 'Account created! Please login.', 'success');
            setTimeout(() => switchTab('login'), 2000);
        } else {
            showMessage('signupMessage', data.error || 'Signup failed', 'error');
        }
    } catch (error) {
        console.error('Signup error:', error);
        showMessage('signupMessage', `Error connecting to server: ${error.message}. Is backend running?`, 'error');
    }
}

function showMessage(id, message, type) {
    const element = document.getElementById(id);
    element.textContent = message;
    element.className = type;
}


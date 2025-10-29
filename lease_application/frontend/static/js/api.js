/**
 * API Client
 * Centralized API communication functions
 */

const API_BASE_URL = 'http://localhost:5001/api';

/**
 * API Request Helper
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const defaultOptions = {
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };
    
    try {
        const response = await fetch(url, defaultOptions);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

/**
 * Authentication API
 */
const AuthAPI = {
    async login(username, password) {
        return apiRequest('/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    },
    
    async register(username, email, password) {
        return apiRequest('/register', {
            method: 'POST',
            body: JSON.stringify({ username, email, password })
        });
    },
    
    async logout() {
        return apiRequest('/logout', { method: 'POST' });
    },
    
    async getCurrentUser() {
        return apiRequest('/user', { method: 'GET' });
    }
};

/**
 * Leases API
 */
const LeasesAPI = {
    async getAll() {
        return apiRequest('/leases', { method: 'GET' });
    },
    
    async get(leaseId) {
        return apiRequest(`/leases/${leaseId}`, { method: 'GET' });
    },
    
    async create(leaseData) {
        return apiRequest('/leases', {
            method: 'POST',
            body: JSON.stringify(leaseData)
        });
    },
    
    async update(leaseId, leaseData) {
        return apiRequest(`/leases/${leaseId}`, {
            method: 'PUT',
            body: JSON.stringify(leaseData)
        });
    },
    
    async delete(leaseId) {
        return apiRequest(`/leases/${leaseId}`, { method: 'DELETE' });
    }
};

/**
 * Calculation API
 */
const CalculationAPI = {
    async calculate(calculationData) {
        return apiRequest('/calculate_lease', {
            method: 'POST',
            body: JSON.stringify(calculationData)
        });
    }
};


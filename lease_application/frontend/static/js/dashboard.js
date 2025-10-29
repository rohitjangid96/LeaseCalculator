/**
 * Dashboard Page JavaScript
 */

// Initialize on page load
window.addEventListener('DOMContentLoaded', async () => {
    // Check authentication and load leases
    const isAuthenticated = await requireAuth('login.html');
    if (isAuthenticated) {
        await updateUserDisplay('username');
        await loadLeases();
    }
});

async function loadLeases() {
    try {
        const data = await LeasesAPI.getAll();
        
        if (data.success) {
            displayLeases(data.leases);
        }
    } catch (error) {
        console.error('Failed to load leases:', error);
        alert('Failed to load leases. Please try again.');
    }
}

function displayLeases(leases) {
    const container = document.getElementById('leasesContainer');
    
    if (leases.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h2>No leases yet</h2>
                <p>Create your first lease to get started</p>
            </div>
        `;
        return;
    }

    container.innerHTML = leases.map(lease => `
        <div class="lease-card">
            <div class="lease-header">
                <div class="lease-name">${escapeHtml(lease.lease_name || 'Untitled Lease')}</div>
                <span class="lease-badge">${escapeHtml(lease.asset_class || 'N/A')}</span>
            </div>
            <div class="lease-info">
                <div><strong>Asset:</strong> ${escapeHtml(lease.asset_id_code || 'N/A')}</div>
                <div><strong>Start:</strong> ${lease.lease_start_date || 'N/A'}</div>
                <div><strong>End:</strong> ${lease.end_date || 'N/A'}</div>
                <div><strong>Created:</strong> ${new Date(lease.created_at).toLocaleDateString()}</div>
            </div>
            <div class="lease-actions">
                <button onclick="editLease(${lease.lease_id})">Edit</button>
                <button onclick="calculateLease(${lease.lease_id})">Calculate</button>
                <button onclick="deleteLease(${lease.lease_id})" style="background: #e74c3c; color: white;">Delete</button>
            </div>
        </div>
    `).join('');
}

function createLease() {
    window.location.href = 'complete_lease_form.html';
}

function editLease(leaseId) {
    window.location.href = `complete_lease_form.html?id=${leaseId}`;
}

function calculateLease(leaseId) {
    window.location.href = `calculate.html?lease_id=${leaseId}`;
}

async function deleteLease(leaseId) {
    if (!confirm('Are you sure you want to delete this lease?')) return;
    
    try {
        await LeasesAPI.delete(leaseId);
        loadLeases(); // Refresh list
    } catch (error) {
        console.error('Failed to delete lease:', error);
        alert('Failed to delete lease. Please try again.');
    }
}

function refreshLeases() {
    loadLeases();
}

async function logout() {
    try {
        await AuthAPI.logout();
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        window.location.href = 'login.html';
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


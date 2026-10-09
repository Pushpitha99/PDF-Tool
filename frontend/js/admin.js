let autoRefreshTimer = null;

function getAuthHeader() {
    const auth = sessionStorage.getItem('admin_auth');
    return auth ? { 'Authorization': `Basic ${auth}` } : {};
}

function showLoginModal(errMsg = '') {
    const modal = document.getElementById('login-modal');
    const errContainer = document.getElementById('login-error-msg');
    if (errMsg) {
        errContainer.textContent = errMsg;
        errContainer.classList.remove('hidden');
    } else {
        errContainer.classList.add('hidden');
    }
    modal.classList.remove('hidden');
}

function hideLoginModal() {
    document.getElementById('login-modal').classList.add('hidden');
}

function handleLoginSubmit(event) {
    event.preventDefault();
    const user = document.getElementById('admin-user-input').value.trim();
    const pass = document.getElementById('admin-pass-input').value.trim();
    if (!user || !pass) return;

    const authB64 = btoa(`${user}:${pass}`);
    sessionStorage.setItem('admin_auth', authB64);
    hideLoginModal();

    // Immediately test credentials by fetching stats
    fetchMetrics();
    fetchStorage();
}

document.addEventListener('DOMContentLoaded', () => {
    // Check if auth exists
    if (!sessionStorage.getItem('admin_auth')) {
        showLoginModal();
    } else {
        fetchMetrics();
        fetchStorage();
    }
    
    // Auto-refresh metrics every 5 seconds
    autoRefreshTimer = setInterval(() => {
        if (sessionStorage.getItem('admin_auth')) {
            fetchMetrics();
            fetchStorage();
        }
    }, 5000);
});

function switchTab(tabName) {
    document.getElementById('tab-dashboard').classList.add('hidden');
    document.getElementById('tab-storage').classList.add('hidden');
    document.getElementById('tab-users').classList.add('hidden');
    document.getElementById('tab-health').classList.add('hidden');

    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    document.getElementById(`tab-${tabName}`).classList.remove('hidden');

    const navIndex = tabName === 'dashboard' ? 0 : (tabName === 'storage' ? 1 : (tabName === 'users' ? 2 : 3));
    document.querySelectorAll('.nav-item')[navIndex].classList.add('active');

    const titleMap = {
        'dashboard': 'System Overview',
        'storage': 'Storage Manager',
        'users': 'User Management & Accounts',
        'health': 'Server Health & Diagnostics'
    };
    document.getElementById('page-title').textContent = titleMap[tabName] || 'Dashboard';

    if (tabName === 'users') {
        fetchUsers();
    }
}

async function fetchMetrics() {
    try {
        const response = await fetch('/api/v1/admin/stats', {
            headers: getAuthHeader()
        });
        
        if (response.status === 401) {
            sessionStorage.removeItem('admin_auth');
            showLoginModal('Invalid username or password.');
            return;
        }
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        hideLoginModal();
        updateMetricsUI(data);
    } catch (err) {
        console.error('Failed to fetch stats:', err);
    }
}

function updateMetricsUI(data) {
    document.getElementById('val-cpu').textContent = `${data.cpu.percent}%`;
    document.getElementById('bar-cpu').style.width = `${data.cpu.percent}%`;
    document.getElementById('sub-cpu').textContent = `Logical Cores: ${data.cpu.cores}`;

    document.getElementById('val-ram').textContent = `${data.memory.percent}%`;
    document.getElementById('bar-ram').style.width = `${data.memory.percent}%`;
    document.getElementById('sub-ram').textContent = `${data.memory.used_mb} MB / ${data.memory.total_mb} MB`;

    document.getElementById('val-disk').textContent = `${data.disk.percent}%`;
    document.getElementById('bar-disk').style.width = `${data.disk.percent}%`;
    document.getElementById('sub-disk').textContent = `Free: ${data.disk.free_gb} GB / ${data.disk.total_gb} GB`;

    document.getElementById('val-temp-mb').textContent = `${data.temp_storage.mb} MB`;
    document.getElementById('sub-temp-files').textContent = `${data.temp_storage.file_count} File(s) Pending`;

    document.getElementById('health-last-refreshed').textContent = new Date().toLocaleTimeString();
}

async function fetchStorage() {
    try {
        const response = await fetch('/api/v1/admin/storage', {
            headers: getAuthHeader()
        });

        if (response.status === 401) {
            sessionStorage.removeItem('admin_auth');
            showLoginModal('Invalid username or password.');
            return;
        }

        if (!response.ok) return;

        const data = await response.json();
        renderStorageTable(data);
    } catch (err) {
        console.error('Failed to fetch storage data:', err);
    }
}

function renderStorageTable(data) {
    document.getElementById('health-temp-dir').textContent = data.base_temp_dir || '-';

    const recentTable = document.getElementById('table-recent-jobs');
    const fullTable = document.getElementById('table-full-storage');

    if (!data.jobs || data.jobs.length === 0) {
        const emptyRow = `<tr><td colspan="5" style="text-align: center; color: var(--text-secondary);">No temporary storage records found. Storage clean!</td></tr>`;
        recentTable.innerHTML = emptyRow;
        fullTable.innerHTML = emptyRow;
        return;
    }

    let rowsHtml = '';
    data.jobs.forEach(job => {
        const ageMins = Math.round(job.age_seconds / 60);
        rowsHtml += `
            <tr>
                <td style="font-family: monospace; font-size: 0.85rem;">${job.job_id}</td>
                <td>${job.size_mb} MB</td>
                <td>${job.file_count}</td>
                <td>${job.created_at}</td>
                <td>${ageMins} min(s) ago</td>
            </tr>
        `;
    });

    recentTable.innerHTML = rowsHtml;
    fullTable.innerHTML = rowsHtml;
}

// User Management Functions
async function fetchUsers() {
    try {
        const response = await fetch('/api/v1/admin/users', {
            headers: getAuthHeader()
        });

        if (response.status === 401) {
            sessionStorage.removeItem('admin_auth');
            showLoginModal('Session expired. Please log in again.');
            return;
        }

        if (!response.ok) return;

        const data = await response.json();
        renderUsersTable(data);
    } catch (err) {
        console.error('Failed to fetch users list:', err);
    }
}

function renderUsersTable(data) {
    document.getElementById('val-total-users').textContent = data.total_users || 0;
    document.getElementById('val-admin-count').textContent = data.admin_count || 0;
    document.getElementById('val-user-count').textContent = data.user_count || 0;

    const tableBody = document.getElementById('table-users');
    if (!data.users || data.users.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-secondary);">No registered users found.</td></tr>`;
        return;
    }

    let html = '';
    data.users.forEach(u => {
        const roleStyle = u.role === 'admin' ? 'style="background-color: rgba(99, 102, 241, 0.15); color: var(--accent-primary);"' : 'style="background-color: rgba(16, 185, 129, 0.15); color: var(--success);"';
        const targetRole = u.role === 'admin' ? 'user' : 'admin';
        const roleBtnLabel = u.role === 'admin' ? 'Demote to User' : 'Promote to Admin';
        const roleBtnIcon = u.role === 'admin' ? 'arrow_downward' : 'arrow_upward';

        html += `
            <tr>
                <td style="font-family: monospace;">#${u.id}</td>
                <td><strong>${u.username}</strong></td>
                <td><span class="status-badge" ${roleStyle}>${u.role.toUpperCase()}</span></td>
                <td>${u.created_at}</td>
                <td>
                    <div style="display: flex; gap: 0.4rem;">
                        <button class="btn btn-outline" style="padding: 0.35rem 0.6rem; font-size: 0.8rem;" onclick="toggleUserRole(${u.id}, '${targetRole}', '${u.username}')">
                            <span class="material-symbols-rounded" style="font-size: 16px;">${roleBtnIcon}</span>
                            ${roleBtnLabel}
                        </button>
                        <button class="btn btn-outline" style="padding: 0.35rem 0.6rem; font-size: 0.8rem;" onclick="openResetPassModal(${u.id}, '${u.username}')">
                            <span class="material-symbols-rounded" style="font-size: 16px;">key</span>
                            Reset Pass
                        </button>
                        <button class="btn btn-danger" style="padding: 0.35rem 0.6rem; font-size: 0.8rem;" onclick="deleteUser(${u.id}, '${u.username}')">
                            <span class="material-symbols-rounded" style="font-size: 16px;">delete</span>
                            Delete
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });

    tableBody.innerHTML = html;
}

function openAddUserModal() {
    document.getElementById('add-user-form').reset();
    document.getElementById('add-user-modal').classList.remove('hidden');
}

function closeAddUserModal() {
    document.getElementById('add-user-modal').classList.add('hidden');
}

async function submitAddUser(event) {
    event.preventDefault();
    const username = document.getElementById('new-user-name').value.trim();
    const password = document.getElementById('new-user-pass').value.trim();
    const role = document.getElementById('new-user-role').value;

    if (!username || !password) return;

    try {
        const response = await fetch('/api/v1/admin/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            },
            body: JSON.stringify({ username, password, role })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Failed to create user');

        showToast(data.message, 'success');
        closeAddUserModal();
        fetchUsers();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function toggleUserRole(userId, newRole, username) {
    if (!confirm(`Are you sure you want to change '${username}' role to '${newRole.toUpperCase()}'?`)) return;

    try {
        const response = await fetch(`/api/v1/admin/users/${userId}/role`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            },
            body: JSON.stringify({ role: newRole })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Failed to update role');

        showToast(data.message, 'success');
        fetchUsers();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function openResetPassModal(userId, username) {
    document.getElementById('reset-target-id').value = userId;
    document.getElementById('reset-target-username').textContent = username;
    document.getElementById('reset-new-pass').value = '';
    document.getElementById('reset-pass-modal').classList.remove('hidden');
}

function closeResetPassModal() {
    document.getElementById('reset-pass-modal').classList.add('hidden');
}

async function submitResetPassword(event) {
    event.preventDefault();
    const userId = document.getElementById('reset-target-id').value;
    const newPassword = document.getElementById('reset-new-pass').value.trim();

    if (!newPassword) return;

    try {
        const response = await fetch(`/api/v1/admin/users/${userId}/password`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            },
            body: JSON.stringify({ new_password: newPassword })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Failed to reset password');

        showToast(data.message, 'success');
        closeResetPassModal();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteUser(userId, username) {
    if (!confirm(`Are you sure you want to permanently delete user account '${username}'? This cannot be undone.`)) return;

    try {
        const response = await fetch(`/api/v1/admin/users/${userId}`, {
            method: 'DELETE',
            headers: getAuthHeader()
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Failed to delete user');

        showToast(data.message, 'success');
        fetchUsers();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function triggerCleanup(maxAge = 3600) {
    if (!confirm(`Are you sure you want to clean temporary storage files older than ${maxAge === 0 ? '0 seconds (PURGE ALL)' : '1 hour'}?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/admin/storage/clean?max_age_seconds=${maxAge}`, {
            method: 'DELETE',
            headers: getAuthHeader()
        });

        if (response.status === 401) {
            sessionStorage.removeItem('admin_auth');
            showLoginModal('Session expired. Please log in again.');
            return;
        }

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Cleanup failed');
        }

        const res = await response.json();
        showToast(`Success: ${res.message}`, 'success');

        fetchMetrics();
        fetchStorage();
    } catch (err) {
        showToast(`Error: ${err.message}`, 'error');
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const iconMap = {
        'success': 'check_circle',
        'error': 'error',
        'info': 'info'
    };
    
    toast.innerHTML = `
        <span class="material-symbols-rounded">${iconMap[type] || 'info'}</span>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

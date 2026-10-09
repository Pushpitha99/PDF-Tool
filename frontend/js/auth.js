// Global Auth State Manager & Responsive Header UI
document.addEventListener('DOMContentLoaded', () => {
    initAuthUI();
    checkUrlAuthPrompt();
});

function getStoredToken() {
    return localStorage.getItem('jwt_token');
}

function getStoredUser() {
    const raw = localStorage.getItem('user_info');
    try {
        return raw ? JSON.parse(raw) : null;
    } catch (e) {
        return null;
    }
}

function checkUrlAuthPrompt() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('auth') === 'required' || urlParams.get('auth') === 'expired') {
        openAuthModal('login', 'Please log in to access your account.');
    }
}

function initAuthUI() {
    const headerActions = document.querySelector('.header-actions');
    if (!headerActions) return;

    // Clear header actions container to build clean profile bar
    headerActions.innerHTML = '';

    const user = getStoredUser();
    const token = getStoredToken();

    if (user && token) {
        // Render logged-in user profile pill with smooth floating dropdown
        const menuContainer = document.createElement('div');
        menuContainer.className = 'user-profile-menu-container';
        menuContainer.id = 'user-profile-menu';

        menuContainer.innerHTML = `
            <button class="user-auth-btn logged-in" id="profile-pill-btn" onclick="toggleProfileDropdown(event)" type="button">
                <div class="user-avatar-circle">
                    <span class="material-symbols-rounded">person</span>
                </div>
                <span class="user-name-text">${user.username}</span>
                <span class="user-role-badge ${user.role}">${user.role}</span>
                <span class="material-symbols-rounded chevron-icon">expand_more</span>
            </button>
            
            <div class="profile-dropdown-menu hidden" id="profile-dropdown-content">
                <div class="dropdown-user-header">
                    <div class="user-name-full">${user.username}</div>
                    <div class="user-role-label">${user.role === 'admin' ? 'System Administrator' : 'Standard Member'}</div>
                </div>
                <div class="dropdown-divider"></div>
                ${user.role === 'admin' ? `
                <a href="/admin" class="dropdown-item admin">
                    <span class="material-symbols-rounded">admin_panel_settings</span>
                    <span>Admin Dashboard</span>
                </a>
                ` : ''}
                <a href="/account" class="dropdown-item">
                    <span class="material-symbols-rounded">account_box</span>
                    <span>My Workspace</span>
                </a>
                <div class="dropdown-divider"></div>
                <button type="button" onclick="logoutAuth()" class="dropdown-item logout-btn">
                    <span class="material-symbols-rounded">logout</span>
                    <span>Sign Out</span>
                </button>
            </div>
        `;

        headerActions.appendChild(menuContainer);
    } else {
        // Render Guest "Sign In" Button
        const loginBtn = document.createElement('button');
        loginBtn.className = 'user-auth-btn guest';
        loginBtn.id = 'auth-btn-guest';
        loginBtn.type = 'button';
        loginBtn.onclick = () => openAuthModal('login');
        loginBtn.innerHTML = `
            <span class="material-symbols-rounded">account_circle</span>
            <span>Sign In</span>
        `;

        headerActions.appendChild(loginBtn);
    }
}

function toggleProfileDropdown(event) {
    if (event) event.stopPropagation();
    const dropdown = document.getElementById('profile-dropdown-content');
    const pillBtn = document.getElementById('profile-pill-btn');
    if (!dropdown) return;

    const isHidden = dropdown.classList.contains('hidden');

    if (isHidden) {
        dropdown.classList.remove('hidden');
        if (pillBtn) pillBtn.classList.add('active');
    } else {
        dropdown.classList.add('hidden');
        if (pillBtn) pillBtn.classList.remove('active');
    }
}

function closeAllDropdowns() {
    const dropdown = document.getElementById('profile-dropdown-content');
    const pillBtn = document.getElementById('profile-pill-btn');
    if (dropdown) dropdown.classList.add('hidden');
    if (pillBtn) pillBtn.classList.remove('active');
}

// Close dropdown when clicking anywhere outside
document.addEventListener('click', (e) => {
    const menuContainer = document.getElementById('user-profile-menu');
    if (menuContainer && !menuContainer.contains(e.target)) {
        closeAllDropdowns();
    }
});

function openAuthModal(tab = 'login', msg = '') {
    const modal = document.getElementById('main-auth-modal');
    if (!modal) return;

    switchAuthTab(tab);
    
    const errBox = document.getElementById('auth-error-msg');
    if (msg && errBox) {
        errBox.textContent = msg;
        errBox.classList.remove('hidden');
    } else if (errBox) {
        errBox.classList.add('hidden');
    }

    modal.classList.remove('hidden');
}

function closeAuthModal() {
    const modal = document.getElementById('main-auth-modal');
    if (modal) modal.classList.add('hidden');
}

function switchAuthTab(tab) {
    const loginTab = document.getElementById('auth-tab-login');
    const regTab = document.getElementById('auth-tab-register');
    const loginForm = document.getElementById('form-auth-login');
    const regForm = document.getElementById('form-auth-register');

    if (tab === 'login') {
        loginTab.classList.add('active');
        regTab.classList.remove('active');
        loginForm.classList.remove('hidden');
        regForm.classList.add('hidden');
    } else {
        regTab.classList.add('active');
        loginTab.classList.remove('active');
        regForm.classList.remove('hidden');
        loginForm.classList.add('hidden');
    }
}

async function handleLoginRequest(event) {
    event.preventDefault();
    const userIn = document.getElementById('login-username').value.trim();
    const passIn = document.getElementById('login-password').value.trim();
    const errBox = document.getElementById('auth-error-msg');

    if (!userIn || !passIn) return;

    try {
        const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: userIn, password: passIn })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Login failed. Invalid username or password.');
        }

        // Store JWT token and user profile
        localStorage.setItem('jwt_token', data.access_token);
        localStorage.setItem('user_info', JSON.stringify(data.user));

        closeAuthModal();

        // ROLE-BASED REDIRECT
        if (data.user.role === 'admin') {
            window.location.href = '/admin';
        } else {
            window.location.href = '/account';
        }

    } catch (err) {
        if (errBox) {
            errBox.textContent = err.message;
            errBox.classList.remove('hidden');
        }
    }
}

async function handleRegisterRequest(event) {
    event.preventDefault();
    const userIn = document.getElementById('reg-username').value.trim();
    const passIn = document.getElementById('reg-password').value.trim();
    const errBox = document.getElementById('auth-error-msg');

    if (!userIn || !passIn) return;

    try {
        const response = await fetch('/api/v1/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: userIn, password: passIn, role: 'user' })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Registration failed.');
        }

        // Auto-login registered user
        const loginRes = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: userIn, password: passIn })
        });

        const loginData = await loginRes.json();
        localStorage.setItem('jwt_token', loginData.access_token);
        localStorage.setItem('user_info', JSON.stringify(loginData.user));

        closeAuthModal();
        window.location.href = '/account';

    } catch (err) {
        if (errBox) {
            errBox.textContent = err.message;
            errBox.classList.remove('hidden');
        }
    }
}

function logoutAuth() {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('user_info');
    window.location.href = '/';
}

function openCreditsModal() {
    const modal = document.getElementById('credits-modal');
    if (modal) modal.classList.remove('hidden');
}

function closeCreditsModal() {
    const modal = document.getElementById('credits-modal');
    if (modal) modal.classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    fetchUserProfile();
});

async function fetchUserProfile() {
    const token = localStorage.getItem('jwt_token');
    if (!token) {
        // Redirect to homepage login modal if unauthenticated
        window.location.href = '/?auth=required';
        return;
    }

    try {
        const response = await fetch('/api/v1/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            localStorage.removeItem('jwt_token');
            localStorage.removeItem('user_info');
            window.location.href = '/?auth=expired';
            return;
        }

        if (!response.ok) throw new Error('Failed to load user profile');

        const user = await response.json();
        updateAccountUI(user);
    } catch (err) {
        console.error('Account profile error:', err);
    }
}

function updateAccountUI(user) {
    document.getElementById('welcome-username').textContent = `Welcome Back, ${user.username}!`;
    document.getElementById('acc-username').textContent = user.username;
    document.getElementById('acc-role').textContent = user.role.toUpperCase();
    document.getElementById('role-badge').textContent = user.role.toUpperCase();

    const adminCard = document.getElementById('admin-shortcut-card');
    if (user.role === 'admin') {
        adminCard.classList.remove('hidden');
    } else {
        adminCard.classList.add('hidden');
    }
}

function logoutUser() {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('user_info');
    window.location.href = '/';
}

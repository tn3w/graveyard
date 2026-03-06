const API_BASE = '';

const ui = {
  showError(message) {
    const alert = document.getElementById('alert');
    alert.className = 'alert alert-error';
    alert.textContent = message;
    alert.classList.remove('hidden');
  },

  showSuccess(message) {
    const alert = document.getElementById('alert');
    alert.className = 'alert alert-success';
    alert.textContent = message;
    alert.classList.remove('hidden');
  },

  showInfo(message) {
    const alert = document.getElementById('alert');
    alert.className = 'alert alert-info';
    alert.textContent = message;
    alert.classList.remove('hidden');
  },

  hideAlert() {
    document.getElementById('alert')?.classList.add('hidden');
  },

  setLoading(button, loading) {
    if (loading) {
      button.disabled = true;
      button.dataset.originalText = button.textContent;
      button.innerHTML = '<span>⏳</span> Processing...';
    } else {
      button.disabled = false;
      button.textContent = button.dataset.originalText;
    }
  }
};

const auth = {
  saveTokens(accessToken, refreshToken) {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  },

  getAccessToken() {
    return localStorage.getItem('access_token');
  },

  getRefreshToken() {
    return localStorage.getItem('refresh_token');
  },

  clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  async refreshAccessToken() {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${API_BASE}/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });

      if (response.ok) {
        const data = await response.json();
        this.saveTokens(data.access_token, data.refresh_token);
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }

    this.clearTokens();
    return false;
  },

  async apiRequest(url, options = {}) {
    const token = this.getAccessToken();
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    let response = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers
    });

    if (response.status === 401 && token) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
        response = await fetch(`${API_BASE}${url}`, {
          ...options,
          headers
        });
      } else {
        window.location.href = '/login.html';
        return null;
      }
    }

    return response;
  }
};

const validation = {
  password(password) {
    if (password.length < 12) {
      return 'Password must be at least 12 characters';
    }
    if (password.length > 128) {
      return 'Password must not exceed 128 characters';
    }
    if (!/[A-Z]/.test(password)) {
      return 'Password must contain uppercase letter';
    }
    if (!/[a-z]/.test(password)) {
      return 'Password must contain lowercase letter';
    }
    if (!/[0-9]/.test(password)) {
      return 'Password must contain digit';
    }
    if (!/[^A-Za-z0-9]/.test(password)) {
      return 'Password must contain special character';
    }
    return null;
  },

  username(username) {
    if (username.length < 3) {
      return 'Username must be at least 3 characters';
    }
    if (username.length > 32) {
      return 'Username must not exceed 32 characters';
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
      return 'Username can only contain alphanumeric, underscore, hyphen';
    }
    return null;
  },

  updatePasswordStrength(password, containerId) {
    const container = document.getElementById(containerId);
    if (!password) {
      container.innerHTML = '';
      return;
    }

    if (typeof zxcvbn === 'undefined') {
      container.innerHTML = '<div class="strength-loading">Loading...</div>';
      return;
    }

    const result = zxcvbn(password);
    const score = result.score;
    
    const colors = ['#ef4444', '#f59e0b', '#f59e0b', '#10b981', '#10b981'];
    const labels = ['Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
    const widths = ['20%', '40%', '60%', '80%', '100%'];

    let html = `
      <div class="strength-row">
        <div class="strength-bar">
          <div class="strength-fill" 
               style="width: ${widths[score]}; background: ${colors[score]};"></div>
        </div>
        <span class="strength-label" style="color: ${colors[score]};">
          ${labels[score]}
        </span>
      </div>
    `;

    if (result.feedback.warning) {
      html += `<span class="strength-warning">${result.feedback.warning}</span>`;
    } else if (result.feedback.suggestions.length > 0) {
      html += `<span class="strength-warning">
        ${result.feedback.suggestions[0]}
      </span>`;
    }

    container.innerHTML = html;
  }
};

if (window.location.pathname !== '/login.html' && 
    window.location.pathname !== '/register.html' &&
    window.location.pathname !== '/') {
  if (!auth.getAccessToken()) {
    window.location.href = '/login.html';
  }
}

// View management
function showView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    const view = document.getElementById('view-' + viewName);
    if (view) view.classList.remove('hidden');
    hideError();
    
    // Init captcha when showing register view
    if (viewName === 'register' && window.iamCaptchaInit) {
        setTimeout(() => window.iamCaptchaInit(), 100);
    }
}

function showError(message) {
    const el = document.getElementById('error');
    if (el) { el.textContent = message; el.classList.remove('hidden'); }
}

function hideError() {
    const el = document.getElementById('error');
    if (el) el.classList.add('hidden');
}

// Token management
async function refreshAccessToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) throw new Error('No refresh token');
    
    const response = await fetch('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
    });
    
    if (!response.ok) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        throw new Error('Token refresh failed');
    }
    
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data.access_token;
}

async function authFetch(url, options = {}) {
    let token = localStorage.getItem('access_token');
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    let response = await fetch(url, { ...options, headers });
    
    if (response.status === 401) {
        try {
            const data = await response.clone().json();
            if (data.token_expired) {
                token = await refreshAccessToken();
                headers['Authorization'] = `Bearer ${token}`;
                response = await fetch(url, { ...options, headers });
            }
        } catch {}
    }
    return response;
}

// WebAuthn helpers
function base64ToArrayBuffer(base64) {
    const b64 = base64.replace(/-/g, '+').replace(/_/g, '/');
    const pad = '='.repeat((4 - b64.length % 4) % 4);
    const bin = atob(b64 + pad);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes.buffer;
}

function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let bin = '';
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

// Navigation helpers
function goToDashboard() { window.location.href = '/dashboard'; }
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
}

async function skipMfa() { goToDashboard(); }

async function dismissMfa() {
    try { await authFetch('/api/mfa/dismiss', { method: 'POST' }); } catch {}
    goToDashboard();
}

// Event handlers
document.addEventListener('DOMContentLoaded', () => {
    // Register form - single page with captcha
    const regForm = document.getElementById('registerForm');
    if (regForm) {
        regForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('reg-username').value.trim();
            
            if (username.length < 3 || username.length > 32) {
                showError('Username must be 3-32 characters');
                return;
            }
            if (!/^[a-zA-Z0-9_]+$/.test(username)) {
                showError('Username can only contain letters, numbers, and underscores');
                return;
            }
            
            // Get captcha token from register captcha widget
            const registerCaptcha = document.getElementById('register-captcha');
            const captchaToken = registerCaptcha?._iamCaptcha?.getResponse() || null;
            
            if (!captchaToken) {
                showError('Please complete the captcha');
                return;
            }
            
            try {
                const res = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, captcha_token: captchaToken })
                });
                const data = await res.json();
                if (res.ok) {
                    document.getElementById('cred-username').textContent = data.username;
                    document.getElementById('cred-password').textContent = data.password;
                    showView('credentials');
                } else {
                    showError(data.error);
                    // Reset captcha on error
                    registerCaptcha?._iamCaptcha?.reset();
                }
            } catch { showError('Network error'); }
        });
    }

    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('login-username').value;
            const password = document.getElementById('login-password').value;
            
            // Get captcha token from login captcha widget
            const loginCaptcha = document.getElementById('login-captcha');
            const captchaToken = loginCaptcha?._iamCaptcha?.getResponse() || null;
            
            if (!captchaToken) {
                showError('Please complete the captcha');
                return;
            }
            
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, captcha_token: captchaToken })
                });
                const data = await res.json();
                if (res.ok) {
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('refresh_token', data.refresh_token);
                    if (data.mfa_required) {
                        showView('mfa-verify');
                    } else if (data.mfa_setup_prompt) {
                        showView('mfa-prompt');
                    } else {
                        goToDashboard();
                    }
                } else {
                    showError(data.error);
                    // Reset captcha on error
                    loginCaptcha?._iamCaptcha?.reset();
                }
            } catch { showError('Network error'); }
        });
    }

    // TOTP setup button
    const btnSetupTotp = document.getElementById('btn-setup-totp');
    if (btnSetupTotp) {
        btnSetupTotp.addEventListener('click', async () => {
            try {
                const res = await authFetch('/api/mfa/totp/setup');
                const data = await res.json();
                if (res.ok) {
                    document.getElementById('totp-setup').classList.remove('hidden');
                    document.getElementById('qr-code').innerHTML = `<img src="data:image/png;base64,${data.qr_code}" alt="QR">`;
                    document.getElementById('totp-secret').textContent = data.secret;
                } else {
                    showError(data.error);
                }
            } catch { showError('Failed to setup TOTP'); }
        });
    }

    // TOTP enable form
    const totpEnableForm = document.getElementById('totpEnableForm');
    if (totpEnableForm) {
        totpEnableForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const code = document.getElementById('totp-code').value;
            try {
                const res = await authFetch('/api/mfa/totp/enable', {
                    method: 'POST',
                    body: JSON.stringify({ code })
                });
                const data = await res.json();
                if (res.ok) {
                    if (data.access_token) localStorage.setItem('access_token', data.access_token);
                    goToDashboard();
                } else {
                    showError(data.error);
                }
            } catch { showError('Verification failed'); }
        });
    }

    // WebAuthn setup button
    const btnSetupWebauthn = document.getElementById('btn-setup-webauthn');
    if (btnSetupWebauthn) {
        btnSetupWebauthn.addEventListener('click', async () => {
            try {
                const startRes = await authFetch('/api/mfa/webauthn/register/start', { method: 'POST' });
                const options = await startRes.json();
                if (!startRes.ok) { showError(options.error); return; }

                options.publicKey.challenge = base64ToArrayBuffer(options.publicKey.challenge);
                options.publicKey.user.id = base64ToArrayBuffer(options.publicKey.user.id);
                if (options.publicKey.excludeCredentials) {
                    options.publicKey.excludeCredentials = options.publicKey.excludeCredentials.map(c => ({
                        ...c, id: base64ToArrayBuffer(c.id)
                    }));
                }

                const cred = await navigator.credentials.create(options);
                const credData = {
                    id: cred.id,
                    rawId: arrayBufferToBase64(cred.rawId),
                    type: cred.type,
                    response: {
                        clientDataJSON: arrayBufferToBase64(cred.response.clientDataJSON),
                        attestationObject: arrayBufferToBase64(cred.response.attestationObject)
                    }
                };

                const finishRes = await authFetch('/api/mfa/webauthn/register/finish', {
                    method: 'POST',
                    body: JSON.stringify(credData)
                });
                const result = await finishRes.json();
                if (finishRes.ok) {
                    if (result.access_token) localStorage.setItem('access_token', result.access_token);
                    goToDashboard();
                } else {
                    showError(result.error);
                }
            } catch (err) { showError('WebAuthn failed: ' + err.message); }
        });
    }

    // TOTP verify form
    const totpVerifyForm = document.getElementById('totpVerifyForm');
    if (totpVerifyForm) {
        totpVerifyForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const code = document.getElementById('verify-totp-code').value;
            try {
                const res = await authFetch('/api/mfa/totp/verify', {
                    method: 'POST',
                    body: JSON.stringify({ code })
                });
                const data = await res.json();
                if (res.ok) {
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('refresh_token', data.refresh_token);
                    goToDashboard();
                } else {
                    showError(data.error);
                }
            } catch { showError('Verification failed'); }
        });
    }

    // WebAuthn verify button
    const btnVerifyWebauthn = document.getElementById('btn-verify-webauthn');
    if (btnVerifyWebauthn) {
        btnVerifyWebauthn.addEventListener('click', async () => {
            try {
                const startRes = await authFetch('/api/mfa/webauthn/auth/start', { method: 'POST' });
                const options = await startRes.json();
                if (!startRes.ok) { showError(options.error); return; }

                options.publicKey.challenge = base64ToArrayBuffer(options.publicKey.challenge);
                if (options.publicKey.allowCredentials) {
                    options.publicKey.allowCredentials = options.publicKey.allowCredentials.map(c => ({
                        ...c, id: base64ToArrayBuffer(c.id)
                    }));
                }

                const assertion = await navigator.credentials.get(options);
                const assertionData = {
                    id: assertion.id,
                    rawId: arrayBufferToBase64(assertion.rawId),
                    type: assertion.type,
                    response: {
                        clientDataJSON: arrayBufferToBase64(assertion.response.clientDataJSON),
                        authenticatorData: arrayBufferToBase64(assertion.response.authenticatorData),
                        signature: arrayBufferToBase64(assertion.response.signature),
                        userHandle: assertion.response.userHandle ? arrayBufferToBase64(assertion.response.userHandle) : null
                    }
                };

                const finishRes = await authFetch('/api/mfa/webauthn/auth/finish', {
                    method: 'POST',
                    body: JSON.stringify(assertionData)
                });
                const result = await finishRes.json();
                if (finishRes.ok) {
                    localStorage.setItem('access_token', result.access_token);
                    localStorage.setItem('refresh_token', result.refresh_token);
                    goToDashboard();
                } else {
                    showError(result.error);
                }
            } catch (err) { showError('WebAuthn failed: ' + err.message); }
        });
    }
});

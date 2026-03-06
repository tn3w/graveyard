(() => {
    let pendingRegData = null;
    const isMobile = () => window.innerWidth <= 768;

    const $ = id => document.getElementById(id);
    const showError = (id, msg) => { const el = $(id); el.textContent = msg; el.classList.remove('hidden'); };
    const hideError = id => $(id).classList.add('hidden');

    const initCaptcha = () => window.iamCaptchaInit?.();

    $('auth-toggle').addEventListener('click', e => {
        e.stopPropagation();
        isMobile() ? openAuthModal() : toggleDropdown();
    });

    const toggleDropdown = () => {
        const dropdown = $('auth-dropdown');
        dropdown.classList.toggle('hidden');
        if (!dropdown.classList.contains('hidden')) setTimeout(initCaptcha, 100);
    };

    const openAuthModal = () => {
        $('auth-modal-overlay').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        setTimeout(initCaptcha, 100);
    };

    const closeAuthModal = () => {
        $('auth-modal-overlay').classList.add('hidden');
        document.body.style.overflow = '';
    };

    document.addEventListener('click', e => {
        if (!document.querySelector('.auth-dropdown-wrapper').contains(e.target)) {
            $('auth-dropdown').classList.add('hidden');
        }
    });

    $('auth-modal-overlay').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeAuthModal();
    });

    const showView = (prefix, view, errorId) => {
        document.querySelectorAll(`.${prefix}-view`).forEach(v => v.classList.add('hidden'));
        $(`${prefix}-${view}`).classList.remove('hidden');
        hideError(errorId);
        setTimeout(initCaptcha, 100);
    };

    window.showDropdownView = view => showView('dropdown', view, 'dropdown-error');
    window.showModalView = view => showView('modal', view, 'modal-error');
    window.closeAuthModal = closeAuthModal;
    window.openAuthModal = openAuthModal;

    const validatePassword = password => {
        if (password.length < 12) return { valid: false, error: 'Password must be at least 12 characters' };
        if (!/[^a-zA-Z0-9]/.test(password)) {
            return { valid: false, error: 'Password must contain at least one special character' };
        }
        if (typeof zxcvbn !== 'undefined') {
            const result = zxcvbn(password);
            if (result.score < 2) {
                return {
                    valid: false,
                    error: 'Password is too weak. ' + (result.feedback.warning || 'Try a longer or more complex password.')
                };
            }
        }
        return { valid: true };
    };

    const updatePasswordStrength = (password, elementId) => {
        const el = $(elementId);
        if (!el) return;
        if (!password) { el.innerHTML = ''; return; }
        if (typeof zxcvbn === 'undefined') return;

        const result = zxcvbn(password);
        const labels = ['Very Weak', 'Weak', 'Fair', 'Strong', 'Very Strong'];
        const colors = ['#ff4444', '#ff8800', '#ffcc00', '#88cc00', '#00cc44'];
        const { score, feedback } = result;

        el.innerHTML = `
            <div class="strength-row">
                <div class="strength-bar">
                    <div class="strength-fill" style="width: ${(score + 1) * 20}%; background: ${colors[score]}"></div>
                </div>
                <span class="strength-label" style="color: ${colors[score]}">${labels[score]}</span>
            </div>
            ${feedback.warning ? `<span class="strength-warning">${feedback.warning}</span>` : ''}`;
    };

    const refreshStrength = () => {
        const dropdownPw = $('dropdown-reg-password');
        const modalPw = $('modal-reg-password');
        if (dropdownPw?.value) updatePasswordStrength(dropdownPw.value, 'dropdown-password-strength');
        if (modalPw?.value) updatePasswordStrength(modalPw.value, 'modal-password-strength');
    };

    $('dropdown-reg-password')?.addEventListener('input', e =>
        updatePasswordStrength(e.target.value, 'dropdown-password-strength'));
    $('modal-reg-password')?.addEventListener('input', e =>
        updatePasswordStrength(e.target.value, 'modal-password-strength'));

    const waitForZxcvbn = setInterval(() => {
        if (typeof zxcvbn !== 'undefined') { clearInterval(waitForZxcvbn); refreshStrength(); }
    }, 100);

    const getCaptchaToken = el => el?._iamCaptcha?.getResponse() || null;
    const resetCaptcha = el => el?._iamCaptcha?.reset();

    const handleLogin = async (username, password, captchaEl, errorFn) => {
        const captchaToken = getCaptchaToken(captchaEl);
        if (!captchaToken) { errorFn('Please complete the captcha'); return; }

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
                window.location.href = '/dashboard';
            } else {
                errorFn(data.error || 'Login failed');
                resetCaptcha(captchaEl);
            }
        } catch { errorFn('Network error'); }
    };

    const handleRegisterStep1 = (username, password, confirmPassword, errorFn, showCaptchaView) => {
        if (username.length < 3 || username.length > 32) {
            errorFn('Username must be 3-32 characters'); return;
        }
        if (!/^[a-zA-Z0-9_]+$/.test(username)) {
            errorFn('Username: letters, numbers, underscores only'); return;
        }
        const pwValidation = validatePassword(password);
        if (!pwValidation.valid) { errorFn(pwValidation.error); return; }
        if (password !== confirmPassword) { errorFn('Passwords do not match'); return; }

        pendingRegData = { username, password };
        showCaptchaView();
    };

    const handleRegisterComplete = async (captchaEl, errorFn) => {
        if (!pendingRegData) { errorFn('Please fill in the registration form first'); return; }
        const captchaToken = getCaptchaToken(captchaEl);
        if (!captchaToken) return;

        try {
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: pendingRegData.username,
                    password: pendingRegData.password,
                    captcha_token: captchaToken
                })
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                pendingRegData = null;
                window.location.href = '/dashboard';
            } else {
                errorFn(data.error || 'Registration failed');
                resetCaptcha(captchaEl);
            }
        } catch { errorFn('Network error'); }
    };

    const showDropdownError = msg => showError('dropdown-error', msg);
    const showModalError = msg => showError('modal-error', msg);

    $('dropdownLoginForm').addEventListener('submit', async e => {
        e.preventDefault();
        await handleLogin(
            $('dropdown-login-username').value,
            $('dropdown-login-password').value,
            $('dropdown-login-captcha'),
            showDropdownError
        );
    });

    $('dropdownRegisterForm').addEventListener('submit', e => {
        e.preventDefault();
        handleRegisterStep1(
            $('dropdown-reg-username').value.trim(),
            $('dropdown-reg-password').value,
            $('dropdown-reg-password-confirm').value,
            showDropdownError,
            () => showDropdownView('register-captcha')
        );
    });

    $('modalLoginForm').addEventListener('submit', async e => {
        e.preventDefault();
        await handleLogin(
            $('modal-login-username').value,
            $('modal-login-password').value,
            $('modal-login-captcha'),
            showModalError
        );
    });

    $('modalRegisterForm').addEventListener('submit', e => {
        e.preventDefault();
        handleRegisterStep1(
            $('modal-reg-username').value.trim(),
            $('modal-reg-password').value,
            $('modal-reg-password-confirm').value,
            showModalError,
            () => showModalView('register-captcha')
        );
    });

    setInterval(() => {
        if (!pendingRegData) return;
        const dropdownCaptcha = $('dropdown-reg-captcha');
        const modalCaptcha = $('modal-reg-captcha');
        if (getCaptchaToken(dropdownCaptcha)) handleRegisterComplete(dropdownCaptcha, showDropdownError);
        if (getCaptchaToken(modalCaptcha)) handleRegisterComplete(modalCaptcha, showModalError);
    }, 500);
})();

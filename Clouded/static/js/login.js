let sessionToken = null;
let captchaWidgetId = null;

async function handleLogin(event) {
  event.preventDefault();
  ui.hideAlert();

  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const submitBtn = document.getElementById('submitBtn');

  ui.setLoading(submitBtn, true);

  try {
    document.getElementById('step1').classList.add('hidden');
    document.getElementById('step2').classList.remove('hidden');
    document.getElementById('page-header').classList.add('hidden');
    
    setTimeout(() => {
      if (typeof iamcaptcha !== 'undefined') {
        const captchaEl = document.getElementById('login-captcha');
        if (captchaEl && !captchaWidgetId) {
          captchaWidgetId = iamcaptcha.render(captchaEl, {
            sitekey: 'HtFBvvSKHpWEIh1JmOHnwQ4l5hTsGcvu',
            theme: 'dark',
            mode: 'inline',
            callback: async function(token) {
              await completeCaptchaLogin(username, password, token);
            }
          });
        }
      }
    }, 100);
  } catch (error) {
    ui.showError('Network error. Please try again.');
  } finally {
    ui.setLoading(submitBtn, false);
  }
}

async function completeCaptchaLogin(username, password, captchaToken) {
  try {
    const response = await fetch(`${API_BASE}/login/step1`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, captcha_token: captchaToken })
    });

    const data = await response.json();

    if (!response.ok) {
      ui.showError(data.error || 'Login failed');
      resetToStep1();
      return;
    }

    sessionToken = data.session_token;
    document.getElementById('step2').classList.add('hidden');
    document.getElementById('step3').classList.remove('hidden');
    document.getElementById('page-header').classList.remove('hidden');
  } catch (error) {
    ui.showError('Network error. Please try again.');
    resetToStep1();
  }
}

function resetToStep1() {
  document.getElementById('step2').classList.add('hidden');
  document.getElementById('step1').classList.remove('hidden');
  document.getElementById('page-header').classList.remove('hidden');
  if (captchaWidgetId !== null && typeof iamcaptcha !== 'undefined') {
    iamcaptcha.reset(captchaWidgetId);
    captchaWidgetId = null;
  }
}

async function handleTotpVerification(event) {
  event.preventDefault();
  ui.hideAlert();

  const totpCode = document.getElementById('totpCode').value;
  const verifyBtn = document.getElementById('verifyBtn');

  if (totpCode.length !== 6) {
    ui.showError('TOTP code must be 6 digits');
    return;
  }

  ui.setLoading(verifyBtn, true);

  try {
    const response = await fetch(`${API_BASE}/login/step2/totp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_token: sessionToken,
        totp_code: totpCode
      })
    });

    const data = await response.json();

    if (!response.ok) {
      ui.showError(data.error || 'Verification failed');
      ui.setLoading(verifyBtn, false);
      return;
    }

    auth.saveTokens(data.access_token, data.refresh_token);
    ui.showSuccess('Login successful! Redirecting...');
    setTimeout(() => {
      window.location.href = '/dashboard.html';
    }, 1000);
  } catch (error) {
    ui.showError('Network error. Please try again.');
    ui.setLoading(verifyBtn, false);
  }
}

async function handleWebAuthn() {
  ui.hideAlert();
  const webauthnBtn = document.getElementById('webauthnBtn');
  ui.setLoading(webauthnBtn, true);

  try {
    const startResponse = await fetch(`${API_BASE}/login/step2/webauthn/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_token: sessionToken })
    });

    const startData = await startResponse.json();

    if (!startResponse.ok) {
      ui.showError(startData.error || 'WebAuthn start failed');
      ui.setLoading(webauthnBtn, false);
      return;
    }

    ui.showInfo('Please use your security key...');

    const credential = await navigator.credentials.get({
      publicKey: startData.options
    });

    const finishResponse = await fetch(
      `${API_BASE}/login/step2/webauthn/finish`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_token: sessionToken,
          credential: credential
        })
      }
    );

    const finishData = await finishResponse.json();

    if (!finishResponse.ok) {
      ui.showError(finishData.error || 'WebAuthn verification failed');
      ui.setLoading(webauthnBtn, false);
      return;
    }

    auth.saveTokens(finishData.access_token, finishData.refresh_token);
    ui.showSuccess('Login successful! Redirecting...');
    setTimeout(() => {
      window.location.href = '/dashboard.html';
    }, 1000);
  } catch (error) {
    ui.showError('WebAuthn failed: ' + error.message);
    ui.setLoading(webauthnBtn, false);
  }
}

document.getElementById('loginForm').addEventListener('submit', handleLogin);
document.getElementById('totpForm').addEventListener('submit', handleTotpVerification);
document.getElementById('webauthnBtn').addEventListener('click', handleWebAuthn);

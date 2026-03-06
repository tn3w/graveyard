const urlParams = new URLSearchParams(window.location.search);
const registrationToken = urlParams.get('token');

if (!registrationToken) {
  ui.showError('Invalid registration link');
  document.getElementById('registerForm').style.display = 'none';
}

let totpSecret = null;
let webauthnOptions = null;
let captchaWidgetId = null;

async function completeCaptchaRegistration(username, password, captchaToken) {
  try {
    const response = await fetch(`${API_BASE}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: registrationToken,
        username,
        password,
        captcha_token: captchaToken
      })
    });

    const data = await response.json();

    if (!response.ok) {
      ui.showError(data.error || 'Registration failed');
      resetToStep1();
      return;
    }

    totpSecret = data.totp_secret;
    webauthnOptions = data.webauthn_options;

    document.getElementById('totpUri').textContent = data.totp_uri;
    document.getElementById('totpSecret').textContent = totpSecret;

    setTimeout(() => generateQRCode(data.totp_uri), 100);

    document.getElementById('step2').classList.add('hidden');
    document.getElementById('step3').classList.remove('hidden');
  } catch (error) {
    ui.showError('Network error. Please try again.');
    resetToStep1();
  }
}

function resetToStep1() {
  document.getElementById('step2').classList.add('hidden');
  document.getElementById('step3').classList.add('hidden');
  document.getElementById('step4').classList.add('hidden');
  document.getElementById('step1').classList.remove('hidden');
  document.getElementById('page-header').classList.remove('hidden');
  if (captchaWidgetId !== null && typeof iamcaptcha !== 'undefined') {
    iamcaptcha.reset(captchaWidgetId);
    captchaWidgetId = null;
  }
}

document.getElementById('password').addEventListener('input', (e) => {
  validation.updatePasswordStrength(e.target.value, 'password-strength');
});

async function handleRegister(event) {
  event.preventDefault();
  ui.hideAlert();

  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirmPassword').value;

  const usernameError = validation.username(username);
  if (usernameError) {
    ui.showError(usernameError);
    return;
  }

  const passwordError = validation.password(password);
  if (passwordError) {
    ui.showError(passwordError);
    return;
  }

  if (password !== confirmPassword) {
    ui.showError('Passwords do not match');
    return;
  }

  document.getElementById('step1').classList.add('hidden');
  document.getElementById('step2').classList.remove('hidden');
  document.getElementById('page-header').classList.add('hidden');

  setTimeout(() => {
    if (typeof iamcaptcha !== 'undefined') {
      const captchaEl = document.getElementById('reg-captcha');
      if (captchaEl && !captchaWidgetId) {
        captchaWidgetId = iamcaptcha.render(captchaEl, {
          sitekey: 'HtFBvvSKHpWEIh1JmOHnwQ4l5hTsGcvu',
          theme: 'dark',
          mode: 'inline',
          callback: async function(token) {
            await completeCaptchaRegistration(username, password, token);
          }
        });
      }
    }
  }, 100);
}

function generateQRCode(uri) {
  const qrContainer = document.getElementById('qrCode');
  qrContainer.innerHTML = '';
  
  if (typeof QRCode !== 'undefined') {
    new QRCode(qrContainer, {
      text: uri,
      width: 200,
      height: 200,
      colorDark: '#ffffff',
      colorLight: 'rgba(0,0,0,0)',
      correctLevel: QRCode.CorrectLevel.M
    });
  } else {
    qrContainer.innerHTML = '<p style="color: var(--text-secondary);">Loading QR code...</p>';
  }
}

async function handleTotpSetup(event) {
  event.preventDefault();
  ui.hideAlert();

  const totpCode = document.getElementById('totpCode').value;
  const verifyBtn = document.getElementById('verifyBtn');

  if (totpCode.length !== 6) {
    ui.showError('TOTP code must be 6 digits');
    return;
  }

  ui.setLoading(verifyBtn, true);

  const isValid = await verifyTotpCode(totpCode);

  if (!isValid) {
    ui.showError('Invalid TOTP code. Please try again.');
    ui.setLoading(verifyBtn, false);
    return;
  }

  document.getElementById('step3').classList.add('hidden');
  document.getElementById('step4').classList.remove('hidden');
  ui.setLoading(verifyBtn, false);
}

async function verifyTotpCode(code) {
  try {
    const response = await fetch(`${API_BASE}/verify-totp-code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        totp_secret: totpSecret,
        totp_code: code
      })
    });
    
    if (!response.ok) {
      return false;
    }
    
    const data = await response.json();
    return data.valid;
  } catch (error) {
    return false;
  }
}

async function handleWebAuthnSetup() {
  ui.hideAlert();
  const webauthnBtn = document.getElementById('webauthnBtn');
  ui.setLoading(webauthnBtn, true);

  try {
    ui.showInfo('Please use your security key...');

    const credential = await navigator.credentials.create({
      publicKey: webauthnOptions
    });

    ui.showSuccess('Registration complete! Redirecting to login...');
    setTimeout(() => {
      window.location.href = '/login.html';
    }, 2000);
  } catch (error) {
    ui.showError('WebAuthn registration failed: ' + error.message);
    ui.setLoading(webauthnBtn, false);
  }
}

function skipWebAuthn() {
  ui.showSuccess('Registration complete! Redirecting to login...');
  setTimeout(() => {
    window.location.href = '/login.html';
  }, 1500);
}

document.getElementById('registerForm').addEventListener('submit', handleRegister);
document.getElementById('totpForm').addEventListener('submit', handleTotpSetup);
document.getElementById('webauthnBtn').addEventListener('click', handleWebAuthnSetup);
document.getElementById('skipBtn').addEventListener('click', skipWebAuthn);

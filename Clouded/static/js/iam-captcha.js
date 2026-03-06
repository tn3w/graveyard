((global, factory) => {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else if (typeof define === 'function' && define.amd) define(factory);
    else {
        const exports = factory();
        global.IAmCaptcha = exports.IAmCaptcha;
        global.iamcaptcha = exports.iamcaptcha;
        global.__iamcaptcha_onload?.();
    }
})(typeof window !== 'undefined' ? window : this, () => {
    const ORIGIN = typeof window !== 'undefined' ? window.location.origin : '';
    const SCENE_W = 150, REF_W = 100;

    const ErrorCodes = Object.freeze({
        RATE_LIMITED: 'rate-limited',
        NETWORK_ERROR: 'network-error',
        INVALID_DATA: 'invalid-data',
        CHALLENGE_ERROR: 'challenge-error',
        CHALLENGE_CLOSED: 'challenge-closed',
        CHALLENGE_EXPIRED: 'challenge-expired',
        MISSING_CAPTCHA: 'missing-captcha',
        INVALID_CAPTCHA_ID: 'invalid-captcha-id',
        INTERNAL_ERROR: 'internal-error',
        INVALID_SITEKEY: 'invalid-sitekey',
        VERIFICATION_FAILED: 'verification-failed'
    });

    class EventEmitter {
        _events = new Map();

        on(event, listener) {
            if (!this._events.has(event)) this._events.set(event, new Set());
            this._events.get(event).add(listener);
            return this;
        }

        off(event, listener) {
            this._events.get(event)?.delete(listener);
            return this;
        }

        once(event, listener) {
            const wrapper = (...args) => {
                this.off(event, wrapper);
                listener.apply(this, args);
            };
            return this.on(event, wrapper);
        }

        emit(event, ...args) {
            this._events.get(event)?.forEach(listener => {
                try { listener.apply(this, args); }
                catch (error) { console.error(`IAm Captcha: Error in ${event} listener:`, error); }
            });
            return this;
        }

        removeAllListeners(event) {
            event ? this._events.delete(event) : this._events.clear();
            return this;
        }
    }

    const DEFAULT_CONFIG = Object.freeze({
        sitekey: null, theme: 'dark', size: 'normal', tabindex: 0,
        callback: null, 'error-callback': null, 'expired-callback': null,
        'chalexpired-callback': null, 'open-callback': null, 'close-callback': null,
        'challenge-container': null, hl: 'auto', endpoint: ORIGIN,
        'passive-mode': false, 'passive-callback': null, 'passive-threshold': 0.4,
        'mode': 'checkbox', 'float': 'auto', 'challenge-size': 'auto',
        'bond': null, 'bond-event': 'click', 'auto-submit': false
    });

    class CaptchaWidget extends EventEmitter {
        static _idCounter = 0;

        constructor(container, config = {}) {
            super();
            this.id = CaptchaWidget._idCounter++;
            this.container = typeof container === 'string'
                ? document.getElementById(container) : container;
            if (!this.container) throw new Error('IAm Captcha: Container not found');

            this.config = { ...DEFAULT_CONFIG, ...config };
            this.siteKey = this.config.sitekey;
            if (!this.siteKey) throw new Error('IAm Captcha: sitekey is required');

            this.token = null;
            this.responseKey = null;
            this.verified = null;
            this.img = null;
            this.round = 0;
            this.totalRounds = 1;
            this.sceneCounts = [];
            this.answers = [];
            this.scene = 0;
            this.isOpen = false;
            this.isLoading = false;
            this.expiryTimeout = null;
            this.challengeExpiryTimeout = null;
            this.bondElement = null;
            this.bondedMode = false;

            this._handleKeydown = this._handleKeydown.bind(this);
            this._handleBondClick = this._handleBondClick.bind(this);
            this._handleClickOutside = this._handleClickOutside.bind(this);
            this._handleViewportChange = this._handleViewportChange.bind(this);

            this.container._iamCaptcha = this;
            this.container.dataset.iamWidgetId = this.id;

            this._loadStyles().then(() => {
                this._render();
                this._setupBond();
            });
        }

        _loadStyles() {
            return new Promise(resolve => {
                if (document.getElementById('iam-captcha-css')) return resolve();
                const link = document.createElement('link');
                link.id = 'iam-captcha-css';
                link.rel = 'stylesheet';
                link.href = `${this.config.endpoint}/iam-captcha.css`;
                link.onload = link.onerror = resolve;
                document.head.appendChild(link);
            });
        }

        _getCanvasDimensions(size) {
            const dims = {
                small: { refW: 60, refH: 90, sceneW: 90, sceneH: 90 },
                large: { refW: 120, refH: 180, sceneW: 180, sceneH: 180 },
                normal: { refW: 100, refH: 150, sceneW: 150, sceneH: 150 }
            };
            return dims[size] || dims.normal;
        }

        _render() {
            const theme = this.config.theme === 'light' ? 'iam-theme-light' : '';
            const size = this.config.size === 'compact' ? 'iam-size-compact' : '';
            const challengeSize = this.config['challenge-size'] || 'auto';
            const sizeClass = challengeSize !== 'auto' ? `iam-challenge-${challengeSize}` : '';
            const dims = this._getCanvasDimensions(challengeSize);

            if (this.config.mode === 'inline') {
                this._renderInline(theme, size, sizeClass, dims);
            } else {
                this._renderCheckbox(theme, size, sizeClass, dims);
            }
            this.emit('render', { widgetId: this.id });
        }

        _renderInline(theme, size, sizeClass, dims) {
            this.container.innerHTML = `
                <div class="iam-widget iam-mode-inline ${theme} ${size}"
                     tabindex="${this.config.tabindex}">
                    <div class="iam-challenge iam-challenge-inline ${sizeClass} open">
                        ${this._challengeContent(dims, false)}
                        <div class="iam-success-overlay">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
                                 stroke="currentColor" stroke-width="2">
                                <path d="M20 6L9 17l-5-5"/>
                            </svg>
                            <span>Verified</span>
                        </div>
                    </div>
                </div>`;
            this._bindInlineEvents();
            this._loadInlineChallenge();
        }

        _renderCheckbox(theme, size, sizeClass, dims) {
            this.container.innerHTML = `
                <div class="iam-widget ${theme} ${size}" tabindex="${this.config.tabindex}">
                    <div class="iam-checkbox-container">
                        <div class="iam-checkbox-left">
                            <div class="iam-checkbox">
                                <div class="iam-spinner"></div>
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                                     stroke="currentColor" stroke-width="3">
                                    <path d="M20 6L9 17l-5-5"/>
                                </svg>
                            </div>
                            <span class="iam-label">I am not a robot</span>
                        </div>
                        <div class="iam-branding">
                            <div class="iam-logo">IAm</div>
                            <div class="iam-links">
                                <a href="#" tabindex="-1">Terms</a> ·
                                <a href="#" tabindex="-1">Privacy</a>
                            </div>
                        </div>
                    </div>
                    <div class="iam-challenge ${sizeClass}" data-float="${this.config.float}">
                        ${this._challengeContent(dims, true)}
                    </div>
                </div>`;
            this._bindEvents();
        }

        _challengeContent(dims, showClose) {
            return `
                <div class="iam-header">
                    <span class="iam-round"></span>
                    ${showClose ? `
                        <button type="button" class="iam-close" aria-label="Close challenge">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                                 stroke="currentColor" stroke-width="2">
                                <path d="M18 6L6 18M6 6l12 12"/>
                            </svg>
                        </button>` : `
                        <div class="iam-branding-inline"><span class="iam-logo">IAm</span></div>`}
                </div>
                <div class="iam-prompt"></div>
                <div class="iam-content">
                    <div class="iam-reference">
                        <canvas class="iam-reference-canvas" width="${dims.refW}" height="${dims.refH}"></canvas>
                        <div class="iam-ref-label">Target Icon</div>
                    </div>
                    <div class="iam-scene-container">
                        <canvas class="iam-scene-canvas"
                                width="${dims.sceneW}" height="${dims.sceneH}"></canvas>
                        <div class="iam-controls">
                            <button type="button" class="iam-arrow iam-left"
                                    aria-label="Previous scene">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                                     stroke="currentColor" stroke-width="2">
                                    <path d="M15 18l-6-6 6-6"/>
                                </svg>
                            </button>
                            <div class="iam-dots"></div>
                            <button type="button" class="iam-arrow iam-right"
                                    aria-label="Next scene">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                                     stroke="currentColor" stroke-width="2">
                                    <path d="M9 18l6-6-6-6"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
                <button type="button" class="iam-submit">Continue</button>
                <div class="iam-token"></div>`;
        }

        _bindInlineEvents() {
            this.container.querySelector('.iam-left').addEventListener('click',
                () => this._navigate(-1));
            this.container.querySelector('.iam-right').addEventListener('click',
                () => this._navigate(1));
            this.container.querySelector('.iam-submit').addEventListener('click',
                () => this._nextRound());
            document.addEventListener('keydown', this._handleKeydown);
        }

        async _loadInlineChallenge() {
            const submit = this.container.querySelector('.iam-submit');
            submit.disabled = true;
            submit.textContent = 'Loading...';

            try {
                const data = await this._fetchChallenge();
                this._setChallenge(data);
                submit.disabled = false;
                submit.textContent = this.round < this.totalRounds - 1 ? 'Continue' : 'Verify';
            } catch (error) {
                this._handleError(error.message || ErrorCodes.CHALLENGE_ERROR);
            }
        }

        _setupBond() {
            const bondSelector = this.config.bond;
            if (!bondSelector) return;

            this.bondElement = typeof bondSelector === 'string'
                ? document.querySelector(bondSelector) : bondSelector;
            if (!this.bondElement) {
                console.warn('IAm Captcha: Bond element not found:', bondSelector);
                return;
            }

            this.bondedMode = true;
            this.container.style.display = 'none';
            this.container.classList.add('iam-bonded');

            this.bondElement.addEventListener(this.config['bond-event'] || 'click',
                this._handleBondClick);
            document.addEventListener('click', this._handleClickOutside);
            window.addEventListener('resize', this._handleViewportChange);
            window.addEventListener('scroll', this._handleViewportChange, true);
        }

        async _handleBondClick(event) {
            event.preventDefault();
            event.stopPropagation();

            if (this.verified) {
                this._invokeCallback('callback', this.verified);
                this.emit('success', {
                    widgetId: this.id, response: this.verified,
                    key: this.responseKey, bonded: true
                });
                return;
            }

            this.bondElement.classList.add('iam-bond-loading');

            if (this.config['passive-mode']) {
                const result = await this._tryPassiveVerification();
                if (result.success && result.token) {
                    this._handlePassiveSuccess(result.token, true);
                    return;
                }
            }

            this.bondElement.classList.remove('iam-bond-loading');
            this._showBondedChallenge();
        }

        _handlePassiveSuccess(token, bonded = false) {
            this.verified = token;
            this.responseKey = this._generateResponseKey();

            if (bonded) {
                this.bondElement.classList.remove('iam-bond-loading');
                this.bondElement.classList.add('iam-bond-verified');
                this.container.style.display = 'none';
            } else {
                const checkbox = this.container.querySelector('.iam-checkbox');
                checkbox?.classList.remove('loading');
                checkbox?.classList.add('checked');
            }

            this._createHiddenInput(token);
            this._setTokenExpiry();
            this._invokeCallback('callback', token);
            this.emit('success', {
                widgetId: this.id, response: token,
                key: this.responseKey, passive: true, bonded
            });
            this._autoSubmitForm();
        }

        _showBondedChallenge() {
            this.container.style.display = 'block';
            this.container.style.position = 'fixed';
            this.container.style.zIndex = '10000';
            this._positionBondedChallenge();
            this.execute();
        }

        _positionBondedChallenge() {
            if (!this.bondElement) return;

            const rect = this.bondElement.getBoundingClientRect();
            const width = 380, height = 400;
            const position = this._calculatePosition(rect, width, height);
            const coords = this._getPositionCoords(rect, width, height, position);

            this.container.style.top = `${coords.top}px`;
            this.container.style.left = `${coords.left}px`;

            const challenge = this.container.querySelector('.iam-challenge');
            if (challenge) challenge.dataset.float = position;
        }

        _calculatePosition(rect, width, height) {
            const pref = this.config.float || 'auto';
            if (pref !== 'auto') return pref;

            const spaces = {
                top: rect.top, bottom: window.innerHeight - rect.bottom,
                left: rect.left, right: window.innerWidth - rect.right
            };

            if (spaces.top >= height + 20) return 'top';
            if (spaces.bottom >= height + 20) return 'bottom';
            if (spaces.right >= width + 20) return 'right';
            if (spaces.left >= width + 20) return 'left';
            return spaces.top > spaces.bottom ? 'top' : 'bottom';
        }

        _getPositionCoords(rect, width, height, position) {
            let top, left;
            switch (position) {
                case 'top':
                    top = rect.top - height - 10;
                    left = rect.left + rect.width / 2 - width / 2;
                    break;
                case 'bottom':
                    top = rect.bottom + 10;
                    left = rect.left + rect.width / 2 - width / 2;
                    break;
                case 'left':
                    top = rect.top + rect.height / 2 - height / 2;
                    left = rect.left - width - 10;
                    break;
                case 'right':
                    top = rect.top + rect.height / 2 - height / 2;
                    left = rect.right + 10;
                    break;
            }
            return {
                top: Math.max(10, Math.min(top, window.innerHeight - height - 10)),
                left: Math.max(10, Math.min(left, window.innerWidth - width - 10))
            };
        }

        _handleClickOutside(event) {
            if (!this.bondedMode || !this.isOpen) return;
            if (!this.container.contains(event.target) &&
                !this.bondElement.contains(event.target)) {
                this._closeBondedChallenge();
            }
        }

        _handleViewportChange() {
            if (!this.isOpen) return;
            if (this.bondedMode) this._positionBondedChallenge();
            else if (this.config.float === 'auto') this._autoPositionChallenge();
        }

        _closeBondedChallenge() {
            if (!this.bondedMode) return;
            this._closeChallenge(true);
            this.container.style.display = 'none';
        }

        _bindEvents() {
            const container = this.container.querySelector('.iam-checkbox-container');
            container.addEventListener('click', event => {
                if (event.target.closest('a') || this.verified || this.isLoading) return;
                this.execute();
            });

            this.container.querySelector('.iam-close').addEventListener('click',
                () => this._closeChallenge(true));
            this.container.querySelector('.iam-left').addEventListener('click',
                () => this._navigate(-1));
            this.container.querySelector('.iam-right').addEventListener('click',
                () => this._navigate(1));
            this.container.querySelector('.iam-submit').addEventListener('click',
                () => this._nextRound());

            document.addEventListener('keydown', this._handleKeydown);

            if (this.config.float === 'auto') {
                window.addEventListener('resize', this._handleViewportChange);
                window.addEventListener('scroll', this._handleViewportChange, true);
            }
        }

        _handleKeydown(event) {
            if (!this.isOpen) return;
            const actions = {
                ArrowLeft: () => this._navigate(-1),
                ArrowRight: () => this._navigate(1),
                Enter: () => this._nextRound(),
                Escape: () => this._closeChallenge(true)
            };
            if (actions[event.key]) {
                event.preventDefault();
                actions[event.key]();
            }
        }

        async _tryPassiveVerification() {
            if (!this.config['passive-mode']) return { success: false, reason: 'passive-disabled' };
            if (typeof window.IAmPassive === 'undefined') {
                console.warn('IAm Captcha: IAmPassive not loaded');
                return { success: false, reason: 'passive-not-loaded' };
            }

            try {
                const result = await window.IAmPassive.verify(this.siteKey, this.config.endpoint);
                this._invokeCallback('passive-callback', result);
                this.emit('passive-result', { widgetId: this.id, ...result });

                if (result.success && result.verified_token) {
                    return { success: true, token: result.verified_token };
                }
                return { success: false, reason: 'challenge-required' };
            } catch (error) {
                console.warn('IAm Captcha: Passive verification failed:', error);
                return { success: false, reason: 'passive-error', error: error.message };
            }
        }

        async _openChallenge() {
            const checkbox = this.container.querySelector('.iam-checkbox');
            checkbox?.classList.add('loading');
            this.isLoading = true;

            try {
                const passiveResult = await this._tryPassiveVerification();
                if (passiveResult.success && passiveResult.token) {
                    this.isLoading = false;
                    this._handlePassiveSuccess(passiveResult.token, this.bondedMode);
                    return { response: passiveResult.token, key: this.responseKey };
                }

                const data = await this._fetchChallenge();
                this._setChallenge(data);

                const challenge = this.container.querySelector('.iam-challenge');
                challenge.classList.add('open');
                this.isOpen = true;
                this._autoPositionChallenge();

                this._invokeCallback('open-callback');
                this.emit('open', { widgetId: this.id });
            } catch (error) {
                this._handleError(error.message || ErrorCodes.CHALLENGE_ERROR);
                throw error;
            } finally {
                checkbox?.classList.remove('loading');
                this.isLoading = false;
            }
        }

        async _fetchChallenge() {
            const response = await fetch(`${this.config.endpoint}/captcha/challenge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ site_key: this.siteKey })
            });
            if (!response.ok) throw new Error(ErrorCodes.NETWORK_ERROR);
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            return data;
        }

        _autoPositionChallenge() {
            const challenge = this.container.querySelector('.iam-challenge');
            if (!challenge) return;

            if (this.bondedMode) {
                this._positionBondedChallenge();
                return;
            }

            const rect = this.container.getBoundingClientRect();
            const position = this._calculatePosition(rect, 380, 400);

            challenge.classList.remove('iam-float-top', 'iam-float-bottom',
                'iam-float-left', 'iam-float-right');
            challenge.classList.add(`iam-float-${position}`);
            challenge.dataset.float = position;
        }

        _closeChallenge(userInitiated = false) {
            this.container.querySelector('.iam-challenge').classList.remove('open');
            this.isOpen = false;

            this._invokeCallback('close-callback');
            this.emit('close', { widgetId: this.id, userInitiated });

            if (userInitiated && !this.verified) {
                this.emit('challenge-closed', { widgetId: this.id });
            }

            if (this.bondedMode && userInitiated) {
                this.container.style.display = 'none';
            }
        }

        _setChallenge(data) {
            this.token = data.token;
            this.responseKey = this._generateResponseKey();
            this.totalRounds = data.scene_counts.length;
            this.sceneCounts = data.scene_counts;
            this.round = 0;
            this.answers = [];
            this.scene = 0;

            this._clearTimeouts();
            this.challengeExpiryTimeout = setTimeout(() => {
                if (!this.isOpen || this.verified) return;
                this._closeChallenge();
                this._invokeCallback('chalexpired-callback');
                this.emit('challenge-expired', { widgetId: this.id });
            }, 120000);

            this.container.querySelector('.iam-token').textContent =
                data.token.split('.')[0];

            const img = new Image();
            img.onload = () => { this.img = img; this._updateRound(); };
            img.onerror = () => this._handleError(ErrorCodes.INVALID_DATA);
            img.src = 'data:image/jpeg;base64,' + data.image;
        }

        _generateResponseKey() {
            const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
            return Array.from({ length: 32 },
                () => chars[Math.floor(Math.random() * chars.length)]).join('');
        }

        _updateRound() {
            this.scene = 0;
            this.container.querySelector('.iam-round').textContent =
                `${this.round + 1} of ${this.totalRounds}`;
            this.container.querySelector('.iam-prompt').textContent =
                'Find the scene with the target icon above the fullest cup';

            const button = this.container.querySelector('.iam-submit');
            button.textContent = this.round < this.totalRounds - 1 ? 'Continue' : 'Verify';
            button.disabled = false;

            this._drawReference();
            this._drawScene();
            this._updateDots();
        }

        _getRoundOffset() {
            return this.sceneCounts.slice(0, this.round)
                .reduce((sum, count) => sum + REF_W + count * SCENE_W, 0);
        }

        _drawReference() {
            const canvas = this.container.querySelector('.iam-reference-canvas');
            const context = canvas.getContext('2d');
            context.clearRect(0, 0, canvas.width, canvas.height);
            context.drawImage(this.img, this._getRoundOffset(), 0, REF_W, 150,
                0, 0, canvas.width, canvas.height);
        }

        _drawScene() {
            const canvas = this.container.querySelector('.iam-scene-canvas');
            const context = canvas.getContext('2d');
            context.clearRect(0, 0, canvas.width, canvas.height);
            const offset = this._getRoundOffset() + REF_W + this.scene * SCENE_W;
            context.drawImage(this.img, offset, 0, SCENE_W, 150,
                0, 0, canvas.width, canvas.height);
        }

        _updateDots() {
            const container = this.container.querySelector('.iam-dots');
            const count = this.sceneCounts[this.round];
            container.innerHTML = '';

            for (let i = 0; i < count; i++) {
                const dot = document.createElement('button');
                dot.className = 'iam-dot' + (i === this.scene ? ' active' : '');
                dot.setAttribute('aria-label', `Scene ${i + 1} of ${count}`);
                dot.addEventListener('click', () => {
                    this.scene = i;
                    this._drawScene();
                    this._updateDots();
                });
                container.appendChild(dot);
            }
        }

        _navigate(direction) {
            const count = this.sceneCounts[this.round];
            this.scene = (this.scene + direction + count) % count;
            this._drawScene();
            this._updateDots();
        }

        async _nextRound() {
            this.answers.push(this.scene);
            if (this.round < this.totalRounds - 1) {
                this.round++;
                this._updateRound();
            } else {
                await this._submit();
            }
        }

        async _submit() {
            const button = this.container.querySelector('.iam-submit');
            button.disabled = true;
            button.textContent = 'Verifying...';

            try {
                const response = await fetch(`${this.config.endpoint}/captcha/submit`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        token: this.token, site_key: this.siteKey, answers: this.answers
                    })
                });

                if (!response.ok) throw new Error(ErrorCodes.NETWORK_ERROR);
                const data = await response.json();

                if (data.verified_token) {
                    return this._handleVerificationSuccess(data.verified_token);
                }

                const error = data.error || ErrorCodes.VERIFICATION_FAILED;
                this._showError(error === 'Incorrect answers' ? 'Incorrect, please try again' : error);
                setTimeout(() => {
                    this.config.mode === 'inline' ? this._loadInlineChallenge() : this._openChallenge();
                }, 1500);
                throw new Error(error);
            } catch (error) {
                button.disabled = false;
                button.textContent = 'Verify';
                throw error;
            }
        }

        _handleVerificationSuccess(token) {
            this.verified = token;
            const isInline = this.config.mode === 'inline';

            if (isInline) {
                const overlay = this.container.querySelector('.iam-success-overlay');
                overlay?.classList.add('show');
                const button = this.container.querySelector('.iam-submit');
                button.textContent = '✓ Verified';
                button.classList.add('iam-submit-success');
            } else {
                this._closeChallenge();
                this.container.querySelector('.iam-checkbox')?.classList.add('checked');
            }

            this._createHiddenInput(token);
            this._setTokenExpiry();

            if (this.bondedMode) {
                this.bondElement.classList.add('iam-bond-verified');
                this.container.style.display = 'none';
            }

            this._invokeCallback('callback', token);
            this.emit('success', {
                widgetId: this.id, response: token,
                key: this.responseKey, bonded: this.bondedMode
            });
            this._autoSubmitForm();

            return { response: token, key: this.responseKey };
        }

        _createHiddenInput(token) {
            ['iam-captcha-response', 'h-captcha-response'].forEach(name => {
                let input = this.container.querySelector(`input[name="${name}"]`);
                if (!input) {
                    input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = name;
                    this.container.appendChild(input);
                }
                input.value = token;
            });
        }

        _setTokenExpiry() {
            this._clearTimeouts();
            this.expiryTimeout = setTimeout(() => this._handleExpiry(), 120000);
        }

        _handleExpiry() {
            this.verified = null;
            this.container.querySelector('.iam-checkbox')?.classList.remove('checked');
            this.container.querySelectorAll('input[type="hidden"]')
                .forEach(input => input.value = '');
            this._invokeCallback('expired-callback');
            this.emit('expired', { widgetId: this.id });
        }

        _handleError(errorCode) {
            this._showError(this._getErrorMessage(errorCode));
            this._invokeCallback('error-callback', errorCode);
            this.emit('error', { widgetId: this.id, error: errorCode });
        }

        _getErrorMessage(code) {
            const messages = {
                [ErrorCodes.RATE_LIMITED]: 'Too many requests. Please wait.',
                [ErrorCodes.NETWORK_ERROR]: 'Network error. Please check your connection.',
                [ErrorCodes.INVALID_DATA]: 'Invalid data received.',
                [ErrorCodes.CHALLENGE_ERROR]: 'Challenge failed to load.',
                [ErrorCodes.INTERNAL_ERROR]: 'An internal error occurred.',
                [ErrorCodes.INVALID_SITEKEY]: 'Invalid site key.',
                [ErrorCodes.VERIFICATION_FAILED]: 'Verification failed. Please try again.'
            };
            return messages[code] || code;
        }

        _showError(message) {
            let error = this.container.querySelector('.iam-error');
            if (!error) {
                error = document.createElement('div');
                error.className = 'iam-error';
                this.container.querySelector('.iam-challenge').appendChild(error);
            }
            error.textContent = message;
            setTimeout(() => error.remove(), 3000);
        }

        _invokeCallback(name, ...args) {
            const callback = this.config[name];
            const fn = typeof callback === 'function' ? callback
                : typeof callback === 'string' ? window[callback] : null;
            try { fn?.apply(null, args); }
            catch (error) { console.error(`IAm Captcha: Error in ${name}:`, error); }
        }

        _clearTimeouts() {
            clearTimeout(this.expiryTimeout);
            clearTimeout(this.challengeExpiryTimeout);
            this.expiryTimeout = null;
            this.challengeExpiryTimeout = null;
        }

        _autoSubmitForm() {
            if (!this.config['auto-submit']) return;
            const form = this.container.closest('form');
            if (!form) return;
            setTimeout(() => {
                if (typeof form.requestSubmit === 'function') form.requestSubmit();
                else form.submit();
            }, 100);
        }

        execute(options = {}) {
            if (this.verified) {
                const result = { response: this.verified, key: this.responseKey };
                return options.async ? Promise.resolve(result) : undefined;
            }

            if (!options.async) {
                this._openChallenge().catch(() => {});
                return;
            }

            return new Promise((resolve, reject) => {
                const cleanup = () => {
                    this.off('success', onSuccess);
                    this.off('error', onError);
                    this.off('challenge-closed', onClosed);
                };
                const onSuccess = event => { cleanup(); resolve({ response: event.response, key: event.key }); };
                const onError = event => { cleanup(); reject(new Error(event.error)); };
                const onClosed = () => { cleanup(); reject(new Error(ErrorCodes.CHALLENGE_CLOSED)); };

                this.on('success', onSuccess).on('error', onError).on('challenge-closed', onClosed);
                this._openChallenge().catch(reject);
            });
        }

        reset() {
            this._clearTimeouts();
            Object.assign(this, {
                verified: null, token: null, responseKey: null,
                answers: [], round: 0, scene: 0, isOpen: false, isLoading: false
            });

            this.container.querySelector('.iam-checkbox')?.classList.remove('checked', 'loading');
            this.container.querySelector('.iam-challenge')?.classList.remove('open');
            this.container.querySelectorAll('input[type="hidden"]')
                .forEach(input => input.value = '');

            this.emit('reset', { widgetId: this.id });
        }

        getResponse() { return this.verified || ''; }
        getRespKey() { return this.responseKey || ''; }
        getId() { return this.id; }
        isOpened() { return this.isOpen; }
        isVerified() { return !!this.verified; }
        setData(data) { this.customData = { ...this.customData, ...data }; }

        remove() {
            this._clearTimeouts();
            document.removeEventListener('keydown', this._handleKeydown);
            document.removeEventListener('click', this._handleClickOutside);
            window.removeEventListener('resize', this._handleViewportChange);
            window.removeEventListener('scroll', this._handleViewportChange, true);

            if (this.bondElement) {
                this.bondElement.removeEventListener(this.config['bond-event'] || 'click',
                    this._handleBondClick);
                this.bondElement.classList.remove('iam-bond-loading', 'iam-bond-verified');
            }

            this.removeAllListeners();
            this.container.innerHTML = '';
            delete this.container._iamCaptcha;
            delete this.container.dataset.iamWidgetId;
        }
    }

    const widgets = new Map();

    const iamcaptcha = {
        render(container, params = {}) {
            const widget = new CaptchaWidget(container, params);
            widgets.set(widget.id, widget);
            return widget.id;
        },

        execute(widgetId, options = {}) {
            return this._getWidget(widgetId).execute(options);
        },

        reset(widgetId) { this._getWidget(widgetId).reset(); },
        getResponse(widgetId) { return this._getWidget(widgetId).getResponse(); },
        getRespKey(widgetId) { return this._getWidget(widgetId).getRespKey(); },

        remove(widgetId) {
            const widget = widgets.get(widgetId);
            if (widget) { widget.remove(); widgets.delete(widgetId); }
        },

        setData(widgetId, data) { widgets.get(widgetId)?.setData(data); },

        _getWidget(widgetId) {
            if (widgetId == null) {
                const first = widgets.values().next().value;
                if (!first) throw new Error(ErrorCodes.MISSING_CAPTCHA);
                return first;
            }
            const widget = widgets.get(widgetId);
            if (!widget) throw new Error(ErrorCodes.INVALID_CAPTCHA_ID);
            return widget;
        },

        getWidgetIds() { return [...widgets.keys()]; },
        getWidget(widgetId) { return widgets.get(widgetId); },

        bond(element, params = {}) {
            const container = document.createElement('div');
            container.className = 'iam-captcha-bonded-container';
            document.body.appendChild(container);
            return this.render(container, {
                ...params, bond: element,
                'bond-event': params['bond-event'] || params.bondEvent || 'click'
            });
        },

        ErrorCodes,
        version: '2.0.0'
    };

    function autoInit() {
        document.querySelectorAll('.iam-captcha, .iam-captcha-widget, .h-captcha')
            .forEach(element => {
                if (element.dataset.iamWidgetId !== undefined) return;
                const sitekey = element.dataset.sitekey;
                if (!sitekey) return;

                iamcaptcha.render(element, {
                    sitekey,
                    theme: element.dataset.theme || 'dark',
                    size: element.dataset.size || 'normal',
                    tabindex: parseInt(element.dataset.tabindex, 10) || 0,
                    callback: element.dataset.callback,
                    'error-callback': element.dataset.errorCallback,
                    'expired-callback': element.dataset.expiredCallback,
                    'chalexpired-callback': element.dataset.chalexpiredCallback,
                    'open-callback': element.dataset.openCallback,
                    'close-callback': element.dataset.closeCallback,
                    'passive-mode': element.dataset.passiveMode === 'true',
                    'passive-callback': element.dataset.passiveCallback,
                    'passive-threshold': parseFloat(element.dataset.passiveThreshold) || 0.4,
                    'mode': element.dataset.mode || 'checkbox',
                    'float': element.dataset.float || 'auto',
                    'challenge-size': element.dataset.challengeSize || 'auto',
                    'bond': element.dataset.bond || null,
                    'bond-event': element.dataset.bondEvent || 'click',
                    'auto-submit': element.dataset.autoSubmit === 'true'
                });
            });
    }

    function parseScriptParams() {
        for (const script of document.querySelectorAll('script[src*="iam-captcha"]')) {
            const params = new URL(script.src, window.location.origin).searchParams;
            const onload = params.get('onload');
            if (onload && typeof window[onload] === 'function') {
                window.__iamcaptcha_onload = window[onload];
            }
            if (params.get('render') === 'explicit') return false;
        }
        return true;
    }

    function init() {
        const shouldAutoRender = parseScriptParams();
        const ready = callback => {
            document.readyState === 'loading'
                ? document.addEventListener('DOMContentLoaded', callback)
                : callback();
        };

        if (shouldAutoRender) ready(autoInit);
        if (window.__iamcaptcha_onload) ready(() => setTimeout(window.__iamcaptcha_onload, 0));
    }

    init();

    return { IAmCaptcha: CaptchaWidget, iamcaptcha, ErrorCodes };
});

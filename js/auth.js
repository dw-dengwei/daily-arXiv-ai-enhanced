/**
 * Authentication Module
 * Handles password verification and session management for the application
 *
 * @module Auth
 * @requires auth-config.js
 */

const Auth = {
    /**
     * Pure JavaScript SHA-256 implementation (fallback for non-secure contexts)
     * Based on: https://geraintluff.github.io/sha256/
     *
     * @param {string} ascii - String to hash
     * @returns {string} Hexadecimal hash string
     */
    sha256Fallback(ascii) {
        function rightRotate(value, amount) {
            return (value >>> amount) | (value << (32 - amount));
        }

        const mathPow = Math.pow;
        const maxWord = mathPow(2, 32);
        const lengthProperty = 'length';
        let i, j;
        let result = '';

        const words = [];
        const asciiBitLength = ascii[lengthProperty] * 8;

        let hash = this.sha256Fallback.h = this.sha256Fallback.h || [];
        const k = this.sha256Fallback.k = this.sha256Fallback.k || [];
        let primeCounter = k[lengthProperty];

        const isComposite = {};
        for (let candidate = 2; primeCounter < 64; candidate++) {
            if (!isComposite[candidate]) {
                for (i = 0; i < 313; i += candidate) {
                    isComposite[i] = candidate;
                }
                hash[primeCounter] = (mathPow(candidate, .5) * maxWord) | 0;
                k[primeCounter++] = (mathPow(candidate, 1 / 3) * maxWord) | 0;
            }
        }

        ascii += '\x80';
        while (ascii[lengthProperty] % 64 - 56) ascii += '\x00';
        for (i = 0; i < ascii[lengthProperty]; i++) {
            j = ascii.charCodeAt(i);
            if (j >> 8) return;
            words[i >> 2] |= j << ((3 - i) % 4) * 8;
        }
        words[words[lengthProperty]] = ((asciiBitLength / maxWord) | 0);
        words[words[lengthProperty]] = (asciiBitLength);

        for (j = 0; j < words[lengthProperty];) {
            const w = words.slice(j, j += 16);
            const oldHash = hash;
            hash = hash.slice(0, 8);

            for (i = 0; i < 64; i++) {
                const w15 = w[i - 15], w2 = w[i - 2];

                const a = hash[0], e = hash[4];
                const temp1 = hash[7]
                    + (rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25))
                    + ((e & hash[5]) ^ ((~e) & hash[6]))
                    + k[i]
                    + (w[i] = (i < 16) ? w[i] : (
                        w[i - 16]
                        + (rightRotate(w15, 7) ^ rightRotate(w15, 18) ^ (w15 >>> 3))
                        + w[i - 7]
                        + (rightRotate(w2, 17) ^ rightRotate(w2, 19) ^ (w2 >>> 10))
                    ) | 0
                    );

                const temp2 = (rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22))
                    + ((a & hash[1]) ^ (a & hash[2]) ^ (hash[1] & hash[2]));

                hash = [(temp1 + temp2) | 0].concat(hash);
                hash[4] = (hash[4] + temp1) | 0;
            }

            for (i = 0; i < 8; i++) {
                hash[i] = (hash[i] + oldHash[i]) | 0;
            }
        }

        for (i = 0; i < 8; i++) {
            for (j = 3; j + 1; j--) {
                const b = (hash[i] >> (j * 8)) & 255;
                result += ((b < 16) ? 0 : '') + b.toString(16);
            }
        }
        return result;
    },

    /**
     * Calculate SHA-256 hash of a string
     *
     * @param {string} password - The password to hash
     * @returns {Promise<string>} The hexadecimal hash string
     */
    async hashPassword(password) {
        // Check if crypto.subtle is available (secure context required)
        if (window.crypto && window.crypto.subtle) {
            try {
                const encoder = new TextEncoder();
                const data = encoder.encode(password);
                const hashBuffer = await crypto.subtle.digest('SHA-256', data);
                const hashArray = Array.from(new Uint8Array(hashBuffer));
                return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            } catch (e) {
                console.warn('crypto.subtle failed, using fallback SHA-256:', e);
                return this.sha256Fallback(password);
            }
        } else {
            // Fallback for non-secure contexts (file://, HTTP, etc.)
            console.warn('crypto.subtle not available, using pure JS SHA-256 implementation');
            return this.sha256Fallback(password);
        }
    },

    /**
     * Authenticate user with password
     *
     * @param {string} password - User input password
     * @param {boolean} remember - Whether to remember login for 7 days (default: true)
     * @returns {Promise<boolean>} True if authentication successful
     */
    async login(password, remember = true) {
        const inputHash = await this.hashPassword(password);

        if (inputHash === AUTH_CONFIG.passwordHash) {
            const now = Date.now();
            // Remember: 7 days, otherwise: 1 day
            const expireTime = remember
                ? now + AUTH_CONFIG.sessionDuration
                : now + 24 * 60 * 60 * 1000;

            localStorage.setItem(AUTH_CONFIG.storageKey, inputHash);
            localStorage.setItem(AUTH_CONFIG.storageExpireKey, expireTime.toString());

            console.log('Authentication successful');
            return true;
        }

        console.warn('Authentication failed: Invalid password');
        return false;
    },

    /**
     * Check if user is authenticated
     *
     * @returns {boolean} True if valid session exists
     */
    isAuthenticated() {
        const token = localStorage.getItem(AUTH_CONFIG.storageKey);
        const expireTime = localStorage.getItem(AUTH_CONFIG.storageExpireKey);

        if (!token || !expireTime) {
            return false;
        }

        const now = Date.now();
        if (now > parseInt(expireTime)) {
            // Session expired
            console.log('Session expired');
            this.logout();
            return false;
        }

        return token === AUTH_CONFIG.passwordHash;
    },

    /**
     * Logout user and redirect to login page
     */
    logout() {
        localStorage.removeItem(AUTH_CONFIG.storageKey);
        localStorage.removeItem(AUTH_CONFIG.storageExpireKey);
        console.log('Logged out');
        window.location.href = 'login.html';
    },

    /**
     * Check if password protection is enabled
     * @returns {boolean} True if password is configured
     */
    isPasswordEnabled() {
        // If passwordHash is the placeholder or empty, password protection is disabled
        return AUTH_CONFIG.passwordHash &&
               AUTH_CONFIG.passwordHash !== 'PLACEHOLDER_PASSWORD_HASH' &&
               AUTH_CONFIG.passwordHash !== 'DISABLED_NO_PASSWORD_SET_IN_SECRETS';
    },

    /**
     * Require authentication (call on protected pages)
     * Redirects to login page if not authenticated
     * If password protection is disabled, this function does nothing
     */
    requireAuth() {
        // If password protection is not enabled, allow access without authentication
        if (!this.isPasswordEnabled()) {
            console.log('Password protection is disabled, allowing direct access');
            return;
        }

        // Password protection is enabled, check authentication
        if (!this.isAuthenticated()) {
            const currentPage = window.location.pathname.split('/').pop() || 'index.html';
            console.log('Authentication required, redirecting to login page');
            window.location.href = `login.html?redirect=${currentPage}`;
        }
    },

    /**
     * Get remaining session time in milliseconds
     *
     * @returns {number} Milliseconds until session expires
     */
    getSessionTimeLeft() {
        const expireTime = localStorage.getItem(AUTH_CONFIG.storageExpireKey);
        if (!expireTime) return 0;
        return Math.max(0, parseInt(expireTime) - Date.now());
    },

    /**
     * Format session time for display
     *
     * @returns {string} Human-readable time left (e.g., "5 days 3 hours" or "2 hours 45 min")
     */
    getSessionTimeLeftFormatted() {
        const ms = this.getSessionTimeLeft();
        const days = Math.floor(ms / (24 * 60 * 60 * 1000));
        const hours = Math.floor((ms % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000));

        if (days > 0) {
            return `${days} day${days > 1 ? 's' : ''} ${hours} hour${hours > 1 ? 's' : ''}`;
        } else if (hours > 0) {
            const minutes = Math.floor((ms % (60 * 60 * 1000)) / (60 * 1000));
            return `${hours} hour${hours > 1 ? 's' : ''} ${minutes} min`;
        } else {
            const minutes = Math.floor(ms / (60 * 1000));
            return `${minutes} minute${minutes > 1 ? 's' : ''}`;
        }
    },

    /**
     * Get session expiration date
     *
     * @returns {Date|null} Expiration date or null if not authenticated
     */
    getSessionExpireDate() {
        const expireTime = localStorage.getItem(AUTH_CONFIG.storageExpireKey);
        if (!expireTime) return null;
        return new Date(parseInt(expireTime));
    }
};

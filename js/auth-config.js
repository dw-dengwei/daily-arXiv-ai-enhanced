/**
 * Authentication Configuration
 * This is a client-side UI gate only. GitHub Pages and the public data branch
 * do not provide server-side access control; do not use this for private data.
 */

const AUTH_CONFIG = {
    /**
     * SHA-256 hash of the access password
     * Keep disabled for public GitHub Pages deployments.
     */
    passwordHash: 'DISABLED_NO_PASSWORD_SET_IN_SECRETS',

    /**
     * Session duration in milliseconds
     * Default: 7 days (604800000 ms)
     */
    sessionDuration: 7 * 24 * 60 * 60 * 1000,

    /**
     * LocalStorage key for storing authentication token
     */
    storageKey: 'arxiv_auth_token',

    /**
     * LocalStorage key for storing session expiration time
     */
    storageExpireKey: 'arxiv_auth_expire'
};

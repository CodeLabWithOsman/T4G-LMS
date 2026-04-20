/**
 * session.js
 * ──────────────────────────────────────────────────────────────
 * Shared session utility for Tech4Girls LMS.
 * Include this BEFORE any page script on every protected page:
 *
 *   <script src="js/session.js"></script>
 *
 * It exposes a global `Session` object and a global `apiFetch()`
 * wrapper that automatically attaches the auth header and handles
 * 401 responses without logging the user out for transient errors.
 * ──────────────────────────────────────────────────────────────
 */

const Session = {
  TOKEN_KEY:  "student_token",
  USER_KEY:   "student_user",
  EXPIRY_KEY: "student_token_expiry",

  // ── Read ───────────────────────────────────────────────────
  getToken() {
    return localStorage.getItem(this.TOKEN_KEY);
  },

  getUser() {
    try {
      return JSON.parse(localStorage.getItem(this.USER_KEY));
    } catch {
      return null;
    }
  },

  // Returns true only when a token AND user object exist AND the
  // token has not passed its locally-stored expiry timestamp.
  isValid() {
    const token  = this.getToken();
    const user   = this.getUser();
    if (!token || !user) return false;

    const expiry = localStorage.getItem(this.EXPIRY_KEY);
    if (!expiry) return true; // old session without expiry — keep alive
    return Date.now() < Number(expiry);
  },

  // ── Write ──────────────────────────────────────────────────
  save(token, user, expiresInSeconds) {
    localStorage.setItem(this.TOKEN_KEY, token);
    localStorage.setItem(this.USER_KEY,  JSON.stringify(user));

    // Default: 7 days so users stay logged in across browser restarts
    const ttl     = expiresInSeconds || 60 * 60 * 24 * 7;
    const expiry  = Date.now() + ttl * 1000;
    localStorage.setItem(this.EXPIRY_KEY, String(expiry));
  },

  updateUser(updatedFields) {
    const current = this.getUser() || {};
    const merged  = { ...current, ...updatedFields };
    localStorage.setItem(this.USER_KEY, JSON.stringify(merged));
    return merged;
  },

  // ── Destroy — ONLY call this on explicit logout ────────────
  clear() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    localStorage.removeItem(this.EXPIRY_KEY);
  },

  // ── Auth guard — call once at top of every protected page ──
  // Redirects to login only if there is genuinely no session.
  requireAuth(loginPage = "login.html") {
    if (!this.isValid()) {
      window.location.replace(loginPage);
      return false;
    }
    return true;
  },

  // ── Logout helper ──────────────────────────────────────────
  logout(loginPage = "login.html") {
    this.clear();
    window.location.replace(loginPage);
  },
};


/**
 * apiFetch(url, options)
 * ──────────────────────────────────────────────────────────────
 * Drop-in replacement for fetch() on authenticated endpoints.
 *
 * - Automatically adds Authorization header
 * - On 401: tries once to silently re-validate by hitting /students/me
 *   If re-validation fails → logs out. If it passes → retries the request.
 *   This handles the case where the token is still valid on the server
 *   but the local expiry timestamp was wrong (e.g. clock skew).
 * - On other errors: throws normally so callers can handle them.
 *
 * Usage — exactly like fetch():
 *   const res = await apiFetch(`${BASE_URL}/enrollments/student/${id}`);
 *   const data = await res.json();
 */
const BASE_URL = "https://t4g-lms-production.up.railway.app";

async function apiFetch(url, options = {}) {
  const token = Session.getToken();

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(url, { ...options, headers });

  // ── 401 handling ────────────────────────────────────────────
  if (res.status === 401) {
    // The token was rejected. Before logging the user out entirely,
    // do one silent check against /students/me to see if the server
    // actually considers the token invalid, or if this was a one-off.
    const recheckPassed = await _silentRevalidate(token);

    if (!recheckPassed) {
      // Server confirmed the token is dead — log out cleanly.
      Session.clear();
      window.location.replace("login.html");
      // Return a dummy response so any caller awaiting this doesn't crash.
      return new Response(JSON.stringify({ detail: "Session expired." }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Token is still valid on the server — retry the original request once.
    return fetch(url, { ...options, headers });
  }

  return res;
}

async function _silentRevalidate(token) {
  try {
    const res = await fetch(`${BASE_URL}/students/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (res.ok) {
      // Token is valid — refresh the local expiry to extend the session.
      const user = await res.json();
      Session.updateUser(user);
      // Reset expiry to another 7 days from now
      localStorage.setItem(
        Session.EXPIRY_KEY,
        String(Date.now() + 60 * 60 * 24 * 7 * 1000)
      );
      return true;
    }
    return false;
  } catch {
    // Network error during revalidation — do NOT log the user out.
    // They may just be temporarily offline. Keep the session alive.
    return true;
  }
}
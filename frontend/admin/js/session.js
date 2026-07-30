/* ==========================================================================
   Tech4Girls LMS - Session layer

   Fixes:
   - Sessions no longer expire on their own. A user stays signed in until they
     explicitly log out, or the server definitively rejects the token (401/403).
   - No login-page flash on refresh. The guard runs before paint via an inline
     <head> snippet that adds `auth-pending` to <html>; the body stays hidden
     until the local session check resolves (synchronous, no network).
   - Revalidation happens in the background and NEVER logs the user out on a
     network error, timeout, CORS failure or 5xx. Only a real 401/403 does.
   - Role aware: student | staff | admin, each with its own storage namespace.
   ========================================================================== */

(function (global) {
  "use strict";

  var BASE_URL = "https://t4g-lms-backend.fly.dev";

  // Allow local development against a local API without editing this file.
  try {
    var host = global.location && global.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      BASE_URL = global.__T4G_API__ || "http://127.0.0.1:8000";
    }
  } catch (e) {
    /* non-browser context */
  }

  var ROLES = {
    student: {
      tokenKey: "student_token",
      userKey: "student_user",
      loginUrl: "login.html",
      homeUrl: "student-dashboard.html",
      meEndpoint: "/students/me"
    },
    staff: {
      tokenKey: "staff_token",
      userKey: "staff_user",
      loginUrl: "index.html",
      homeUrl: "staff-dashboard.html",
      meEndpoint: "/staff/me"
    },
    admin: {
      tokenKey: "admin_token",
      userKey: "admin_user",
      loginUrl: "index.html",
      homeUrl: "admin-dashboard.html",
      meEndpoint: "/admin/me"
    }
  };

  var LAST_PAGE_KEY = "t4g_last_page";

  /* ---------------- storage helpers (never throw) ---------------- */

  function safeGet(key) {
    try {
      return global.localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function safeSet(key, value) {
    try {
      global.localStorage.setItem(key, value);
      return true;
    } catch (e) {
      return false;
    }
  }

  function safeRemove(key) {
    try {
      global.localStorage.removeItem(key);
    } catch (e) {
      /* ignore */
    }
  }

  function parseJSON(raw) {
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  /* ---------------- JWT inspection (local, offline) ---------------- */

  function decodeJwt(token) {
    if (!token || typeof token !== "string") return null;
    var parts = token.split(".");
    if (parts.length !== 3) return null;
    try {
      var payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
      while (payload.length % 4) payload += "=";
      return JSON.parse(global.atob(payload));
    } catch (e) {
      return null;
    }
  }

  /**
   * A token is only treated as locally invalid when it is structurally broken.
   * We deliberately do NOT enforce `exp` on the client: the backend issues
   * long-lived tokens and silently refreshes them, and a clock skew on the
   * user's device must never sign them out.
   */
  function isStructurallyValid(token) {
    return typeof token === "string" && token.length > 20;
  }

  /* ---------------- role resolution ---------------- */

  function resolveRole(explicit) {
    if (explicit && ROLES[explicit]) return explicit;
    if (global.__T4G_ROLE__ && ROLES[global.__T4G_ROLE__]) {
      return global.__T4G_ROLE__;
    }
    var path = (global.location && global.location.pathname) || "";
    if (path.indexOf("/admin") !== -1) return "admin";
    if (path.indexOf("/staff") !== -1) return "staff";
    return "student";
  }

  /* ---------------- Session ---------------- */

  function Session(role) {
    this.role = resolveRole(role);
    this.config = ROLES[this.role];
  }

  Session.prototype.getToken = function () {
    var token = safeGet(this.config.tokenKey);
    return isStructurallyValid(token) ? token : null;
  };

  Session.prototype.getUser = function () {
    return parseJSON(safeGet(this.config.userKey));
  };

  Session.prototype.isAuthenticated = function () {
    return this.getToken() !== null;
  };

  /**
   * Persist a session. Called once after a successful login.
   * There is no expiry stored -- the session lives until logout.
   */
  Session.prototype.save = function (token, user) {
    if (!isStructurallyValid(token)) return false;
    safeSet(this.config.tokenKey, token);
    if (user && typeof user === "object") {
      safeSet(this.config.userKey, JSON.stringify(user));
    }
    // Remove any legacy expiry keys written by older builds so they can never
    // trigger a spurious logout again.
    safeRemove(this.config.tokenKey + "_expiry");
    safeRemove(this.config.tokenKey + "_refresh");
    safeRemove("student_token_expiry");
    safeRemove("student_token_refresh");
    return true;
  };

  /** Merge fields into the stored user object (e.g. after a profile update). */
  Session.prototype.updateUser = function (patch) {
    var user = this.getUser() || {};
    for (var key in patch) {
      if (Object.prototype.hasOwnProperty.call(patch, key)) {
        user[key] = patch[key];
      }
    }
    safeSet(this.config.userKey, JSON.stringify(user));
    return user;
  };

  Session.prototype.clear = function () {
    safeRemove(this.config.tokenKey);
    safeRemove(this.config.userKey);
    safeRemove(this.config.tokenKey + "_expiry");
    safeRemove(this.config.tokenKey + "_refresh");
  };

  /* ---------------- page memory (refresh returns to same page) -------- */

  Session.prototype.rememberPage = function () {
    try {
      var here = global.location.pathname + global.location.search + global.location.hash;
      safeSet(LAST_PAGE_KEY + "_" + this.role, here);
    } catch (e) {
      /* ignore */
    }
  };

  Session.prototype.lastPage = function () {
    return safeGet(LAST_PAGE_KEY + "_" + this.role);
  };

  /* ---------------- guards ---------------- */

  /**
   * Guard a protected page. Runs synchronously against localStorage only, so
   * it resolves before the first paint and cannot flash the login page.
   * Returns true when the page may render.
   */
  Session.prototype.requireAuth = function () {
    if (this.isAuthenticated()) {
      this.rememberPage();
      Session.reveal();
      this._revalidateInBackground();
      return true;
    }
    // Preserve where the user was trying to go so login can return them there.
    try {
      var here = global.location.pathname + global.location.search;
      safeSet("t4g_redirect_after_login", here);
    } catch (e) {
      /* ignore */
    }
    global.location.replace(this.config.loginUrl);
    return false;
  };

  /**
   * Guard a login page. If a session already exists, go straight to the app.
   * Also runs pre-paint, so a signed-in user never sees the login form.
   */
  Session.prototype.redirectIfAuthenticated = function () {
    if (!this.isAuthenticated()) {
      Session.reveal();
      return false;
    }
    var target = safeGet("t4g_redirect_after_login");
    safeRemove("t4g_redirect_after_login");
    var dest = this.config.homeUrl;
    if (target && target.indexOf("//") === -1 && target.charAt(0) === "/") {
      dest = target;
    }
    global.location.replace(dest);
    return true;
  };

  /** Reveal the document once the guard has decided. */
  Session.reveal = function () {
    try {
      document.documentElement.classList.remove("auth-pending");
    } catch (e) {
      /* ignore */
    }
  };

  /**
   * Background revalidation. Purely opportunistic:
   *   - refreshes the cached user object,
   *   - signs the user out ONLY on a definitive 401/403.
   * Network errors, CORS failures, timeouts and 5xx are ignored so an offline
   * or flaky connection can never end the session.
   */
  Session.prototype._revalidateInBackground = function () {
    var self = this;
    var token = this.getToken();
    if (!token) return;

    var controller =
      typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = global.setTimeout(function () {
      if (controller) controller.abort();
    }, 12000);

    var options = {
      method: "GET",
      headers: { Authorization: "Bearer " + token }
    };
    if (controller) options.signal = controller.signal;

    global
      .fetch(BASE_URL + this.config.meEndpoint, options)
      .then(function (res) {
        global.clearTimeout(timer);
        if (res.status === 401 || res.status === 403) {
          self.logout(true);
          return null;
        }
        if (!res.ok) return null; // 404/5xx -> keep the session
        return res.json().catch(function () {
          return null;
        });
      })
      .then(function (user) {
        if (user && typeof user === "object") {
          safeSet(self.config.userKey, JSON.stringify(user));
          try {
            global.dispatchEvent(
              new CustomEvent("t4g:user-refreshed", { detail: user })
            );
          } catch (e) {
            /* ignore */
          }
        }
      })
      .catch(function () {
        global.clearTimeout(timer);
        // Offline / CORS / abort -> keep the session, stay signed in.
      });
  };

  /* ---------------- logout ---------------- */

  Session.prototype.logout = function (silent) {
    var loginUrl = this.config.loginUrl;
    this.clear();
    safeRemove(LAST_PAGE_KEY + "_" + this.role);
    safeRemove("t4g_redirect_after_login");
    if (!silent) {
      global.location.replace(loginUrl);
    } else {
      global.location.replace(loginUrl);
    }
  };

  /* ---------------- authenticated fetch ---------------- */

  /**
   * fetch() wrapper that attaches the bearer token and surfaces clean errors.
   * A 401/403 ends the session; every other failure is thrown to the caller so
   * the page can show an inline message instead of dumping the user to login.
   */
  Session.prototype.apiFetch = function (path, options) {
    var self = this;
    options = options || {};

    var headers = {};
    var provided = options.headers || {};
    for (var h in provided) {
      if (Object.prototype.hasOwnProperty.call(provided, h)) {
        headers[h] = provided[h];
      }
    }

    var token = this.getToken();
    if (token) headers.Authorization = "Bearer " + token;

    var isFormData =
      typeof FormData !== "undefined" && options.body instanceof FormData;
    if (!isFormData && options.body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    var url = /^https?:\/\//.test(path) ? path : BASE_URL + path;

    return global
      .fetch(url, {
        method: options.method || "GET",
        headers: headers,
        body: options.body
      })
      .then(function (res) {
        if (res.status === 401 || res.status === 403) {
          self.logout(true);
          throw new Error("Your session has ended. Please sign in again.");
        }
        return res;
      });
  };

  /** apiFetch + JSON parsing + backend error-detail extraction. */
  Session.prototype.apiJson = function (path, options) {
    return this.apiFetch(path, options).then(function (res) {
      return res
        .json()
        .catch(function () {
          return null;
        })
        .then(function (data) {
          if (!res.ok) {
            var message =
              (data && (data.detail || data.message)) ||
              "Request failed (" + res.status + ").";
            if (typeof message !== "string") message = JSON.stringify(message);
            var err = new Error(message);
            err.status = res.status;
            err.data = data;
            throw err;
          }
          return data;
        });
    });
  };

  /* ---------------- exports ---------------- */

  var sessions = {};

  function getSession(role) {
    var resolved = resolveRole(role);
    if (!sessions[resolved]) sessions[resolved] = new Session(resolved);
    return sessions[resolved];
  }

  var api = getSession();
  api.for = getSession;
  api.BASE_URL = BASE_URL;
  api.reveal = Session.reveal;
  api.decodeJwt = decodeJwt;

  global.Session = api;
  global.T4GSession = api;
  global.BASE_URL = BASE_URL;
})(window);

# 🔐 PuroBeach Security Audit Report

**Date:** 2025-07-26  
**Auditor:** Dot (Automated)  
**App:** PuroBeach Beach Club Management System  
**Stack:** Flask 3.0.0, SQLite (raw), Gunicorn, Nginx, Docker  

---

## 📊 Summary

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 3 |
| 🟡 MEDIUM | 8 |
| 🟢 LOW | 6 |
| ✅ GOOD | 14 |

---

## 1. SQL Injection

### ✅ GOOD — Parameterized queries used consistently

The codebase uses **parameterized queries (`?` placeholders)** throughout all models. No string concatenation of user input into SQL was found. Every `cursor.execute()` call passes user data as tuple parameters.

**Evidence (all models follow this pattern):**
```python
# models/user.py:89
cursor.execute('''
    SELECT u.*, r.name as role_name
    FROM users u LEFT JOIN roles r ON u.role_id = r.id
    WHERE u.username = ?
''', (username,))

# models/reservation_queries.py:80
query += ' AND (c.first_name LIKE ? OR c.last_name LIKE ?)'
params.extend([f'%{guest_name}%', f'%{guest_name}%'])
```

### ✅ GOOD — Dynamic UPDATE queries use allowed-field whitelists

All dynamic `UPDATE` queries (e.g., `models/user.py:198`, `models/furniture.py:182`, `models/reservation_crud.py:407`) follow a safe pattern:
1. Fields are checked against an `allowed_fields` whitelist
2. Only field **names** from the whitelist are interpolated (never user input)
3. **Values** are always passed as `?` parameters

```python
# models/user.py:198-208
allowed_fields = ['email', 'full_name', 'role_id', 'active', 'theme_preference']
for field in allowed_fields:
    if field in kwargs:
        updates.append(f'{field} = ?')  # field name from whitelist only
        values.append(kwargs[field])     # value as parameter
query = f'UPDATE users SET {", ".join(updates)} WHERE id = ?'
cursor.execute(query, values)
```

### ✅ GOOD — IN clause placeholders generated safely

```python
# models/role.py:274
placeholders = ','.join('?' * len(permission_ids))
cursor.execute(f'SELECT id, code, name FROM permissions WHERE id IN ({placeholders})', permission_ids)
```

### 🟡 MEDIUM — `map_res_edit_fields.py:146-149` — Dynamic UPDATE with user-controlled keys

**File:** `blueprints/beach/routes/api/map_res_edit_fields.py`, lines 60-149

The `update_reservation_partial` endpoint builds an UPDATE query where the **column names** come from user-submitted JSON keys, filtered through `allowed_fields` and `field_mapping`. While the whitelist mitigates injection, the code is fragile — if someone adds a new field mapping without thinking about SQL implications, it could be exploited.

```python
# Line 146-149
set_clauses = ', '.join(f'{k} = ?' for k in updates.keys())
values = list(updates.values()) + [reservation_id]
conn.execute(f'''
    UPDATE beach_reservations SET {set_clauses}, updated_at = CURRENT_TIMESTAMP WHERE id = ?
''', values)
```

**Risk:** LOW in current state (whitelisted), but the pattern is harder to audit than model-layer equivalents. Consider routing through `models/reservation_crud.py:update_beach_reservation()` instead.

### 🟡 MEDIUM — `map_res_search.py:164` — Dynamic IN clause from computed list

```python
placeholders = ','.join('?' * len(customer_ids))
cursor = conn.execute(f'''
    SELECT DISTINCT rf.furniture_id ...
    WHERE r.customer_id IN ({placeholders})
    ...
''', customer_ids + [date_str])
```

This is technically safe (customer_ids are integers from DB), but the f-string IN pattern is repeated ad-hoc across multiple files. **Recommendation:** Extract a helper function like `in_clause(ids)` to centralize this pattern.

### 🟡 MEDIUM — `models/waitlist.py:169` — String-interpolated status filter

```python
status_filter = "" if include_all else "AND w.status = 'waiting'"
cursor.execute(f'''SELECT ... {status_filter} ...''')
```

This is safe because `status_filter` is a hardcoded string (not user input), but the pattern of injecting SQL fragments via f-strings is fragile and harder to audit. **Recommendation:** Use parameterized approach instead.

---

## 2. XSS (Cross-Site Scripting)

### ✅ GOOD — Jinja2 auto-escaping enabled (default)

Flask/Jinja2 auto-escapes all `{{ variable }}` output in HTML templates by default. No `|safe` filter is used on user-supplied data.

### ✅ GOOD — No `Markup()` calls found in the codebase

No use of `Markup()` in models, blueprints, or utils, eliminating a common XSS vector.

### 🟢 LOW — `tojson|safe` used in one template

**File:** `templates/beach/reservations.html:955`
```html
const statesData = {{ states | tojson | safe }};
```

The `|safe` is needed here because `tojson` produces valid JSON that shouldn't be double-escaped. The data (`states`) comes from the database (admin-configured state names), not directly from user input. **Risk is LOW** but if a state name contained `</script>`, it could break out. Jinja2's `tojson` filter handles this by escaping `</` sequences, so this is actually safe.

### ✅ GOOD — Other `tojson` uses don't use `|safe`

```html
<!-- templates/beach/reservation_form/_scripts.html:909 -->
preferences: {{ preselected_customer.preference_codes|default([])|tojson }}
<!-- templates/admin/role_detail.html:183 -->
initRolePermissions({{ role.id }}, {{ can_edit|tojson }});
```

---

## 3. Authentication & Authorization

### ✅ GOOD — Password hashing with Werkzeug

Passwords are hashed using `werkzeug.security.generate_password_hash()` (pbkdf2:sha256 by default) and verified with `check_password_hash()`.

```python
# models/user.py:163
password_hash = generate_password_hash(password)
# models/user.py:263
return check_password_hash(user_dict['password_hash'], password)
```

### ✅ GOOD — Login rate limiting

```python
# blueprints/auth/routes.py:20
@limiter.limit("5 per minute")
def login():
```

Plus Nginx-level rate limiting on `/login`:
```nginx
location /login {
    limit_req zone=login burst=3 nodelay;
}
```

### ✅ GOOD — Open redirect protection

```python
# blueprints/auth/routes.py:62
next_page = request.args.get('next')
if not next_page or urlparse(next_page).netloc != '':
    next_page = url_for('beach.map')
```

### ✅ GOOD — All routes require authentication + permission

Every route (except login, health check) uses `@login_required` + `@permission_required('...')`. The `permission_required` decorator properly checks against loaded permissions and aborts with 403.

### 🟡 MEDIUM — Weak password policy for form-based change

**File:** `blueprints/auth/forms.py:47`
```python
new_password = PasswordField('Nueva Contraseña', validators=[
    DataRequired(message='La nueva contraseña es requerida'),
    Length(min=6, message='La contraseña debe tener al menos 6 caracteres')
])
```

**File:** `blueprints/admin/services/user_service.py:35`
```python
if len(password) < 6:
    return False, 'La contraseña debe tener al menos 6 caracteres'
```

The CLI `create-user` command requires 8 chars + uppercase + lowercase + digit, but the web forms only require 6 characters with no complexity requirements. **This is inconsistent and weak for a production system.**

**Recommendation:** Enforce minimum 8 characters + complexity across all password entry points.

### 🟡 MEDIUM — Logout via GET request

**File:** `blueprints/auth/routes.py:74`
```python
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
```

Logout is a state-changing operation triggered via GET. This is vulnerable to **CSRF via image tags or link prefetching**: `<img src="/logout">`. Should use POST + CSRF token.

### 🟡 MEDIUM — No `session_protection` configured for Flask-Login

Flask-Login's `session_protection` setting (defaults to `'basic'`) isn't explicitly configured. While `'basic'` is adequate, setting `login_manager.session_protection = 'strong'` would provide better protection against session hijacking by invalidating sessions when the client IP or user agent changes.

### 🟢 LOW — No account lockout mechanism

After 5 failed logins per minute (rate limit), the user just has to wait. There's no progressive lockout, CAPTCHA, or notification of suspicious login attempts.

---

## 4. CSRF Protection

### ✅ GOOD — Global CSRF enabled

```python
# config.py:26
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 3600
```

```python
# extensions.py:10
csrf = CSRFProtect()
# app.py:82
csrf.init_app(app)
```

### ✅ GOOD — CSRF meta tag in base template

```html
<!-- templates/base.html:6 -->
<meta name="csrf-token" content="{{ csrf_token() }}">
```

### ✅ GOOD — CSRF tokens in all POST forms

Verified across all templates: `csrf_token()` is included in every POST form as a hidden input and in AJAX requests via `X-CSRFToken` header.

### ✅ GOOD — No CSRF exemptions found

No uses of `@csrf.exempt` or `csrf_exempt` anywhere in the codebase.

---

## 5. File Upload Security

### ✅ GOOD — File extension whitelist

```python
# config.py:36
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'pdf', 'png', 'jpg', 'jpeg'}
```

### ✅ GOOD — `secure_filename()` used

```python
# blueprints/admin/routes.py (hotel_guests_import)
filename = secure_filename(file.filename)
```

### ✅ GOOD — Size limit configured

```python
# config.py:35
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
```

### 🟢 LOW — Temp file cleanup has retry but no guaranteed cleanup

The upload handler uses a try/finally with retry for Windows file locking:
```python
finally:
    for _ in range(3):
        try:
            if os.path.exists(temp_path): os.remove(temp_path)
            ...
```

If all 3 retries fail, temp files accumulate. Consider using `tempfile.NamedTemporaryFile` with automatic cleanup.

### 🟢 LOW — No MIME type validation

Only the file extension is checked (`.xlsx`, `.xls`), not the actual file content/MIME type. A malicious file with a `.xlsx` extension but different content would pass validation.

---

## 6. Dependencies

### 🔴 CRITICAL — Outdated Flask and Werkzeug with known CVEs

**File:** `requirements.txt` / `requirements/production.txt`

| Package | Current | Latest Stable | Known Issues |
|---------|---------|---------------|-------------|
| Flask | 3.0.0 | 3.1.1 | Multiple patches since 3.0.0 |
| Werkzeug | 3.0.1 | 3.1.3 | **CVE-2024-34069** (debugger RCE, dev only), path traversal fixes |
| Flask-Login | 0.6.3 | 0.6.3 | ✅ Current |
| Flask-WTF | 1.2.1 | 1.2.2 | Minor fix |
| Flask-Limiter | 3.5.0 | 3.12 | Multiple improvements |
| gunicorn | 21.2.0 | 23.0.0 | Security hardening |
| openpyxl | 3.1.2 | 3.1.5 | Bug fixes |
| Jinja2 | (via Flask) | 3.1.6 | **CVE-2024-56326** (sandbox escape, impacts `|attr` filter) |

**Action Required:** Update all dependencies. At minimum:
```
Flask>=3.1.0
Werkzeug>=3.1.0
Jinja2>=3.1.5
gunicorn>=23.0.0
```

---

## 7. Docker Security

### ✅ GOOD — Non-root user in Dockerfile

```dockerfile
# Dockerfile:12
RUN groupadd -r purobeach && useradd -r -g purobeach -d /app -s /sbin/nologin purobeach
# Dockerfile:26
USER purobeach
```

### ✅ GOOD — Health check configured

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1
```

### ✅ GOOD — Named volumes for persistent data

Database, uploads, and logs use named Docker volumes — not host bind mounts.

### ✅ GOOD — Internal network isolation

```yaml
networks:
  internal:
    driver: bridge
```

App port (8000) is exposed to host but Nginx handles external traffic.

### 🔴 CRITICAL — `.env.production` contains real SECRET_KEY committed to repo

**File:** `.env.production`
```
SECRET_KEY=d9b89ffbec6d5ec5d4210b3ccb9068cca567fa400fd9ca5580014d685a9739d7
DOMAIN=beachclubinterno.duckdns.org
ADMIN_EMAIL=catia.schubert@proton.me
```

While `.env.production` is in `.gitignore` and NOT tracked by git (verified: `git ls-files` only shows `.env.example` and `.env.production.example`), **the file exists on disk with real secrets**. The real domain and admin email are exposed.

**The `.env.production.example` is properly template-only (no secrets) — ✅ GOOD**

**Risk:** If the server is compromised or backup includes this file, the secret key is leaked. The key should be rotated since it was printed in this audit.

**Recommendation:** Rotate the SECRET_KEY and ensure `.env.production` is never accidentally committed.

### 🟢 LOW — App port exposed to all interfaces

```yaml
ports:
  - "${APP_PORT:-8000}:8000"
```

This exposes port 8000 on all interfaces. Should be `127.0.0.1:8000:8000` since Nginx handles external traffic.

---

## 8. Configuration

### ✅ GOOD — Production config validates SECRET_KEY

```python
# config.py:56-63
class ProductionConfig(Config):
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set in production")
    if len(SECRET_KEY) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters in production")
```

### ✅ GOOD — Production enforces HTTPS cookies

```python
# config.py:54
SESSION_COOKIE_SECURE = True  # Require HTTPS
WTF_CSRF_SSL_STRICT = True
PREFERRED_URL_SCHEME = 'https'
```

### ✅ GOOD — Debug mode off in production

```python
# config.py:52
DEBUG = False
```

### ✅ GOOD — Security headers in Nginx

The nginx config includes a comprehensive set:
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (HSTS with preload)
- `Content-Security-Policy` (restrictive)
- `Permissions-Policy` (camera/mic/geo disabled)
- `Referrer-Policy: strict-origin-when-cross-origin`

### 🟡 MEDIUM — Dev fallback SECRET_KEY is weak

```python
# config.py:14
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
```

If `FLASK_ENV` is not set to `production` (e.g., misconfigured deployment), the app falls back to `DevelopmentConfig` which uses this hardcoded key. The production config correctly raises an error, but the fallback path is dangerous.

**Recommendation:** Also validate SECRET_KEY in the base `Config` class, or at minimum log a warning.

### 🟢 LOW — No CORS configuration

No CORS headers or Flask-CORS extension is used. This is actually **fine** since the app is a server-rendered monolith (not a SPA with a separate API). No cross-origin requests are expected.

### 🟡 MEDIUM — CSP allows `unsafe-inline` and `unsafe-eval`

```nginx
Content-Security-Policy: "... script-src 'self' 'unsafe-inline' 'unsafe-eval' ...;
                           style-src 'self' 'unsafe-inline' ..."
```

While inline scripts/styles are common in server-rendered apps, `unsafe-eval` is rarely needed and weakens XSS protection. **Recommendation:** Try removing `unsafe-eval` and use nonces for inline scripts if needed.

---

## 9. Input Validation

### ✅ GOOD — WTForms with validators for auth forms

```python
# blueprints/auth/forms.py
username = StringField('Usuario', validators=[DataRequired()])
email = StringField('Correo', validators=[DataRequired(), Email()])
new_password = PasswordField('Nueva Contraseña', validators=[DataRequired(), Length(min=6)])
```

### 🟡 MEDIUM — Admin user creation form has no WTForms

**File:** `blueprints/admin/routes.py:97-133` (`users_create`)

The admin user creation uses raw `request.form.get()` without WTForms validation:
```python
username = request.form.get('username', '').strip()
email = request.form.get('email', '').strip()
password = request.form.get('password', '')
```

Validation is done by `validate_user_creation()` which only checks uniqueness and password length (≥6 chars). No email format validation, no username format validation on the web form side.

**Recommendation:** Create a `CreateUserForm` with proper WTForms validators.

### 🟡 MEDIUM — Numeric conversions without try/except in config routes

**File:** `blueprints/beach/routes/config/states.py:37`, `minimum_consumption.py:36`, `packages.py:36-46`

```python
priority = int(request.form.get('display_priority', 0) or 0)
minimum_amount = float(request.form.get('minimum_amount', 0) or 0)
```

If a user sends non-numeric data, these will throw `ValueError` and return a 500 error. Should be wrapped in try/except.

### ✅ GOOD — API endpoints validate JSON inputs

The API endpoints (e.g., `map_res_edit_fields.py`) properly validate types, ranges, and enum values before updating.

---

## 10. Information Disclosure

### 🔴 CRITICAL — Exception details exposed to users in flash messages

**Multiple files across `blueprints/`:**

```python
# blueprints/admin/routes.py:131
flash(f'Error al crear usuario: {str(e)}', 'error')

# blueprints/beach/routes/config/furniture.py:280
return jsonify({'error': str(e)}), 500

# blueprints/beach/routes/config/states.py:157
return jsonify({'success': False, 'error': str(e)}), 500

# blueprints/beach/routes/api/map_res_edit_fields.py:155
return jsonify({'success': False, 'error': f'Error al actualizar reserva: {str(e)}'}), 500
```

There are **20+ instances** of `str(e)` being returned to the client. Exception messages can contain:
- Database schema information (table/column names)
- File paths
- SQL query fragments
- Internal state details

**Recommendation:** Log the full exception server-side, return a generic error message to the user:
```python
app.logger.error(f'Error creating user: {e}', exc_info=True)
flash('Error al crear usuario. Contacte al administrador.', 'error')
```

### 🟡 MEDIUM — `traceback.print_exc()` in production code

**File:** `blueprints/beach/routes/api/map_res_create.py:203-205, 309-310`
```python
import traceback
traceback.print_exc()
```

Stack traces are printed to stdout/stderr. In production with gunicorn, these go to the error log (not directly to users), but they should use proper logging instead.

### ✅ GOOD — Error pages don't leak information

The custom error templates (`404.html`, `500.html`, `403.html`) show generic messages without any technical details, stack traces, or debug information.

### ✅ GOOD — Health endpoint reveals minimal information

```python
return jsonify({
    'status': 'ok',
    'version': '1.0.0',
    'app': 'PuroBeach Beach Club Management System',
    'database': db_status
})
```

No sensitive information in the health check.

---

## 🏆 Security Scorecard

| Category | Grade | Notes |
|----------|-------|-------|
| SQL Injection | A | All parameterized, whitelisted dynamic fields |
| XSS | A | Auto-escaping, no unsafe patterns |
| Authentication | B | Good hashing/rate-limiting, weak password policy |
| Authorization | A | Permission-based, all routes protected |
| CSRF | A | Global protection, no exemptions |
| File Uploads | B+ | Extension check, secure_filename, no MIME validation |
| Dependencies | D | Multiple outdated packages with CVEs |
| Docker | B+ | Non-root, isolated network, but port exposure |
| Configuration | B+ | Good prod checks, CSP could be tighter |
| Input Validation | B | Good where WTForms used, gaps in admin forms |
| Info Disclosure | C | Exception messages leaked to 20+ endpoints |

---

## 📋 Priority Action Items

### Must Fix Before Production (🔴 CRITICAL)
1. **Update dependencies** — `pip install --upgrade Flask Werkzeug Jinja2 gunicorn Flask-Limiter`
2. **Stop exposing `str(e)` to users** — Replace all 20+ instances with generic error messages + server-side logging
3. **Rotate SECRET_KEY** — The current key was printed in `.env.production` and is visible on disk

### Should Fix Soon (🟡 MEDIUM)
4. Enforce minimum 8-char passwords with complexity across all forms
5. Change logout to POST with CSRF token
6. Set `login_manager.session_protection = 'strong'`
7. Remove `unsafe-eval` from CSP
8. Create WTForms for admin user creation
9. Add try/except around `int()`/`float()` conversions in config routes
10. Bind Docker app port to `127.0.0.1` only
11. Route `map_res_edit_fields.py` updates through the model layer

### Nice to Have (🟢 LOW)
12. Add MIME type validation for file uploads
13. Implement account lockout after repeated failures
14. Use `tempfile.NamedTemporaryFile` for auto-cleanup
15. Add CSP nonces instead of `unsafe-inline` for scripts
16. Extract `in_clause()` helper for dynamic SQL IN patterns
17. No CORS needed (server-rendered app) — already good

---

*Report generated from static code analysis of the PUROBEACH_NEW codebase.*

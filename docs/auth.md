# HBntory - Authentication

## Password storage

- Mechanism: **bcrypt** (`bcrypt` Python package).
- Hashing: `bcrypt.hashpw(password, bcrypt.gensalt())`. A random salt is generated for each password and stored inside the hash string (`$2b$12$...`).
- Verification: `bcrypt.checkpw(password, stored_hash)` re-hashes the typed password with the salt found in the stored hash and compares the results.
- The database never contains a plain-text password, including for the admin created by `init_db.py`.

### Why not plain text or plain SHA256

- Plain text: anyone who reads the database (leak, backup, SQL injection) gets every password immediately, and users reuse passwords on other sites.
- Plain SHA256: it is a fast general-purpose hash. An attacker with a graphics card can try billions of candidates per second. Without salt, two users with the same password have the same hash, and precomputed tables (rainbow tables) work.
- bcrypt is slow on purpose (cost factor 12 = 4096 rounds) and salted: each guess is expensive and must be redone for each user.

## Authentication (who are you?)

The Backoffice uses server-side sessions. The logic is in `backoffice/auth.py`, and `app.py` handles the cookie.

1. The user sends their username and password to `/login`.
2. The server looks for an active user with this name. Unknown users, soft-deleted users and wrong passwords all get the same message: "Invalid username or password." For an unknown user, a password check is still run on a dummy hash, so the response time does not show whether the account exists.
3. On success, the server creates a random token (`secrets.token_urlsafe(32)`). It stores only the SHA-256 hash of this token in the `user_sessions` table, with an expiry date 8 hours later.
4. The token is sent to the browser in the `session_token` cookie (`HttpOnly`, `SameSite=Lax`).
5. On every request, `permissions.py` reads the cookie and `auth.get_current_user` checks the database: the token must exist, must not be expired, and must belong to a user who is not deleted. A deleted user loses access at once.
6. Logout (`POST /logout`) deletes the session from the database and removes the cookie.

Flask's `SECRET_KEY` is only used to sign the cookie that carries the flash messages.

### Why SHA-256 is enough for the token but not for passwords

The token is long and random (256 bits), so nobody can find it by trying values. A password is chosen by a person and can be guessed, which is why it needs a slow hash like bcrypt.

### Why server-side sessions

The Backoffice builds its pages on the server, so the browser sends the cookie by itself. Because the session is stored in our database, logout and account deletion take effect immediately.

## Known limitations

- Expired sessions stay in the table.
- There is no limit on the number of login attempts.
- Forms have no CSRF token. `SameSite=Lax` reduces the risk.
- The cookie is not marked `Secure`, because the project does not use HTTPS.

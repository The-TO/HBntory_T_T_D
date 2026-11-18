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

1. The user posts username and password to `/login`.
2. The server loads the user, rejects unknown users, soft-deleted users and wrong passwords with the same message.
3. On success the session is cleared and `session["user_id"]` is set. Flask signs the cookie with `SECRET_KEY`, so the browser cannot forge it.
4. Before every request, `load_current_user` reloads the user from the database. A user deleted in the meantime loses access at once.

We chose sessions over tokens because the Backoffice is server-rendered: the browser sends the cookie by itself and logout is just `session.clear()`.

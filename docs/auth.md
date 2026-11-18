# HBntory - Authentication and authorization

## Password storage

- Salt : a string of random characters added to a password before it is hashed
- Mechanism: **bcrypt** (`bcrypt` Python package).
- Hashing: `bcrypt.hashpw(password, bcrypt.gensalt())`. A random salt is generated for each password and stored inside the hash string (`$2b$12$...`).
- Verification: `bcrypt.checkpw(password, stored_hash)` re-hashes the typed password with the salt found in the stored hash and compares the results.
- The database never contains a plain-text password, including for the admin created by `init_db.py`.

### Why not plain text or plain SHA256

- Plain text: anyone who reads the database (leak, backup, SQL injection) gets every password immediately.
- Plain SHA256: it is a fast general-purpose hash. An attacker with a graphics card can try billions of candidates per second. Without salt, two users with the same password have the same hash, and precomputed tables (rainbow tables) work.
- bcrypt is slow on purpose (cost factor 12 = 4096 rounds) and salted: each guess is expensive and must be redone for each user.



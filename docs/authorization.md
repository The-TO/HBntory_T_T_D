# HBntory - Authorization

Authentication answers "who are you?". Authorization answers "what are you allowed to do?".
Authorization is enforced in the backend: hiding a button in the interface is never enough.

## Roles

- `admin`: the only administrator. Has no branch.
- `common`: a regular user, assigned to exactly one branch.

## Rules

| Action | Admin | Common user | Anonymous |
|---|---|---|---|
| List, create, modify, soft-delete users | Yes | No (403) | No (401) |
| Add, remove, consult stock | No (403) | Own branch only | No (401) |

## How the rules are enforced

All checks are in `backoffice/permissions.py`. Every route starts with one call:

- `require_login()`: refuses anonymous visitors (401).
- `require_role("admin")`: refuses anonymous visitors (401) and any other role (403). Used at the beginning of user-management routes.
- `current_branch_id()`: used by stock routes. It requires the `common` role and returns the branch of the **logged-in user**.

The branch is never read from the URL or from a form. A common user therefore cannot act on another branch, even by modifying the request. The admin has no branch and is refused (403) on every stock route.

## What authentication provides

`get_current_user()` reads the session token from the request cookie and asks `auth.py` for the user. It returns `None` when the visitor is anonymous, when the session is unknown or expired, or when the user has been soft-deleted. The database is checked on every request, so a deleted user loses access immediately, even with an open session.

## Responses

- **401 Unauthorized**: the backend raises 401, and the application redirects the visitor to the login page.
- **403 Forbidden**: the user is logged in but does not have the right role.

## Tests

`backoffice/tests/test_permissions.py` checks, with a simulated logged-in user:

- anonymous visitors are refused everywhere (401);
- a common user cannot use admin routes (403);
- the admin cannot use stock routes (403);
- the admin can use admin routes;
- a common user works on their own branch.

## Known limitations

- Each route must call `require_role` or `current_branch_id` by hand. Forgetting it leaves the route open, so every new route is tested for the anonymous case.
- Permissions are role-based and branch-based only, there is no finer per-object permission.

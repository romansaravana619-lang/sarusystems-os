# Audit 4 — Authentication, RBAC & Company Isolation

## Scope
- Authentication lifecycle and active-account checks
- Access-token validation and refresh boundaries
- Permission enforcement through existing RBAC
- Company isolation at authentication boundaries
- Cross-company privilege risks

## Confirmed findings

### Finding A — Inactive company could authenticate active users
`/auth/login` validated only the user's active flag. An active user belonging to an inactive company could still receive an access token.

**Severity:** High
**Status:** Fixed

### Finding B — Existing access tokens remained usable after company deactivation
`get_current_user` validated the user but did not validate the current company's active state. This allowed existing tokens to continue through authenticated endpoints after company deactivation.

**Severity:** High
**Status:** Fixed

## Review note
Role and permission definitions are currently global system-level entities. This is retained as the existing authorization architecture rather than introducing a new tenant-role model during this audit. Company-scoped business data remains enforced through the existing user company identity and domain checks.

## Fix boundary
- No new authentication architecture.
- Existing JWT and dependency flow retained.
- Existing RBAC permission vocabulary retained.
- Company active-state validation added at both login and authenticated-user resolution.
- Focused regression tests added.

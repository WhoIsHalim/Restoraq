# System & Marketing Site Review Report

## Scope & Method
- Static code review across Django views, templates, and configuration.
- `python manage.py check` executed (passed with no issues).
- Live UI/UX walkthrough could not be performed because the local server was not reachable at `http://127.0.0.1:8000/`.

## What I Could Not Validate (Needs Live Server)
- End-to-end UX flows (login, dashboard navigation, POS, reports, kitchen screen, admin CRUD).
- Visual/layout regressions across breakpoints.
- Runtime JS errors and HTMX/Alpine interactions.

## Findings (Functional / Product)

### F-1: System login redirect ignores hidden system path
- Location: `accounts/views.py:25`
- Evidence: `return "/system/"`
- Why this is a problem: When `SYSTEM_PATH` is set to a hidden route (default `secure-system/`), system users are redirected to `/system/`, which is intentionally masked to a 404. This breaks login for SystemOwner/SystemAdmin.
- Recommended fix: Use `reverse("system:dashboard")` or `resolve_url` instead of hard-coded `/system/`.

## Notes
- No other functional errors were deterministically observable without running the server.

## Next Step (If You Want Full UI QA)
Run the server locally and tell me the URL/port. I will run a Playwright-based walkthrough to validate key flows and produce a full UI error report.

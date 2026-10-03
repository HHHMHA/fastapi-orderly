refresh token model (hashed) and tests to revoke it

oauth2_scheme → decode_token → get_current_user → get_current_active_user → require_roles("admin")

repositores and abstract one maybe with tests

services register, auth, issue, refresh, revoke and tests

deps

endpoints and tests

exceptions

Rotation with reuse detection. This is the part worth building carefully. Each refresh token carries a family_id. On refresh: verify, mark the presented token used, issue a new one in the same family. If a token marked used is presented again, that means two parties hold it — one of them stole it — so revoke the entire family and force re-authentication. Without this, a stolen refresh token grants indefinite access; with it, the theft becomes self-detecting the moment either party uses it.

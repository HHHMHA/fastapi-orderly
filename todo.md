services register, auth, issue, refresh, revoke and tests:

register request -> is admin false, is active false, is verified false -> send otp email
to test

RegisterUserRequest normalize email

UserService register_user with dup cases

check otp -> update user to is_active=True, is_verified=True (rate limit)

login request -> issue token
refresh token request -> issue new token (and rotate refresh token)
get current active user -> require_permission (refresh token not accepted)
revoke token
log out all (revoke all refresh tokens)

refresh token model (hashed) and tests to revoke it

oauth2_scheme → decode_token → get_current_user → get_current_active_user → require_roles("admin")

deps

endpoints and tests

exceptions

Rotation with reuse detection. This is the part worth building carefully. Each refresh token carries a family_id. On refresh: verify, mark the presented token used, issue a new one in the same family. If a token marked used is presented again, that means two parties hold it — one of them stole it — so revoke the entire family and force re-authentication. Without this, a stolen refresh token grants indefinite access; with it, the theft becomes self-detecting the moment either party uses it.

translations

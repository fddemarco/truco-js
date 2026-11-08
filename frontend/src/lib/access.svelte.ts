/**
 * The access gate (backend app/access.py): with ACCESS_PASSWORD set on the server, the API
 * answers 401 `access_required` until this browser enters the password, which leaves an
 * HttpOnly cookie. The layout shows AccessGate instead of the app while `locked`.
 *
 * `checked` turns true after the first `GET /api/access`; any API call refused for access
 * (an expired cookie, a new password) locks the app again, through the client middleware.
 */
export const access = $state({ checked: false, locked: false });

const ACCESS_REQUIRED = "access_required";

/** Whether a response body is the gate's refusal. */
export function isAccessRefusal(status: number, body: unknown): boolean {
  return (
    status === 401 &&
    !!body &&
    typeof body === "object" &&
    (body as { detail?: unknown }).detail === ACCESS_REQUIRED
  );
}

export function setAccess(state: { required: boolean; granted: boolean }): void {
  access.checked = true;
  access.locked = state.required && !state.granted;
}

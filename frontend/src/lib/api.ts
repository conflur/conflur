import { startRegistration, startAuthentication } from "@simplewebauthn/browser";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return data.detail ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

/** Registro de un profesional nuevo. Devuelve { access_token, principal }. */
export async function registerAccount(input: {
  email: string;
  password: string;
  full_name: string;
  practice_name?: string;
}) {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  return res.json();
}

/**
 * Login por passkey: corre la ceremonia WebAuthn en el navegador y devuelve el
 * access token emitido por el backend. El caller lo pasa a signIn("passkey").
 */
export async function passkeyLogin(email: string): Promise<string> {
  const optRes = await fetch(`${API_URL}/auth/passkey/login/options`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!optRes.ok) throw new ApiError(optRes.status, await parseError(optRes));
  const { options, challenge_token } = await optRes.json();

  const assertion = await startAuthentication(options);

  const verRes = await fetch(`${API_URL}/auth/passkey/login/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential: assertion, challenge_token }),
  });
  if (!verRes.ok) throw new ApiError(verRes.status, await parseError(verRes));
  const data = await verRes.json();
  return data.access_token as string;
}

/** Registra una passkey para el usuario autenticado (necesita su access token). */
export async function passkeyRegister(accessToken: string, deviceName?: string): Promise<void> {
  const optRes = await fetch(`${API_URL}/auth/passkey/register/options`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!optRes.ok) throw new ApiError(optRes.status, await parseError(optRes));
  const { options, challenge_token } = await optRes.json();

  const attestation = await startRegistration(options);

  const verRes = await fetch(`${API_URL}/auth/passkey/register/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ credential: attestation, challenge_token, device_name: deviceName }),
  });
  if (!verRes.ok) throw new ApiError(verRes.status, await parseError(verRes));
}

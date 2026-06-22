import { API_URL, ApiError } from "./api";

export { ApiError };

/**
 * Cliente HTTP autenticado contra el backend. Adjunta el Bearer token (del
 * access token que NextAuth guarda en la sesión) y normaliza errores.
 */
export async function authedFetch<T = unknown>(
  token: string,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });

  if (res.status === 204) return undefined as T;

  if (!res.ok) {
    let detail: string = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? data);
    } catch {
      /* sin body json */
    }
    throw new ApiError(res.status, detail);
  }

  return res.json();
}

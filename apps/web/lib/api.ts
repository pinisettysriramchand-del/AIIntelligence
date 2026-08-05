const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Tokens = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export function getTokens(): Tokens | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("stratiq_tokens");
  return raw ? (JSON.parse(raw) as Tokens) : null;
}

export function setTokens(tokens: Tokens | null) {
  if (typeof window === "undefined") return;
  if (!tokens) {
    localStorage.removeItem("stratiq_tokens");
    return;
  }
  localStorage.setItem("stratiq_tokens", JSON.stringify(tokens));
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const tokens = getTokens();
    if (tokens?.access_token) {
      headers.set("Authorization", `Bearer ${tokens.access_token}`);
    }
  }
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

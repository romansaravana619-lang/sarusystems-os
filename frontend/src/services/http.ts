const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function apiRequest<T>(token: string, path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string; error?: { message?: string } }
      | null;
    throw new Error(body?.detail ?? body?.error?.message ?? "Request failed.");
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

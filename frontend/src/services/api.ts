const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type MeResponse = { id: string; company_id: string; email: string; full_name: string; is_active: boolean; roles: string[]; permissions: string[] };
type TokenResponse = { access_token: string; token_type: string };
export type UserRecord = { id: string; company_id: string; email: string; full_name: string; is_active: boolean };
export type RoleRecord = { id: string; name: string; description: string | null; is_active: boolean; permission_ids: string[] };
export type PermissionRecord = { id: string; code: string; description: string | null };
export type AuditRecord = { id: string; actor_user_id: string | null; action: string; entity_type: string; entity_id: string | null; details: string | null; created_at: string };
export type CreateUserPayload = { company_id: string; email: string; full_name: string; password: string; role_ids: string[] };
type RolePermissionsResponse = { role_id: string; permission_ids: string[] };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
  if (!response.ok) { const body = (await response.json().catch(() => null)) as { detail?: string } | null; throw new Error(body?.detail ?? "Request failed."); }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
export async function login(email: string, password: string): Promise<TokenResponse> { return request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }); }
export async function getMe(token: string): Promise<MeResponse> { return request<MeResponse>("/auth/me", { headers: { Authorization: `Bearer ${token}` } }); }
export async function logout(token: string): Promise<void> { await request<void>("/auth/logout", { method: "POST", headers: { Authorization: `Bearer ${token}` } }); }
export async function listUsers(token: string): Promise<UserRecord[]> { return request<UserRecord[]>("/users", { headers: { Authorization: `Bearer ${token}` } }); }
export async function listRoles(token: string): Promise<RoleRecord[]> { return request<RoleRecord[]>("/roles", { headers: { Authorization: `Bearer ${token}` } }); }
export async function listPermissions(token: string): Promise<PermissionRecord[]> { return request<PermissionRecord[]>("/permissions", { headers: { Authorization: `Bearer ${token}` } }); }
export async function listAuditLogs(token: string): Promise<AuditRecord[]> { return request<AuditRecord[]>("/audit", { headers: { Authorization: `Bearer ${token}` } }); }
export async function createUser(token: string, payload: CreateUserPayload): Promise<UserRecord> { return request<UserRecord>("/users", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }); }
export async function createRole(token: string, payload: { name: string; description?: string; permission_ids: string[] }): Promise<RoleRecord> { return request<RoleRecord>("/roles", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }); }
export async function replaceRolePermissions(token: string, roleId: string, permissionIds: string[]): Promise<RolePermissionsResponse> { return request<RolePermissionsResponse>(`/roles/${roleId}/permissions`, { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(permissionIds) }); }

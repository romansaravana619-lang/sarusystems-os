const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type ServiceRecord = { id: string; company_id: string; code: string; name: string; category: string | null; description: string | null; pricing_model: string; base_price: number | null; currency: string; typical_duration_days: number | null; required_skills: string | null; freelancer_roles: string | null; workflow_template: string | null; deliverable_template: string | null; is_active: boolean };
export type ServiceItem = { id: string; service_id: string; name: string; description: string | null; is_mandatory: boolean; sort_order: number; is_active: boolean };

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init?.headers ?? {}) } });
  if (!response.ok) { const body = await response.json().catch(() => null) as { detail?: string } | null; throw new Error(body?.detail ?? "Request failed."); }
  return response.json() as Promise<T>;
}

export const listServices = (token: string) => request<ServiceRecord[]>("/services", token);
export const createService = (token: string, payload: Partial<ServiceRecord> & { code: string; name: string }) => request<ServiceRecord>("/services", token, { method: "POST", body: JSON.stringify(payload) });
export const updateService = (token: string, id: string, payload: Partial<ServiceRecord>) => request<ServiceRecord>(`/services/${id}`, token, { method: "PATCH", body: JSON.stringify(payload) });
export const listServiceRequirements = (token: string, id: string) => request<ServiceItem[]>(`/services/${id}/requirements`, token);
export const listServiceDeliverables = (token: string, id: string) => request<ServiceItem[]>(`/services/${id}/deliverables`, token);
export const createServiceRequirement = (token: string, id: string, payload: { name: string; description?: string; is_mandatory?: boolean; sort_order?: number }) => request<ServiceItem>(`/services/${id}/requirements`, token, { method: "POST", body: JSON.stringify(payload) });
export const updateServiceRequirement = (token: string, id: string, itemId: string, payload: Partial<Pick<ServiceItem, "name" | "description" | "is_mandatory" | "sort_order" | "is_active">>) => request<ServiceItem>(`/services/${id}/requirements/${itemId}`, token, { method: "PATCH", body: JSON.stringify(payload) });
export const createServiceDeliverable = (token: string, id: string, payload: { name: string; description?: string; is_mandatory?: boolean; sort_order?: number }) => request<ServiceItem>(`/services/${id}/deliverables`, token, { method: "POST", body: JSON.stringify(payload) });
export const updateServiceDeliverable = (token: string, id: string, itemId: string, payload: Partial<Pick<ServiceItem, "name" | "description" | "is_mandatory" | "sort_order" | "is_active">>) => request<ServiceItem>(`/services/${id}/deliverables/${itemId}`, token, { method: "PATCH", body: JSON.stringify(payload) });

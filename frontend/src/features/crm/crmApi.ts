const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init?.headers ?? {}) } });
  if (!response.ok) { const body = await response.json().catch(() => null) as { detail?: string } | null; throw new Error(body?.detail ?? "Request failed."); }
  return response.json() as Promise<T>;
}

export type CRMProspect = { id: string; name: string; company_name: string | null; email: string | null; phone: string | null; source: string | null; industry: string | null; status: string; lead_score: number; qualification_level: string; notes: string | null; next_action: string | null; next_action_at: string | null; last_contact_at: string | null };
export type CRMCommunication = { id: string; prospect_id: string | null; contact_id: string | null; channel: string; direction: string; subject: string | null; summary: string; occurred_at: string; };
export type CRMFollowUp = { id: string; prospect_id: string | null; contact_id: string | null; owner_user_id: string; title: string; due_at: string; status: string; notes: string | null; completed_at: string | null; };

export const listCRMProspects = (token: string) => request<CRMProspect[]>("/crm/prospects", token);
export const createCRMProspect = (token: string, payload: Partial<CRMProspect> & { name: string }) => request<CRMProspect>("/crm/prospects", token, { method: "POST", body: JSON.stringify(payload) });
export const updateCRMProspect = (token: string, id: string, payload: Partial<CRMProspect>) => request<CRMProspect>(`/crm/prospects/${id}`, token, { method: "PATCH", body: JSON.stringify(payload) });
export const listCRMFollowUps = (token: string) => request<CRMFollowUp[]>("/crm/follow-ups", token);
export const createCRMFollowUp = (token: string, payload: { prospect_id: string; owner_user_id: string; title: string; due_at: string; notes?: string }) => request<CRMFollowUp>("/crm/follow-ups", token, { method: "POST", body: JSON.stringify(payload) });
export const updateCRMFollowUp = (token: string, id: string, payload: { status?: string; title?: string; due_at?: string; notes?: string }) => request<CRMFollowUp>(`/crm/follow-ups/${id}`, token, { method: "PATCH", body: JSON.stringify(payload) });
export const listCRMCommunications = (token: string, prospectId: string) => request<CRMCommunication[]>(`/crm/prospects/${prospectId}/communications`, token);
export const createCRMCommunication = (token: string, payload: { prospect_id: string; channel: string; direction?: string; subject?: string; summary: string; occurred_at?: string }) => request<CRMCommunication>("/crm/communications", token, { method: "POST", body: JSON.stringify(payload) });

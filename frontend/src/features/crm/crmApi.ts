const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init?.headers ?? {}) } });
  if (!response.ok) { const body = await response.json().catch(() => null) as { detail?: string } | null; throw new Error(body?.detail ?? "Request failed."); }
  return response.json() as Promise<T>;
}

export type CRMProspect = { id: string; name: string; company_name: string | null; email: string | null; phone: string | null; source: string | null; industry: string | null; location?: string | null; website?: string | null; preferred_channel?: string | null; outreach_channel?: string | null; problem_observed?: string | null; potential_service?: string | null; discovery_angle?: string | null; why_selected?: string | null; status: string; lead_score: number; qualification_level: string; notes: string | null; next_action: string | null; next_action_at: string | null; first_contact_at?: string | null; last_contact_at: string | null; follow_up_count?: number };
export type CRMCommunication = { id: string; prospect_id: string | null; contact_id: string | null; channel: string; direction: string; subject: string | null; summary: string; occurred_at: string; };
export type CRMFollowUp = { id: string; prospect_id: string | null; contact_id: string | null; owner_user_id: string; title: string; due_at: string; status: string; notes: string | null; completed_at: string | null; };
export type CRMDashboard = { total_prospects: number; active_prospects: number; qualified_leads: number; outreach_sent: number; replies: number; positive_replies: number; follow_ups_open: number; follow_ups_overdue: number; discovery_calls: number; proposals: number; negotiations: number; won_opportunities: number; pipeline_value: number; won_value: number; by_prospect_status: Record<string, number>; by_source: Record<string, number>; by_outreach_channel: Record<string, number>; by_opportunity_stage: Record<string, number> };

export const getCRMBoard = (token: string) => request<CRMDashboard>("/crm/dashboard", token);
export const listCRMProspects = (token: string) => request<CRMProspect[]>("/crm/prospects", token);
export const createCRMProspect = (token: string, payload: Partial<CRMProspect> & { name: string }) => request<CRMProspect>("/crm/prospects", token, { method: "POST", body: JSON.stringify(payload) });
export const updateCRMProspect = (token: string, id: string, payload: Partial<CRMProspect>) => request<CRMProspect>(`/crm/prospects/${id}`, token, { method: "PATCH", body: JSON.stringify(payload) });
export const listCRMFollowUps = (token: string) => request<CRMFollowUp[]>("/crm/follow-ups", token);
export const createCRMFollowUp = (token: string, payload: { prospect_id: string; owner_user_id: string; title: string; due_at: string; notes?: string }) => request<CRMFollowUp>("/crm/follow-ups", token, { method: "POST", body: JSON.stringify(payload) });
export const updateCRMFollowUp = (token: string, id: string, payload: { status?: string; title?: string; due_at?: string; notes?: string }) => request<CRMFollowUp>(`/crm/follow-ups/${id}`, token, { method: "PATCH", body: JSON.stringify(payload) });
export const listCRMCommunications = (token: string, prospectId: string) => request<CRMCommunication[]>(`/crm/prospects/${prospectId}/communications`, token);
export const createCRMCommunication = (token: string, payload: { prospect_id: string; channel: string; direction?: string; subject?: string; summary: string; occurred_at?: string }) => request<CRMCommunication>("/crm/communications", token, { method: "POST", body: JSON.stringify(payload) });

export type CommandCenterTaskItem = { id: string; title: string; status: string; priority: string; due_at: string | null; owner_user_id: string | null; client_id: string | null };
export type CommandCenterFollowUpItem = { id: string; name: string; stage: string; estimated_value: number | null; owner_user_id: string | null; updated_at: string };
export type CommandCenterApprovalItem = { id: string; type: string; description: string; reference_id: string };
export type CommandCenterAuditItem = { id: string; actor_user_id: string | null; action: string; entity_type: string; entity_id: string | null; details: string | null; created_at: string };
export type CommandCenterResponse = {
  user: { id: string; full_name: string; email: string; is_active: boolean; roles: string[] };
  priorities: CommandCenterTaskItem[];
  follow_ups: CommandCenterFollowUpItem[];
  approvals: CommandCenterApprovalItem[];
  deadlines: CommandCenterTaskItem[];
  business_health: Record<string, number>;
  alerts: CommandCenterTaskItem[];
  quick_actions: string[];
  counts: Record<string, number>;
  recent_activity: CommandCenterAuditItem[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getCommandCenter(token: string): Promise<CommandCenterResponse> {
  const response = await fetch(`${API_BASE_URL}/command-center`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Failed to load founder command center.");
  }
  return (await response.json()) as CommandCenterResponse;
}

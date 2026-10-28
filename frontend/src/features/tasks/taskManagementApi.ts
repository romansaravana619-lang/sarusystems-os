const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type TaskRecord = {
  id: string;
  company_id: string;
  project_id: string | null;
  milestone_id: string | null;
  required_deliverable_id: string | null;
  title: string;
  description: string | null;
  expected_output: string | null;
  status: string;
  priority: string;
  owner_user_id: string | null;
  client_id: string | null;
  start_at: string | null;
  due_at: string | null;
  estimated_hours: number | null;
  completed_at: string | null;
  founder_notes: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type TaskWorkspace = {
  total_tasks: number;
  open_tasks: number;
  backlog_tasks: number;
  ready_tasks: number;
  in_progress_tasks: number;
  blocked_tasks: number;
  review_tasks: number;
  revision_tasks: number;
  completed_tasks: number;
  cancelled_tasks: number;
  overdue_tasks: number;
  unassigned_tasks: number;
  critical_tasks: number;
  tasks: TaskRecord[];
};

export type ChecklistRecord = { id: string; task_id: string; title: string; is_completed: boolean; completed_at: string | null; created_at: string; updated_at: string };
export type DependencyRecord = { id: string; task_id: string; depends_on_task_id: string; notes: string | null; created_at: string; updated_at: string };
export type BlockerRecord = { id: string; task_id: string; blocker: string; blocked_by: string | null; identified_at: string; required_action: string; owner_user_id: string | null; resolution_date: string | null; status: string; created_at: string; updated_at: string };

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init?.headers ?? {}) } });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Request failed.");
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function getTaskWorkspace(token: string): Promise<TaskWorkspace> { return request<TaskWorkspace>("/tasks/workspace", token); }
export function listTasksV1(token: string): Promise<TaskRecord[]> { return request<TaskRecord[]>("/tasks", token); }
export function createTaskV1(token: string, payload: Partial<TaskRecord> & { title: string }): Promise<TaskRecord> { return request<TaskRecord>("/tasks", token, { method: "POST", body: JSON.stringify(payload) }); }
export function updateTaskV1(token: string, taskId: string, payload: Partial<TaskRecord>): Promise<TaskRecord> { return request<TaskRecord>(`/tasks/${taskId}`, token, { method: "PATCH", body: JSON.stringify(payload) }); }
export function submitTask(token: string, taskId: string): Promise<TaskRecord> { return request<TaskRecord>(`/tasks/${taskId}/submit`, token, { method: "POST" }); }
export function requestTaskRevision(token: string, taskId: string): Promise<TaskRecord> { return request<TaskRecord>(`/tasks/${taskId}/request-revision`, token, { method: "POST" }); }
export function completeTaskV1(token: string, taskId: string): Promise<TaskRecord> { return request<TaskRecord>(`/tasks/${taskId}/complete`, token, { method: "POST" }); }
export function assignTaskV1(token: string, taskId: string, ownerUserId: string): Promise<TaskRecord> { return request<TaskRecord>(`/tasks/${taskId}/assign?owner_user_id=${encodeURIComponent(ownerUserId)}`, token, { method: "POST" }); }
export function listChecklistV1(token: string, taskId: string): Promise<ChecklistRecord[]> { return request<ChecklistRecord[]>(`/tasks/${taskId}/checklist`, token); }
export function createChecklistV1(token: string, taskId: string, title: string): Promise<ChecklistRecord> { return request<ChecklistRecord>(`/tasks/${taskId}/checklist`, token, { method: "POST", body: JSON.stringify({ title }) }); }
export function updateChecklistV1(token: string, taskId: string, itemId: string, payload: { title?: string; is_completed?: boolean }): Promise<ChecklistRecord> { return request<ChecklistRecord>(`/tasks/${taskId}/checklist/${itemId}`, token, { method: "PATCH", body: JSON.stringify(payload) }); }
export function listDependenciesV1(token: string, taskId: string): Promise<DependencyRecord[]> { return request<DependencyRecord[]>(`/tasks/${taskId}/dependencies`, token); }
export function listBlockersV1(token: string, taskId: string): Promise<BlockerRecord[]> { return request<BlockerRecord[]>(`/tasks/${taskId}/blockers`, token); }
export function createBlockerV1(token: string, taskId: string, payload: { blocker: string; blocked_by?: string; required_action: string; owner_user_id?: string }): Promise<BlockerRecord> { return request<BlockerRecord>(`/tasks/${taskId}/blockers`, token, { method: "POST", body: JSON.stringify(payload) }); }
export function resolveBlockerV1(token: string, taskId: string, blockerId: string): Promise<BlockerRecord> { return request<BlockerRecord>(`/tasks/${taskId}/blockers/${blockerId}`, token, { method: "PATCH", body: JSON.stringify({ status: "resolved" }) }); }

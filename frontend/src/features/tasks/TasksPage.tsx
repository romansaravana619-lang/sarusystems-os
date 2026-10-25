import { useEffect, useMemo, useState } from "react";

import {
  completeTaskV1,
  createBlockerV1,
  createChecklistV1,
  createTaskV1,
  getTaskWorkspace,
  listBlockersV1,
  listChecklistV1,
  listTasksV1,
  requestTaskRevision,
  resolveBlockerV1,
  submitTask,
  updateChecklistV1,
  updateTaskV1,
  type BlockerRecord,
  type ChecklistRecord,
  type TaskRecord,
  type TaskWorkspace,
} from "./taskManagementApi";

const statuses = ["backlog", "ready", "in_progress", "blocked", "review", "revision", "completed", "cancelled"];
const priorities = ["critical", "high", "medium", "low"];

function label(value: string): string { return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function isClosed(status: string): boolean { return ["completed", "cancelled", "done"].includes(status); }
function isOverdue(task: TaskRecord): boolean { return Boolean(task.due_at && !isClosed(task.status) && new Date(task.due_at).getTime() < Date.now()); }
function statusClass(status: string): string { if (status === "completed") return "active"; if (["blocked", "cancelled"].includes(status)) return "muted"; if (["review", "revision", "in_progress"].includes(status)) return "warning"; return "pending"; }

export default function TasksPage({ token }: { token: string }) {
  const [workspace, setWorkspace] = useState<TaskWorkspace | null>(null);
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [checklist, setChecklist] = useState<ChecklistRecord[]>([]);
  const [blockers, setBlockers] = useState<BlockerRecord[]>([]);
  const [filter, setFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newChecklistTitle, setNewChecklistTitle] = useState("");
  const [newBlocker, setNewBlocker] = useState("");
  const [newBlockerAction, setNewBlockerAction] = useState("");

  const refresh = async () => {
    setLoading(true); setError("");
    try {
      const [dashboard, records] = await Promise.all([getTaskWorkspace(token), listTasksV1(token)]);
      setWorkspace(dashboard); setTasks(records);
    } catch (err) { setError((err as Error).message); }
    finally { setLoading(false); }
  };

  useEffect(() => { void refresh(); }, [token]);

  const selected = tasks.find((task) => task.id === selectedTaskId) ?? null;
  useEffect(() => {
    if (!selected) { setChecklist([]); setBlockers([]); return; }
    void Promise.all([listChecklistV1(token, selected.id), listBlockersV1(token, selected.id)]).then(([items, taskBlockers]) => { setChecklist(items); setBlockers(taskBlockers); }).catch((err) => setError((err as Error).message));
  }, [selectedTaskId, token]);

  const filteredTasks = useMemo(() => tasks.filter((task) => (filter === "all" || task.status === filter) && (priorityFilter === "all" || task.priority === priorityFilter)), [filter, priorityFilter, tasks]);

  const mutate = async (action: () => Promise<TaskRecord>, message: string) => {
    setSaving(true); setError(""); setSuccess("");
    try { const task = await action(); setTasks((current) => current.map((item) => item.id === task.id ? task : item)); setSuccess(message); const next = await getTaskWorkspace(token); setWorkspace(next); }
    catch (err) { setError((err as Error).message); }
    finally { setSaving(false); }
  };

  const create = async () => {
    if (!newTaskTitle.trim()) return;
    setSaving(true); setError(""); setSuccess("");
    try { const task = await createTaskV1(token, { title: newTaskTitle.trim(), priority: "medium", status: "backlog" }); setTasks((current) => [task, ...current]); setNewTaskTitle(""); setSelectedTaskId(task.id); setSuccess("Task created in Backlog."); setWorkspace(await getTaskWorkspace(token)); }
    catch (err) { setError((err as Error).message); }
    finally { setSaving(false); }
  };

  const addChecklist = async () => {
    if (!selected || !newChecklistTitle.trim()) return;
    setSaving(true); setError("");
    try { const item = await createChecklistV1(token, selected.id, newChecklistTitle.trim()); setChecklist((current) => [...current, item]); setNewChecklistTitle(""); }
    catch (err) { setError((err as Error).message); }
    finally { setSaving(false); }
  };

  const addBlocker = async () => {
    if (!selected || !newBlocker.trim() || !newBlockerAction.trim()) return;
    setSaving(true); setError("");
    try { const item = await createBlockerV1(token, selected.id, { blocker: newBlocker.trim(), required_action: newBlockerAction.trim() }); setBlockers((current) => [item, ...current]); setNewBlocker(""); setNewBlockerAction(""); const updated = await listTasksV1(token); setTasks(updated); setWorkspace(await getTaskWorkspace(token)); }
    catch (err) { setError((err as Error).message); }
    finally { setSaving(false); }
  };

  if (loading || !workspace) return <section className="module-panel"><p>Loading task operations…</p></section>;

  return (
    <section className="module-panel tasks-page">
      <div className="module-header">
        <div><p className="eyebrow">DELIVERY OPERATIONS · 4.8 TASK MANAGEMENT</p><h2>Tasks</h2><p className="module-subtitle">Project → Milestone → Task → Deliverable → Review → Completion</p></div>
        <button className="secondary-button" type="button" disabled={loading || saving} onClick={() => void refresh()}>Refresh</button>
      </div>

      {error && <p className="form-error">{error}</p>}
      {success && <p className="success-message">{success}</p>}

      <div className="stats-grid">
        <div className="stat-card"><span>Total</span><strong>{workspace.total_tasks}</strong></div>
        <div className="stat-card"><span>Open</span><strong>{workspace.open_tasks}</strong></div>
        <div className="stat-card"><span>Blocked</span><strong>{workspace.blocked_tasks}</strong></div>
        <div className="stat-card"><span>Review</span><strong>{workspace.review_tasks + workspace.revision_tasks}</strong></div>
        <div className="stat-card"><span>Overdue</span><strong>{workspace.overdue_tasks}</strong></div>
        <div className="stat-card"><span>Unassigned</span><strong>{workspace.unassigned_tasks}</strong></div>
        <div className="stat-card"><span>Critical</span><strong>{workspace.critical_tasks}</strong></div>
        <div className="stat-card"><span>Completed</span><strong>{workspace.completed_tasks}</strong></div>
      </div>

      <div className="module-toolbar">
        <div className="filter-row">
          <button className={filter === "all" ? "primary-button" : "secondary-button"} type="button" onClick={() => setFilter("all")}>All</button>
          {statuses.map((status) => <button key={status} className={filter === status ? "primary-button" : "secondary-button"} type="button" onClick={() => setFilter(status)}>{label(status)}</button>)}
        </div>
        <div className="filter-row">
          <span className="table-muted">Priority</span>
          <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}><option value="all">All</option>{priorities.map((priority) => <option key={priority} value={priority}>{label(priority)}</option>)}</select>
          <div className="inline-form"><input value={newTaskTitle} onChange={(event) => setNewTaskTitle(event.target.value)} placeholder="New task title" onKeyDown={(event) => { if (event.key === "Enter") void create(); }} /><button className="primary-button" type="button" disabled={saving || !newTaskTitle.trim()} onClick={() => void create()}>Create</button></div>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead><tr><th>Task</th><th>Status</th><th>Priority</th><th>Owner</th><th>Project</th><th>Due</th><th>Action</th></tr></thead>
          <tbody>
            {filteredTasks.length ? filteredTasks.map((task) => (
              <tr key={task.id} className="clickable-row" onClick={() => setSelectedTaskId(task.id)}>
                <td><strong>{task.title}</strong>{task.expected_output && <><br /><span className="table-muted">Output: {task.expected_output}</span></>}</td>
                <td><span className={`status-pill ${statusClass(task.status)}`}>{label(task.status)}</span></td>
                <td><span className={`status-pill ${task.priority === "critical" || task.priority === "urgent" || task.priority === "high" ? "warning" : "pending"}`}>{label(task.priority)}</span></td>
                <td>{task.owner_user_id ?? "Unassigned"}</td>
                <td>{task.project_id ? task.project_id.slice(0, 8) : "Internal"}</td>
                <td className={isOverdue(task) ? "overdue-text" : ""}>{task.due_at ? new Date(task.due_at).toLocaleString("en-IN") : "—"}</td>
                <td>
                  {!isClosed(task.status) && task.status === "in_progress" && <button className="secondary-button" type="button" disabled={saving} onClick={(event) => { event.stopPropagation(); void mutate(() => submitTask(token, task.id), "Task submitted for review."); }}>Submit</button>}
                  {task.status === "review" && <button className="secondary-button" type="button" disabled={saving} onClick={(event) => { event.stopPropagation(); void mutate(() => requestTaskRevision(token, task.id), "Revision requested."); }}>Revision</button>}
                  {task.status === "review" && <button className="primary-button" type="button" disabled={saving} onClick={(event) => { event.stopPropagation(); void mutate(() => completeTaskV1(token, task.id), "Task completed."); }}>Complete</button>}
                </td>
              </tr>
            )) : <tr><td colSpan={7}><p className="empty-state">No tasks match this view.</p></td></tr>}
          </tbody>
        </table>
      </div>

      {selected && <aside className="detail-panel">
        <div className="module-header"><div><p className="eyebrow">TASK RECORD</p><h3>{selected.title}</h3><p className="module-subtitle">{label(selected.status)} · {label(selected.priority)}</p></div><button className="secondary-button" type="button" onClick={() => setSelectedTaskId(null)}>Close</button></div>
        <div className="detail-grid">
          <div><span>Status</span><strong>{label(selected.status)}</strong></div>
          <div><span>Priority</span><strong>{label(selected.priority)}</strong></div>
          <div><span>Owner</span><strong>{selected.owner_user_id ?? "Unassigned"}</strong></div>
          <div><span>Project</span><strong>{selected.project_id ?? "Internal"}</strong></div>
          <div><span>Milestone</span><strong>{selected.milestone_id ?? "—"}</strong></div>
          <div><span>Estimated Hours</span><strong>{selected.estimated_hours ?? "—"}</strong></div>
          <div><span>Start</span><strong>{selected.start_at ? new Date(selected.start_at).toLocaleString("en-IN") : "—"}</strong></div>
          <div><span>Due</span><strong>{selected.due_at ? new Date(selected.due_at).toLocaleString("en-IN") : "—"}</strong></div>
        </div>
        {selected.description && <div className="record-notes"><span>Description</span><p>{selected.description}</p></div>}
        {selected.expected_output && <div className="record-notes"><span>Expected Output</span><p>{selected.expected_output}</p></div>}
        {selected.founder_notes && <div className="record-notes"><span>Founder Notes</span><p>{selected.founder_notes}</p></div>}

        <div className="record-notes"><span>Checklist</span>
          {checklist.map((item) => <div className="checklist-item" key={item.id}><button className="secondary-button" type="button" disabled={saving} onClick={() => void updateChecklistV1(token, selected.id, item.id, { is_completed: !item.is_completed }).then((updated) => setChecklist((current) => current.map((entry) => entry.id === updated.id ? updated : entry))).catch((err) => setError((err as Error).message))}>{item.is_completed ? "✓" : "○"}</button><span>{item.title}</span></div>)}
          <div className="inline-form"><input value={newChecklistTitle} onChange={(event) => setNewChecklistTitle(event.target.value)} placeholder="Add checklist item" onKeyDown={(event) => { if (event.key === "Enter") void addChecklist(); }} /><button className="secondary-button" type="button" disabled={saving || !newChecklistTitle.trim()} onClick={() => void addChecklist()}>Add</button></div>
        </div>

        <div className="record-notes"><span>Blockers</span>
          {blockers.map((blocker) => <div className="checklist-item" key={blocker.id}><span><strong>{blocker.status}</strong> · {blocker.blocker}</span>{blocker.status === "open" && <button className="secondary-button" type="button" disabled={saving} onClick={() => void resolveBlockerV1(token, selected.id, blocker.id).then((updated) => setBlockers((current) => current.map((entry) => entry.id === updated.id ? updated : entry))).catch((err) => setError((err as Error).message))}>Resolve</button>}</div>)}
          <div className="inline-form"><input value={newBlocker} onChange={(event) => setNewBlocker(event.target.value)} placeholder="Blocker" /><input value={newBlockerAction} onChange={(event) => setNewBlockerAction(event.target.value)} placeholder="Required action" /><button className="secondary-button" type="button" disabled={saving || !newBlocker.trim() || !newBlockerAction.trim()} onClick={() => void addBlocker()}>Block Task</button></div>
        </div>

        <div className="inline-form">
          {selected.status === "backlog" && <button className="secondary-button" type="button" disabled={saving} onClick={() => void mutate(() => updateTaskV1(token, selected.id, { status: "ready" }), "Task moved to Ready.")}>Ready</button>}
          {selected.status === "ready" && <button className="secondary-button" type="button" disabled={saving} onClick={() => void mutate(() => updateTaskV1(token, selected.id, { status: "in_progress" }), "Task started.")}>Start</button>}
          {selected.status === "revision" && <button className="secondary-button" type="button" disabled={saving} onClick={() => void mutate(() => updateTaskV1(token, selected.id, { status: "in_progress" }), "Task returned to In Progress.")}>Resume</button>}
        </div>
      </aside>}
    </section>
  );
}

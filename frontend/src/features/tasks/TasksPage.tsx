import { useEffect, useMemo, useState } from "react";

import {
  completeTask,
  createTask,
  createTaskChecklistItem,
  listClients,
  listTaskChecklist,
  listTasks,
  type ChecklistRecord,
  type ClientRecord,
  type TaskRecord,
} from "../../services/api";

const statuses = ["backlog", "to_do", "in_progress", "blocked", "review", "done", "cancelled"];
const priorities = ["low", "medium", "high", "urgent"];

function label(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusClass(status: string): string {
  if (status === "done") return "active";
  if (status === "blocked" || status === "cancelled") return "muted";
  if (status === "review" || status === "in_progress") return "warning";
  return "pending";
}

function isOverdue(task: TaskRecord): boolean {
  return Boolean(task.due_at && !["done", "cancelled"].includes(task.status) && new Date(task.due_at).getTime() < Date.now());
}

export default function TasksPage({ token }: { token: string }) {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [checklist, setChecklist] = useState<ChecklistRecord[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newChecklistTitle, setNewChecklistTitle] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [taskData, clientData] = await Promise.all([listTasks(token), listClients(token)]);
      setTasks(taskData);
      setClients(clientData);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [token]);

  const selected = tasks.find((task) => task.id === selectedTaskId) ?? null;
  useEffect(() => {
    if (!selected) { setChecklist([]); return; }
    void listTaskChecklist(token, selected.id).then(setChecklist).catch((err) => setError((err as Error).message));
  }, [selectedTaskId, token]);

  const filteredTasks = useMemo(() => filter === "all" ? tasks : tasks.filter((task) => task.status === filter), [filter, tasks]);
  const overdue = tasks.filter(isOverdue).length;
  const open = tasks.filter((task) => !["done", "cancelled"].includes(task.status)).length;
  const review = tasks.filter((task) => task.status === "review").length;
  const clientName = (clientId: string | null) => clients.find((client) => client.id === clientId)?.name ?? "Internal";

  const create = async () => {
    if (!newTaskTitle.trim()) return;
    setSaving(true); setError(""); setSuccess("");
    try {
      const task = await createTask(token, { title: newTaskTitle.trim(), priority: "medium", status: "to_do" });
      setTasks((current) => [task, ...current]);
      setNewTaskTitle(""); setSelectedTaskId(task.id); setSuccess("Task created.");
    } catch (err) { setError((err as Error).message); }
    finally { setSaving(false); }
  };

  const finish = async (taskId: string) => {
    setSaving(true); setError(""); setSuccess("");
    try {
      const task = await completeTask(token, taskId);
      setTasks((current) => current.map((item) => item.id === task.id ? task : item));
      setSuccess("Task completed.");
    } catch (err) { setError((err as Error).message); }
    finally { setSaving(false); }
  };

  const addChecklist = async () => {
    if (!selected || !newChecklistTitle.trim()) return;
    setSaving(true); setError("");
    try {
      const item = await createTaskChecklistItem(token, selected.id, newChecklistTitle.trim());
      setChecklist((current) => [...current, item]); setNewChecklistTitle("");
    } catch (err) { setError((err as Error).message); }
    finally { setSaving(false); }
  };

  if (loading) return <section className="module-panel"><p>Loading tasks…</p></section>;

  return (
    <section className="module-panel tasks-page">
      <div className="module-header">
        <div><p className="eyebrow">DELIVERY OPERATIONS</p><h2>Tasks</h2><p className="module-subtitle">Founder-level work queue across internal and client delivery</p></div>
      </div>

      {error && <p className="form-error">{error}</p>}
      {success && <p className="success-message">{success}</p>}

      <div className="stats-grid">
        <div className="stat-card"><span>Total</span><strong>{tasks.length}</strong></div>
        <div className="stat-card"><span>Open</span><strong>{open}</strong></div>
        <div className="stat-card"><span>Review</span><strong>{review}</strong></div>
        <div className="stat-card"><span>Overdue</span><strong>{overdue}</strong></div>
      </div>

      <div className="module-toolbar">
        <div className="filter-row">
          <button className={filter === "all" ? "primary-button" : "secondary-button"} type="button" onClick={() => setFilter("all")}>All</button>
          {statuses.map((status) => <button key={status} className={filter === status ? "primary-button" : "secondary-button"} type="button" onClick={() => setFilter(status)}>{label(status)}</button>)}
        </div>
        <div className="inline-form">
          <input value={newTaskTitle} onChange={(event) => setNewTaskTitle(event.target.value)} placeholder="New task title" onKeyDown={(event) => { if (event.key === "Enter") void create(); }} />
          <button className="primary-button" type="button" disabled={saving || !newTaskTitle.trim()} onClick={() => void create()}>Create task</button>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead><tr><th>Task</th><th>Status</th><th>Priority</th><th>Client</th><th>Due</th><th>Action</th></tr></thead>
          <tbody>
            {filteredTasks.length ? filteredTasks.map((task) => (
              <tr key={task.id} className="clickable-row" onClick={() => setSelectedTaskId(task.id)}>
                <td><strong>{task.title}</strong>{task.description && <><br /><span className="table-muted">{task.description}</span></>}</td>
                <td><span className={`status-pill ${statusClass(task.status)}`}>{label(task.status)}</span></td>
                <td><span className={`status-pill ${task.priority === "urgent" || task.priority === "high" ? "warning" : "pending"}`}>{label(task.priority)}</span></td>
                <td>{clientName(task.client_id)}</td>
                <td className={isOverdue(task) ? "overdue-text" : ""}>{task.due_at ? new Date(task.due_at).toLocaleString("en-IN") : "—"}</td>
                <td>{!["done", "cancelled"].includes(task.status) ? <button className="secondary-button" type="button" disabled={saving} onClick={(event) => { event.stopPropagation(); void finish(task.id); }}>Complete</button> : <span className="table-muted">Closed</span>}</td>
              </tr>
            )) : <tr><td colSpan={6}><p className="empty-state">No tasks match this view.</p></td></tr>}
          </tbody>
        </table>
      </div>

      {selected && <aside className="detail-panel">
        <div className="module-header">
          <div><p className="eyebrow">TASK RECORD</p><h3>{selected.title}</h3><p className="module-subtitle">{label(selected.status)} · {label(selected.priority)}</p></div>
          <button className="secondary-button" type="button" onClick={() => setSelectedTaskId(null)}>Close</button>
        </div>
        <div className="detail-grid">
          <div><span>Status</span><strong>{label(selected.status)}</strong></div>
          <div><span>Priority</span><strong>{label(selected.priority)}</strong></div>
          <div><span>Owner</span><strong>{selected.owner_user_id ?? "Unassigned"}</strong></div>
          <div><span>Client</span><strong>{clientName(selected.client_id)}</strong></div>
          <div><span>Due</span><strong>{selected.due_at ? new Date(selected.due_at).toLocaleString("en-IN") : "No due date"}</strong></div>
          <div><span>Created</span><strong>{new Date(selected.created_at).toLocaleDateString("en-IN")}</strong></div>
        </div>
        {selected.description && <div className="record-notes"><span>Description</span><p>{selected.description}</p></div>}
        {selected.notes && <div className="record-notes"><span>Notes</span><p>{selected.notes}</p></div>}

        <div className="record-notes">
          <span>Checklist</span>
          {checklist.map((item) => <div className="checklist-item" key={item.id}><span>{item.is_completed ? "✓" : "○"} {item.title}</span></div>)}
          <div className="inline-form"><input value={newChecklistTitle} onChange={(event) => setNewChecklistTitle(event.target.value)} placeholder="Add checklist item" onKeyDown={(event) => { if (event.key === "Enter") void addChecklist(); }} /><button className="secondary-button" type="button" disabled={saving || !newChecklistTitle.trim()} onClick={() => void addChecklist()}>Add</button></div>
        </div>
      </aside>}
    </section>
  );
}

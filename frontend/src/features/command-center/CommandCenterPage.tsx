import { useEffect, useState } from "react";

import { approveSalesRequirement, createFounderAction, getCommandCenter, updateFounderAction, type CommandCenterResponse } from "../../services/api";

function formatDate(value: string | null): string {
  if (!value) return "No date";
  return new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function money(value: number): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

function TaskList({ items, empty }: { items: CommandCenterResponse["priorities"]; empty: string }) {
  if (!items.length) return <div className="empty-state">{empty}</div>;
  return <div className="activity-list">{items.map((item) => <article className="activity-item" key={item.id}><div><strong>{item.title}</strong><p>{item.status.replaceAll("_", " ")} · {item.priority}</p></div><time>{formatDate(item.due_at)}</time></article>)}</div>;
}

export default function CommandCenterPage({ token }: { token: string }) {
  const [data, setData] = useState<CommandCenterResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionTitle, setActionTitle] = useState("");
  const [actionDescription, setActionDescription] = useState("");
  const [actionDueDate, setActionDueDate] = useState("");
  const [actionPriority, setActionPriority] = useState("medium");
  const [savingAction, setSavingAction] = useState(false);
  const [actionMessage, setActionMessage] = useState("");

  const reload = () => {
    setLoading(true);
    getCommandCenter(token)
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    getCommandCenter(token)
      .then((result) => { if (active) setData(result); })
      .catch((err: Error) => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  async function approveRequirement(requirementId: string) {
    setActionMessage("");
    try {
      await approveSalesRequirement(token, requirementId);
      setActionMessage("Requirement approved successfully.");
      reload();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Approval failed.");
    }
  }

  async function completeFounderAction(actionId: string) {
    setActionMessage("");
    try {
      await updateFounderAction(token, actionId, { status: "done" });
      setActionMessage("Founder action closed.");
      reload();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Action update failed.");
    }
  }

  async function saveFounderAction() {
    if (!actionTitle.trim() || !actionDescription.trim()) {
      setActionMessage("Action title and required action are required.");
      return;
    }
    setSavingAction(true);
    setActionMessage("");
    try {
      await createFounderAction(token, {
        category: "founder",
        source_module: "command_center",
        priority: actionPriority,
        description: actionTitle.trim(),
        required_action: actionDescription.trim(),
        owner_user_id: data?.user.id ?? "",
        ...(actionDueDate ? { due_date: actionDueDate } : {}),
      });
      setActionTitle("");
      setActionDescription("");
      setActionDueDate("");
      setActionPriority("medium");
      setActionMessage("Founder action created.");
      reload();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : "Founder action creation failed.");
    } finally {
      setSavingAction(false);
    }
  }

  if (loading && !data) return <section className="module-panel"><p>Loading founder command center…</p></section>;
  if (error && !data) return <section className="module-panel error-state"><p>{error}</p></section>;
  if (!data) return null;

  const health = data.business_health;

  return (
    <section className="command-center-page">
      <section className="welcome-card">
        <div><p className="eyebrow">FOUNDER OPERATING CONSOLE</p><h2>Good to see you, {data.user.full_name}</h2><p className="subtitle">See clearly → Decide deliberately → Act → Follow up → Close.</p></div>
        <div className="role-badge">{data.user.roles[0] ?? "Founder"}</div>
      </section>

      <section className="console-grid command-metrics" aria-label="Founder business health">
        <article><span>ACTIVE CLIENTS</span><strong>{health.active_clients ?? 0}</strong><p>Current relationships</p></article>
        <article><span>OPEN PIPELINE</span><strong>{health.open_opportunities ?? 0}</strong><p>{money(health.pipeline_value ?? 0)} potential value</p></article>
        <article><span>OVERDUE</span><strong>{health.overdue_tasks ?? 0}</strong><p>Tasks needing action</p></article>
        <article><span>BLOCKED</span><strong>{health.blocked_tasks ?? 0}</strong><p>Work requiring attention</p></article>
      </section>

      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">TODAY</p><h3>Today’s priorities</h3></div><span className="section-count">{data.counts.today_priorities ?? 0}</span></div>
        <TaskList items={data.priorities} empty="No priority work is due today." />
      </section>

      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">FOLLOW-UPS</p><h3>Sales follow-up queue</h3></div><span className="section-count">{data.counts.follow_ups ?? 0}</span></div>
        {!data.follow_ups.length ? <div className="empty-state">No open sales follow-ups.</div> : <div className="activity-list">{data.follow_ups.map((item) => <article className="activity-item" key={item.id}><div><strong>{item.name}</strong><p>{item.stage.replaceAll("_", " ")}{item.estimated_value != null ? ` · ${money(item.estimated_value)}` : ""}</p></div><time>{formatDate(item.updated_at)}</time></article>)}</div>}
      </section>

      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">APPROVALS</p><h3>Founder approval queue</h3></div><span className="section-count">{data.counts.approvals ?? 0}</span></div>
        {!data.approvals.length ? <div className="empty-state">No pending requirement approvals.</div> : <div className="activity-list">{data.approvals.map((item) => <article className="activity-item" key={item.id}><div><strong>{item.type.toUpperCase()}</strong><p>{item.description}</p></div><button type="button" className="role-badge" onClick={() => approveRequirement(item.id)}>Approve</button></article>)}</div>}
      </section>

      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">FOUNDER ACTIONS</p><h3>Tracked decisions and follow-ups</h3></div><span className="section-count">{data.counts.founder_actions ?? 0}</span></div>
        {!data.founder_actions.length ? <div className="empty-state">No open founder actions.</div> : <div className="activity-list">{data.founder_actions.map((item) => <article className="activity-item" key={item.id}><div><strong>{item.description}</strong><p>{item.priority} · {item.required_action}{item.due_date ? ` · Due ${item.due_date}` : ""}</p></div><button type="button" className="role-badge" onClick={() => completeFounderAction(item.id)}>Close</button></article>)}</div>}
      </section>

      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">DEADLINES</p><h3>Upcoming deadlines</h3></div><span className="section-count">{data.counts.deadlines ?? 0}</span></div>
        <TaskList items={data.deadlines} empty="No deadlines in the next 7 days." />
      </section>

      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">ALERTS</p><h3>Needs attention now</h3></div><span className="section-count">{data.counts.alerts ?? 0}</span></div>
        <TaskList items={data.alerts} empty="No overdue or blocked work." />
      </section>

      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">QUICK ACTIONS</p><h3>Founder actions</h3></div></div>
        <div className="console-grid">
          <article className="dashboard-card"><strong>Create founder action</strong><input aria-label="Action title" value={actionTitle} onChange={(event) => setActionTitle(event.target.value)} placeholder="What needs to be done?" /><textarea aria-label="Required action" value={actionDescription} onChange={(event) => setActionDescription(event.target.value)} placeholder="Required action / decision" /><div className="console-grid"><select aria-label="Priority" value={actionPriority} onChange={(event) => setActionPriority(event.target.value)}><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select><input aria-label="Due date" type="date" value={actionDueDate} onChange={(event) => setActionDueDate(event.target.value)} /></div><button type="button" onClick={saveFounderAction} disabled={savingAction}>{savingAction ? "Saving…" : "Create action"}</button></article>
          <article className="dashboard-card"><strong>Operational shortcuts</strong><p>Create prospects, opportunities and tasks from their dedicated modules without duplicate dashboard records.</p></article>
        </div>
        {actionMessage ? <p className="subtitle">{actionMessage}</p> : null}
      </section>

      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">SYSTEM ACTIVITY</p><h3>Recent activity</h3></div><span className="section-count">{data.recent_activity.length}</span></div>
        {!data.recent_activity.length ? <div className="empty-state">No audit activity yet.</div> : <div className="activity-list">{data.recent_activity.map((item) => <article className="activity-item" key={item.id}><div><strong>{item.action}</strong><p>{item.entity_type}{item.entity_id ? ` · ${item.entity_id}` : ""}</p></div><time>{formatDate(item.created_at)}</time></article>)}</div>}
      </section>
    </section>
  );
}

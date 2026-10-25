import { useEffect, useState } from "react";

import { getCommandCenter, type CommandCenterResponse } from "./commandCenterApi";

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

  useEffect(() => {
    let active = true;
    setLoading(true);
    getCommandCenter(token)
      .then((result) => { if (active) setData(result); })
      .catch((err: Error) => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  if (loading) return <section className="module-panel"><p>Loading founder command center…</p></section>;
  if (error) return <section className="module-panel error-state"><p>{error}</p></section>;
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
        {!data.approvals.length ? <div className="empty-state">No pending requirement approvals.</div> : <div className="activity-list">{data.approvals.map((item) => <article className="activity-item" key={item.id}><div><strong>{item.type.toUpperCase()}</strong><p>{item.description}</p></div><span className="role-badge">Review</span></article>)}</div>}
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
        <div className="console-grid">{data.quick_actions.map((action) => <article className="attention-row" key={action}><strong>+</strong><span>{action}</span></article>)}</div>
      </section>

      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">SYSTEM ACTIVITY</p><h3>Recent activity</h3></div><span className="section-count">{data.recent_activity.length}</span></div>
        {!data.recent_activity.length ? <div className="empty-state">No audit activity yet.</div> : <div className="activity-list">{data.recent_activity.map((item) => <article className="activity-item" key={item.id}><div><strong>{item.action}</strong><p>{item.entity_type}{item.entity_id ? ` · ${item.entity_id}` : ""}</p></div><time>{formatDate(item.created_at)}</time></article>)}</div>}
      </section>
    </section>
  );
}

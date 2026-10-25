import { useEffect, useState } from "react";

import { getCommandCenter, type CommandCenterResponse } from "../../services/api";

function formatActivityTime(value: string): string {
  return new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
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

  if (loading) return <section className="module-panel"><p>Loading command center…</p></section>;
  if (error) return <section className="module-panel error-state"><p>{error}</p></section>;
  if (!data) return null;

  return (
    <section className="command-center-page">
      <section className="welcome-card">
        <div><p className="eyebrow">FOUNDER OPERATING CONSOLE</p><h2>Good to see you, {data.user.full_name}</h2><p className="subtitle">{data.user.email}</p></div>
        <div className="role-badge">{data.user.roles[0] ?? "User"}</div>
      </section>

      <section className="console-grid command-metrics" aria-label="Live company foundation metrics">
        <article><span>USERS</span><strong>{data.counts.users}</strong><p>{data.counts.active_users} active</p></article>
        <article><span>ROLES</span><strong>{data.counts.roles}</strong><p>Active roles</p></article>
        <article><span>PERMISSIONS</span><strong>{data.counts.permissions}</strong><p>Defined permissions</p></article>
        <article><span>ATTENTION</span><strong>{data.attention.inactive_users}</strong><p>Inactive users</p></article>
      </section>

      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">ATTENTION QUEUE</p><h3>What needs attention</h3></div></div>
        {data.attention.inactive_users > 0 ? <div className="attention-row"><strong>{data.attention.inactive_users}</strong><span>inactive company user{data.attention.inactive_users === 1 ? "" : "s"}</span></div> : <div className="empty-state">No inactive users requiring attention.</div>}
      </section>

      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">ACTIVITY</p><h3>Recent system activity</h3></div><span className="section-count">{data.attention.recent_audit_events}</span></div>
        {data.recent_activity.length === 0 ? <div className="empty-state">No audit activity yet.</div> : <div className="activity-list">{data.recent_activity.map((item) => <article className="activity-item" key={item.id}><div><strong>{item.action}</strong><p>{item.entity_type}{item.entity_id ? ` · ${item.entity_id}` : ""}</p></div><time>{formatActivityTime(item.created_at)}</time></article>)}</div>}
      </section>
    </section>
  );
}

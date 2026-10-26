import { useEffect, useState } from "react";
import { financeApi, FinanceDashboard, PaymentMilestone } from "./financeApi";

const money = (value: number) => `₹${Number(value ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

export default function FinancePaymentsPage() {
  const [dashboard, setDashboard] = useState<FinanceDashboard | null>(null);
  const [milestones, setMilestones] = useState<PaymentMilestone[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([financeApi.dashboard(), financeApi.milestones()])
      .then(([d, m]) => { setDashboard(d); setMilestones(m); })
      .catch((e) => setError(e instanceof Error ? e.message : "Unable to load finance data"));
  }, []);

  if (error) return <section><h1>Finance & Payments</h1><p>{error}</p></section>;
  if (!dashboard) return <section><h1>Finance & Payments</h1><p>Loading…</p></section>;

  return (
    <section>
      <header><h1>Finance & Payments</h1><p>Founder financial operating view.</p></header>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16 }}>
        <article><strong>Revenue</strong><div>{money(dashboard.revenue)}</div></article>
        <article><strong>Expenses</strong><div>{money(dashboard.expenses)}</div></article>
        <article><strong>Outstanding</strong><div>{money(dashboard.outstanding)}</div></article>
        <article><strong>Freelancer Payments</strong><div>{money(dashboard.freelancer_payments)}</div></article>
        <article><strong>Project Profitability</strong><div>{money(dashboard.project_profitability)}</div></article>
      </div>
      <h2>Payment Milestones</h2>
      {milestones.length === 0 ? <p>No payment milestones recorded.</p> : <ul>{milestones.map((m) => <li key={m.id}>{m.name} — {money(Number(m.paid_amount))} / {money(Number(m.amount))} — {m.status}</li>)}</ul>}
    </section>
  );
}

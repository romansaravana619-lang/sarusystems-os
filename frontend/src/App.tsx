import AuthGate from "./features/auth/AuthGate";
import type { MeResponse } from "./services/api";

function FounderConsole({ user, signOut }: { user: MeResponse; signOut: () => Promise<void> }) {
  return (
    <main className="console-shell">
      <header className="console-header">
        <div>
          <p className="eyebrow">SARU SYSTEMS</p>
          <h1>Founder Command Center</h1>
        </div>
        <button className="secondary-button" type="button" onClick={() => void signOut()}>
          Sign out
        </button>
      </header>

      <section className="welcome-card">
        <div>
          <p className="eyebrow">AUTHENTICATED</p>
          <h2>Welcome, {user.full_name}</h2>
          <p className="subtitle">{user.email}</p>
        </div>
        <div className="role-badge">{user.roles[0] ?? "User"}</div>
      </section>

      <section className="console-grid" aria-label="Command center modules">
        <article><span>01</span><h3>Today</h3><p>Attention queue will live here.</p></article>
        <article><span>02</span><h3>Pipeline</h3><p>CRM and sales visibility comes next.</p></article>
        <article><span>03</span><h3>Delivery</h3><p>Projects and tasks will connect here.</p></article>
        <article><span>04</span><h3>Finance</h3><p>Commercial attention will be surfaced here.</p></article>
      </section>
    </main>
  );
}

function App() {
  return (
    <AuthGate>
      {(user, signOut) => <FounderConsole user={user} signOut={signOut} />}
    </AuthGate>
  );
}

export default App;

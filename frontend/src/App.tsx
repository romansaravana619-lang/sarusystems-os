import { useState } from "react";

import AuthGate from "./features/auth/AuthGate";
import AuditPage from "./features/audit/AuditPage";
import RolesPage from "./features/roles/RolesPage";
import UsersPage from "./features/users/UsersPage";
import type { MeResponse } from "./services/api";

function FounderConsole({ user, token, signOut }: { user: MeResponse; token: string; signOut: () => Promise<void> }) {
  const [activeModule, setActiveModule] = useState<"command" | "users" | "roles" | "audit">("command");
  const canManageUsers = user.permissions.includes("users.view");
  const canManageRoles = user.permissions.includes("roles.view");
  const canViewAudit = user.permissions.includes("audit.view");

  const go = (module: typeof activeModule) => setActiveModule(activeModule === module ? "command" : module);

  return (
    <main className="console-shell">
      <header className="console-header">
        <div><p className="eyebrow">SARU SYSTEMS</p><h1>Founder Command Center</h1></div>
        <div className="header-actions">
          {canManageUsers && <button className="secondary-button" type="button" onClick={() => go("users")}>{activeModule === "users" ? "Command Center" : "Users"}</button>}
          {canManageRoles && <button className="secondary-button" type="button" onClick={() => go("roles")}>{activeModule === "roles" ? "Command Center" : "Roles & Permissions"}</button>}
          {canViewAudit && <button className="secondary-button" type="button" onClick={() => go("audit")}>{activeModule === "audit" ? "Command Center" : "Audit"}</button>}
          <button className="secondary-button" type="button" onClick={() => void signOut()}>Sign out</button>
        </div>
      </header>

      {activeModule === "users" && canManageUsers ? <UsersPage token={token} companyId={user.company_id} /> : activeModule === "roles" && canManageRoles ? <RolesPage token={token} /> : activeModule === "audit" && canViewAudit ? <AuditPage token={token} /> : (
        <>
          <section className="welcome-card">
            <div><p className="eyebrow">AUTHENTICATED</p><h2>Welcome, {user.full_name}</h2><p className="subtitle">{user.email}</p></div>
            <div className="role-badge">{user.roles[0] ?? "User"}</div>
          </section>
          <section className="console-grid" aria-label="Command center modules">
            <article><span>01</span><h3>Today</h3><p>Attention queue will live here.</p></article>
            <article><span>02</span><h3>Pipeline</h3><p>CRM and sales visibility comes next.</p></article>
            <article><span>03</span><h3>Delivery</h3><p>Projects and tasks will connect here.</p></article>
            <article><span>04</span><h3>Finance</h3><p>Commercial attention will be surfaced here.</p></article>
          </section>
        </>
      )}
    </main>
  );
}

function App() { return <AuthGate>{(user, token, signOut) => <FounderConsole user={user} token={token} signOut={signOut} />}</AuthGate>; }

export default App;

import { useState } from "react";

import AuthGate from "./features/auth/AuthGate";
import AuditPage from "./features/audit/AuditPage";
import ClientsPage from "./features/clients/ClientsPage";
import CommandCenterPage from "./features/command-center/CommandCenterPage";
import CRMPage from "./features/crm/CRMPage";
import RolesPage from "./features/roles/RolesPage";
import TasksPage from "./features/tasks/TasksPage";
import UsersPage from "./features/users/UsersPage";
import type { MeResponse } from "./services/api";

type Module = "command" | "crm" | "clients" | "tasks" | "users" | "roles" | "audit";

function FounderConsole({ user, token, signOut }: { user: MeResponse; token: string; signOut: () => Promise<void> }) {
  const [activeModule, setActiveModule] = useState<Module>("command");
  const canViewCommandCenter = user.permissions.includes("command_center.view");
  const canViewCRM = user.permissions.includes("crm.prospects.view");
  const canViewClients = user.permissions.includes("clients.view");
  const canViewTasks = user.permissions.includes("tasks.view");
  const canManageUsers = user.permissions.includes("users.view");
  const canManageRoles = user.permissions.includes("roles.view");
  const canViewAudit = user.permissions.includes("audit.view");

  const go = (module: Module) => setActiveModule(module === activeModule ? "command" : module);

  return (
    <main className="console-shell">
      <header className="console-header">
        <div><p className="eyebrow">SARU SYSTEMS</p><h1>Founder Command Center</h1></div>
        <div className="header-actions">
          {canViewCommandCenter && <button className="secondary-button" type="button" onClick={() => go("command")}>Command Center</button>}
          {canViewCRM && <button className="secondary-button" type="button" onClick={() => go("crm")}>CRM</button>}
          {canViewClients && <button className="secondary-button" type="button" onClick={() => go("clients")}>Clients</button>}
          {canViewTasks && <button className="secondary-button" type="button" onClick={() => go("tasks")}>Tasks</button>}
          {canManageUsers && <button className="secondary-button" type="button" onClick={() => go("users")}>Users</button>}
          {canManageRoles && <button className="secondary-button" type="button" onClick={() => go("roles")}>Roles & Permissions</button>}
          {canViewAudit && <button className="secondary-button" type="button" onClick={() => go("audit")}>Audit</button>}
          <button className="secondary-button" type="button" onClick={() => void signOut()}>Sign out</button>
        </div>
      </header>

      {activeModule === "crm" && canViewCRM ? <CRMPage token={token} /> : activeModule === "clients" && canViewClients ? <ClientsPage token={token} /> : activeModule === "tasks" && canViewTasks ? <TasksPage token={token} /> : activeModule === "users" && canManageUsers ? <UsersPage token={token} companyId={user.company_id} /> : activeModule === "roles" && canManageRoles ? <RolesPage token={token} /> : activeModule === "audit" && canViewAudit ? <AuditPage token={token} /> : canViewCommandCenter ? <CommandCenterPage token={token} /> : (
        <section className="module-panel"><p>You do not have permission to view the Founder Command Center.</p></section>
      )}
    </main>
  );
}

function App() { return <AuthGate>{(user, token, signOut) => <FounderConsole user={user} token={token} signOut={signOut} />}</AuthGate>; }

export default App;

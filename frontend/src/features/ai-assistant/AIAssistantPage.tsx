import { useEffect, useState } from "react";

import {
  confirmAIAssistantWrite,
  listAIAssistantTools,
  previewAIAssistantWrite,
  runAIAssistantRead,
  type AIAssistantResponse,
  type AIAssistantTool,
} from "./assistantApi";

type Props = { token: string };

function displayValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function AIAssistantPage({ token }: Props) {
  const [tools, setTools] = useState<AIAssistantTool[]>([]);
  const [writeTools, setWriteTools] = useState<AIAssistantTool[]>([]);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskPriority, setTaskPriority] = useState("medium");
  const [writePreview, setWritePreview] = useState<AIAssistantResponse | null>(null);
  const [writeLoading, setWriteLoading] = useState(false);
  const [otherWritePreview, setOtherWritePreview] = useState<AIAssistantResponse | null>(null);
  const [otherWriteInvocation, setOtherWriteInvocation] = useState<{ message: string; tool_name: string; input: Record<string, unknown> } | null>(null);
  const [otherWriteLoading, setOtherWriteLoading] = useState(false);
  const [followupTargetType, setFollowupTargetType] = useState("prospect");
  const [followupTargetId, setFollowupTargetId] = useState("");
  const [followupTitle, setFollowupTitle] = useState("");
  const [followupDueAt, setFollowupDueAt] = useState("");
  const [calendarTargetType, setCalendarTargetType] = useState("prospect");
  const [calendarTargetId, setCalendarTargetId] = useState("");
  const [calendarTitle, setCalendarTitle] = useState("");
  const [calendarStartAt, setCalendarStartAt] = useState("");
  const [calendarEndAt, setCalendarEndAt] = useState("");
  const [reminderTitle, setReminderTitle] = useState("");
  const [reminderStartAt, setReminderStartAt] = useState("");
  const [reminderEndAt, setReminderEndAt] = useState("");
  const [selectedTool, setSelectedTool] = useState("global_search");
  const [query, setQuery] = useState("");
  const [entityType, setEntityType] = useState("");
  const [response, setResponse] = useState<AIAssistantResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [toolsLoading, setToolsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    listAIAssistantTools(token)
      .then((result) => {
        if (!active) return;
        setTools(result.tools);
        setWriteTools(result.write_tools ?? []);
        if (result.tools.length) {
          setSelectedTool((current) => result.tools.some((tool) => tool.name === current) ? current : result.tools[0].name);
        }
      })
      .catch((err: Error) => { if (active) setError(err.message); })
      .finally(() => { if (active) setToolsLoading(false); });
    async function previewOtherWrite(toolName: string, message: string, input: Record<string, unknown>) {
    setOtherWriteLoading(true);
    setError("");
    setOtherWritePreview(null);
    const invocation = { message, tool_name: toolName, input };
    try {
      const result = await previewAIAssistantWrite(token, invocation);
      setOtherWriteInvocation(invocation);
      setOtherWritePreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The action preview failed.");
    } finally {
      setOtherWriteLoading(false);
    }
  }

  async function confirmOtherWrite() {
    const previewId = otherWritePreview?.data.preview_id;
    if (!previewId || !otherWriteInvocation) return;
    setOtherWriteLoading(true);
    setError("");
    try {
      const result = await confirmAIAssistantWrite(token, { ...otherWriteInvocation, preview_id: previewId });
      setOtherWritePreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The action could not be confirmed.");
    } finally {
      setOtherWriteLoading(false);
    }
  }

  function toIso(value: string): string {
    const parsed = new Date(value);
    if (!value || Number.isNaN(parsed.getTime())) throw new Error("Enter a valid date and time.");
    return parsed.toISOString();
  }
  return () => { active = false; };
  }, [token]);

  async function submit(message?: string, toolName = selectedTool) {
    const selected = tools.find((tool) => tool.name === toolName);
    const text = (message ?? query).trim() || (toolName === "global_search" ? "" : selected?.purpose ?? "");
    if (!text) {
      setError("Enter a record name or keyword to search.");
      return;
    }
    setLoading(true);
    setError("");
    setResponse(null);
    try {
      const idFields: Record<string, string> = {
        get_client_summary: "client_id",
        get_project_summary: "project_id",
        get_project_milestones: "project_id",
        get_opportunity_summary: "opportunity_id",
      };
      const idField = idFields[toolName];
      const input: Record<string, unknown> = toolName === "global_search"
        ? { query: text, ...(entityType ? { entity_types: [entityType] } : {}) }
        : toolName === "get_tasks" && query.trim()
          ? { status: query.trim() }
          : idField && query.trim()
            ? { [idField]: query.trim() }
            : {};
      const result = await runAIAssistantRead(token, {
        message: text,
        tool_name: toolName,
        input,
      });
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The assistant request failed.");
    } finally {
      setLoading(false);
    }
  }

  async function previewTaskCreation() {
    if (!taskTitle.trim()) {
      setError("Enter a task title before previewing.");
      return;
    }
    const payload = { title: taskTitle.trim(), priority: taskPriority };
    const message = `Create a task: ${taskTitle.trim()}`;
    setWriteLoading(true);
    setError("");
    setWritePreview(null);
    try {
      const result = await previewAIAssistantWrite(token, {
        message,
        tool_name: "create_task",
        input: payload,
      });
      setWritePreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The task preview failed.");
    } finally {
      setWriteLoading(false);
    }
  }

  async function confirmTaskCreation() {
    const previewId = writePreview?.data.preview_id;
    if (!previewId) return;
    const payload = { title: taskTitle.trim(), priority: taskPriority };
    const message = `Create a task: ${taskTitle.trim()}`;
    setWriteLoading(true);
    setError("");
    try {
      const result = await confirmAIAssistantWrite(token, {
        message,
        tool_name: "create_task",
        input: payload,
        preview_id: previewId,
      });
      setWritePreview(result);
      if (result.response_type === "action_result") {
        setTaskTitle("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "The task could not be confirmed.");
    } finally {
      setWriteLoading(false);
    }
  }

  return (
    <section className="ai-assistant-page">
      <header className="ai-assistant-hero">
        <div>
          <p className="eyebrow">SARU SYSTEMS · INTELLIGENCE</p>
          <h2>Founder AI Assistant</h2>
          <p>Retrieve permitted company information and perform confirmed Founder actions through existing OS workflows.</p>
        </div>
        <span className="ai-runtime-status"><i /> Connected to OS</span>
      </header>

      <section className="ai-assistant-layout">
        <aside className="ai-assistant-sidebar">
          <p className="eyebrow">AVAILABLE CAPABILITIES</p>
          {toolsLoading ? <p className="ai-muted">Loading capabilities…</p> : tools.map((tool) => (
            <button
              className={selectedTool === tool.name ? "ai-tool-option active" : "ai-tool-option"}
              key={tool.name}
              type="button"
              onClick={() => { setSelectedTool(tool.name); setResponse(null); setError(""); }}
            >
              <strong>{tool.name.replaceAll("_", " ")}</strong>
              <span>{tool.purpose}</span>
            </button>
          ))}
          {!toolsLoading && !tools.length ? <p className="ai-muted">No read capabilities are available for this account.</p> : null}
          {writeTools.map((tool) => (
            <div className="ai-tool-option" key={tool.name}>
              <strong>{tool.name.replaceAll("_", " ")}</strong>
              <span>{tool.purpose}</span>
            </div>
          ))}
          <p className="ai-runtime-note">AI provider inference is not connected in this phase. Requests use registered, permission-checked OS tools.</p>
        </aside>

        <div className="ai-assistant-main">
          <div className="ai-assistant-welcome">
            <span className="ai-assistant-orb">S</span>
            <div><strong>What would you like to find?</strong><p>Choose a capability, enter your request, and the assistant will retrieve information allowed by your account.</p></div>
          </div>

          {selectedTool === "global_search" ? (
            <div className="ai-assistant-composer">
              <label htmlFor="ai-query">Search company records</label>
              <input id="ai-query" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void submit(); }} placeholder="Search clients, projects, tasks, prospects…" />
              <div className="ai-composer-row">
                <select aria-label="Record type" value={entityType} onChange={(event) => setEntityType(event.target.value)}>
                  <option value="">All record types</option>
                  {["prospect", "client", "project", "opportunity", "task", "document", "payment", "communication", "contact"].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}
                </select>
                <button className="primary-button" type="button" disabled={loading} onClick={() => void submit()}>{loading ? "Searching…" : "Search OS"}</button>
              </div>
            </div>
          ) : selectedTool === "get_tasks" ? (
            <div className="ai-assistant-composer">
              <label htmlFor="ai-query">Optional task status filter</label>
              <input id="ai-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. in_progress, blocked, ready" />
              <button className="primary-button" type="button" disabled={loading} onClick={() => void submit("Show my permitted tasks.")}>{loading ? "Loading…" : "Retrieve tasks"}</button>
            </div>
          ) : (
            <div className="ai-assistant-composer">
              <p className="ai-muted">This capability retrieves information using your existing OS permissions.</p>
              {["get_client_summary", "get_project_summary", "get_project_milestones", "get_opportunity_summary"].includes(selectedTool) ? (
                <>
                  <label htmlFor="ai-query">Record ID (UUID)</label>
                  <input id="ai-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Paste the record ID" />
                </>
              ) : null}
              <button className="primary-button" type="button" disabled={loading} onClick={() => void submit(tools.find((tool) => tool.name === selectedTool)?.purpose ?? "Run this read query.")}>{loading ? "Loading…" : "Run query"}</button>
            </div>
          )}

          {writeTools.some((tool) => tool.name === "create_task") ? (
            <section className="ai-result-panel ai-write-panel">
              <div className="ai-result-heading">
                <div><p className="eyebrow">CONFIRMATION-PROTECTED ACTION</p><h3>Create a task</h3></div>
                <span>Founder approval required</span>
              </div>
              <div className="ai-assistant-composer">
                <label htmlFor="ai-task-title">Task title</label>
                <input id="ai-task-title" value={taskTitle} onChange={(event) => { setTaskTitle(event.target.value); setWritePreview(null); }} placeholder="e.g. Follow up with the restaurant client" />
                <label htmlFor="ai-task-priority">Priority</label>
                <select id="ai-task-priority" value={taskPriority} onChange={(event) => { setTaskPriority(event.target.value); setWritePreview(null); }}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                  <option value="urgent">Urgent</option>
                </select>
                <button className="primary-button" type="button" disabled={writeLoading} onClick={() => void previewTaskCreation()}>{writeLoading ? "Preparing preview…" : "Preview task"}</button>
              </div>
              {writePreview ? (
                <div className="ai-write-confirmation">
                  <p><strong>{writePreview.summary}</strong></p>
                  <p className="ai-muted">Title: {displayValue(writePreview.data.task?.title)} · Priority: {displayValue(writePreview.data.task?.priority)}</p>
                  {writePreview.response_type === "action_preview" ? (
                    <button className="primary-button" type="button" disabled={writeLoading} onClick={() => void confirmTaskCreation()}>{writeLoading ? "Creating…" : "Confirm & create task"}</button>
                  ) : null}
                  {writePreview.response_type === "action_result" ? <p className="success-message">Task created. Audit reference: {writePreview.audit_reference ?? "—"}</p> : null}
                  {writePreview.warnings.map((warning) => <p className="ai-muted" key={warning}>{warning}</p>)}
                </div>
              ) : null}
            </section>
          ) : null}

          {writeTools.some((tool) => tool.name === "create_followup") ? (
            <section className="ai-result-panel ai-write-panel">
              <div className="ai-result-heading"><div><p className="eyebrow">CONFIRMATION-PROTECTED ACTION</p><h3>Create CRM follow-up</h3></div><span>Founder approval required</span></div>
              <div className="ai-assistant-composer">
                <label htmlFor="ai-followup-target-type">Linked record type</label>
                <select id="ai-followup-target-type" value={followupTargetType} onChange={(event) => setFollowupTargetType(event.target.value)}><option value="prospect">Prospect</option><option value="contact">Contact</option></select>
                <label htmlFor="ai-followup-target-id">Prospect / Contact ID</label>
                <input id="ai-followup-target-id" value={followupTargetId} onChange={(event) => setFollowupTargetId(event.target.value)} placeholder="Paste record UUID" />
                <label htmlFor="ai-followup-title">Follow-up title</label>
                <input id="ai-followup-title" value={followupTitle} onChange={(event) => setFollowupTitle(event.target.value)} placeholder="e.g. Call prospect about requirements" />
                <label htmlFor="ai-followup-due">Due date and time</label>
                <input id="ai-followup-due" type="datetime-local" value={followupDueAt} onChange={(event) => setFollowupDueAt(event.target.value)} />
                <button className="primary-button" type="button" disabled={otherWriteLoading} onClick={() => { try { void previewOtherWrite("create_followup", `Create follow-up: ${followupTitle}`, { target_type: followupTargetType, target_id: followupTargetId.trim(), title: followupTitle.trim(), due_at: toIso(followupDueAt) }); } catch (err) { setError(err instanceof Error ? err.message : "Enter valid follow-up details."); } }}>{otherWriteLoading ? "Preparing preview…" : "Preview follow-up"}</button>
              </div>
            </section>
          ) : null}
          {writeTools.some((tool) => tool.name === "schedule_followup") ? (
            <section className="ai-result-panel ai-write-panel">
              <div className="ai-result-heading"><div><p className="eyebrow">CONFIRMATION-PROTECTED ACTION</p><h3>Schedule follow-up</h3></div><span>Founder approval required</span></div>
              <div className="ai-assistant-composer">
                <label htmlFor="ai-calendar-target-type">Linked record type</label>
                <select id="ai-calendar-target-type" value={calendarTargetType} onChange={(event) => setCalendarTargetType(event.target.value)}><option value="prospect">Prospect</option><option value="client">Client</option></select>
                <label htmlFor="ai-calendar-target-id">Prospect / Client ID</label>
                <input id="ai-calendar-target-id" value={calendarTargetId} onChange={(event) => setCalendarTargetId(event.target.value)} placeholder="Paste record UUID" />
                <label htmlFor="ai-calendar-title">Event title</label>
                <input id="ai-calendar-title" value={calendarTitle} onChange={(event) => setCalendarTitle(event.target.value)} placeholder="e.g. Client follow-up call" />
                <label htmlFor="ai-calendar-start">Starts at</label>
                <input id="ai-calendar-start" type="datetime-local" value={calendarStartAt} onChange={(event) => setCalendarStartAt(event.target.value)} />
                <label htmlFor="ai-calendar-end">Ends at</label>
                <input id="ai-calendar-end" type="datetime-local" value={calendarEndAt} onChange={(event) => setCalendarEndAt(event.target.value)} />
                <button className="primary-button" type="button" disabled={otherWriteLoading} onClick={() => { try { void previewOtherWrite("schedule_followup", `Schedule follow-up: ${calendarTitle}`, { target_type: calendarTargetType, target_id: calendarTargetId.trim(), title: calendarTitle.trim(), scheduled_at: toIso(calendarStartAt), end_at: toIso(calendarEndAt) }); } catch (err) { setError(err instanceof Error ? err.message : "Enter valid calendar details."); } }}>{otherWriteLoading ? "Preparing preview…" : "Preview schedule"}</button>
              </div>
            </section>
          ) : null}
          {writeTools.some((tool) => tool.name === "create_founder_reminder") ? (
            <section className="ai-result-panel ai-write-panel">
              <div className="ai-result-heading"><div><p className="eyebrow">CONFIRMATION-PROTECTED ACTION</p><h3>Create Founder reminder</h3></div><span>Founder approval required</span></div>
              <div className="ai-assistant-composer">
                <label htmlFor="ai-reminder-title">Reminder title</label>
                <input id="ai-reminder-title" value={reminderTitle} onChange={(event) => setReminderTitle(event.target.value)} placeholder="e.g. Review weekly business performance" />
                <label htmlFor="ai-reminder-start">Reminder time</label>
                <input id="ai-reminder-start" type="datetime-local" value={reminderStartAt} onChange={(event) => setReminderStartAt(event.target.value)} />
                <label htmlFor="ai-reminder-end">End time</label>
                <input id="ai-reminder-end" type="datetime-local" value={reminderEndAt} onChange={(event) => setReminderEndAt(event.target.value)} />
                <button className="primary-button" type="button" disabled={otherWriteLoading} onClick={() => { try { void previewOtherWrite("create_founder_reminder", `Create Founder reminder: ${reminderTitle}`, { title: reminderTitle.trim(), remind_at: toIso(reminderStartAt), end_at: toIso(reminderEndAt) }); } catch (err) { setError(err instanceof Error ? err.message : "Enter valid reminder details."); } }}>{otherWriteLoading ? "Preparing preview…" : "Preview reminder"}</button>
              </div>
            </section>
          ) : null}
          {otherWritePreview ? (
            <section className="ai-result-panel ai-write-confirmation" aria-live="polite">
              <p><strong>{otherWritePreview.summary}</strong></p>
              <p className="ai-muted">{displayValue(otherWritePreview.data.payload)}</p>
              {otherWritePreview.response_type === "action_preview" ? <button className="primary-button" type="button" disabled={otherWriteLoading} onClick={() => void confirmOtherWrite()}>{otherWriteLoading ? "Executing…" : "Confirm & execute"}</button> : null}
              {otherWritePreview.response_type === "action_result" ? <p className="success-message">Action completed. Audit reference: {otherWritePreview.audit_reference ?? "—"}</p> : null}
              {otherWritePreview.warnings.map((warning) => <p className="ai-muted" key={warning}>{warning}</p>)}
            </section>
          ) : null}
          {error ? <p className="ai-error" role="alert">{error}</p> : null}
          {response ? (
            <section className="ai-result-panel" aria-live="polite">
              <div className="ai-result-heading"><div><p className="eyebrow">OS RESPONSE</p><h3>{response.summary}</h3></div><span>{response.data.items?.length ?? 0} results</span></div>
              {response.data.items?.length ? (
                <div className="ai-result-list">
                  {response.data.items.map((item, index) => (
                    <article className="ai-result-item" key={String(item.id ?? index)}>
                      <div><strong>{displayValue(item.title ?? item.name ?? item.description ?? "OS record")}</strong><p>{displayValue(item.subtitle ?? item.status ?? item.type)}</p></div>
                      <small>{displayValue(item.type ?? item.priority ?? "")}</small>
                    </article>
                  ))}
                </div>
              ) : <p className="ai-muted">No matching records were returned.</p>}
              <footer className="ai-result-footer">
                <span>Intent: {response.intent ?? "—"}</span>
                <span>Audit reference: {response.audit_reference ?? "—"}</span>
              </footer>
              {response.warnings.map((warning) => <p className="ai-muted" key={warning}>{warning}</p>)}
            </section>
          ) : null}
        </div>
      </section>
    </section>
  );
}

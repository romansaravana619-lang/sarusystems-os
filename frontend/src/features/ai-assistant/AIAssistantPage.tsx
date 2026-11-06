import { useEffect, useState } from "react";

import { listAIAssistantTools, runAIAssistantRead, type AIAssistantResponse, type AIAssistantTool } from "./assistantApi";

type Props = { token: string };

function displayValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function AIAssistantPage({ token }: Props) {
  const [tools, setTools] = useState<AIAssistantTool[]>([]);
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
        if (result.tools.length) {
          setSelectedTool((current) => result.tools.some((tool) => tool.name === current) ? current : result.tools[0].name);
        }
      })
      .catch((err: Error) => { if (active) setError(err.message); })
      .finally(() => { if (active) setToolsLoading(false); });
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
      const input: Record<string, unknown> = toolName === "global_search"
        ? { query: text, ...(entityType ? { entity_types: [entityType] } : {}) }
        : toolName === "get_tasks" && query.trim()
          ? { status: query.trim() }
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

  return (
    <section className="ai-assistant-page">
      <header className="ai-assistant-hero">
        <div>
          <p className="eyebrow">SARU SYSTEMS · INTELLIGENCE</p>
          <h2>Founder AI Assistant</h2>
          <p>Search company records and retrieve permitted OS information from one workspace.</p>
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
              <button className="primary-button" type="button" disabled={loading} onClick={() => void submit(tools.find((tool) => tool.name === selectedTool)?.purpose ?? "Run this read query.")}>{loading ? "Loading…" : "Run query"}</button>
            </div>
          )}

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

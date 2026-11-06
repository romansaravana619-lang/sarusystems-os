import { apiRequest } from "../../services/http";

export type AIAssistantTool = {
  name: string;
  purpose: string;
  input_schema: Record<string, unknown>;
};

export type AIAssistantResponse = {
  request_id: string;
  intent: string | null;
  response_type: "answer" | "clarification" | "action_preview" | "action_result" | "blocked" | "error";
  summary: string;
  data: { items?: Array<Record<string, unknown>>; task?: Record<string, unknown>; preview_id?: string; action?: string };
  records: Array<{ entity_type: string; entity_id: string; label: string | null }>;
  recommendations: string[];
  actions_available: string[];
  confirmation_required: boolean;
  confidence: number | null;
  warnings: string[];
  error_code: string | null;
  audit_reference: string | null;
};

export async function listAIAssistantTools(token: string): Promise<{ tools: AIAssistantTool[]; write_tools: AIAssistantTool[]; provider_connected: boolean }> {
  return apiRequest(token, "/ai-assistant/tools");
}

export async function runAIAssistantRead(
  token: string,
  payload: { message: string; tool_name: string; input: Record<string, unknown> },
): Promise<AIAssistantResponse> {
  return apiRequest(token, "/ai-assistant/read", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function previewAIAssistantWrite(
  token: string,
  payload: { message: string; tool_name: string; input: Record<string, unknown> },
): Promise<AIAssistantResponse> {
  return apiRequest(token, "/ai-assistant/write/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function confirmAIAssistantWrite(
  token: string,
  payload: { message: string; tool_name: string; input: Record<string, unknown>; preview_id: string },
): Promise<AIAssistantResponse> {
  return apiRequest(token, "/ai-assistant/write/confirm", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

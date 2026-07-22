export interface JSONRPCResponse {
  jsonrpc: "2.0";
  id?: number | string | null;
  result?: unknown;
  error?: { code: number; message: string };
}

export interface JSONRPCEvent {
  jsonrpc: "2.0";
  method: "event";
  params: {
    event: string;
    payload: Record<string, unknown>;
  };
}

export interface ToolMetadata {
  name: string;
  description: string;
  category: string;
  tags: string[];
  risky: boolean;
  parameters_schema: Record<string, unknown>;
}

export interface TimelineEntry {
  id: string;
  event_type: string;
  description: string;
  timestamp: string;
  status: "info" | "success" | "error" | "warning";
  detail: Record<string, unknown>;
  duration_ms: number | null;
}

export interface ChatMessage {
  id: string;
  text: string;
  sender: "user" | "system";
  timestamp: Date;
  streaming?: boolean;
}

export interface ConfirmStep {
  action: string;
  params?: Record<string, unknown>;
  description?: string;
  risky?: boolean;
  reasoning?: string;
}

export interface ConfirmRequest {
  confirm_id: string;
  plan: {
    steps: ConfirmStep[];
    reasoning?: string;
  };
  user_input: string;
}

export interface Toast {
  id: string;
  type: "success" | "error" | "info" | "warning";
  message: string;
}

export interface FileEntry {
  name: string;
  is_dir: boolean;
  size: number;
  modified: number;
}

export interface FsListResult {
  path: string;
  entries: FileEntry[];
  error?: string;
}

export interface FsReadResult {
  name: string;
  content: string;
  size: number;
  error?: string;
}

export interface FsWriteResult {
  success: boolean;
  path: string;
  size: number;
  error?: string;
}

export interface ConversationInfo {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
  last_preview: string;
}

export interface Attachment {
  name: string;
  content: string;
  size: number;
}

export interface ProviderConfig {
  id: string;
  name: string;
  api: 'openai' | 'anthropic' | 'gemini' | 'custom';
  baseUrl: string;
  models: { id: string; label: string }[];
  apiKey?: string;
}

export interface McpServer {
  id: string;
  name: string;
  transport: 'stdio' | 'http' | 'sse';
  enabled: boolean;
  command?: string;
  args?: string[];
  url?: string;
}

export interface AgentActivity {
  step: string;
  status: 'running' | 'done' | 'error';
  detail?: string;
  timestamp: number;
}

export interface RuntimeStatus {
  planner: 'READY' | 'RUNNING' | 'IDLE';
  executor: 'READY' | 'RUNNING' | 'WAITING' | 'ERROR';
  permission: 'WAITING' | 'GRANTED' | 'DENIED';
  workspace: 'READY' | 'INDEXING' | 'ERROR';
  mission: 'IDLE' | 'RUNNING' | 'COMPLETED' | 'FAILED';
}

export interface MissionInfo {
  id: string;
  goal: string;
  progress: number;
  steps: number;
  currentStep: string;
  tokens: number;
  budget: number;
  eta: number;
  reflection: 'PASS' | 'FAIL' | 'PENDING';
}

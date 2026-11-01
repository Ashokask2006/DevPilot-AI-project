export interface Project {
  id: number;
  project_name: string;
  project_type: string;
  workspace_path: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  tool_calls?: ToolExecution[];
}

export interface Conversation {
  id: number;
  title: string;
  project_id?: number;
  created_at: string;
  messages: Message[];
}

export interface ToolExecution {
  id?: number;
  task_id?: number;
  tool_name: string;
  execution_status: 'running' | 'success' | 'error';
  execution_output?: string;
  created_at?: string;
}

export interface AgentTask {
  id: number;
  project_id?: number;
  task_description: string;
  task_status: 'pending' | 'planning' | 'running' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  tool_executions?: ToolExecution[];
}

export interface FileItem {
  name: string;
  path: string;
  is_dir: boolean;
  size_bytes: number;
  children?: FileItem[];
}

export interface AIStatus {
  success: boolean;
  configured: boolean;
  model: string;
  latency_ms?: number;
  reply?: string;
  message: string;
  error_code?: number;
}

import { AIStatus, Conversation, FileItem, Project, ToolExecution } from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

const apiUrl = (path: string) => `${API_BASE_URL}${path}`;

export interface AgentPrompt {
  prompt: string;
  conversation_id?: number;
  project_id?: number;
  model?: string;
}

export interface AgentResponse {
  success: boolean;
  reply?: string;
  content?: string;
  tool_calls?: ToolExecution[];
  logs?: string[];
}

export async function fetchAIStatus(): Promise<AIStatus> {
  const res = await fetch(apiUrl('/api/v1/ai/status'));
  if (!res.ok) {
    throw new Error(`Failed to fetch AI status: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchProjects(): Promise<Project[]> {
  const res = await fetch(apiUrl('/api/v1/projects'));
  if (!res.ok) {
    throw new Error(`Failed to fetch projects: ${res.statusText}`);
  }
  return res.json();
}

export async function createProject(data: { project_name: string; project_type: string; description?: string }): Promise<Project> {
  const res = await fetch(apiUrl('/api/v1/projects'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to create project: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchProjectFiles(projectId: number, subpath: string = '.'): Promise<{ success: boolean; files: FileItem[] }> {
  const res = await fetch(apiUrl(`/api/v1/projects/${projectId}/files?subpath=${encodeURIComponent(subpath)}`));
  if (!res.ok) {
    throw new Error(`Failed to fetch project files: ${res.statusText}`);
  }
  return res.json();
}

export async function readFile(projectId: number, filePath: string): Promise<{ success: boolean; content: string; lines: number }> {
  const res = await fetch(apiUrl(`/api/v1/projects/${projectId}/file?file_path=${encodeURIComponent(filePath)}`));
  if (!res.ok) {
    throw new Error(`Failed to read file: ${res.statusText}`);
  }
  return res.json();
}

export async function saveFile(projectId: number, filePath: string, content: string): Promise<{ success: boolean; message: string }> {
  const res = await fetch(apiUrl(`/api/v1/projects/${projectId}/file`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_path: filePath, content }),
  });
  if (!res.ok) {
    throw new Error(`Failed to save file: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchConversations(projectId?: number): Promise<Conversation[]> {
  const path = projectId
    ? `/api/v1/conversations?project_id=${projectId}`
    : '/api/v1/conversations';
  const res = await fetch(apiUrl(path));
  if (!res.ok) {
    throw new Error(`Failed to fetch conversations: ${res.statusText}`);
  }
  return res.json();
}

export async function createConversation(data: { title?: string; project_id?: number }): Promise<Conversation> {
  const res = await fetch(apiUrl('/api/v1/conversations'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to create conversation: ${res.statusText}`);
  }
  return res.json();
}

export async function sendAgentPrompt(data: AgentPrompt): Promise<AgentResponse> {
  const res = await fetch(apiUrl('/api/v1/agent/prompt'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Agent request failed: ${res.statusText}`);
  }
  return res.json();
}

export async function executeTerminalCommand(projectId: number, command: string) {
  const res = await fetch(apiUrl(`/api/v1/projects/${projectId}/terminal`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  });
  if (!res.ok) {
    throw new Error(`Terminal request failed: ${res.statusText}`);
  }
  return res.json();
}

export function projectDownloadUrl(projectId: number): string {
  return apiUrl(`/api/v1/projects/${projectId}/download`);
}

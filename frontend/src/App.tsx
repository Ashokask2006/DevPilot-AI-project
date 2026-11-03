import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ChatArea } from './components/ChatArea';
import { FileExplorer } from './components/FileExplorer';
import { CodeEditor } from './components/CodeEditor';
import { BottomPanel } from './components/BottomPanel';
import { SettingsModal } from './components/SettingsModal';
import { NewProjectModal } from './components/NewProjectModal';

import { Project, Conversation, Message, FileItem, AIStatus } from './types';
import * as api from './services/api';

export const App: React.FC = () => {
  // State
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [isSavingFile, setIsSavingFile] = useState(false);

  // Status & Panel States
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('gemini-flash-lite-latest');
  const [isGenerating, setIsGenerating] = useState(false);
  const [agentStatus, setAgentStatus] = useState<string | null>(null);
  const isRunningCode = false;
  const executionEnabled = false;
  
  // Modals & Panels
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);
  const [isBottomPanelOpen, setIsBottomPanelOpen] = useState(true);
  
  // Terminal logs & Problems
  const [terminalLogs, setTerminalLogs] = useState<string[]>([
    'DevPilot AI environment initialized.',
    'Project command execution is disabled until the Docker sandbox is implemented.'
  ]);
  const problems: { file: string; line: number; message: string; severity: 'error' | 'warning' }[] = [];
  const testResults: { passed: number; failed: number; total: number; output: string } | null = null;

  // Initial load
  useEffect(() => {
    loadAIStatus();
    loadProjects();
  }, []);

  const loadAIStatus = async () => {
    try {
      const status = await api.fetchAIStatus();
      setAiStatus(status);
      if (status.model) setSelectedModel(status.model);
    } catch (err) {
      console.error('Failed to load AI status:', err);
    }
  };

  const loadProjects = async () => {
    try {
      const projs = await api.fetchProjects();
      setProjects(projs);
      if (projs.length > 0 && !activeProject) {
        handleSelectProject(projs[0]);
      }
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  };

  const handleSelectProject = async (project: Project) => {
    setActiveProject(project);
    setActiveFile(null);
    setFileContent('');
    loadFiles(project.id);
    loadConversations(project.id);
  };

  const loadFiles = async (projectId: number) => {
    try {
      const res = await api.fetchProjectFiles(projectId);
      if (res.success) {
        setFiles(res.files);
        // Automatically open main file if present
        const mainFile = res.files.find(f => !f.is_dir && (f.name.startsWith('main.') || f.name.startsWith('app.')));
        if (mainFile) {
          handleOpenFile(mainFile.path, projectId);
        }
      }
    } catch (err) {
      console.error('Failed to load files:', err);
    }
  };

  const loadConversations = async (projectId: number) => {
    try {
      const convs = await api.fetchConversations(projectId);
      setConversations(convs);
      if (convs.length > 0) {
        setActiveConversation(convs[0]);
        setMessages(convs[0].messages || []);
      } else {
        handleNewChat(projectId);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  const handleOpenFile = async (filePath: string, projId?: number) => {
    const id = projId || activeProject?.id;
    if (!id) return;
    try {
      const res = await api.readFile(id, filePath);
      if (res.success) {
        setActiveFile(filePath);
        setFileContent(res.content);
      }
    } catch (err) {
      console.error('Failed to read file:', err);
    }
  };

  const handleSaveFile = async () => {
    if (!activeProject || !activeFile) return;
    setIsSavingFile(true);
    try {
      await api.saveFile(activeProject.id, activeFile, fileContent);
      setTerminalLogs(prev => [...prev, `[Saved] ${activeFile}`]);
    } catch (err: any) {
      setTerminalLogs(prev => [...prev, `[Save Error] ${err.message}`]);
    } finally {
      setTimeout(() => setIsSavingFile(false), 800);
    }
  };

  const handleCreateProject = async (name: string, type: string, description: string) => {
    try {
      const newProj = await api.createProject({ project_name: name, project_type: type, description });
      setProjects(prev => [newProj, ...prev]);
      handleSelectProject(newProj);
      setTerminalLogs(prev => [...prev, `[Project Created] Initialized ${name} (${type})`]);
    } catch (err: any) {
      setTerminalLogs(prev => [...prev, `[Project Creation Failed] ${err.message}`]);
    }
  };

  const handleCreateFile = async (fileName: string) => {
    if (!activeProject) return;
    try {
      await api.saveFile(activeProject.id, fileName, '');
      loadFiles(activeProject.id);
      setActiveFile(fileName);
      setFileContent('');
      setTerminalLogs(prev => [...prev, `[File Created] ${fileName}`]);
    } catch (err: any) {
      setTerminalLogs(prev => [...prev, `[Error creating file] ${err.message}`]);
    }
  };

  const handleNewChat = async (projId?: number) => {
    const id = projId || activeProject?.id;
    try {
      const newConv = await api.createConversation({ title: 'New Agent Task', project_id: id });
      setConversations(prev => [newConv, ...prev]);
      setActiveConversation(newConv);
      setMessages([]);
    } catch (err) {
      console.error('Failed to create new chat:', err);
    }
  };

  const handleSendMessage = async (userPrompt: string) => {
    if (!userPrompt.trim()) return;
    if (!activeProject) {
      setTerminalLogs(prev => [
        ...prev,
        '[Agent Error] Select or create a project before sending an agent request.'
      ]);
      return;
    }

    // Add User Message
    const userMsg: Message = {
      id: Date.now(),
      conversation_id: activeConversation?.id || 0,
      role: 'user',
      content: userPrompt,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsGenerating(true);
    setAgentStatus('analysing_request');

    try {
      const data = await api.sendAgentPrompt({
        prompt: userPrompt,
        conversation_id: activeConversation?.id,
        project_id: activeProject.id,
        model: selectedModel,
      });
      
      const assistantMsg: Message = {
        id: Date.now() + 1,
        conversation_id: activeConversation?.id || 0,
        role: 'assistant',
        content: data.reply || data.content || 'Task completed.',
        created_at: new Date().toISOString(),
        tool_calls: data.tool_calls || [],
      };

      setMessages(prev => [...prev, assistantMsg]);

      // If files were modified or created, reload file explorer
      if (activeProject) {
        loadFiles(activeProject.id);
      }

      const logs = data.logs ?? [];
      if (logs.length > 0) {
        setTerminalLogs(prev => [...prev, ...logs]);
      }
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          conversation_id: activeConversation?.id || 0,
          role: 'assistant',
          content: `⚠️ **Agent Error:** ${err.message}`,
          created_at: new Date().toISOString(),
        }
      ]);
    } finally {
      setIsGenerating(false);
      setAgentStatus(null);
    }
  };

  const handleRunCode = async () => {
    if (!activeProject) return;
    setTerminalLogs(prev => [
      ...prev,
      '[Execution Disabled] Project commands require the forthcoming Docker sandbox.'
    ]);
  };

  const handleDownloadProject = () => {
    if (!activeProject) return;
    window.open(api.projectDownloadUrl(activeProject.id), '_blank', 'noopener');
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 font-sans">
      {/* 1. Left Sidebar */}
      <Sidebar
        projects={projects}
        activeProject={activeProject}
        onSelectProject={handleSelectProject}
        onNewProject={() => setIsNewProjectOpen(true)}
        conversations={conversations}
        activeConversation={activeConversation}
        onSelectConversation={(conv) => {
          setActiveConversation(conv);
          setMessages(conv.messages || []);
        }}
        onNewChat={() => handleNewChat()}
        aiStatus={aiStatus}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* 2. Main Workspace Layout */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Header */}
        <Header
          activeProject={activeProject}
          onRunCode={handleRunCode}
          onSaveFile={handleSaveFile}
          onDownloadProject={handleDownloadProject}
          isRunning={isRunningCode}
          executionEnabled={executionEnabled}
          selectedModel={selectedModel}
          onSelectModel={setSelectedModel}
        />

        {/* Workspace Central Area: Split between AI Chat and Code/Explorer */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Split: AI Agent Chat */}
          <div className="w-1/2 border-r border-slate-800 flex flex-col h-full">
            <ChatArea
              messages={messages}
              onSendMessage={handleSendMessage}
              isGenerating={isGenerating}
              agentStatus={agentStatus}
              activeProjectName={activeProject?.project_name}
            />
          </div>

          {/* Right Split: Explorer + Monaco Editor */}
          <div className="w-1/2 flex h-full">
            <FileExplorer
              files={files}
              activeFile={activeFile}
              onSelectFile={(f) => handleOpenFile(f)}
              onRefresh={() => activeProject && loadFiles(activeProject.id)}
              onCreateFile={handleCreateFile}
            />
            <CodeEditor
              activeFile={activeFile}
              content={fileContent}
              onChange={setFileContent}
              onSave={handleSaveFile}
              isSaving={isSavingFile}
            />
          </div>
        </div>

        {/* Bottom Panel: Terminal, Problems, Tests */}
        <BottomPanel
          terminalLogs={terminalLogs}
          problems={problems}
          testResults={testResults}
          onClearTerminal={() => setTerminalLogs([])}
          isOpen={isBottomPanelOpen}
          onToggle={() => setIsBottomPanelOpen(prev => !prev)}
        />
      </div>

      {/* Modals */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        aiStatus={aiStatus}
        onStatusUpdate={setAiStatus}
      />

      <NewProjectModal
        isOpen={isNewProjectOpen}
        onClose={() => setIsNewProjectOpen(false)}
        onCreate={handleCreateProject}
      />
    </div>
  );
};

export default App;

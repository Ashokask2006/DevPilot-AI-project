import React from 'react';
import { 
  FolderPlus, 
  MessageSquare, 
  Settings as SettingsIcon, 
  Terminal, 
  Code2, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle,
  FolderTree,
  ChevronRight,
  Plus
} from 'lucide-react';
import { Project, Conversation, AIStatus } from '../types';

interface SidebarProps {
  projects: Project[];
  activeProject: Project | null;
  onSelectProject: (project: Project) => void;
  onNewProject: () => void;
  conversations: Conversation[];
  activeConversation: Conversation | null;
  onSelectConversation: (conversation: Conversation) => void;
  onNewChat: () => void;
  aiStatus: AIStatus | null;
  onOpenSettings: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  projects,
  activeProject,
  onSelectProject,
  onNewProject,
  conversations,
  activeConversation,
  onSelectConversation,
  onNewChat,
  aiStatus,
  onOpenSettings,
}) => {
  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-screen select-none text-slate-300">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-white text-base tracking-wide flex items-center gap-1.5">
              DevPilot <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 font-mono">AI</span>
            </span>
            <span className="text-[10px] text-slate-400 block -mt-0.5">Autonomous Engineer</span>
          </div>
        </div>
      </div>

      {/* New Chat Primary Action */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-medium text-xs py-2 px-3 rounded-lg shadow-sm transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Navigation Sections */}
      <div className="flex-1 overflow-y-auto px-2 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
        {/* Projects Section */}
        <div>
          <div className="flex items-center justify-between px-2 py-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <FolderTree className="w-3.5 h-3.5" />
              Projects
            </span>
            <button
              onClick={onNewProject}
              title="Create new project"
              className="text-slate-400 hover:text-white p-0.5 rounded transition"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
          
          <div className="mt-1 space-y-0.5">
            {projects.length === 0 ? (
              <div className="px-3 py-2 text-xs text-slate-400 italic">No projects yet</div>
            ) : (
              projects.map((proj) => {
                const isActive = activeProject?.id === proj.id;
                return (
                  <button
                    key={proj.id}
                    onClick={() => onSelectProject(proj)}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition text-left ${
                      isActive
                        ? 'bg-slate-800 text-indigo-300 font-medium'
                        : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                    }`}
                  >
                    <span className="truncate flex items-center gap-2">
                      <Code2 className="w-3.5 h-3.5 flex-shrink-0 text-slate-400" />
                      <span className="truncate">{proj.project_name}</span>
                    </span>
                    <span className="text-[10px] text-slate-400 px-1.5 py-0.2 bg-slate-950/40 rounded border border-slate-800">
                      {proj.project_type}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Conversations History */}
        <div>
          <div className="px-2 py-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <MessageSquare className="w-3.5 h-3.5" />
            Recent Chats
          </div>
          <div className="mt-1 space-y-0.5">
            {conversations.length === 0 ? (
              <div className="px-3 py-2 text-xs text-slate-400 italic">No history yet</div>
            ) : (
              conversations.map((conv) => {
                const isActive = activeConversation?.id === conv.id;
                return (
                  <button
                    key={conv.id}
                    onClick={() => onSelectConversation(conv)}
                    className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs transition text-left truncate ${
                      isActive
                        ? 'bg-slate-800 text-indigo-300 font-medium'
                        : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                    }`}
                  >
                    <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 text-slate-400" />
                    <span className="truncate">{conv.title || 'Untitled Chat'}</span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Footer / Status & Settings */}
      <div className="p-3 border-t border-slate-800 space-y-2">
        {/* Gemini API Status Badge */}
        <div className="flex items-center justify-between px-2 py-1.5 rounded-md bg-slate-950/60 border border-slate-800/80 text-xs">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                aiStatus?.success ? 'bg-emerald-400' : 'bg-amber-400'
              }`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${
                aiStatus?.success ? 'bg-emerald-500' : 'bg-amber-500'
              }`}></span>
            </span>
            <span className="text-slate-300 font-mono text-[11px]">
              {aiStatus?.model || 'Gemini'}
            </span>
          </div>
          <span className="text-[10px] text-slate-400">
            {aiStatus?.success ? `${aiStatus.latency_ms ? Math.round(aiStatus.latency_ms) : 0}ms` : 'Offline'}
          </span>
        </div>

        {/* Settings Button */}
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
        >
          <span className="flex items-center gap-2">
            <SettingsIcon className="w-3.5 h-3.5" />
            <span>Settings</span>
          </span>
          <ChevronRight className="w-3.5 h-3.5 opacity-60" />
        </button>
      </div>
    </aside>
  );
};

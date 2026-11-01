import React from 'react';
import { 
  FolderGit2, 
  Play, 
  Download, 
  Save, 
  Sparkles,
  Layers,
  ChevronDown,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import { Project, AIStatus } from '../types';

interface HeaderProps {
  activeProject: Project | null;
  aiStatus: AIStatus | null;
  onRunCode: () => void;
  onSaveFile: () => void;
  onDownloadProject: () => void;
  isRunning: boolean;
  selectedModel: string;
  onSelectModel: (model: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeProject,
  aiStatus,
  onRunCode,
  onSaveFile,
  onDownloadProject,
  isRunning,
  selectedModel,
  onSelectModel,
}) => {
  return (
    <header className="h-12 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 select-none">
      {/* Active Project Info */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs font-medium text-slate-200">
          <FolderGit2 className="w-4 h-4 text-indigo-400" />
          <span className="font-semibold text-white">
            {activeProject ? activeProject.project_name : 'No Project Selected'}
          </span>
          {activeProject && (
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/60">
              {activeProject.project_type}
            </span>
          )}
        </div>
      </div>

      {/* Model Selection & Quick Status */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 bg-slate-950/80 px-2.5 py-1 rounded-md border border-slate-800 text-xs text-slate-300">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <select
            value={selectedModel}
            onChange={(e) => onSelectModel(e.target.value)}
            className="bg-transparent text-slate-200 text-xs focus:outline-none cursor-pointer"
          >
            <option value="gemini-flash-lite-latest" className="bg-slate-900">gemini-flash-lite (Fastest)</option>
            <option value="gemini-flash-latest" className="bg-slate-900">gemini-flash-latest</option>
            <option value="gemini-pro-latest" className="bg-slate-900">gemini-pro (Deep Reasoning)</option>
          </select>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={onSaveFile}
            title="Save Current File (Ctrl+S)"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition"
          >
            <Save className="w-3.5 h-3.5 text-slate-400" />
            <span>Save</span>
          </button>

          <button
            onClick={onRunCode}
            disabled={isRunning}
            title="Run Code in Isolated Sandbox"
            className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold shadow-sm transition ${
              isRunning 
                ? 'bg-amber-600/60 text-amber-200 cursor-not-allowed'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white'
            }`}
          >
            {isRunning ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            <span>{isRunning ? 'Running...' : 'Run'}</span>
          </button>

          {activeProject && (
            <button
              onClick={onDownloadProject}
              title="Download Project ZIP"
              className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            >
              <Download className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

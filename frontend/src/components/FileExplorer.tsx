import React, { useState } from 'react';
import { 
  Folder, 
  FileText, 
  FilePlus, 
  RefreshCw
} from 'lucide-react';
import { FileItem } from '../types';

interface FileExplorerProps {
  files: FileItem[];
  activeFile: string | null;
  onSelectFile: (filePath: string) => void;
  onRefresh: () => void;
  onCreateFile: (fileName: string) => void;
}

export const FileExplorer: React.FC<FileExplorerProps> = ({
  files,
  activeFile,
  onSelectFile,
  onRefresh,
  onCreateFile,
}) => {
  const [newFileInput, setNewFileInput] = useState(false);
  const [newFileName, setNewFileName] = useState('');

  const getFileIcon = (fileName: string) => {
    if (fileName.endsWith('.py')) return <span className="text-yellow-400 font-bold text-[10px]">PY</span>;
    if (fileName.endsWith('.ts') || fileName.endsWith('.tsx')) return <span className="text-blue-400 font-bold text-[10px]">TS</span>;
    if (fileName.endsWith('.js') || fileName.endsWith('.jsx')) return <span className="text-amber-400 font-bold text-[10px]">JS</span>;
    if (fileName.endsWith('.json')) return <span className="text-emerald-400 font-bold text-[10px]">{}</span>;
    if (fileName.endsWith('.css')) return <span className="text-sky-400 font-bold text-[10px]">#</span>;
    if (fileName.endsWith('.md')) return <span className="text-slate-400 font-bold text-[10px]">MD</span>;
    return <FileText className="w-3.5 h-3.5 text-slate-400" />;
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFileName.trim()) return;
    onCreateFile(newFileName.trim());
    setNewFileName('');
    setNewFileInput(false);
  };

  return (
    <div className="w-56 bg-slate-900 border-r border-slate-800 flex flex-col h-full select-none text-slate-300">
      {/* File Explorer Header */}
      <div className="px-3 py-2 border-b border-slate-800 flex items-center justify-between">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Explorer
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setNewFileInput(true)}
            title="New File"
            className="p-1 hover:text-white hover:bg-slate-800 rounded transition"
          >
            <FilePlus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onRefresh}
            title="Refresh Files"
            className="p-1 hover:text-white hover:bg-slate-800 rounded transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* New File Inline Input */}
      {newFileInput && (
        <form onSubmit={handleCreateSubmit} className="p-2 border-b border-slate-800 bg-slate-950">
          <input
            type="text"
            autoFocus
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            onBlur={() => setNewFileInput(false)}
            placeholder="filename.ext"
            className="w-full bg-slate-900 border border-indigo-500 rounded px-2 py-1 text-xs text-white focus:outline-none"
          />
        </form>
      )}

      {/* File List */}
      <div className="flex-1 overflow-y-auto p-1 space-y-0.5 text-xs">
        {files.length === 0 ? (
          <div className="p-3 text-center text-slate-400 text-[11px] italic">
            Workspace is empty
          </div>
        ) : (
          files.map((file) => {
            const isActive = activeFile === file.path;
            return (
              <button
                key={file.path}
                onClick={() => !file.is_dir && onSelectFile(file.path)}
                className={`w-full flex items-center gap-2 px-2 py-1.5 rounded transition text-left truncate ${
                  isActive
                    ? 'bg-indigo-600/20 text-indigo-300 font-medium border-l-2 border-indigo-500'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                {file.is_dir ? (
                  <Folder className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                ) : (
                  <span className="w-3.5 flex justify-center flex-shrink-0">
                    {getFileIcon(file.name)}
                  </span>
                )}
                <span className="truncate">{file.name}</span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};

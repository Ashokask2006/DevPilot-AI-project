import React from 'react';
import Editor from '@monaco-editor/react';
import { FileCode, Save, Check } from 'lucide-react';

interface CodeEditorProps {
  activeFile: string | null;
  content: string;
  onChange: (value: string) => void;
  onSave: () => void;
  isSaving?: boolean;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  activeFile,
  content,
  onChange,
  onSave,
  isSaving,
}) => {
  // Infer Monaco language from file extension
  const getLanguage = (fileName: string | null): string => {
    if (!fileName) return 'plaintext';
    if (fileName.endsWith('.py')) return 'python';
    if (fileName.endsWith('.js') || fileName.endsWith('.jsx')) return 'javascript';
    if (fileName.endsWith('.ts') || fileName.endsWith('.tsx')) return 'typescript';
    if (fileName.endsWith('.json')) return 'json';
    if (fileName.endsWith('.html')) return 'html';
    if (fileName.endsWith('.css')) return 'css';
    if (fileName.endsWith('.sql')) return 'sql';
    if (fileName.endsWith('.md')) return 'markdown';
    if (fileName.endsWith('.sh') || fileName.endsWith('.bat')) return 'shell';
    return 'plaintext';
  };

  if (!activeFile) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-slate-950 text-slate-400 select-none">
        <FileCode className="w-12 h-12 mb-3 text-slate-800" />
        <span className="text-xs">Select a file from the explorer to view or edit</span>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 overflow-hidden">
      {/* Editor Tab Bar */}
      <div className="h-9 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-3 select-none">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-200">
          <span className="px-2.5 py-1 bg-slate-950 border-t border-x border-slate-800 rounded-t text-indigo-300 flex items-center gap-1.5">
            <FileCode className="w-3.5 h-3.5 text-indigo-400" />
            {activeFile}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onSave}
            title="Save (Ctrl+S)"
            className="flex items-center gap-1 text-[11px] text-slate-300 hover:text-white px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 transition"
          >
            {isSaving ? (
              <>
                <Check className="w-3 h-3 text-emerald-400" />
                <span>Saved</span>
              </>
            ) : (
              <>
                <Save className="w-3 h-3 text-slate-400" />
                <span>Save</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Monaco Editor Container */}
      <div className="flex-1 w-full h-full">
        <Editor
          height="100%"
          language={getLanguage(activeFile)}
          value={content}
          theme="vs-dark"
          onChange={(val) => onChange(val || '')}
          options={{
            minimap: { enabled: true },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            wordWrap: 'on',
            renderLineHighlight: 'all',
          }}
        />
      </div>
    </div>
  );
};

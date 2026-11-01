import React, { useState } from 'react';
import { 
  Terminal as TerminalIcon, 
  AlertCircle, 
  CheckCircle2, 
  Trash2, 
  ChevronDown, 
  ChevronUp,
  FileCheck
} from 'lucide-react';

interface BottomPanelProps {
  terminalLogs: string[];
  problems: { file: string; line: number; message: string; severity: 'error' | 'warning' }[];
  testResults: { passed: number; failed: number; total: number; output: string } | null;
  onClearTerminal: () => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const BottomPanel: React.FC<BottomPanelProps> = ({
  terminalLogs,
  problems,
  testResults,
  onClearTerminal,
  isOpen,
  onToggle,
}) => {
  const [activeTab, setActiveTab] = useState<'terminal' | 'problems' | 'tests'>('terminal');

  return (
    <div className={`bg-slate-900 border-t border-slate-800 flex flex-col transition-all duration-200 ${
      isOpen ? 'h-52' : 'h-8'
    }`}>
      {/* Panel Tab Header */}
      <div className="h-8 bg-slate-950 px-3 flex items-center justify-between border-b border-slate-800 select-none">
        <div className="flex items-center gap-1">
          <button
            onClick={() => { setActiveTab('terminal'); if (!isOpen) onToggle(); }}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-t text-xs font-medium transition ${
              activeTab === 'terminal' && isOpen
                ? 'bg-slate-900 text-indigo-400 border-t-2 border-indigo-500'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <TerminalIcon className="w-3.5 h-3.5" />
            <span>Terminal</span>
          </button>

          <button
            onClick={() => { setActiveTab('problems'); if (!isOpen) onToggle(); }}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-t text-xs font-medium transition ${
              activeTab === 'problems' && isOpen
                ? 'bg-slate-900 text-indigo-400 border-t-2 border-indigo-500'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            <span>Problems ({problems.length})</span>
          </button>

          <button
            onClick={() => { setActiveTab('tests'); if (!isOpen) onToggle(); }}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-t text-xs font-medium transition ${
              activeTab === 'tests' && isOpen
                ? 'bg-slate-900 text-indigo-400 border-t-2 border-indigo-500'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Tests {testResults ? `(${testResults.passed}/${testResults.total})` : ''}</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          {activeTab === 'terminal' && isOpen && (
            <button
              onClick={onClearTerminal}
              title="Clear terminal"
              className="p-1 text-slate-400 hover:text-slate-200 transition"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={onToggle}
            className="p-1 text-slate-400 hover:text-slate-200 transition"
          >
            {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Panel Tab Content */}
      {isOpen && (
        <div className="flex-1 overflow-y-auto p-3 bg-slate-950 font-mono text-xs select-text">
          {activeTab === 'terminal' && (
            <div className="space-y-1 text-slate-300">
              {terminalLogs.length === 0 ? (
                <div className="text-slate-600 italic">Terminal ready. Output will appear here.</div>
              ) : (
                terminalLogs.map((log, idx) => (
                  <div key={idx} className="whitespace-pre-wrap leading-relaxed">
                    {log}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'problems' && (
            <div className="space-y-1.5">
              {problems.length === 0 ? (
                <div className="text-slate-500 italic">No problems detected in workspace.</div>
              ) : (
                problems.map((prob, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-xs">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="text-slate-400">[{prob.file}:{prob.line}] </span>
                      <span className="text-slate-200">{prob.message}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'tests' && (
            <div>
              {testResults ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-semibold">
                      Passed: {testResults.passed}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-400 font-semibold">
                      Failed: {testResults.failed}
                    </span>
                  </div>
                  <pre className="text-slate-400 text-xs whitespace-pre-wrap bg-slate-900 p-2 rounded">
                    {testResults.output}
                  </pre>
                </div>
              ) : (
                <div className="text-slate-500 italic">No tests executed yet. Click 'Run' to execute test suite.</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

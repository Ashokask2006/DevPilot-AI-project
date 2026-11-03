import React, { useState } from 'react';
import { 
  X, 
  Sparkles, 
  RefreshCw, 
  ExternalLink,
  ShieldCheck
} from 'lucide-react';
import { AIStatus } from '../types';
import { fetchAIStatus } from '../services/api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  aiStatus: AIStatus | null;
  onStatusUpdate: (status: AIStatus) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  aiStatus,
  onStatusUpdate,
}) => {
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await fetchAIStatus();
      onStatusUpdate(res);
      setTestResult(res.message);
    } catch (err: any) {
      setTestResult(`Error: ${err.message}`);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm select-none">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden text-slate-200">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-white text-sm">DevPilot AI Settings</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 text-xs">
          {/* Gemini AI Status Card */}
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-white flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-indigo-400" />
                Google Gemini API
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                aiStatus?.success 
                  ? 'bg-emerald-500/20 text-emerald-400' 
                  : 'bg-amber-500/20 text-amber-400'
              }`}>
                {aiStatus?.success ? 'Connected' : 'Offline'}
              </span>
            </div>

            <div className="text-slate-400 text-[11px] space-y-1">
              <div>Model: <strong className="text-slate-200 font-mono">{aiStatus?.model || 'gemini-flash-lite-latest'}</strong></div>
              <div>Latency: <strong className="text-slate-200 font-mono">{aiStatus?.latency_ms ? `${Math.round(aiStatus.latency_ms)}ms` : 'N/A'}</strong></div>
              <div>Storage: <strong className="text-slate-200 font-mono">backend/.env (Excluded from Git)</strong></div>
            </div>

            <button
              onClick={handleTestConnection}
              disabled={isTesting}
              className="w-full mt-2 flex items-center justify-center gap-2 py-1.5 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition"
            >
              {isTesting ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Testing Connection...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Test API Connection</span>
                </>
              )}
            </button>

            {testResult && (
              <div className="mt-2 p-2 rounded bg-slate-900 border border-slate-800 text-[11px] text-slate-300">
                {testResult}
              </div>
            )}
          </div>

          {/* Key Management Info */}
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-slate-400 space-y-1.5">
            <div className="font-medium text-slate-300">How to update API Key:</div>
            <p className="text-[11px] leading-relaxed">
              Open <code className="text-indigo-400 bg-slate-900 px-1 py-0.5 rounded">backend/.env</code> in your editor and update <code className="text-indigo-400 bg-slate-900 px-1 py-0.5 rounded">GEMINI_API_KEY</code>. It is securely kept on your backend server and never exposed to the frontend.
            </p>
            <a
              href="https://aistudio.google.com/api-keys"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 mt-1"
            >
              <span>Get API Key from Google AI Studio</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-800 bg-slate-950 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

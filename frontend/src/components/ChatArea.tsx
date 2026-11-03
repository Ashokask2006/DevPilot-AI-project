import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Sparkles, 
  Bot, 
  User, 
  Terminal, 
  Square,
  ArrowRight
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Message } from '../types';

interface ChatAreaProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  isGenerating: boolean;
  onStopGeneration?: () => void;
  agentStatus: string | null;
  activeProjectName?: string;
}

const SAMPLE_PROMPTS = [
  {
    title: 'Create a Python Calculator',
    desc: 'Build a CLI or GUI calculator with unit tests',
    prompt: 'Create a complete Python calculator project with addition, subtraction, multiplication, and division functions, plus automated pytest tests.',
  },
  {
    title: 'FastAPI REST API',
    desc: 'CRUD endpoints with SQLite database',
    prompt: 'Build a FastAPI REST API for a task management system with SQLite database and CRUD endpoints.',
  },
  {
    title: 'Streamlit Data Dashboard',
    desc: 'Interactive data visualization web app',
    prompt: 'Develop an interactive Streamlit application with charts, filters, and synthetic dataset generation.',
  },
  {
    title: 'Debug & Test Project',
    desc: 'Run tests, diagnose errors, and verify fixes',
    prompt: 'Inspect current project files, run the test suite, analyze any errors found, and apply automated fixes.',
  },
];

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  onSendMessage,
  isGenerating,
  onStopGeneration,
  agentStatus,
  activeProjectName,
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, agentStatus]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;
    onSendMessage(input.trim());
    setInput('');
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 text-slate-200 overflow-hidden relative">
      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center px-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-500 to-pink-500 flex items-center justify-center text-white mb-4 shadow-xl shadow-indigo-500/10">
              <Sparkles className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">
              What should DevPilot AI build for you today?
            </h2>
            <p className="text-xs text-slate-400 mb-8 max-w-md">
              Powered by Google Gemini API. Ask me to scaffold software projects, write code, run isolated tests, and fix bugs autonomously.
            </p>

            {/* Sample Prompts Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full text-left">
              {SAMPLE_PROMPTS.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => onSendMessage(item.prompt)}
                  className="p-3 rounded-lg border border-slate-800/80 bg-slate-900/60 hover:bg-slate-800/80 hover:border-slate-700 transition text-left group"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200 group-hover:text-indigo-300 transition">
                      {item.title}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transform group-hover:translate-x-0.5 transition" />
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                    {item.desc}
                  </p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div
              key={msg.id || index}
              className={`flex gap-3 max-w-3xl ${
                msg.role === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-white text-xs ${
                  msg.role === 'user'
                    ? 'bg-indigo-600'
                    : 'bg-gradient-to-tr from-purple-600 to-indigo-600 shadow-md shadow-purple-600/20'
                }`}
              >
                {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Content Bubble */}
              <div
                className={`rounded-xl px-4 py-3 text-xs leading-relaxed max-w-[85%] ${
                  msg.role === 'user'
                    ? 'bg-indigo-600/90 text-white rounded-tr-none'
                    : 'bg-slate-900 border border-slate-800/90 text-slate-200 rounded-tl-none shadow-sm'
                }`}
              >
                {/* Tool Executions List if any */}
                {msg.tool_calls && msg.tool_calls.length > 0 && (
                  <div className="mb-2 space-y-1.5 pb-2 border-b border-slate-800">
                    {msg.tool_calls.map((tool, tIdx) => (
                      <div
                        key={tIdx}
                        className="flex items-center gap-2 px-2 py-1 bg-slate-950/60 rounded border border-slate-800 text-[11px] font-mono text-slate-400"
                      >
                        <Terminal className="w-3 h-3 text-indigo-400" />
                        <span>Executed: <strong className="text-slate-200">{tool.tool_name}</strong></span>
                        <span className={`ml-auto px-1.5 py-0.2 rounded text-[9px] ${
                          tool.execution_status === 'success' 
                            ? 'bg-emerald-500/20 text-emerald-400' 
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {tool.execution_status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Markdown text */}
                <div className="prose prose-invert prose-xs max-w-none break-words">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>
            </div>
          ))
        )}

        {/* Live Agent Status Indicator */}
        {agentStatus && (
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-indigo-950/40 border border-indigo-800/40 text-indigo-300 text-xs animate-pulse max-w-md">
            <Sparkles className="w-4 h-4 text-indigo-400 animate-spin" />
            <span className="font-medium capitalize">{agentStatus.replace(/_/g, ' ')}...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form Bar */}
      <div className="p-3 border-t border-slate-800 bg-slate-900/80 backdrop-blur">
        <form onSubmit={handleSubmit} className="flex items-end gap-2 max-w-4xl mx-auto">
          <div className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 focus-within:border-indigo-500/80 transition shadow-inner">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder={
                activeProjectName
                  ? `Ask DevPilot to generate or edit code for ${activeProjectName}...`
                  : 'Ask DevPilot AI to build a project, write code, or fix errors...'
              }
              rows={1}
              className="w-full bg-transparent text-slate-100 text-xs focus:outline-none resize-none placeholder-slate-500 max-h-32"
            />
          </div>

          {isGenerating ? (
            <button
              type="button"
              onClick={onStopGeneration}
              className="p-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white transition shadow-sm"
              title="Stop Generation"
            >
              <Square className="w-4 h-4 fill-current" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white transition shadow-sm"
              title="Send Message"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </form>
      </div>
    </div>
  );
};

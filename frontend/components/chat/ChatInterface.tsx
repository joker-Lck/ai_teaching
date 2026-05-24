'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { useChatStore, useAuthStore } from '@/stores';
import api from '@/lib/api';
import {
  Send, Mic, Loader2, BookOpen, Trash2,
  GraduationCap, Lightbulb, MessageSquare,
  ChevronDown, Download, Copy, Check
} from 'lucide-react';

const scenarios = [
  { id: 'smart', label: '智能答疑', icon: '💬', desc: '通用问答' },
  { id: 'preview', label: '课前预习', icon: '📖', desc: '知识点梳理' },
  { id: 'classroom', label: '课中互动', icon: '🎯', desc: '实时提问' },
  { id: 'homework', label: '课后辅导', icon: '📝', desc: '作业讲解' },
];

const quickQuestions = [
  '请解释一下函数的单调性',
  '什么是牛顿第三定律？',
  '如何区分化学变化和物理变化？',
  '请帮我梳理三角函数的知识框架',
];

export default function ChatInterface() {
  const { messages, isGenerating, currentScenario, addMessage, appendToLastMessage, setGenerating, setScenario, clearMessages } = useChatStore();
  const { isGuest } = useAuthStore();
  const [input, setInput] = useState('');
  const [selectedScenario, setSelectedScenario] = useState('smart');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isGenerating) return;

    const scenarioLabel = scenarios.find(s => s.id === selectedScenario)?.label || '智能答疑';

    // 添加用户消息
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user' as const,
      content: text,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    };
    addMessage(userMsg);
    setInput('');

    // 添加 AI 占位消息
    const aiMsg = {
      id: `ai-${Date.now()}`,
      role: 'assistant' as const,
      content: '',
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      isStreaming: true,
    };
    addMessage(aiMsg);
    setGenerating(true);

    // 使用流式 API
    try {
      await api.askQuestionStream(
        text,
        scenarioLabel,
        (chunk) => appendToLastMessage(chunk),
        (data) => {
          setGenerating(false);
        },
        (error) => {
          appendToLastMessage(`\n\n❌ 请求失败: ${error}`);
          setGenerating(false);
        },
      );
    } catch (err: any) {
      appendToLastMessage(`\n\n❌ ${err.message || '网络错误'}`);
      setGenerating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopy = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleQuickQuestion = (q: string) => {
    setInput(q);
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-screen">
      {/* 头部 */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white border-b border-gray-100 px-6 py-4 flex-shrink-0"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-800">智能答疑</h1>
              <p className="text-xs text-gray-500">RAG 优先策略 · 多轮对话 · 流式输出</p>
            </div>
          </div>

          <button
            onClick={clearMessages}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-500 hover:text-red-500 hover:bg-red-50 transition-all"
          >
            <Trash2 className="w-4 h-4" />
            清空对话
          </button>
        </div>

        {/* 场景选择 */}
        <div className="flex gap-2 mt-4 overflow-x-auto pb-1">
          {scenarios.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedScenario(s.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all ${
                selectedScenario === s.id
                  ? 'bg-blue-500 text-white shadow-md shadow-blue-500/30'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <span>{s.icon}</span>
              {s.label}
            </button>
          ))}
        </div>
      </motion.header>

      {/* 消息区域 */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center h-full text-center"
          >
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-6 shadow-lg shadow-blue-500/30">
              <GraduationCap className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-xl font-bold text-gray-800 mb-2">AI 智能答疑</h2>
            <p className="text-gray-500 mb-8 max-w-md">
              基于 RAG 优先策略，结合 93 本电子书知识库，为您提供准确、专业的教学答疑
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-lg">
              {quickQuestions.map((q, i) => (
                <motion.button
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 * i }}
                  onClick={() => handleQuickQuestion(q)}
                  className="text-left p-3 rounded-xl border-2 border-gray-100 hover:border-blue-300 hover:bg-blue-50 transition-all group"
                >
                  <div className="flex items-start gap-2">
                    <Lightbulb className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-gray-600 group-hover:text-blue-600">{q}</span>
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-4">
            <AnimatePresence>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white'
                        : 'bg-white shadow-card border border-gray-100'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <div className="markdown-body">
                        <ReactMarkdown>{msg.content || (msg.isStreaming ? '思考中...' : '')}</ReactMarkdown>
                        {msg.isStreaming && (
                          <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-1" />
                        )}
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    )}

                    {/* 消息操作栏 */}
                    {msg.role === 'assistant' && !msg.isStreaming && msg.content && (
                      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-100">
                        <button
                          onClick={() => handleCopy(msg.content, msg.id)}
                          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
                        >
                          {copiedId === msg.id ? (
                            <><Check className="w-3 h-3" /> 已复制</>
                          ) : (
                            <><Copy className="w-3 h-3" /> 复制</>
                          )}
                        </button>
                        <span className="text-xs text-gray-300">{msg.timestamp}</span>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white border-t border-gray-100 px-6 py-4 flex-shrink-0"
      >
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入您的问题... (Enter 发送, Shift+Enter 换行)"
                rows={1}
                className="w-full px-4 py-3 pr-12 rounded-xl border-2 border-gray-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20 outline-none resize-none transition-all text-sm"
                style={{ minHeight: '48px', maxHeight: '120px' }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = Math.min(target.scrollHeight, 120) + 'px';
                }}
              />
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleSend}
                disabled={!input.trim() || isGenerating}
                className="w-12 h-12 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 text-white flex items-center justify-center hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGenerating ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>

          <p className="text-xs text-gray-400 mt-2 text-center">
            AI 回答基于 RAG 知识库，仅供参考 · 支持多轮对话和上下文理解
          </p>
        </div>
      </motion.div>
    </div>
  );
}

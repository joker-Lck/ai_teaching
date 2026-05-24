'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { useAuthStore, useUIStore } from '@/stores';
import api from '@/lib/api';
import Sidebar from '@/components/layout/Sidebar';
import {
  Database, Search, BookOpen, Loader2, Upload, Trash2
} from 'lucide-react';

export default function KnowledgePage() {
  const router = useRouter();
  const { isLoggedIn } = useAuthStore();
  const { sidebarOpen } = useUIStore();

  useEffect(() => {
    if (!isLoggedIn) router.push('/');
  }, [isLoggedIn, router]);

  if (!isLoggedIn) return null;

  return (
    <div className="flex min-h-screen bg-surface-secondary">
      <Sidebar />
      <main className={`flex-1 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-20'}`}>
        <KnowledgeContent />
      </main>
    </div>
  );
}

function KnowledgeContent() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({});
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadStats();
    loadDocuments();
  }, []);

  const loadStats = async () => {
    try {
      const res: any = await api.getKnowledgeStats();
      if (res.success) setStats(res);
    } catch {}
  };

  const loadDocuments = async () => {
    try {
      const res: any = await api.getKnowledgeDocuments();
      if (res.success) setDocuments(res.documents || []);
    } catch {}
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const res: any = await api.searchKnowledgeDocuments(searchQuery);
      if (res.success) setSearchResults(res.results || []);
    } catch {}
    setLoading(false);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const formData = new FormData();
    Array.from(files).forEach(f => formData.append('files', f));

    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch('/api/knowledge/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data: any = await res.json();
      if (data.success) {
        loadStats();
        loadDocuments();
      }
    } catch {}
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
            <Database className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">知识库管理</h1>
            <p className="text-sm text-gray-500">RAG 知识库 · 智能检索 · AI 解析</p>
          </div>
        </div>
      </motion.div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'RAG 文档总数', value: stats.total_documents || 0, icon: '📚' },
          { label: '知识点数量', value: stats.total_knowledge_points || 0, icon: '🎯' },
          { label: '平均使用次数', value: (stats.average_usage || 0).toFixed(1), icon: '📊' },
          { label: '覆盖学科数', value: (stats.subject_distribution || []).length, icon: '🎓' },
        ].map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="bg-white rounded-xl p-4 shadow-card"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">{s.icon}</span>
              <div>
                <p className="text-xl font-bold text-gray-800">{s.value}</p>
                <p className="text-xs text-gray-500">{s.label}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* 搜索栏 */}
      <div className="bg-white rounded-2xl p-6 shadow-card mb-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
          <Search className="w-5 h-5 text-green-500" />
          RAG 智能检索
        </h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="输入关键词搜索知识文档..."
            className="flex-1 px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-green-400 outline-none transition-all"
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-green-500 to-emerald-500 text-white font-medium hover:shadow-lg transition-all flex items-center gap-2 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            搜索
          </button>
        </div>

        {searchResults.length > 0 && (
          <div className="mt-4 space-y-3">
            {searchResults.map((doc, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="p-4 bg-green-50 rounded-xl"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium text-gray-800">{doc.title}</h3>
                    <p className="text-xs text-gray-500 mt-1">{doc.subject}</p>
                    <p className="text-sm text-gray-600 mt-2">{doc.content_preview}...</p>
                  </div>
                  {doc.similarity > 0 && (
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded-lg text-xs font-medium">
                      {(doc.similarity * 100).toFixed(0)}% 匹配
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* 上传区域 */}
      <div className="bg-white rounded-2xl p-6 shadow-card mb-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
          <Upload className="w-5 h-5 text-green-500" />
          上传文档
        </h2>
        <label className="block w-full p-8 border-2 border-dashed border-gray-300 rounded-xl text-center cursor-pointer hover:border-green-400 hover:bg-green-50 transition-all">
          <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-gray-600 font-medium">点击或拖拽上传文档</p>
          <p className="text-xs text-gray-400 mt-1">支持 PDF、Word、PPT、TXT、图片等格式</p>
          <input
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md,.jpg,.jpeg,.png"
            onChange={handleUpload}
            className="hidden"
          />
        </label>
      </div>

      {/* 文档列表 */}
      <div className="bg-white rounded-2xl p-6 shadow-card">
        <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-green-500" />
          知识库文档 ({documents.length})
        </h2>
        {documents.length === 0 ? (
          <p className="text-center text-gray-400 py-8">📭 知识库为空，请上传文档</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {documents.map((doc, i) => (
              <motion.div
                key={doc.id || i}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.03 }}
                className="p-4 border-2 border-gray-100 rounded-xl hover:border-green-300 hover:bg-green-50 transition-all cursor-pointer"
              >
                <div className="flex items-start gap-3">
                  <span className="text-xl">📄</span>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-800 truncate">{doc.title}</h3>
                    <p className="text-xs text-gray-500 mt-1">{doc.subject} · {doc.file_type}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

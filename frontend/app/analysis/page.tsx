'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { useAuthStore, useUIStore } from '@/stores';
import api from '@/lib/api';
import Sidebar from '@/components/layout/Sidebar';
import {
  BarChart3, FileText, Sparkles, Loader2, Users, User
} from 'lucide-react';

export default function AnalysisPage() {
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
        <AnalysisContent />
      </main>
    </div>
  );
}

function AnalysisContent() {
  const [mode, setMode] = useState('全班评估');
  const [studentName, setStudentName] = useState('');
  const [className, setClassName] = useState('');
  const [totalStudents, setTotalStudents] = useState(45);
  const [report, setReport] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    setReport('');

    try {
      const res: any = await api.generateAnalysisReport(
        mode,
        mode === '单个学生' ? studentName : undefined,
        mode === '全班评估' ? className : undefined,
        totalStudents,
      );

      if (res.success) {
        setReport(res.report);
      } else {
        setError(res.error || '生成失败');
      }
    } catch (err: any) {
      setError(err.message || '网络错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">AI 学情分析</h1>
            <p className="text-sm text-gray-500">7 维度深度分析 · 数据可视化 · 个性化报告</p>
          </div>
        </div>
      </motion.div>

      {/* 模式选择 */}
      <div className="bg-white rounded-2xl p-6 shadow-card mb-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4">分析模式</h2>
        <div className="flex gap-4 mb-6">
          {[
            { id: '单个学生', label: '单个学生', icon: User },
            { id: '全班评估', label: '全班评估', icon: Users },
          ].map((m) => {
            const Icon = m.icon;
            return (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
                  mode === m.id
                    ? 'bg-orange-500 text-white shadow-md shadow-orange-500/30'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                {m.label}
              </button>
            );
          })}
        </div>

        {mode === '单个学生' ? (
          <input
            type="text"
            value={studentName}
            onChange={(e) => setStudentName(e.target.value)}
            placeholder="请输入学生姓名"
            className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-orange-400 outline-none transition-all"
          />
        ) : (
          <div className="flex gap-4">
            <input
              type="text"
              value={className}
              onChange={(e) => setClassName(e.target.value)}
              placeholder="班级名称，如：高一(3)班"
              className="flex-1 px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-orange-400 outline-none transition-all"
            />
            <input
              type="number"
              value={totalStudents}
              onChange={(e) => setTotalStudents(Number(e.target.value))}
              className="w-32 px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-orange-400 outline-none transition-all"
              placeholder="人数"
            />
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="mt-4 w-full py-3 rounded-xl bg-gradient-to-r from-orange-500 to-red-500 text-white font-medium hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {loading ? (
            <><Loader2 className="w-5 h-5 animate-spin" /> 正在分析...</>
          ) : (
            <><Sparkles className="w-5 h-5" /> AI 生成学情报告</>
          )}
        </button>

        {error && <p className="text-red-500 text-sm mt-2">❌ {error}</p>}
      </div>

      {/* 报告展示 */}
      {report && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl p-8 shadow-card"
        >
          <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-orange-500" />
            分析报告
          </h2>
          <div className="markdown-body">
            <ReactMarkdown>{report}</ReactMarkdown>
          </div>
        </motion.div>
      )}
    </div>
  );
}

'use client';

import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores';
import {
  MessageSquare, FileText, BarChart3, Database,
  Sparkles, TrendingUp, Users, BookOpen,
  ArrowRight, Zap, Clock, Target
} from 'lucide-react';

const featureCards = [
  {
    title: '智能答疑',
    description: 'RAG 优先策略，多轮对话，语音输入',
    icon: MessageSquare,
    path: '/qa',
    gradient: 'from-blue-500 to-cyan-500',
    stats: '响应 < 0.5s',
    emoji: '💬',
  },
  {
    title: '课件生成',
    description: 'AI 一键生成专业 PPT，5 种模板风格',
    icon: FileText,
    path: '/courseware',
    gradient: 'from-purple-500 to-pink-500',
    stats: '15-90 秒生成',
    emoji: '📚',
  },
  {
    title: '学情分析',
    description: '7 维度深度分析，数据可视化',
    icon: BarChart3,
    path: '/analysis',
    gradient: 'from-orange-500 to-red-500',
    stats: '7 维度分析',
    emoji: '📊',
  },
  {
    title: '知识库管理',
    description: '93 本电子书，向量化智能检索',
    icon: Database,
    path: '/knowledge',
    gradient: 'from-green-500 to-emerald-500',
    stats: 'RAG 智能检索',
    emoji: '🗄️',
  },
];

const stats = [
  { label: 'API 成本降低', value: '60%', icon: TrendingUp, color: 'text-green-500' },
  { label: '课堂互动提升', value: '80%', icon: Users, color: 'text-blue-500' },
  { label: '备课效率提升', value: '50%', icon: Clock, color: 'text-purple-500' },
  { label: '准确率提升', value: '30%', icon: Target, color: 'text-orange-500' },
];

export default function DashboardContent() {
  const router = useRouter();
  const { user, isGuest } = useAuthStore();

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 },
    },
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* 头部欢迎 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-cyan to-accent-blue flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-primary-500">
              欢迎回来，{user?.username || '用户'}
            </h1>
            <p className="text-gray-500 text-sm">
              {isGuest ? '游客模式 · 仅开放智能答疑功能' : 'AI 赋能教育，智能引领未来 🚀'}
            </p>
          </div>
        </div>
      </motion.div>

      {/* 功能卡片 */}
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
      >
        {featureCards.map((card) => {
          const Icon = card.icon;
          const isDisabled = isGuest && card.path !== '/qa';

          return (
            <motion.div
              key={card.path}
              variants={item}
              whileHover={isDisabled ? {} : { y: -8, scale: 1.02 }}
              whileTap={isDisabled ? {} : { scale: 0.98 }}
              onClick={() => !isDisabled && router.push(card.path)}
              className={`relative overflow-hidden rounded-2xl p-6 cursor-pointer group transition-shadow duration-300 ${
                isDisabled
                  ? 'bg-gray-100 opacity-60 cursor-not-allowed'
                  : 'bg-white shadow-card hover:shadow-card-hover'
              }`}
            >
              {/* 背景渐变装饰 */}
              <div
                className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl opacity-10 group-hover:opacity-20 transition-opacity bg-gradient-to-br ${card.gradient}`}
              />

              <div className="relative z-10">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-3xl">{card.emoji}</span>
                  {!isDisabled && (
                    <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 group-hover:translate-x-1 transition-all" />
                  )}
                </div>

                <h3 className="text-lg font-bold text-gray-800 mb-1">{card.title}</h3>
                <p className="text-sm text-gray-500 mb-3">{card.description}</p>

                <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r ${card.gradient} text-white`}>
                  <Zap className="w-3 h-3" />
                  {card.stats}
                </div>
              </div>
            </motion.div>
          );
        })}
      </motion.div>

      {/* 核心指标 */}
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
      >
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={i}
              variants={item}
              className="bg-white rounded-xl p-4 shadow-card"
            >
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg bg-gray-50 flex items-center justify-center ${stat.color}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <motion.p
                    className="text-2xl font-bold text-gray-800"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 + i * 0.1 }}
                  >
                    {stat.value}
                  </motion.p>
                  <p className="text-xs text-gray-500">{stat.label}</p>
                </div>
              </div>
            </motion.div>
          );
        })}
      </motion.div>

      {/* 快捷操作 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="bg-white rounded-2xl p-6 shadow-card"
      >
        <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-accent-blue" />
          快捷操作
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={() => router.push('/qa')}
            className="flex items-center gap-3 p-4 rounded-xl border-2 border-gray-100 hover:border-accent-blue/30 hover:bg-accent-blue/5 transition-all group"
          >
            <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center group-hover:bg-blue-100 transition-colors">
              <MessageSquare className="w-5 h-5 text-blue-500" />
            </div>
            <div className="text-left">
              <p className="font-medium text-gray-800">快速提问</p>
              <p className="text-xs text-gray-500">AI 智能答疑</p>
            </div>
          </button>

          <button
            onClick={() => router.push('/courseware')}
            disabled={isGuest}
            className="flex items-center gap-3 p-4 rounded-xl border-2 border-gray-100 hover:border-purple-500/30 hover:bg-purple-50 transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center group-hover:bg-purple-100 transition-colors">
              <FileText className="w-5 h-5 text-purple-500" />
            </div>
            <div className="text-left">
              <p className="font-medium text-gray-800">生成课件</p>
              <p className="text-xs text-gray-500">一键生成 PPT</p>
            </div>
          </button>

          <button
            onClick={() => router.push('/analysis')}
            disabled={isGuest}
            className="flex items-center gap-3 p-4 rounded-xl border-2 border-gray-100 hover:border-orange-500/30 hover:bg-orange-50 transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center group-hover:bg-orange-100 transition-colors">
              <BarChart3 className="w-5 h-5 text-orange-500" />
            </div>
            <div className="text-left">
              <p className="font-medium text-gray-800">学情报告</p>
              <p className="text-xs text-gray-500">AI 分析生成</p>
            </div>
          </button>
        </div>
      </motion.div>
    </div>
  );
}

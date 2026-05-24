'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore, useUIStore } from '@/stores';
import Sidebar from '@/components/layout/Sidebar';
import ChatInterface from '@/components/chat/ChatInterface';

export default function QAPage() {
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
        <ChatInterface />
      </main>
    </div>
  );
}

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore, useUIStore } from '@/stores';
import Sidebar from '@/components/layout/Sidebar';
import CoursewareStudio from '@/components/courseware/CoursewareStudio';

export default function CoursewarePage() {
  const router = useRouter();
  const { isLoggedIn, isGuest } = useAuthStore();
  const { sidebarOpen } = useUIStore();

  useEffect(() => {
    if (!isLoggedIn) router.push('/');
  }, [isLoggedIn, router]);

  if (!isLoggedIn) return null;

  return (
    <div className="flex min-h-screen bg-surface-secondary">
      <Sidebar />
      <main className={`flex-1 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-20'}`}>
        <CoursewareStudio />
      </main>
    </div>
  );
}

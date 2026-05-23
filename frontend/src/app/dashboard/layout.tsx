'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Rss, 
  LogOut, 
  User, 
  Menu, 
  X,
  Activity,
  MessageSquareQuote
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  const navLinks = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Live Feed', href: '/dashboard/feed', icon: Rss },
    { name: 'AI Chat Assistant', href: '/dashboard/chat', icon: MessageSquareQuote },
  ];


  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-zinc-950 text-zinc-50 overflow-hidden">
        {/* Sidebar for desktop */}
        <aside className="hidden md:flex md:flex-col md:w-64 bg-zinc-900 border-r border-zinc-800 p-4">
          <div className="flex items-center gap-2 px-2 py-4 border-b border-zinc-800 mb-6">
            <Activity className="h-6 w-6 text-blue-500 animate-pulse" />
            <span className="text-xl font-bold tracking-wider bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
              NEURALPULSE
            </span>
          </div>

          <nav className="flex-1 space-y-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.name}
                  href={link.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive 
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' 
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {link.name}
                </Link>
              );
            })}
          </nav>

          <div className="border-t border-zinc-800 pt-4 mt-auto">
            {user && (
              <div className="flex items-center gap-2 px-3 py-2 mb-2">
                <User className="h-4 w-4 text-zinc-400" />
                <span className="text-xs text-zinc-400 truncate max-w-[180px]">{user.email}</span>
              </div>
            )}
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </aside>

        {/* Mobile nav header */}
        <div className="flex flex-col flex-1 overflow-hidden">
          <header className="md:hidden flex items-center justify-between bg-zinc-900 border-b border-zinc-800 px-4 py-3">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-500" />
              <span className="text-lg font-bold tracking-wider text-white">NEURALPULSE</span>
            </div>
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-1 rounded-lg text-zinc-400 hover:bg-zinc-800"
            >
              {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </header>

          {/* Mobile menu overlay */}
          {isMobileMenuOpen && (
            <div className="md:hidden fixed inset-0 z-40 bg-zinc-950/90 flex flex-col p-6 pt-20">
              <nav className="space-y-3">
                {navLinks.map((link) => {
                  const Icon = link.icon;
                  const isActive = pathname === link.href;
                  return (
                    <Link
                      key={link.name}
                      href={link.href}
                      onClick={() => setIsMobileMenuOpen(false)}
                      className={`flex items-center gap-4 px-4 py-3 rounded-lg text-base font-medium transition-all ${
                        isActive 
                          ? 'bg-blue-600 text-white' 
                          : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
                      }`}
                    >
                      <Icon className="h-5 w-5" />
                      {link.name}
                    </Link>
                  );
                })}
                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    handleLogout();
                  }}
                  className="flex items-center gap-4 w-full px-4 py-3 rounded-lg text-base font-medium text-red-400 hover:bg-red-500/10 transition-colors"
                >
                  <LogOut className="h-5 w-5" />
                  Logout
                </button>
              </nav>
            </div>
          )}

          {/* Main Content Workspace */}
          <main className="flex-1 overflow-y-auto p-4 md:p-8 bg-zinc-950">
            {children}
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}

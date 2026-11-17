/**
 * Global authenticated layout shell.
 * Includes top navigation bar, container constraints, and page outlet.
 */

import React from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';

export const AppLayout: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      <Navbar />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <Outlet />
      </main>
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        Snack Overflow &copy; {new Date().getFullYear()} &bull; Office Pantry Management System
      </footer>
    </div>
  );
};

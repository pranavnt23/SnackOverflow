/**
 * Application Root Component.
 * Configures routing, authentication, and global toast notifications.
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './components/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { SnacksPage } from './pages/SnacksPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            {/* Public Auth Route */}
            <Route path="/login" element={<LoginPage />} />

            {/* Authenticated Protected Shell */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/snacks" element={<SnacksPage />} />
              </Route>
            </Route>

            {/* Catch-all redirect */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;

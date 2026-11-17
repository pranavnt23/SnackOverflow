/**
 * Login Page with form validation, loading indicators, structured error feedback,
 * and quick-fill demo credentials.
 */

import React, { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { ApiError } from '../api/client';
import { Cookie, Lock, Mail, Loader2, AlertCircle, Sparkles, KeyRound } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const { success } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [formErrors, setFormErrors] = useState<{ email?: string; password?: string }>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // If already logged in, redirect to destination or home
  if (isAuthenticated) {
    const from = (location.state as any)?.from?.pathname || '/';
    return <Navigate to={from} replace />;
  }

  const validateForm = (): boolean => {
    const errors: { email?: string; password?: string } = {};
    const trimmedEmail = email.trim();

    if (!trimmedEmail) {
      errors.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errors.email = 'Please provide a valid email format';
    }

    if (!password) {
      errors.password = 'Password is required';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      await login(email, password);
      success('Welcome back to Snack Overflow!');
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setApiError(err.message);
      } else {
        setApiError('An unexpected connection error occurred. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const fillCredentials = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setFormErrors({});
    setApiError(null);
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-gradient-to-b from-orange-50/50 via-slate-50 to-slate-100">
      <div className="sm:mx-auto sm:w-full sm:max-w-md px-4">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center">
          <div className="w-14 h-14 rounded-2xl bg-orange-600 flex items-center justify-center text-white shadow-md shadow-orange-200 mb-3">
            <Cookie className="w-8 h-8" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Snack<span className="text-orange-600">Overflow</span>
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Sign in to track, consume, and vote on office pantry snacks
          </p>
        </div>

        {/* Login Card */}
        <div className="mt-8 bg-white py-8 px-5 sm:px-10 shadow-xl shadow-slate-200/50 sm:rounded-2xl border border-slate-200/80">
          {/* API Error Alert Banner */}
          {apiError && (
            <div
              role="alert"
              className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3 text-sm text-rose-900 animate-in fade-in duration-200"
            >
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="leading-tight font-medium">{apiError}</div>
            </div>
          )}

          <form className="space-y-5" onSubmit={handleSubmit} noValidate>
            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Work Email
              </label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (formErrors.email) setFormErrors((prev) => ({ ...prev, email: undefined }));
                  }}
                  className={`block w-full pl-10 pr-3 py-2.5 sm:text-sm rounded-xl border bg-slate-50/50 text-slate-900 placeholder:text-slate-400 transition-colors focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 ${
                    formErrors.email
                      ? 'border-rose-400 focus:border-rose-500'
                      : 'border-slate-300 focus:border-orange-500'
                  }`}
                  placeholder="e.g. member@snack.local"
                  disabled={isSubmitting}
                />
              </div>
              {formErrors.email && (
                <p className="mt-1.5 text-xs text-rose-600 font-medium">{formErrors.email}</p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Password
              </label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (formErrors.password) setFormErrors((prev) => ({ ...prev, password: undefined }));
                  }}
                  className={`block w-full pl-10 pr-3 py-2.5 sm:text-sm rounded-xl border bg-slate-50/50 text-slate-900 placeholder:text-slate-400 transition-colors focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 ${
                    formErrors.password
                      ? 'border-rose-400 focus:border-rose-500'
                      : 'border-slate-300 focus:border-orange-500'
                  }`}
                  placeholder="••••••••••••"
                  disabled={isSubmitting}
                />
              </div>
              {formErrors.password && (
                <p className="mt-1.5 text-xs text-rose-600 font-medium">{formErrors.password}</p>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-bold text-white bg-orange-600 hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 transition-colors disabled:opacity-60 disabled:cursor-not-allowed mt-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Signing in...</span>
                </>
              ) : (
                <span>Sign In</span>
              )}
            </button>
          </form>

          {/* Demo Credentials Hint Box */}
          <div className="mt-6 pt-6 border-t border-slate-100">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                <Sparkles className="w-3.5 h-3.5 text-orange-500" />
                <span>Demo Credentials (Click to Auto-Fill)</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {/* Admin Quick-Fill */}
                <button
                  type="button"
                  onClick={() => fillCredentials('admin@snack.local', 'Admin@123')}
                  className="flex flex-col text-left p-2.5 rounded-lg bg-white border border-slate-200 hover:border-purple-300 hover:bg-purple-50/50 transition-colors group"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 group-hover:text-purple-700">
                      Admin Account
                    </span>
                    <KeyRound className="w-3 h-3 text-slate-400 group-hover:text-purple-600" />
                  </div>
                  <span className="text-slate-500 font-mono text-[11px] mt-0.5">admin@snack.local</span>
                  <span className="text-slate-400 font-mono text-[10px]">Admin@123</span>
                </button>

                {/* Member Quick-Fill */}
                <button
                  type="button"
                  onClick={() => fillCredentials('member@snack.local', 'Member@123')}
                  className="flex flex-col text-left p-2.5 rounded-lg bg-white border border-slate-200 hover:border-orange-300 hover:bg-orange-50/50 transition-colors group"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 group-hover:text-orange-700">
                      Member Account
                    </span>
                    <KeyRound className="w-3 h-3 text-slate-400 group-hover:text-orange-600" />
                  </div>
                  <span className="text-slate-500 font-mono text-[11px] mt-0.5">member@snack.local</span>
                  <span className="text-slate-400 font-mono text-[10px]">Member@123</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

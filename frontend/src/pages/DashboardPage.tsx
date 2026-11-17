/**
 * Dashboard Page.
 * Displays pantry summary metrics, Snack of the Week spotlight card,
 * and role-aware quick actions.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { apiClient, ApiError } from '../api/client';
import { SnackSummary } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';
import {
  Trophy,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Package,
  Layers,
  ArrowRight,
  RefreshCw,
  Sparkles,
  ShieldAlert,
  ThumbsUp,
  Tag,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user, isAdmin } = useAuth();
  const [summary, setSummary] = useState<SnackSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<SnackSummary>('/snacks/summary');
      setSummary(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load pantry dashboard summary. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Pantry Dashboard
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Real-time stock monitoring & snack favorites for{' '}
            <span className="font-semibold text-slate-800">{user?.name}</span>.
          </p>
        </div>

        {/* Refresh / Timestamp CTA */}
        <div className="flex items-center gap-3">
          <button
            onClick={fetchSummary}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-orange-500 shadow-sm transition-all disabled:opacity-50"
            title="Refresh dashboard metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <Link
            to="/snacks"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white bg-orange-600 hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500 shadow-sm shadow-orange-200 transition-colors"
          >
            <span>Open Pantry</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Error State with Retry Button */}
      {error && (
        <div
          role="alert"
          className="p-5 rounded-2xl bg-rose-50 border border-rose-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-rose-900 shadow-sm"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-100 flex items-center justify-center shrink-0 text-rose-600">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold">Failed to load dashboard metrics</h2>
              <p className="text-xs text-rose-700 mt-0.5">{error}</p>
            </div>
          </div>
          <button
            onClick={fetchSummary}
            className="px-4 py-2 text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-sm transition-colors"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Loading Skeletons */}
      {isLoading && !summary && (
        <div className="space-y-6">
          {/* Skeleton metric cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm animate-pulse space-y-3"
              >
                <div className="w-8 h-8 rounded-xl bg-slate-200" />
                <div className="h-4 w-20 bg-slate-200 rounded" />
                <div className="h-8 w-14 bg-slate-200 rounded" />
              </div>
            ))}
          </div>

          {/* Skeleton Snack of the Week */}
          <div className="p-6 sm:p-8 rounded-2xl bg-white border border-slate-200/80 shadow-sm animate-pulse space-y-4">
            <div className="h-6 w-44 bg-slate-200 rounded" />
            <div className="h-10 w-72 bg-slate-200 rounded" />
            <div className="h-4 w-32 bg-slate-200 rounded" />
          </div>
        </div>
      )}

      {/* Loaded Dashboard Content */}
      {summary && (
        <>
          {/* Metric Summary Cards Grid */}
          <section aria-label="Stock Summary Metrics">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
              {/* 1. Stocked Card (Green Styling) */}
              <div className="p-5 rounded-2xl bg-emerald-50/70 border border-emerald-200/80 shadow-sm transition-transform hover:-translate-y-0.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">
                    Stocked
                  </span>
                  <div className="w-8 h-8 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <span className="text-3xl sm:text-4xl font-black text-emerald-900 tracking-tight">
                    {summary.stocked}
                  </span>
                  <p className="text-xs text-emerald-700 mt-1 font-medium">Abundant supply</p>
                </div>
              </div>

              {/* 2. Running Low Card (Amber Styling) */}
              <div className="p-5 rounded-2xl bg-amber-50/70 border border-amber-200/80 shadow-sm transition-transform hover:-translate-y-0.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-amber-800">
                    Running Low
                  </span>
                  <div className="w-8 h-8 rounded-xl bg-amber-100 flex items-center justify-center text-amber-700">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <span className="text-3xl sm:text-4xl font-black text-amber-900 tracking-tight">
                    {summary.running_low}
                  </span>
                  <p className="text-xs text-amber-700 mt-1 font-medium">Restock recommended</p>
                </div>
              </div>

              {/* 3. Gone Card (Red Styling) */}
              <div className="p-5 rounded-2xl bg-rose-50/70 border border-rose-200/80 shadow-sm transition-transform hover:-translate-y-0.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-rose-800">
                    Gone
                  </span>
                  <div className="w-8 h-8 rounded-xl bg-rose-100 flex items-center justify-center text-rose-700">
                    <Flame className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <span className="text-3xl sm:text-4xl font-black text-rose-900 tracking-tight">
                    {summary.gone}
                  </span>
                  <p className="text-xs text-rose-700 mt-1 font-medium">Pantry empty</p>
                </div>
              </div>

              {/* 4. Total Card (Neutral Styling) */}
              <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm transition-transform hover:-translate-y-0.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                    Total Tracked
                  </span>
                  <div className="w-8 h-8 rounded-xl bg-slate-100 flex items-center justify-center text-slate-700">
                    <Layers className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <span className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
                    {summary.total}
                  </span>
                  <p className="text-xs text-slate-500 mt-1 font-medium">Distinct pantry items</p>
                </div>
              </div>
            </div>
          </section>

          {/* Snack of the Week Spotlight Card */}
          <section aria-label="Snack of the Week">
            {summary.snack_of_the_week ? (
              <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-amber-500 via-orange-500 to-amber-600 p-6 sm:p-8 text-white shadow-xl shadow-orange-500/10">
                {/* Background decorative glow */}
                <div className="absolute top-0 right-0 -mr-10 -mt-10 w-64 h-64 rounded-full bg-white/10 blur-2xl pointer-events-none" />

                <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                  <div className="space-y-3 max-w-xl">
                    {/* Crown badge */}
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-white/20 backdrop-blur-md text-amber-100 border border-white/20 tracking-wider uppercase">
                      <Trophy className="w-3.5 h-3.5 text-yellow-300" />
                      <span>Snack of the Week</span>
                    </div>

                    {/* Snack Title */}
                    <div>
                      <h2 className="text-2xl sm:text-4xl font-black tracking-tight text-white drop-shadow-sm">
                        {summary.snack_of_the_week.name}
                      </h2>
                      <div className="flex flex-wrap items-center gap-2.5 mt-2">
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-semibold bg-white/15 text-white capitalize">
                          <Tag className="w-3 h-3 text-orange-200" />
                          {summary.snack_of_the_week.category}
                        </span>
                        <StatusBadge
                          status={summary.snack_of_the_week.status}
                          size="sm"
                          className="bg-white/90 shadow-sm"
                        />
                        <span className="text-xs text-orange-100 font-medium">
                          {summary.snack_of_the_week.quantity} remaining in stock
                        </span>
                      </div>
                    </div>

                    <p className="text-sm text-orange-100 leading-relaxed">
                      Crowned as the most beloved pantry snack with the highest employee votes this
                      week! Grab yours before someone beats you to the last packet.
                    </p>
                  </div>

                  {/* Vote Count & Action Button */}
                  <div className="flex flex-row md:flex-col items-center md:items-end justify-between gap-4 pt-4 md:pt-0 border-t md:border-t-0 border-white/20">
                    <div className="flex items-center gap-2 bg-white/15 backdrop-blur-sm px-4 py-2 rounded-2xl border border-white/20">
                      <ThumbsUp className="w-5 h-5 text-yellow-300" />
                      <div className="flex flex-col">
                        <span className="text-xs text-orange-100 uppercase font-bold tracking-wider leading-none">
                          Votes
                        </span>
                        <span className="text-2xl font-black text-white leading-tight">
                          {summary.snack_of_the_week.vote_count}
                        </span>
                      </div>
                    </div>

                    <Link
                      to={`/snacks?search=${encodeURIComponent(summary.snack_of_the_week.name)}`}
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-white text-orange-600 hover:bg-orange-50 focus:outline-none focus:ring-2 focus:ring-white shadow-md transition-all hover:scale-[1.02]"
                    >
                      <span>Vote & Consume</span>
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              </div>
            ) : (
              /* Empty State when no votes exist */
              <div className="p-8 sm:p-10 rounded-3xl bg-white border border-dashed border-slate-300 text-center shadow-sm">
                <div className="w-14 h-14 rounded-2xl bg-amber-50 text-amber-600 border border-amber-200 flex items-center justify-center mx-auto mb-4">
                  <Sparkles className="w-7 h-7" />
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-slate-900">
                  No Snack of the Week Yet!
                </h3>
                <p className="mt-1 text-sm text-slate-500 max-w-md mx-auto">
                  No votes have been cast in the pantry yet. Cast your vote on your favorite snack
                  to help crown the inaugural Snack of the Week!
                </p>
                <div className="mt-5">
                  <Link
                    to="/snacks"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-orange-600 hover:bg-orange-700 shadow-sm transition-colors"
                  >
                    <span>Browse Pantry & Cast Vote</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            )}
          </section>

          {/* Role-Aware UI Section */}
          <section aria-label="Pantry Navigation & Role Controls">
            {isAdmin ? (
              /* Admin-Only Management Card */
              <div className="p-6 rounded-2xl bg-purple-50/60 border border-purple-200/80 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center shrink-0 mt-0.5">
                      <ShieldAlert className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-bold text-purple-950">
                          Administrator Pantry Management
                        </h3>
                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-purple-200 text-purple-800">
                          Admin Active
                        </span>
                      </div>
                      <p className="text-xs text-purple-800 mt-1 max-w-2xl leading-relaxed">
                        As an administrator, you have permission to restock inventory, add new snack
                        items to the catalog, adjust low-stock thresholds, and delete retired snacks.
                      </p>
                    </div>
                  </div>

                  <Link
                    to="/snacks"
                    className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-700 text-white shadow-sm transition-colors shrink-0"
                  >
                    <Package className="w-4 h-4" />
                    <span>Manage Pantry Inventory</span>
                  </Link>
                </div>
              </div>
            ) : (
              /* Member Quick Hint Card */
              <div className="p-5 rounded-2xl bg-slate-100/70 border border-slate-200 flex items-center justify-between gap-4 text-xs text-slate-600">
                <div className="flex items-center gap-3">
                  <Package className="w-5 h-5 text-orange-600 shrink-0" />
                  <span>
                    Need a mid-day energy boost? Head over to the pantry catalogue to claim snacks
                    or vote for your top craving.
                  </span>
                </div>
                <Link
                  to="/snacks"
                  className="font-bold text-orange-600 hover:text-orange-700 hover:underline shrink-0"
                >
                  Explore Pantry &rarr;
                </Link>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
};

/**
 * Pantry Snacks Listing Page.
 * Displays snacks with status filters, category pills, search bar,
 * real-time voting, and atomic consumption.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiClient, ApiError } from '../api/client';
import { PaginatedSnacks, Snack, SnackCategory, SnackStatus } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  Search,
  SlidersHorizontal,
  ThumbsUp,
  Utensils,
  AlertCircle,
  Loader2,
  PackageX,
} from 'lucide-react';

const CATEGORIES: { label: string; value: SnackCategory | 'all' }[] = [
  { label: 'All Items', value: 'all' },
  { label: 'Sweet', value: 'sweet' },
  { label: 'Savoury', value: 'savoury' },
  { label: 'Drinks', value: 'drink' },
  { label: 'Healthy-ish', value: 'healthy-ish' },
];

const STATUS_FILTERS: { label: string; value: SnackStatus | 'all' }[] = [
  { label: 'All Statuses', value: 'all' },
  { label: 'Stocked', value: 'stocked' },
  { label: 'Running Low', value: 'running_low' },
  { label: 'Gone', value: 'gone' },
];

export const SnacksPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const { success, error: toastError } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [data, setData] = useState<PaginatedSnacks | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form states
  const search = searchParams.get('search') || '';
  const category = (searchParams.get('category') as SnackCategory | null) || 'all';
  const status = (searchParams.get('status') as SnackStatus | null) || 'all';
  const page = parseInt(searchParams.get('page') || '1', 10);

  // Action loading states
  const [actingSnackId, setActingSnackId] = useState<number | null>(null);

  const fetchSnacks = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const params: Record<string, any> = {
        page,
        page_size: 12,
      };
      if (search.trim()) params.search = search.trim();
      if (category !== 'all') params.category = category;
      if (status !== 'all') params.status = status;

      const res = await apiClient.get<PaginatedSnacks>('/snacks', { params });
      setData(res);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to load pantry snacks.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [category, status, search, page]);

  useEffect(() => {
    fetchSnacks();
  }, [fetchSnacks]);

  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (!value || value === 'all') {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    next.set('page', '1');
    setSearchParams(next);
  };

  // Atomic consumption handler
  const handleConsume = async (snack: Snack) => {
    setActingSnackId(snack.id);
    try {
      const updatedSnack = await apiClient.post<Snack>(`/snacks/${snack.id}/consume`, { amount: 1 });
      success(`Enjoy your ${snack.name}! Packets left: ${updatedSnack.quantity}`);
      // Optimistically update snack in local state
      setData((prev) =>
        prev
          ? {
              ...prev,
              items: prev.items.map((s) => (s.id === snack.id ? updatedSnack : s)),
            }
          : null
      );
    } catch (err) {
      if (err instanceof ApiError) {
        toastError(err.message);
      } else {
        toastError('Failed to consume snack.');
      }
      // Re-fetch to ensure sync with DB state
      fetchSnacks();
    } finally {
      setActingSnackId(null);
    }
  };

  // Voting toggle handler
  const handleVoteToggle = async (snack: Snack) => {
    setActingSnackId(snack.id);
    try {
      if (snack.has_voted) {
        await apiClient.delete(`/snacks/${snack.id}/vote`);
        success(`Removed your vote for ${snack.name}.`);
      } else {
        await apiClient.post(`/snacks/${snack.id}/vote`);
        success(`Vote recorded for ${snack.name}!`);
      }
      fetchSnacks();
    } catch (err) {
      if (err instanceof ApiError) {
        toastError(err.message);
      } else {
        toastError('Failed to process vote.');
      }
    } finally {
      setActingSnackId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Pantry Catalogue
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Claim available snacks, check stock levels, and vote for your favorites.
          </p>
        </div>

        {/* Search Input */}
        <div className="relative max-w-xs w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => updateParam('search', e.target.value)}
            placeholder="Search snacks..."
            className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 shadow-sm"
          />
        </div>
      </div>

      {/* Filter Chips Bar */}
      <div className="flex flex-wrap items-center gap-2 pt-1 pb-2">
        <div className="flex items-center gap-1.5 text-xs font-bold text-slate-500 uppercase tracking-wider mr-2">
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Filters:</span>
        </div>

        {/* Category Pills */}
        {CATEGORIES.map((cat) => (
          <button
            key={cat.value}
            onClick={() => updateParam('category', cat.value)}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
              category === cat.value
                ? 'bg-orange-600 text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            {cat.label}
          </button>
        ))}

        <div className="h-4 w-px bg-slate-200 mx-1 hidden sm:block" />

        {/* Status Dropdown Filter */}
        <select
          value={status}
          onChange={(e) => updateParam('status', e.target.value)}
          className="px-3 py-1.5 rounded-xl text-xs font-bold bg-white text-slate-700 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-orange-500 shadow-sm"
          aria-label="Filter snacks by stock status"
        >
          {STATUS_FILTERS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* Error State */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-between text-rose-800 text-sm">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={fetchSnacks} className="font-bold underline hover:no-underline">
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeletons */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div
              key={i}
              className="p-5 bg-white border border-slate-200/80 rounded-2xl shadow-sm animate-pulse space-y-4"
            >
              <div className="h-4 bg-slate-200 rounded w-1/3" />
              <div className="h-6 bg-slate-200 rounded w-3/4" />
              <div className="h-10 bg-slate-100 rounded" />
            </div>
          ))}
        </div>
      )}

      {/* Snack Grid */}
      {!isLoading && data && data.items.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">
          {data.items.map((snack) => {
            const isProcessing = actingSnackId === snack.id;
            const isGone = snack.quantity === 0;

            return (
              <div
                key={snack.id}
                className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
              >
                <div>
                  {/* Top Bar: Category & Status */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                      {snack.category}
                    </span>
                    <StatusBadge status={snack.status} size="sm" />
                  </div>

                  {/* Snack Name */}
                  <h3 className="font-bold text-slate-900 text-base leading-snug">
                    {snack.name}
                  </h3>

                  {/* Stock Quantity */}
                  <div className="mt-2 text-xs text-slate-500 flex items-center justify-between">
                    <span>
                      Quantity:{' '}
                      <strong className={`font-semibold ${isGone ? 'text-rose-600' : 'text-slate-800'}`}>
                        {snack.quantity}
                      </strong>{' '}
                      packets
                    </span>
                    {isAdmin && (
                      <span className="text-[10px] text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded font-mono">
                        threshold: {snack.low_stock_threshold}
                      </span>
                    )}
                  </div>
                </div>

                {/* Bottom Actions: Consume & Vote */}
                <div className="mt-5 pt-4 border-t border-slate-100 flex items-center gap-2">
                  {/* Consume Button */}
                  <button
                    onClick={() => handleConsume(snack)}
                    disabled={isGone || isProcessing}
                    className={`flex-1 inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs font-bold transition-colors ${
                      isGone
                        ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                        : 'bg-orange-600 hover:bg-orange-700 text-white shadow-sm shadow-orange-100'
                    }`}
                  >
                    {isProcessing ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Utensils className="w-3.5 h-3.5" />
                    )}
                    <span>{isGone ? 'Gone' : 'Take 1'}</span>
                  </button>

                  {/* Vote Button */}
                  <button
                    onClick={() => handleVoteToggle(snack)}
                    disabled={isProcessing}
                    className={`inline-flex items-center gap-1.5 py-2 px-3 rounded-xl text-xs font-bold border transition-colors ${
                      snack.has_voted
                        ? 'bg-amber-50 border-amber-300 text-amber-800'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                    title={snack.has_voted ? 'Remove your vote' : 'Vote for this snack'}
                  >
                    <ThumbsUp
                      className={`w-3.5 h-3.5 ${
                        snack.has_voted ? 'text-amber-600 fill-amber-500' : 'text-slate-400'
                      }`}
                    />
                    <span>{snack.vote_count}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && data && data.items.length === 0 && (
        <div className="p-12 text-center bg-white border border-dashed border-slate-300 rounded-3xl space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
            <PackageX className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-800">No snacks match your query</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Try adjusting your search terms, changing the category, or clearing the status filter.
          </p>
          <button
            onClick={() => {
              setSearchParams(new URLSearchParams());
            }}
            className="text-xs font-bold text-orange-600 hover:text-orange-700 underline"
          >
            Clear all filters
          </button>
        </div>
      )}
    </div>
  );
};

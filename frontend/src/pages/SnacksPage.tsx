/**
 * Pantry Snacks Catalogue Page.
 * Fully API-driven with:
 * - Debounced search input (~300ms)
 * - Category and Status SQL filtering
 * - Server-side pagination and synchronized URL query parameters
 * - Responsive desktop Table and mobile Cards
 * - In-row atomic Consume and Vote/Unvote toggle
 * - Admin-only Add, Edit, Restock, and Delete operations
 */

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiClient, ApiError } from '../api/client';
import {
  PaginatedSnacks,
  Snack,
  SnackCategory,
  SnackStatus,
  VoteStatusResponse,
} from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { AddSnackModal } from '../components/modals/AddSnackModal';
import { EditSnackModal } from '../components/modals/EditSnackModal';
import { RestockModal } from '../components/modals/RestockModal';
import { DeleteConfirmModal } from '../components/modals/DeleteConfirmModal';
import {
  Search,
  ThumbsUp,
  Utensils,
  Plus,
  PackagePlus,
  Edit,
  Trash2,
  AlertTriangle,
  Loader2,
  PackageX,
  ChevronLeft,
  ChevronRight,
  Minus,
  Plus as PlusIcon,
  Tag,
} from 'lucide-react';

const CATEGORIES: { label: string; value: SnackCategory | 'all' }[] = [
  { label: 'All Categories', value: 'all' },
  { label: 'Sweet', value: 'sweet' },
  { label: 'Savoury', value: 'savoury' },
  { label: 'Drinks', value: 'drink' },
  { label: 'Healthy-ish', value: 'healthy-ish' },
];

const STATUSES: { label: string; value: SnackStatus | 'all' }[] = [
  { label: 'All Statuses', value: 'all' },
  { label: 'Stocked', value: 'stocked' },
  { label: 'Running Low', value: 'running_low' },
  { label: 'Gone', value: 'gone' },
];

const PAGE_SIZE = 10;

export const SnacksPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const { success, error: toastError } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL Query State
  const querySearch = searchParams.get('search') || '';
  const queryCategory = (searchParams.get('category') as SnackCategory | 'all') || 'all';
  const queryStatus = (searchParams.get('status') as SnackStatus | 'all') || 'all';
  const queryPage = parseInt(searchParams.get('page') || '1', 10);

  // Local debounced search state
  const [searchInput, setSearchInput] = useState(querySearch);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Data & Lifecycle States
  const [data, setData] = useState<PaginatedSnacks | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Action Loading & Quantity Pickers
  const [actingSnackId, setActingSnackId] = useState<number | null>(null);
  const [consumeAmounts, setConsumeAmounts] = useState<Record<number, number>>({});

  // Admin Modal States
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingSnack, setEditingSnack] = useState<Snack | null>(null);
  const [restockingSnack, setRestockingSnack] = useState<Snack | null>(null);
  const [deletingSnack, setDeletingSnack] = useState<Snack | null>(null);

  // Synchronize local search input if query param changes externally
  useEffect(() => {
    setSearchInput(querySearch);
  }, [querySearch]);

  // Debounced search handler (~300ms)
  const handleSearchChange = (val: string) => {
    setSearchInput(val);
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);

    debounceTimerRef.current = setTimeout(() => {
      const next = new URLSearchParams(searchParams);
      if (val.trim()) {
        next.set('search', val.trim());
      } else {
        next.delete('search');
      }
      next.set('page', '1');
      setSearchParams(next);
    }, 300);
  };

  // Helper to update URL search params
  const updateQueryParam = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (!value || value === 'all') {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    next.set('page', '1');
    setSearchParams(next);
  };

  const setPage = (newPage: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(newPage));
    setSearchParams(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Server-side Fetcher
  const fetchSnacks = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const params: Record<string, any> = {
        page: queryPage,
        page_size: PAGE_SIZE,
      };
      if (querySearch) params.search = querySearch;
      if (queryCategory !== 'all') params.category = queryCategory;
      if (queryStatus !== 'all') params.status = queryStatus;

      const res = await apiClient.get<PaginatedSnacks>('/snacks', { params });
      setData(res);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to load pantry snacks. Please check your connection.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [queryPage, querySearch, queryCategory, queryStatus]);

  useEffect(() => {
    fetchSnacks();
  }, [fetchSnacks]);

  // Stepper helper for amount picker
  const getConsumeAmount = (snackId: number) => consumeAmounts[snackId] || 1;
  const setConsumeAmount = (snackId: number, amount: number) => {
    const clamped = Math.max(1, Math.min(100, amount));
    setConsumeAmounts((prev) => ({ ...prev, [snackId]: clamped }));
  };

  // Atomic Consume Action
  const handleConsume = async (snack: Snack) => {
    const amount = getConsumeAmount(snack.id);
    setActingSnackId(snack.id);
    try {
      const updated = await apiClient.post<Snack>(`/snacks/${snack.id}/consume`, { amount });
      success(`Enjoyed ${amount} packet${amount > 1 ? 's' : ''} of "${updated.name}"! (${updated.quantity} left)`);

      // Update row locally with response from server
      setData((prev) =>
        prev
          ? {
              ...prev,
              items: prev.items.map((s) => (s.id === updated.id ? updated : s)),
            }
          : null
      );
      // Reset amount picker to 1
      setConsumeAmount(snack.id, 1);
    } catch (err) {
      if (err instanceof ApiError) {
        toastError(err.message);
      } else {
        toastError('Failed to consume snack. Please try again.');
      }
      // Re-fetch to ensure sync with real server state
      fetchSnacks();
    } finally {
      setActingSnackId(null);
    }
  };

  // Vote / Unvote Action
  const handleVoteToggle = async (snack: Snack) => {
    setActingSnackId(snack.id);
    try {
      if (snack.has_voted) {
        const res = await apiClient.delete<VoteStatusResponse>(`/snacks/${snack.id}/vote`);
        success(`Removed vote for "${snack.name}".`);
        setData((prev) =>
          prev
            ? {
                ...prev,
                items: prev.items.map((s) =>
                  s.id === snack.id ? { ...s, vote_count: res.vote_count, has_voted: res.has_voted } : s
                ),
              }
            : null
        );
      } else {
        const res = await apiClient.post<VoteStatusResponse>(`/snacks/${snack.id}/vote`);
        success(`Voted for "${snack.name}"!`);
        setData((prev) =>
          prev
            ? {
                ...prev,
                items: prev.items.map((s) =>
                  s.id === snack.id ? { ...s, vote_count: res.vote_count, has_voted: res.has_voted } : s
                ),
              }
            : null
        );
      }
    } catch (err) {
      if (err instanceof ApiError) {
        toastError(err.message);
      } else {
        toastError('Failed to update vote.');
      }
    } finally {
      setActingSnackId(null);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Header & Admin Add CTA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Pantry Catalogue
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Real-time inventory levels, atomic consumption, and community snack voting.
          </p>
        </div>

        {/* Admin Add Snack Button */}
        {isAdmin && (
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 shadow-sm shadow-purple-200 transition-colors shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>Add New Snack</span>
          </button>
        )}
      </div>

      {/* Filter and Search Bar Controls */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 sm:gap-4 items-center">
          {/* Search Input with Debounce */}
          <div className="md:col-span-5 relative">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search snacks by name..."
              className="w-full pl-10 pr-4 py-2 text-sm bg-slate-50/70 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all placeholder:text-slate-400"
              aria-label="Search snacks by name"
            />
          </div>

          {/* Category Dropdown */}
          <div className="md:col-span-4">
            <select
              value={queryCategory}
              onChange={(e) => updateQueryParam('category', e.target.value)}
              className="w-full px-3.5 py-2 text-sm font-semibold bg-slate-50/70 text-slate-800 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all"
              aria-label="Filter snacks by category"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          {/* Status Dropdown */}
          <div className="md:col-span-3">
            <select
              value={queryStatus}
              onChange={(e) => updateQueryParam('status', e.target.value)}
              className="w-full px-3.5 py-2 text-sm font-semibold bg-slate-50/70 text-slate-800 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all"
              aria-label="Filter snacks by stock status"
            >
              {STATUSES.map((st) => (
                <option key={st.value} value={st.value}>
                  {st.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Active Filter Indicators */}
        {(querySearch || queryCategory !== 'all' || queryStatus !== 'all') && (
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100 text-xs">
            <span className="text-slate-400 font-bold uppercase tracking-wider text-[10px]">Active Filters:</span>
            {querySearch && (
              <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium">
                Search: "{querySearch}"
              </span>
            )}
            {queryCategory !== 'all' && (
              <span className="px-2 py-0.5 rounded-md bg-orange-50 text-orange-700 font-medium capitalize">
                Category: {queryCategory}
              </span>
            )}
            {queryStatus !== 'all' && (
              <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium capitalize">
                Status: {queryStatus.replace('_', ' ')}
              </span>
            )}
            <button
              onClick={() => setSearchParams(new URLSearchParams())}
              className="ml-auto font-bold text-orange-600 hover:text-orange-700 underline text-xs"
            >
              Clear All Filters
            </button>
          </div>
        )}
      </div>

      {/* Error State with Retry Button */}
      {errorMessage && (
        <div
          role="alert"
          className="p-5 rounded-2xl bg-rose-50 border border-rose-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-rose-900 shadow-sm"
        >
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
            <div>
              <p className="text-sm font-bold">Error loading pantry snacks</p>
              <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <button
            onClick={fetchSnacks}
            className="px-4 py-2 text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-sm transition-colors"
          >
            Retry Query
          </button>
        </div>
      )}

      {/* Loading Skeletons */}
      {isLoading && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-4 sm:p-6 space-y-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="animate-pulse flex items-center justify-between py-3 border-b border-slate-100">
              <div className="space-y-2 w-1/3">
                <div className="h-4 bg-slate-200 rounded w-4/5" />
                <div className="h-3 bg-slate-100 rounded w-1/2" />
              </div>
              <div className="h-6 w-20 bg-slate-200 rounded-full" />
              <div className="h-8 w-32 bg-slate-200 rounded-xl" />
            </div>
          ))}
        </div>
      )}

      {/* Main Content: Desktop Table & Mobile Cards */}
      {!isLoading && data && data.items.length > 0 && (
        <div className="space-y-4">
          {/* ======================================================== */}
          {/* DESKTOP TABLE VIEW (Visible md: and up)                   */}
          {/* ======================================================== */}
          <div className="hidden md:block bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50/75 text-xs font-bold uppercase tracking-wider text-slate-500">
                <tr>
                  <th scope="col" className="px-6 py-4">Snack Item</th>
                  <th scope="col" className="px-6 py-4">Category</th>
                  <th scope="col" className="px-6 py-4">Stock Status</th>
                  <th scope="col" className="px-6 py-4">Quantity</th>
                  <th scope="col" className="px-6 py-4 text-center">Votes</th>
                  <th scope="col" className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((snack) => {
                  const isProcessing = actingSnackId === snack.id;
                  const isGone = snack.quantity === 0;
                  const isLow = snack.status === 'running_low';
                  const amount = getConsumeAmount(snack.id);

                  // Row highlighting based on derived stock status
                  const rowClass = isGone
                    ? 'bg-slate-50/90 text-slate-400'
                    : isLow
                    ? 'bg-amber-50/40 hover:bg-amber-50/70 border-l-4 border-l-amber-500'
                    : 'hover:bg-slate-50/80';

                  return (
                    <tr key={snack.id} className={`transition-colors ${rowClass}`}>
                      {/* Name */}
                      <td className="px-6 py-4 font-bold text-slate-900">
                        <div className="flex flex-col">
                          <span className={isGone ? 'line-through text-slate-500' : ''}>{snack.name}</span>
                          {isAdmin && (
                            <span className="text-[11px] font-mono text-purple-700 mt-0.5">
                              ID: {snack.id} &bull; Threshold: {snack.low_stock_threshold}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Category */}
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-700 capitalize">
                          <Tag className="w-3 h-3 text-slate-400" />
                          {snack.category}
                        </span>
                      </td>

                      {/* Status */}
                      <td className="px-6 py-4">
                        <StatusBadge status={snack.status} size="sm" />
                      </td>

                      {/* Quantity */}
                      <td className="px-6 py-4 font-semibold text-slate-800">
                        <span className={`text-base ${isGone ? 'text-rose-600 font-bold' : isLow ? 'text-amber-700 font-bold' : 'text-slate-900'}`}>
                          {snack.quantity}
                        </span>{' '}
                        <span className="text-xs text-slate-500">packets</span>
                      </td>

                      {/* Vote Count & Action */}
                      <td className="px-6 py-4 text-center">
                        <button
                          onClick={() => handleVoteToggle(snack)}
                          disabled={isProcessing}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-colors ${
                            snack.has_voted
                              ? 'bg-amber-50 border-amber-300 text-amber-800 shadow-sm'
                              : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-100'
                          }`}
                          title={snack.has_voted ? 'Withdraw your vote' : 'Vote for this snack'}
                          aria-label={`Vote for ${snack.name}. Current count: ${snack.vote_count}`}
                        >
                          <ThumbsUp
                            className={`w-3.5 h-3.5 ${
                              snack.has_voted ? 'text-amber-600 fill-amber-500' : 'text-slate-400'
                            }`}
                          />
                          <span>{snack.vote_count}</span>
                        </button>
                      </td>

                      {/* Action Buttons: Consume & Admin Controls */}
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {/* Small Amount Stepper & Consume Button */}
                          <div className="inline-flex items-center border border-slate-200 rounded-xl overflow-hidden shadow-sm bg-white">
                            <button
                              type="button"
                              onClick={() => setConsumeAmount(snack.id, amount - 1)}
                              disabled={isGone || amount <= 1 || isProcessing}
                              className="px-2 py-1.5 text-slate-500 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed"
                              aria-label="Decrease consume amount"
                            >
                              <Minus className="w-3 h-3" />
                            </button>
                            <span className="px-2 text-xs font-bold text-slate-800 select-none">
                              {amount}
                            </span>
                            <button
                              type="button"
                              onClick={() => setConsumeAmount(snack.id, amount + 1)}
                              disabled={isGone || amount >= Math.max(1, snack.quantity) || isProcessing}
                              className="px-2 py-1.5 text-slate-500 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed"
                              aria-label="Increase consume amount"
                            >
                              <PlusIcon className="w-3 h-3" />
                            </button>
                          </div>

                          <button
                            onClick={() => handleConsume(snack)}
                            disabled={isGone || isProcessing}
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                              isGone
                                ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
                                : 'bg-orange-600 hover:bg-orange-700 text-white shadow-sm shadow-orange-100'
                            }`}
                            aria-label={`Consume ${amount} packet${amount > 1 ? 's' : ''} of ${snack.name}`}
                          >
                            {isProcessing ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Utensils className="w-3.5 h-3.5" />
                            )}
                            <span>Take</span>
                          </button>

                          {/* Admin Only Dropdown/Buttons */}
                          {isAdmin && (
                            <div className="flex items-center gap-1 pl-2 border-l border-slate-200 ml-1">
                              <button
                                onClick={() => setRestockingSnack(snack)}
                                className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg border border-slate-200 hover:border-emerald-300"
                                title="Restock Snack"
                                aria-label={`Restock ${snack.name}`}
                              >
                                <PackagePlus className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setEditingSnack(snack)}
                                className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-lg border border-slate-200 hover:border-slate-300"
                                title="Edit Snack"
                                aria-label={`Edit ${snack.name}`}
                              >
                                <Edit className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setDeletingSnack(snack)}
                                className="p-1.5 text-rose-600 hover:bg-rose-50 rounded-lg border border-slate-200 hover:border-rose-300"
                                title="Delete Snack"
                                aria-label={`Delete ${snack.name}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* ======================================================== */}
          {/* MOBILE CARDS VIEW (Visible under md: breakpoint)          */}
          {/* ======================================================== */}
          <div className="md:hidden space-y-3.5">
            {data.items.map((snack) => {
              const isProcessing = actingSnackId === snack.id;
              const isGone = snack.quantity === 0;
              const isLow = snack.status === 'running_low';
              const amount = getConsumeAmount(snack.id);

              const cardClass = isGone
                ? 'bg-slate-50/90 border-slate-200 text-slate-500'
                : isLow
                ? 'bg-amber-50/30 border-amber-300 shadow-sm'
                : 'bg-white border-slate-200 shadow-sm';

              return (
                <div key={snack.id} className={`p-4 rounded-2xl border transition-all ${cardClass}`}>
                  {/* Card Top: Category, Status & Votes */}
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                      {snack.category}
                    </span>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={snack.status} size="sm" />
                      <button
                        onClick={() => handleVoteToggle(snack)}
                        disabled={isProcessing}
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-bold border transition-colors ${
                          snack.has_voted
                            ? 'bg-amber-50 border-amber-300 text-amber-800'
                            : 'bg-white border-slate-200 text-slate-600'
                        }`}
                        aria-label={`Vote for ${snack.name}`}
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

                  {/* Snack Name & Quantity */}
                  <div className="my-2">
                    <h3 className={`font-bold text-base ${isGone ? 'line-through text-slate-400' : 'text-slate-900'}`}>
                      {snack.name}
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Stock:{' '}
                      <strong className={`text-sm font-black ${isGone ? 'text-rose-600' : isLow ? 'text-amber-700' : 'text-slate-900'}`}>
                        {snack.quantity}
                      </strong>{' '}
                      packets {isAdmin && `(threshold: ${snack.low_stock_threshold})`}
                    </p>
                  </div>

                  {/* Actions Bar */}
                  <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                    {/* Stepper + Consume */}
                    <div className="flex items-center gap-1.5 flex-1">
                      <div className="inline-flex items-center border border-slate-200 rounded-xl overflow-hidden bg-white">
                        <button
                          type="button"
                          onClick={() => setConsumeAmount(snack.id, amount - 1)}
                          disabled={isGone || amount <= 1 || isProcessing}
                          className="px-2 py-1.5 text-slate-500 hover:bg-slate-100 disabled:opacity-30"
                        >
                          <Minus className="w-3 h-3" />
                        </button>
                        <span className="px-2 text-xs font-bold text-slate-800">{amount}</span>
                        <button
                          type="button"
                          onClick={() => setConsumeAmount(snack.id, amount + 1)}
                          disabled={isGone || amount >= Math.max(1, snack.quantity) || isProcessing}
                          className="px-2 py-1.5 text-slate-500 hover:bg-slate-100 disabled:opacity-30"
                        >
                          <PlusIcon className="w-3 h-3" />
                        </button>
                      </div>

                      <button
                        onClick={() => handleConsume(snack)}
                        disabled={isGone || isProcessing}
                        className={`flex-1 inline-flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-xl text-xs font-bold ${
                          isGone
                            ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                            : 'bg-orange-600 hover:bg-orange-700 text-white'
                        }`}
                      >
                        {isProcessing ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Utensils className="w-3.5 h-3.5" />
                        )}
                        <span>Take</span>
                      </button>
                    </div>

                    {/* Admin Actions (Mobile) */}
                    {isAdmin && (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setRestockingSnack(snack)}
                          className="p-1.5 text-emerald-600 bg-emerald-50 rounded-lg border border-emerald-200"
                          title="Restock"
                        >
                          <PackagePlus className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setEditingSnack(snack)}
                          className="p-1.5 text-slate-600 bg-slate-50 rounded-lg border border-slate-200"
                          title="Edit"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeletingSnack(snack)}
                          className="p-1.5 text-rose-600 bg-rose-50 rounded-lg border border-rose-200"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* ======================================================== */}
          {/* PAGINATION CONTROLS                                      */}
          {/* ======================================================== */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
            {/* Range Text */}
            <div className="text-xs text-slate-500 font-medium">
              Showing{' '}
              <strong className="text-slate-800">
                {(data.page - 1) * data.page_size + 1}
              </strong>{' '}
              to{' '}
              <strong className="text-slate-800">
                {Math.min(data.page * data.page_size, data.total)}
              </strong>{' '}
              of <strong className="text-slate-800">{data.total}</strong> pantry snacks
            </div>

            {/* Buttons */}
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setPage(data.page - 1)}
                disabled={data.page <= 1}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-bold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                aria-label="Go to previous page"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>

              {/* Numbered Page Buttons */}
              {Array.from({ length: data.total_pages }, (_, i) => i + 1)
                .filter((p) => Math.abs(p - data.page) <= 2 || p === 1 || p === data.total_pages)
                .map((pageNum, idx, arr) => {
                  const showEllipsis = idx > 0 && pageNum - arr[idx - 1] > 1;
                  return (
                    <React.Fragment key={pageNum}>
                      {showEllipsis && <span className="px-1 text-slate-400">...</span>}
                      <button
                        onClick={() => setPage(pageNum)}
                        className={`w-8 h-8 rounded-xl text-xs font-bold transition-all ${
                          pageNum === data.page
                            ? 'bg-orange-600 text-white shadow-sm'
                            : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
                        }`}
                        aria-current={pageNum === data.page ? 'page' : undefined}
                      >
                        {pageNum}
                      </button>
                    </React.Fragment>
                  );
                })}

              <button
                onClick={() => setPage(data.page + 1)}
                disabled={data.page >= data.total_pages}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-bold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                aria-label="Go to next page"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && data && data.items.length === 0 && (
        <div className="p-12 text-center bg-white border border-dashed border-slate-300 rounded-3xl space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-orange-50 text-orange-600 flex items-center justify-center mx-auto">
            <PackageX className="w-6 h-6" />
          </div>
          <h2 className="text-base font-bold text-slate-800">No snacks match your filters</h2>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Try adjusting your search query, selecting "All Categories", or resetting the stock status filter.
          </p>
          <button
            onClick={() => {
              setSearchInput('');
              setSearchParams(new URLSearchParams());
            }}
            className="text-xs font-bold text-orange-600 hover:text-orange-700 underline pt-1"
          >
            Clear all filters
          </button>
        </div>
      )}

      {/* Admin Modals */}
      <AddSnackModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSuccess={() => fetchSnacks()}
      />

      <EditSnackModal
        snack={editingSnack}
        isOpen={!!editingSnack}
        onClose={() => setEditingSnack(null)}
        onSuccess={() => fetchSnacks()}
      />

      <RestockModal
        snack={restockingSnack}
        isOpen={!!restockingSnack}
        onClose={() => setRestockingSnack(null)}
        onSuccess={() => fetchSnacks()}
      />

      <DeleteConfirmModal
        snack={deletingSnack}
        isOpen={!!deletingSnack}
        onClose={() => setDeletingSnack(null)}
        onSuccess={() => fetchSnacks()}
      />
    </div>
  );
};

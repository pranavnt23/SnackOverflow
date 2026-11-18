/**
 * Modal component for Admin adding a new snack to the pantry catalogue.
 */

import React, { useState } from 'react';
import { apiClient, ApiError } from '../../api/client';
import { Snack, SnackCategory, SnackCreatePayload } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { X, Loader2, PlusCircle, AlertCircle } from 'lucide-react';

interface AddSnackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (newSnack: Snack) => void;
}

export const AddSnackModal: React.FC<AddSnackModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { success } = useToast();
  const [name, setName] = useState('');
  const [category, setCategory] = useState<SnackCategory>('sweet');
  const [quantity, setQuantity] = useState<number>(10);
  const [threshold, setThreshold] = useState<number>(5);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFieldErrors({});

    const trimmed = name.trim();
    if (!trimmed) {
      setFieldErrors({ name: 'Snack name is required' });
      return;
    }
    if (trimmed.length > 100) {
      setFieldErrors({ name: 'Snack name cannot exceed 100 characters' });
      return;
    }
    if (quantity < 0) {
      setFieldErrors({ quantity: 'Quantity cannot be negative' });
      return;
    }
    if (threshold < 0) {
      setFieldErrors({ threshold: 'Low stock threshold cannot be negative' });
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: SnackCreatePayload = {
        name: trimmed,
        category,
        quantity,
        low_stock_threshold: threshold,
      };
      const createdSnack = await apiClient.post<Snack>('/snacks', payload);
      success(`Added "${createdSnack.name}" to the pantry catalogue.`);
      onSuccess(createdSnack);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.message);
        if (err.details && Array.isArray(err.details)) {
          const map: Record<string, string> = {};
          err.details.forEach((d) => {
            if (d.field) map[d.field] = d.message;
          });
          setFieldErrors(map);
        }
      } else {
        setFormError('Failed to create snack. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-snack-title"
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-2">
            <PlusCircle className="w-5 h-5 text-orange-600" />
            <h2 id="add-snack-title" className="text-base font-bold text-slate-900">
              Add New Pantry Snack
            </h2>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-500"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {formError && (
            <div
              role="alert"
              className="p-3 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-2.5 text-xs text-rose-800 font-medium"
            >
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{formError}</span>
            </div>
          )}

          {/* Name */}
          <div>
            <label htmlFor="snack-name" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
              Snack Name *
            </label>
            <input
              id="snack-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Wasabi Green Peas"
              className={`w-full px-3.5 py-2 text-sm rounded-xl border bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 ${
                fieldErrors.name ? 'border-rose-400 focus:border-rose-500' : 'border-slate-300 focus:border-orange-500'
              }`}
              disabled={isSubmitting}
              autoFocus
            />
            {fieldErrors.name && (
              <p className="mt-1 text-xs text-rose-600 font-medium">{fieldErrors.name}</p>
            )}
          </div>

          {/* Category */}
          <div>
            <label htmlFor="snack-category" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
              Category *
            </label>
            <select
              id="snack-category"
              value={category}
              onChange={(e) => setCategory(e.target.value as SnackCategory)}
              className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-300 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500"
              disabled={isSubmitting}
            >
              <option value="sweet">Sweet</option>
              <option value="savoury">Savoury</option>
              <option value="drink">Drink</option>
              <option value="healthy-ish">Healthy-ish</option>
            </select>
          </div>

          {/* Stock & Threshold Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="snack-quantity" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Initial Stock *
              </label>
              <input
                id="snack-quantity"
                type="number"
                min="0"
                value={quantity}
                onChange={(e) => setQuantity(parseInt(e.target.value || '0', 10))}
                className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-300 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500"
                disabled={isSubmitting}
              />
              {fieldErrors.quantity && (
                <p className="mt-1 text-xs text-rose-600 font-medium">{fieldErrors.quantity}</p>
              )}
            </div>

            <div>
              <label htmlFor="snack-threshold" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Low-Stock Threshold *
              </label>
              <input
                id="snack-threshold"
                type="number"
                min="0"
                value={threshold}
                onChange={(e) => setThreshold(parseInt(e.target.value || '0', 10))}
                className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-300 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500"
                disabled={isSubmitting}
              />
              {fieldErrors.threshold && (
                <p className="mt-1 text-xs text-rose-600 font-medium">{fieldErrors.threshold}</p>
              )}
            </div>
          </div>

          <p className="text-[11px] text-slate-500 leading-normal">
            Status will be derived automatically: Stocked when stock &gt; threshold, Running Low
            when 1..threshold, Gone when 0.
          </p>

          {/* Action Buttons */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-orange-600 hover:bg-orange-700 rounded-xl shadow-sm transition-colors disabled:opacity-60"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Creating...</span>
                </>
              ) : (
                <span>Add Snack</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

/**
 * Modal component for Admin editing an existing snack's metadata.
 * Note: Quantity is deliberately not editable here to uphold the
 * transactional audit logging invariant (Rule 1 & 4).
 */

import React, { useState, useEffect } from 'react';
import { apiClient, ApiError } from '../../api/client';
import { Snack, SnackCategory, SnackUpdatePayload } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { X, Loader2, Edit3, AlertCircle, Info } from 'lucide-react';

interface EditSnackModalProps {
  snack: Snack | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (updatedSnack: Snack) => void;
}

export const EditSnackModal: React.FC<EditSnackModalProps> = ({
  snack,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { success } = useToast();
  const [name, setName] = useState('');
  const [category, setCategory] = useState<SnackCategory>('sweet');
  const [threshold, setThreshold] = useState<number>(5);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (snack) {
      setName(snack.name);
      setCategory(snack.category);
      setThreshold(snack.low_stock_threshold);
      setFormError(null);
      setFieldErrors({});
    }
  }, [snack]);

  if (!isOpen || !snack) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFieldErrors({});

    const trimmed = name.trim();
    if (!trimmed) {
      setFieldErrors({ name: 'Snack name is required' });
      return;
    }
    if (threshold < 0) {
      setFieldErrors({ threshold: 'Threshold cannot be negative' });
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: SnackUpdatePayload = {
        name: trimmed,
        category,
        low_stock_threshold: threshold,
      };
      const updated = await apiClient.patch<Snack>(`/snacks/${snack.id}`, payload);
      success(`Updated "${updated.name}" details.`);
      onSuccess(updated);
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
        setFormError('Failed to update snack. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-snack-title"
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-2">
            <Edit3 className="w-5 h-5 text-orange-600" />
            <h2 id="edit-snack-title" className="text-base font-bold text-slate-900">
              Edit Snack Details
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
            <label htmlFor="edit-name" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
              Snack Name *
            </label>
            <input
              id="edit-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={`w-full px-3.5 py-2 text-sm rounded-xl border bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 ${
                fieldErrors.name ? 'border-rose-400 focus:border-rose-500' : 'border-slate-300 focus:border-orange-500'
              }`}
              disabled={isSubmitting}
            />
            {fieldErrors.name && (
              <p className="mt-1 text-xs text-rose-600 font-medium">{fieldErrors.name}</p>
            )}
          </div>

          {/* Category */}
          <div>
            <label htmlFor="edit-category" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
              Category *
            </label>
            <select
              id="edit-category"
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

          {/* Low Stock Threshold */}
          <div>
            <label htmlFor="edit-threshold" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
              Low-Stock Threshold *
            </label>
            <input
              id="edit-threshold"
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

          {/* Note on Quantity Immutability */}
          <div className="p-3 bg-amber-50/80 border border-amber-200 rounded-xl flex items-start gap-2 text-xs text-amber-900">
            <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Audit Rule:</strong> Quantity ({snack.quantity} packets) is locked here.
              Use <em>Restock</em> or <em>Consume</em> to make audited stock adjustments.
            </p>
          </div>

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
                  <span>Saving...</span>
                </>
              ) : (
                <span>Save Changes</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

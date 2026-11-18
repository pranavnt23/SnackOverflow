/**
 * Modal component for Admin restocking pantry inventory.
 * Atomically updates stock level and logs an audit record in PostgreSQL.
 */

import React, { useState } from 'react';
import { apiClient, ApiError } from '../../api/client';
import { RestockPayload, Snack } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { X, Loader2, PackagePlus, ArrowRight, AlertCircle } from 'lucide-react';

interface RestockModalProps {
  snack: Snack | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (updatedSnack: Snack) => void;
}

export const RestockModal: React.FC<RestockModalProps> = ({
  snack,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { success } = useToast();
  const [amount, setAmount] = useState<number>(10);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  if (!isOpen || !snack) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (amount <= 0 || amount > 1000) {
      setFormError('Restock amount must be between 1 and 1,000 packets.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: RestockPayload = { amount };
      const updated = await apiClient.post<Snack>(`/snacks/${snack.id}/restock`, payload);
      success(`Restocked ${amount} packets of "${updated.name}". New total: ${updated.quantity}`);
      onSuccess(updated);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.message);
      } else {
        setFormError('Failed to restock snack.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const quickAmounts = [5, 10, 20, 50];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="restock-snack-title"
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-2">
            <PackagePlus className="w-5 h-5 text-emerald-600" />
            <h2 id="restock-snack-title" className="text-base font-bold text-slate-900">
              Restock Inventory
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

          {/* Snack Info Preview */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs flex items-center justify-between">
            <div>
              <span className="font-bold text-slate-800 text-sm block">{snack.name}</span>
              <span className="text-slate-500 capitalize">{snack.category}</span>
            </div>
            <div className="text-right">
              <span className="text-slate-500 block">Current Stock</span>
              <span className="font-bold text-slate-900 text-sm">{snack.quantity} packets</span>
            </div>
          </div>

          {/* Amount Input */}
          <div>
            <label htmlFor="restock-amount" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
              Restock Quantity (1..1000) *
            </label>
            <input
              id="restock-amount"
              type="number"
              min="1"
              max="1000"
              value={amount}
              onChange={(e) => setAmount(parseInt(e.target.value || '0', 10))}
              className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-300 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500"
              disabled={isSubmitting}
              autoFocus
            />
          </div>

          {/* Quick-Pick Amount Buttons */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Quick:</span>
            {quickAmounts.map((qty) => (
              <button
                key={qty}
                type="button"
                onClick={() => setAmount(qty)}
                className={`px-2.5 py-1 text-xs font-bold rounded-lg border transition-colors ${
                  amount === qty
                    ? 'bg-emerald-600 text-white border-emerald-600'
                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                }`}
              >
                +{qty}
              </button>
            ))}
          </div>

          {/* Projected Stock Preview */}
          <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between text-xs text-emerald-900 font-medium">
            <span>Projected New Stock:</span>
            <div className="flex items-center gap-1.5 font-bold">
              <span>{snack.quantity}</span>
              <ArrowRight className="w-3.5 h-3.5" />
              <span className="text-sm font-black text-emerald-800">{snack.quantity + (amount > 0 ? amount : 0)}</span>
            </div>
          </div>

          {/* Actions */}
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
              className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-sm transition-colors disabled:opacity-60"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Restocking...</span>
                </>
              ) : (
                <span>Confirm Restock</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

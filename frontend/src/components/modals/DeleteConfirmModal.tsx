/**
 * Confirmation dialog for Admin deleting a snack.
 * Informs the user that votes cascade while activity logs are retained.
 */

import React, { useState } from 'react';
import { apiClient, ApiError } from '../../api/client';
import { Snack } from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { X, Loader2, Trash2, AlertTriangle } from 'lucide-react';

interface DeleteConfirmModalProps {
  snack: Snack | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (deletedSnackId: number) => void;
}

export const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  snack,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { success, error } = useToast();
  const [isDeleting, setIsDeleting] = useState(false);

  if (!isOpen || !snack) return null;

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    try {
      await apiClient.delete(`/snacks/${snack.id}`);
      success(`Successfully removed "${snack.name}" from the pantry.`);
      onSuccess(snack.id);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        error(err.message);
      } else {
        error('Failed to delete snack. Please try again.');
      }
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-snack-title"
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-rose-50/50">
          <div className="flex items-center gap-2 text-rose-700">
            <Trash2 className="w-5 h-5" />
            <h2 id="delete-snack-title" className="text-base font-bold text-slate-900">
              Delete Pantry Snack
            </h2>
          </div>
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-rose-500"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-3 text-xs text-rose-900">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-bold">Are you sure you want to delete this snack?</p>
              <p className="leading-relaxed">
                This will permanently delete <strong className="text-slate-900">"{snack.name}"</strong>.
                Associated votes will cascade, and past consume/restock audit logs will be safely retained.
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isDeleting}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-sm transition-colors disabled:opacity-60"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Deleting...</span>
                </>
              ) : (
                <span>Delete Snack</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

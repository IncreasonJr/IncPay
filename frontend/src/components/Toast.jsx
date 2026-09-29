import React, { useEffect } from 'react';

/**
 * Toast notification component for clean, non-intrusive user feedback.
 * Types: 'info' | 'success' | 'warning' | 'error'
 */
export default function Toast({ message, type = 'info', onClose, duration = 4500 }) {
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => {
      if (onClose) onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  if (!message) return null;

  const typeStyles = {
    info: {
      wrapper: 'bg-white border-blue-200 text-slate-800 shadow-blue-500/10',
      badge: 'bg-blue-50 text-blue-600 border border-blue-100',
      icon: (
        <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      tag: 'Information',
      accent: 'border-l-4 border-l-blue-500',
    },
    success: {
      wrapper: 'bg-white border-emerald-200 text-slate-800 shadow-emerald-500/10',
      badge: 'bg-emerald-50 text-emerald-600 border border-emerald-100',
      icon: (
        <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      tag: 'Success',
      accent: 'border-l-4 border-l-emerald-500',
    },
    warning: {
      wrapper: 'bg-white border-amber-200 text-slate-800 shadow-amber-500/10',
      badge: 'bg-amber-50 text-amber-700 border border-amber-100',
      icon: (
        <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
      tag: 'Notice',
      accent: 'border-l-4 border-l-amber-500',
    },
    error: {
      wrapper: 'bg-white border-rose-200 text-slate-800 shadow-rose-500/10',
      badge: 'bg-rose-50 text-rose-600 border border-rose-100',
      icon: (
        <svg className="w-5 h-5 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      tag: 'Error',
      accent: 'border-l-4 border-l-rose-500',
    },
  };

  const style = typeStyles[type] || typeStyles.info;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-5 right-5 z-50 max-w-sm sm:max-w-md w-full px-4 transition-all duration-300 ease-out animate-bounce-short pointer-events-auto"
    >
      <div className={`p-4 rounded-2xl border shadow-xl flex items-start space-x-3.5 backdrop-blur-sm ${style.wrapper} ${style.accent}`}>
        <div className={`p-1.5 rounded-xl shrink-0 ${style.badge}`}>
          {style.icon}
        </div>
        <div className="flex-1 min-w-0 pt-0.5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              {style.tag}
            </span>
          </div>
          <p className="text-xs sm:text-sm font-medium leading-relaxed text-slate-700">
            {message}
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 -mr-1 -mt-1 rounded-lg hover:bg-slate-100 transition cursor-pointer"
            aria-label="Close notification"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}

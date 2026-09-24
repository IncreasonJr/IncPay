import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';

export default function PaySuccess() {
  const [searchParams] = useSearchParams();
  const reference = searchParams.get('reference') || '—';
  const [copied, setCopied] = useState(false);

  const handleCopyRef = async () => {
    if (!reference || reference === '—') return;
    try {
      await navigator.clipboard.writeText(reference);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy reference:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-between py-12 px-4 sm:px-6">
      <div className="max-w-md w-full mx-auto my-auto">
        <div className="bg-white rounded-2xl shadow-md border border-gray-200 p-8 text-center">
          {/* Animated/Clean Success Checkmark */}
          <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-black">
            ✓
          </div>

          <h1 className="text-2xl font-black text-gray-900 mb-2">
            Payment Received!
          </h1>

          <p className="text-sm text-gray-600 mb-6">
            Your payment was processed successfully. A payment confirmation and receipt will arrive shortly.
          </p>

          {/* Reference Card */}
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-6 text-left">
            <span className="block text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
              Transaction Reference
            </span>
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm font-bold text-gray-800 break-all mr-2">
                {reference}
              </span>
              <button
                onClick={handleCopyRef}
                className="shrink-0 text-xs font-semibold px-2.5 py-1 bg-white border border-gray-300 rounded hover:bg-gray-100 text-gray-700 transition-colors"
              >
                {copied ? '✓ Copied' : 'Copy'}
              </button>
            </div>
          </div>

          {/* Action */}
          <Link
            to="/"
            className="block w-full py-3 px-4 bg-gray-900 hover:bg-gray-800 text-white font-semibold text-sm rounded-xl shadow-sm transition-colors text-center"
          >
            Done
          </Link>
        </div>
      </div>

      <footer className="text-center text-xs text-gray-400 mt-8">
        <p>Secured by IncPay • Direct Merchant Split Settlements</p>
      </footer>
    </div>
  );
}

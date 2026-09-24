import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import client from '../api/client';

export default function PaySuccess() {
  const [searchParams] = useSearchParams();
  const reference = searchParams.get('reference') || '';

  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('loading'); // 'loading' | 'verified' | 'pending' | 'failed' | 'no_reference'
  const [amountPaid, setAmountPaid] = useState(null);
  const [customerEmail, setCustomerEmail] = useState(null);
  const [copied, setCopied] = useState(false);

  const baseURL =
    (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL) ||
    'http://localhost:8000';

  const verifyPayment = useCallback(async () => {
    if (!reference || reference === '—') {
      setStatus('no_reference');
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const res = await client.get(`/api/public/verify-payment/${encodeURIComponent(reference)}`);
      const { status: payStatus, amount_paid, customer_email } = res.data;

      if (amount_paid) {
        setAmountPaid(parseFloat(amount_paid));
      }
      if (customer_email) {
        setCustomerEmail(customer_email);
      }

      const normalizedStatus = (payStatus || '').toLowerCase();
      if (normalizedStatus === 'success') {
        setStatus('verified');
      } else if (['pending', 'ongoing', 'processing', 'queued'].includes(normalizedStatus)) {
        setStatus('pending');
      } else {
        setStatus('failed');
      }
    } catch (err) {
      console.warn('Payment verification returned error:', err);
      // If 404 or network glitch, mark as pending to allow user to retry
      if (err.response?.status === 404) {
        setStatus('pending');
      } else {
        setStatus('failed');
      }
    } finally {
      setLoading(false);
    }
  }, [reference]);

  useEffect(() => {
    verifyPayment();
  }, [verifyPayment]);

  const handleCopyRef = async () => {
    if (!reference) return;
    try {
      await navigator.clipboard.writeText(reference);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy reference:', err);
    }
  };

  const receiptUrl = `${baseURL}/api/public/receipt/${encodeURIComponent(reference)}`;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-between py-12 px-4 sm:px-6">
      <div className="max-w-md w-full mx-auto my-auto">
        <div className="bg-white rounded-2xl shadow-md border border-gray-200 p-8 text-center">
          {/* 1. Loading State */}
          {loading && (
            <div>
              <div className="inline-block w-12 h-12 border-4 border-gray-900 border-t-transparent rounded-full animate-spin mb-6"></div>
              <h1 className="text-xl font-bold text-gray-900 mb-2">Verifying Payment...</h1>
              <p className="text-sm text-gray-600 mb-6">
                Confirming settlement details with Paystack. This will only take a moment.
              </p>
            </div>
          )}

          {/* 2. Verified Success State */}
          {!loading && status === 'verified' && (
            <div>
              <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-black">
                ✓
              </div>

              <h1 className="text-2xl font-black text-gray-900 mb-2">Payment Received!</h1>

              <p className="text-sm text-gray-600 mb-4">
                Your payment {amountPaid ? `of ₵${amountPaid.toFixed(2)}` : ''} was processed
                successfully.
              </p>

              {customerEmail && (
                <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-3 mb-6 text-xs text-emerald-800 text-center">
                  <span>✉️ A copy of your receipt has been sent to <strong>{customerEmail}</strong></span>
                </div>
              )}
            </div>
          )}

          {/* 3. Pending State */}
          {!loading && status === 'pending' && (
            <div>
              <div className="w-16 h-16 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-black">
                ⏳
              </div>

              <h1 className="text-2xl font-black text-gray-900 mb-2">Verification Pending</h1>

              <p className="text-sm text-gray-600 mb-6">
                Verification pending — refresh in a moment to confirm settlement status.
              </p>

              <button
                onClick={verifyPayment}
                className="w-full mb-3 py-2.5 px-4 bg-amber-600 hover:bg-amber-700 text-white font-semibold text-sm rounded-xl transition-colors"
              >
                Refresh Status
              </button>
            </div>
          )}

          {/* 4. Failed State */}
          {!loading && status === 'failed' && (
            <div>
              <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-black">
                ✕
              </div>

              <h1 className="text-2xl font-black text-gray-900 mb-2">Payment Not Confirmed</h1>

              <p className="text-sm text-gray-600 mb-6">
                Payment was not successful or could not be verified with the payment processor.
              </p>
            </div>
          )}

          {/* 5. No Reference Provided */}
          {!loading && status === 'no_reference' && (
            <div>
              <div className="w-16 h-16 bg-gray-100 text-gray-400 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-black">
                ?
              </div>

              <h1 className="text-xl font-bold text-gray-900 mb-2">No Reference Found</h1>

              <p className="text-sm text-gray-600 mb-6">
                No payment transaction reference was found in the checkout URL.
              </p>
            </div>
          )}

          {/* Reference Card (Shown when reference exists) */}
          {reference && reference !== '—' && (
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
          )}

          {/* Action Buttons */}
          <div className="space-y-3">
            {/* Download Receipt PDF Button (Only on verified success) */}
            {!loading && status === 'verified' && reference && (
              <a
                href={receiptUrl}
                target="_blank"
                rel="noopener noreferrer"
                download={`receipt-${reference}.pdf`}
                className="w-full flex items-center justify-center space-x-2 py-3 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm rounded-xl shadow-sm transition-colors text-center"
              >
                <svg
                  className="w-4 h-4 shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                <span>Download Receipt (PDF)</span>
              </a>
            )}

            <Link
              to="/"
              className="block w-full py-3 px-4 bg-gray-900 hover:bg-gray-800 text-white font-semibold text-sm rounded-xl shadow-sm transition-colors text-center"
            >
              Done
            </Link>
          </div>
        </div>
      </div>

      <footer className="text-center text-xs text-gray-400 mt-8">
        <p>Secured by IncPay • Direct Merchant Split Settlements</p>
      </footer>
    </div>
  );
}

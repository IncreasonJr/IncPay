import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';

export default function TransactionDetail() {
  const { id } = useParams();
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const [transaction, setTransaction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Receipt action states
  const [downloading, setDownloading] = useState(false);
  const [resending, setResending] = useState(false);
  const [actionSuccess, setActionSuccess] = useState(null);
  const [actionError, setActionError] = useState(null);

  // Expanded payload log IDs
  const [expandedLogs, setExpandedLogs] = useState({});
  const [copiedRef, setCopiedRef] = useState(false);
  const [copiedLogId, setCopiedLogId] = useState(null);

  const fetchDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.get(`/api/transactions/${id}`);
      setTransaction(res.data);
    } catch (err) {
      console.error('Failed to fetch transaction detail:', err);
      setError(err.response?.data?.detail || err.message || 'Transaction not found.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  const toggleLogExpand = (logId) => {
    setExpandedLogs((prev) => ({
      ...prev,
      [logId]: !prev[logId],
    }));
  };

  const handleCopyRef = () => {
    if (transaction?.paystack_reference && navigator.clipboard) {
      navigator.clipboard.writeText(transaction.paystack_reference);
      setCopiedRef(true);
      setTimeout(() => setCopiedRef(false), 2000);
    }
  };

  const handleCopyPayload = (logId, payload) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      setCopiedLogId(logId);
      setTimeout(() => setCopiedLogId(null), 2000);
    }
  };

  const handleDownloadReceipt = async () => {
    if (!transaction) return;
    setDownloading(true);
    setActionError(null);
    try {
      const response = await client.get(`/api/transactions/${id}/receipt`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `receipt-${transaction.paystack_reference}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download receipt:', err);
      setActionError('Failed to download PDF receipt. Ensure transaction was successful.');
    } finally {
      setDownloading(false);
    }
  };

  const handleResendReceipt = async () => {
    if (!transaction) return;
    setResending(true);
    setActionSuccess(null);
    setActionError(null);
    try {
      const res = await client.post(`/api/transactions/${id}/resend-receipt`);
      setActionSuccess(`Receipt email resent successfully to ${res.data.recipient}!`);
      // Refresh detail so resent audit log shows up
      fetchDetail();
    } catch (err) {
      console.error('Failed to resend receipt:', err);
      setActionError(err.response?.data?.detail || 'Failed to resend receipt email.');
    } finally {
      setResending(false);
    }
  };

  const formatCedis = (val) => {
    const num = Number(val) || 0;
    return `₵${num.toLocaleString('en-GH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return d.toLocaleString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  const getStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    if (s === 'success') {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
          <span className="w-2 h-2 mr-1.5 rounded-full bg-emerald-500"></span>
          Success
        </span>
      );
    }
    if (s === 'failed') {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
          <span className="w-2 h-2 mr-1.5 rounded-full bg-rose-500"></span>
          Failed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
        <span className="w-2 h-2 mr-1.5 rounded-full bg-amber-500"></span>
        {status || 'Pending'}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="flex items-center space-x-3 text-gray-600">
          <svg className="animate-spin h-6 w-6 text-gray-900" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-sm font-medium">Loading transaction details...</span>
        </div>
      </div>
    );
  }

  if (error || !transaction) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
        <div className="bg-white p-6 border border-gray-200 rounded-lg shadow-sm max-w-md w-full text-center">
          <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-gray-900 mb-2">Error Loading Transaction</h2>
          <p className="text-sm text-gray-600 mb-6">{error || 'Transaction record not found.'}</p>
          <button
            onClick={() => navigate('/admin/transactions')}
            className="w-full py-2 px-4 bg-gray-900 text-white rounded-md text-sm font-medium hover:bg-gray-800 transition-colors"
          >
            ← Back to Transactions
          </button>
        </div>
      </div>
    );
  }

  const isSuccess = transaction.status === 'success';
  const hasValidEmail =
    Boolean(transaction.customer_email) &&
    transaction.customer_email.trim().toLowerCase() !== 'noreply@incpay.app';

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top Navbar */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold text-gray-900 tracking-tight">IncPay</span>
              <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded font-medium">
                Admin
              </span>
            </div>

            <nav className="flex space-x-4">
              <Link
                to="/admin"
                className="text-sm font-medium text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md transition-colors"
              >
                Dashboard
              </Link>
              <Link
                to="/admin/sellers"
                className="text-sm font-medium text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md transition-colors"
              >
                Sellers
              </Link>
              <Link
                to="/admin/transactions"
                className="text-sm font-medium text-gray-900 bg-gray-100 px-3 py-2 rounded-md"
              >
                Transactions
              </Link>
            </nav>
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600 hidden sm:inline-block">
              {user?.email}
            </span>
            <button
              onClick={signOut}
              className="text-sm font-medium text-gray-700 hover:text-gray-900 px-3 py-1.5 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Navigation Breadcrumb */}
        <div>
          <Link
            to="/admin/transactions"
            className="text-xs font-semibold text-gray-500 hover:text-gray-900 inline-flex items-center space-x-1"
          >
            <span>&larr;</span>
            <span>Back to All Transactions</span>
          </Link>
        </div>

        {/* Action Alerts */}
        {actionSuccess && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-md text-sm text-emerald-800 flex items-center justify-between">
            <span>{actionSuccess}</span>
            <button onClick={() => setActionSuccess(null)} className="text-emerald-600 font-bold ml-4">
              &times;
            </button>
          </div>
        )}
        {actionError && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-md text-sm text-rose-800 flex items-center justify-between">
            <span>{actionError}</span>
            <button onClick={() => setActionError(null)} className="text-rose-600 font-bold ml-4">
              &times;
            </button>
          </div>
        )}

        {/* Header with Title and Actions */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold font-mono text-gray-900 tracking-tight">
                {transaction.paystack_reference}
              </h1>
              <button
                onClick={handleCopyRef}
                className="text-gray-400 hover:text-gray-700 p-1 rounded transition-colors"
                title="Copy Reference"
              >
                {copiedRef ? (
                  <span className="text-xs text-emerald-600 font-sans font-medium">Copied!</span>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                )}
              </button>
              {getStatusBadge(transaction.status)}
            </div>
            <p className="text-xs text-gray-500">
              Recorded on {formatDate(transaction.created_at)}
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleDownloadReceipt}
              disabled={downloading || !isSuccess}
              title={!isSuccess ? 'Receipt only available for successful payments' : 'Download PDF receipt'}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {downloading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-700" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Downloading...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download Receipt (PDF)
                </>
              )}
            </button>

            <button
              onClick={handleResendReceipt}
              disabled={resending || !isSuccess || !hasValidEmail}
              title={
                !isSuccess
                  ? 'Receipt only available for successful payments'
                  : !hasValidEmail
                  ? 'No customer email address on file'
                  : 'Resend receipt PDF to customer email'
              }
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-900 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {resending ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Resending...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  Resend Receipt
                </>
              )}
            </button>
          </div>
        </div>

        {/* Financial Breakdown Card */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-4">
            Payment &amp; Split Breakdown
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 divide-y md:divide-y-0 md:divide-x divide-gray-100">
            {/* Listed Amount */}
            <div className="pt-2 md:pt-0">
              <span className="block text-xs font-medium text-gray-500">Listed Price</span>
              <span className="block text-xl font-bold text-gray-900 mt-1">
                {formatCedis(transaction.listed_amount)}
              </span>
              <span className="text-[11px] text-gray-400">Pre-discount item price</span>
            </div>

            {/* Visible Discount */}
            <div className="pt-2 md:pt-0 md:pl-4">
              <span className="block text-xs font-medium text-gray-500">Customer Discount (D/2)</span>
              <span className="block text-xl font-bold text-emerald-600 mt-1">
                -{formatCedis(transaction.discount_amount)}
              </span>
              <span className="text-[11px] text-emerald-600/80">Visible customer deduction</span>
            </div>

            {/* Total Paid */}
            <div className="pt-2 md:pt-0 md:pl-4">
              <span className="block text-xs font-medium text-gray-500">Amount Paid</span>
              <span className="block text-xl font-bold text-gray-900 mt-1">
                {formatCedis(transaction.amount_paid)}
              </span>
              <span className="text-[11px] text-gray-400">Settled via Paystack</span>
            </div>

            {/* IncPay Platform Cut */}
            <div className="pt-2 md:pt-0 md:pl-4 bg-indigo-50/50 p-2 rounded-md">
              <span className="block text-xs font-medium text-indigo-900">IncPay Platform Cut (D/2)</span>
              <span className="block text-xl font-bold text-indigo-700 mt-1">
                {formatCedis(transaction.platform_cut)}
              </span>
              <span className="text-[11px] text-indigo-600">Retained platform margin</span>
            </div>

            {/* Seller Net Payout */}
            <div className="pt-2 md:pt-0 md:pl-4">
              <span className="block text-xs font-medium text-gray-500">Seller Payout</span>
              <span className="block text-xl font-bold text-gray-900 mt-1">
                {formatCedis(transaction.seller_payout)}
              </span>
              <span className="text-[11px] text-gray-400">Routed to seller subaccount</span>
            </div>
          </div>
        </div>

        {/* 2-Column Details Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Customer & Transaction Meta */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wider border-b border-gray-100 pb-3">
              Transaction Information
            </h2>
            <dl className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2 text-sm">
              <div>
                <dt className="text-xs font-medium text-gray-500">Customer Email</dt>
                <dd className="font-medium text-gray-900 mt-0.5">
                  {transaction.customer_email && transaction.customer_email !== 'noreply@incpay.app' ? (
                    transaction.customer_email
                  ) : (
                    <span className="text-gray-400 italic">None provided</span>
                  )}
                </dd>
              </div>

              <div>
                <dt className="text-xs font-medium text-gray-500">Currency</dt>
                <dd className="font-medium text-gray-900 mt-0.5">GHS (Ghanaian Cedis)</dd>
              </div>

              <div>
                <dt className="text-xs font-medium text-gray-500">Transaction ID</dt>
                <dd className="font-mono text-xs text-gray-700 mt-0.5 break-all">
                  {transaction.id}
                </dd>
              </div>

              <div>
                <dt className="text-xs font-medium text-gray-500">Coupon Reference</dt>
                <dd className="font-mono text-xs text-gray-700 mt-0.5 break-all">
                  {transaction.coupon_id || '—'}
                </dd>
              </div>

              <div>
                <dt className="text-xs font-medium text-gray-500">Created At</dt>
                <dd className="text-xs text-gray-700 mt-0.5">
                  {formatDate(transaction.created_at)}
                </dd>
              </div>

              <div>
                <dt className="text-xs font-medium text-gray-500">Last Updated</dt>
                <dd className="text-xs text-gray-700 mt-0.5">
                  {formatDate(transaction.updated_at)}
                </dd>
              </div>
            </dl>
          </div>

          {/* Seller Metadata Card */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wider border-b border-gray-100 pb-3">
              Merchant Settlement Profile
            </h2>
            {transaction.seller ? (
              <dl className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2 text-sm">
                <div>
                  <dt className="text-xs font-medium text-gray-500">Business Name</dt>
                  <dd className="font-bold text-gray-900 mt-0.5">
                    {transaction.seller.business_name}
                  </dd>
                </div>

                <div>
                  <dt className="text-xs font-medium text-gray-500">Agreed Discount (D)</dt>
                  <dd className="font-semibold text-gray-900 mt-0.5">
                    {transaction.seller.agreed_discount ? `${transaction.seller.agreed_discount}%` : '—'}
                  </dd>
                </div>

                <div>
                  <dt className="text-xs font-medium text-gray-500">Contact Email</dt>
                  <dd className="text-xs text-gray-700 mt-0.5">
                    {transaction.seller.email || transaction.seller.contact_email || '—'}
                  </dd>
                </div>

                <div>
                  <dt className="text-xs font-medium text-gray-500">Contact Phone</dt>
                  <dd className="text-xs text-gray-700 mt-0.5">
                    {transaction.seller.phone || transaction.seller.contact_phone || '—'}
                  </dd>
                </div>

                <div className="sm:col-span-2 pt-1">
                  <Link
                    to={`/admin/sellers/${transaction.seller.id}/edit`}
                    className="text-xs text-gray-900 hover:underline font-semibold"
                  >
                    View or Edit Seller Record &rarr;
                  </Link>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-gray-500 italic">Seller profile details unavailable.</p>
            )}
          </div>
        </div>

        {/* Audit & Webhook Event Logs */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wider">
                Audit &amp; Webhook Event Logs
              </h2>
              <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-700 rounded-full font-medium">
                {transaction.logs?.length || 0} events
              </span>
            </div>
            <span className="text-xs text-gray-400">Ordered chronologically</span>
          </div>

          {(!transaction.logs || transaction.logs.length === 0) ? (
            <p className="text-sm text-gray-500 py-4 text-center italic">
              No audit logs recorded for this transaction.
            </p>
          ) : (
            <div className="space-y-3">
              {transaction.logs.map((log, index) => {
                const isExpanded = Boolean(expandedLogs[log.id]);
                const isCopied = copiedLogId === log.id;

                return (
                  <div
                    key={log.id}
                    className="border border-gray-200 rounded-lg p-4 bg-gray-50/50 space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                      <div className="flex items-center space-x-2.5">
                        <span className="text-xs font-bold text-gray-400">#{index + 1}</span>
                        <span className="font-mono text-xs font-semibold px-2.5 py-1 bg-white border border-gray-200 rounded text-gray-800">
                          {log.event_type}
                        </span>
                      </div>
                      <div className="flex items-center space-x-3">
                        <span className="text-xs text-gray-500">
                          {formatDate(log.created_at)}
                        </span>
                        <button
                          onClick={() => toggleLogExpand(log.id)}
                          className="text-xs font-medium text-gray-700 hover:text-gray-900 underline"
                        >
                          {isExpanded ? 'Hide Payload' : 'View Payload'}
                        </button>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="pt-2 border-t border-gray-200 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                            Raw JSON Payload
                          </span>
                          <button
                            onClick={() => handleCopyPayload(log.id, log.payload)}
                            className="text-xs text-gray-500 hover:text-gray-800 font-medium"
                          >
                            {isCopied ? 'Copied!' : 'Copy JSON'}
                          </button>
                        </div>
                        <pre className="bg-gray-900 text-gray-100 rounded-md p-4 text-xs font-mono overflow-x-auto max-h-96">
                          {log.payload
                            ? JSON.stringify(log.payload, null, 2)
                            : '// No payload content'}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

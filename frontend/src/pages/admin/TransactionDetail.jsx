import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import client from '../../api/client';
import AdminLayout from '../../components/AdminLayout';

export default function TransactionDetail() {
  const { id } = useParams();
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
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-500"></span>
          Success
        </span>
      );
    }
    if (s === 'failed') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-rose-500"></span>
          Failed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
        <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-amber-500"></span>
        {status || 'Pending'}
      </span>
    );
  };

  if (loading) {
    return (
      <AdminLayout activeTab="transactions">
        <div className="p-12 text-center text-gray-500 text-sm">
          <div className="inline-flex items-center space-x-2">
            <svg className="animate-spin h-5 w-5 text-gray-900" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Loading transaction details...</span>
          </div>
        </div>
      </AdminLayout>
    );
  }

  if (error || !transaction) {
    return (
      <AdminLayout activeTab="transactions">
        <div className="max-w-md mx-auto bg-white p-6 border border-gray-200 rounded-xl shadow-xs text-center">
          <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-gray-900 mb-2">Error Loading Transaction</h2>
          <p className="text-sm text-gray-600 mb-6">{error || 'Transaction record not found.'}</p>
          <button
            onClick={() => navigate('/admin/transactions')}
            className="w-full py-2.5 px-4 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors"
          >
            ← Back to Transactions
          </button>
        </div>
      </AdminLayout>
    );
  }

  const isSuccess = transaction.status === 'success';
  const hasValidEmail =
    Boolean(transaction.customer_email) &&
    transaction.customer_email.trim().toLowerCase() !== 'noreply@incpay.app';

  return (
    <AdminLayout activeTab="transactions">
      <div className="space-y-6">
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
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs sm:text-sm text-emerald-800 flex items-center justify-between">
            <span>{actionSuccess}</span>
            <button onClick={() => setActionSuccess(null)} className="text-emerald-600 font-bold ml-4">
              &times;
            </button>
          </div>
        )}
        {actionError && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs sm:text-sm text-rose-800 flex items-center justify-between">
            <span>{actionError}</span>
            <button onClick={() => setActionError(null)} className="text-rose-600 font-bold ml-4">
              &times;
            </button>
          </div>
        )}

        {/* Header with Title, Status & Action Buttons */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 sm:p-6 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-bold font-mono text-gray-900 tracking-tight break-all">
                {transaction.paystack_reference}
              </h1>
              <button
                onClick={handleCopyRef}
                className="text-gray-400 hover:text-gray-700 p-1 rounded transition-colors"
                title="Copy Reference"
              >
                {copiedRef ? (
                  <span className="text-xs text-emerald-600 font-sans font-semibold">Copied!</span>
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
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3">
            <button
              onClick={handleDownloadReceipt}
              disabled={downloading || !isSuccess}
              title={!isSuccess ? 'Receipt only available for successful payments' : 'Download PDF receipt'}
              className="inline-flex items-center justify-center px-4 py-2.5 border border-gray-300 rounded-lg shadow-xs text-xs sm:text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
                  Download PDF Receipt
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
              className="inline-flex items-center justify-center px-4 py-2.5 border border-transparent rounded-lg shadow-xs text-xs sm:text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
                  Resend Receipt Email
                </>
              )}
            </button>
          </div>
        </div>

        {/* Financial Breakdown Card */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 sm:p-6 shadow-xs">
          <h2 className="text-xs sm:text-sm font-bold text-gray-900 uppercase tracking-wider mb-4">
            Payment &amp; Margin Split Breakdown
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 sm:gap-4">
            {/* Listed Amount */}
            <div className="p-3 bg-gray-50 rounded-lg">
              <span className="block text-[11px] font-semibold text-gray-500 uppercase">Listed Price</span>
              <span className="block text-lg sm:text-xl font-bold text-gray-900 mt-1">
                {formatCedis(transaction.listed_amount)}
              </span>
              <span className="text-[10px] text-gray-400">Pre-discount item price</span>
            </div>

            {/* Visible Discount */}
            <div className="p-3 bg-emerald-50/60 rounded-lg">
              <span className="block text-[11px] font-semibold text-emerald-800 uppercase">Customer Discount</span>
              <span className="block text-lg sm:text-xl font-bold text-emerald-700 mt-1">
                -{formatCedis(transaction.discount_amount)}
              </span>
              <span className="text-[10px] text-emerald-600/80">Visible customer deduction</span>
            </div>

            {/* Total Paid */}
            <div className="p-3 bg-gray-100 rounded-lg">
              <span className="block text-[11px] font-semibold text-gray-700 uppercase">Amount Paid</span>
              <span className="block text-lg sm:text-xl font-black text-gray-900 mt-1">
                {formatCedis(transaction.amount_paid)}
              </span>
              <span className="text-[10px] text-gray-500">Settled via Paystack</span>
            </div>

            {/* IncPay Platform Cut */}
            <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-lg">
              <span className="block text-[11px] font-semibold text-indigo-900 uppercase">IncPay Cut</span>
              <span className="block text-lg sm:text-xl font-bold text-indigo-700 mt-1">
                {formatCedis(transaction.platform_cut)}
              </span>
              <span className="text-[10px] text-indigo-600">Retained platform margin</span>
            </div>

            {/* Seller Net Payout */}
            <div className="p-3 bg-gray-50 rounded-lg col-span-2 md:col-span-1">
              <span className="block text-[11px] font-semibold text-gray-500 uppercase">Seller Payout</span>
              <span className="block text-lg sm:text-xl font-bold text-gray-900 mt-1">
                {formatCedis(transaction.seller_payout)}
              </span>
              <span className="text-[10px] text-gray-400">Routed to subaccount</span>
            </div>
          </div>
        </div>

        {/* 2-Column Details Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
          {/* Customer & Transaction Meta */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 sm:p-6 shadow-xs space-y-4">
            <h2 className="text-xs sm:text-sm font-bold text-gray-900 uppercase tracking-wider border-b border-gray-100 pb-3">
              Transaction Information
            </h2>
            <dl className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2 text-sm">
              <div>
                <dt className="text-xs font-semibold text-gray-500">Customer Email</dt>
                <dd className="font-semibold text-gray-900 mt-0.5 break-all">
                  {transaction.customer_email && transaction.customer_email !== 'noreply@incpay.app' ? (
                    transaction.customer_email
                  ) : (
                    <span className="text-gray-400 italic font-normal">None provided</span>
                  )}
                </dd>
              </div>

              <div>
                <dt className="text-xs font-semibold text-gray-500">Currency</dt>
                <dd className="font-semibold text-gray-900 mt-0.5">GHS (Ghanaian Cedis)</dd>
              </div>

              <div>
                <dt className="text-xs font-semibold text-gray-500">Transaction ID</dt>
                <dd className="font-mono text-xs text-gray-700 mt-0.5 break-all">
                  {transaction.id}
                </dd>
              </div>

              <div>
                <dt className="text-xs font-semibold text-gray-500">Coupon Reference</dt>
                <dd className="font-mono text-xs text-gray-700 mt-0.5 break-all">
                  {transaction.coupon_id || '—'}
                </dd>
              </div>

              <div>
                <dt className="text-xs font-semibold text-gray-500">Created At</dt>
                <dd className="text-xs text-gray-700 mt-0.5">
                  {formatDate(transaction.created_at)}
                </dd>
              </div>

              <div>
                <dt className="text-xs font-semibold text-gray-500">Last Updated</dt>
                <dd className="text-xs text-gray-700 mt-0.5">
                  {formatDate(transaction.updated_at)}
                </dd>
              </div>
            </dl>
          </div>

          {/* Seller Metadata Card */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 sm:p-6 shadow-xs space-y-4">
            <h2 className="text-xs sm:text-sm font-bold text-gray-900 uppercase tracking-wider border-b border-gray-100 pb-3">
              Merchant Settlement Profile
            </h2>
            {transaction.seller ? (
              <dl className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2 text-sm">
                <div>
                  <dt className="text-xs font-semibold text-gray-500">Business Name</dt>
                  <dd className="font-bold text-gray-900 mt-0.5">
                    {transaction.seller.business_name}
                  </dd>
                </div>

                <div>
                  <dt className="text-xs font-semibold text-gray-500">Agreed Discount (D)</dt>
                  <dd className="font-semibold text-gray-900 mt-0.5">
                    {transaction.seller.agreed_discount ? `${transaction.seller.agreed_discount}%` : '—'}
                  </dd>
                </div>

                <div>
                  <dt className="text-xs font-semibold text-gray-500">Contact Email</dt>
                  <dd className="text-xs text-gray-700 mt-0.5 break-all">
                    {transaction.seller.email || transaction.seller.contact_email || '—'}
                  </dd>
                </div>

                <div>
                  <dt className="text-xs font-semibold text-gray-500">Contact Phone</dt>
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
        <div className="bg-white border border-gray-200 rounded-xl p-5 sm:p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div className="flex items-center space-x-2">
              <h2 className="text-xs sm:text-sm font-bold text-gray-900 uppercase tracking-wider">
                Audit &amp; Webhook Event Logs
              </h2>
              <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-700 rounded-full font-semibold">
                {transaction.logs?.length || 0} events
              </span>
            </div>
            <span className="text-xs text-gray-400">Chronological</span>
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
                    className="border border-gray-200 rounded-xl p-3.5 sm:p-4 bg-gray-50/50 space-y-2.5"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 sm:gap-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-gray-400">#{index + 1}</span>
                        <span className="font-mono text-xs font-semibold px-2 py-0.5 bg-white border border-gray-200 rounded text-gray-800">
                          {log.event_type}
                        </span>
                      </div>
                      <div className="flex items-center space-x-3 text-xs">
                        <span className="text-gray-500">
                          {formatDate(log.created_at)}
                        </span>
                        <button
                          onClick={() => toggleLogExpand(log.id)}
                          className="font-semibold text-gray-700 hover:text-gray-900 underline"
                        >
                          {isExpanded ? 'Hide Payload' : 'View Payload'}
                        </button>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="pt-2 border-t border-gray-200 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                            Raw JSON Payload
                          </span>
                          <button
                            onClick={() => handleCopyPayload(log.id, log.payload)}
                            className="text-xs text-gray-500 hover:text-gray-800 font-semibold"
                          >
                            {isCopied ? 'Copied!' : 'Copy JSON'}
                          </button>
                        </div>
                        <pre className="bg-gray-900 text-gray-100 rounded-lg p-3 sm:p-4 text-xs font-mono overflow-x-auto max-h-80">
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
      </div>
    </AdminLayout>
  );
}

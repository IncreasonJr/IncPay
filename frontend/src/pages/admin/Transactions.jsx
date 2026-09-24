import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';

export default function Transactions() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  // Filter state
  const [sellers, setSellers] = useState([]);
  const [selectedSeller, setSelectedSeller] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [datePreset, setDatePreset] = useState('all'); // all, today, 7d, 30d
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Data state
  const [transactions, setTransactions] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedRef, setCopiedRef] = useState(null);

  // Fetch sellers dropdown on mount
  useEffect(() => {
    async function loadSellers() {
      try {
        const res = await client.get('/api/sellers');
        setSellers(res.data || []);
      } catch (err) {
        console.error('Error loading sellers for filter:', err);
      }
    }
    loadSellers();
  }, []);

  // Compute start/end dates from preset
  const getDateRange = (preset) => {
    const now = new Date();
    const formatDate = (d) => d.toISOString().split('T')[0];

    if (preset === 'today') {
      const today = formatDate(now);
      return { start_date: today, end_date: today };
    }
    if (preset === '7d') {
      const past = new Date();
      past.setDate(now.getDate() - 7);
      return { start_date: formatDate(past), end_date: formatDate(now) };
    }
    if (preset === '30d') {
      const past = new Date();
      past.setDate(now.getDate() - 30);
      return { start_date: formatDate(past), end_date: formatDate(now) };
    }
    return { start_date: null, end_date: null };
  };

  // Fetch transactions
  const fetchTransactions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { start_date, end_date } = getDateRange(datePreset);
      const params = {
        page,
        page_size: pageSize,
      };

      if (selectedSeller) params.seller_id = selectedSeller;
      if (statusFilter) params.status = statusFilter;
      if (start_date) params.start_date = start_date;
      if (end_date) params.end_date = end_date;
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const res = await client.get('/api/transactions', { params });
      setTransactions(res.data.transactions || []);
      setTotal(res.data.total || 0);
      setTotalPages(res.data.total_pages || 1);
    } catch (err) {
      console.error('Error fetching transactions:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load transactions.');
    } finally {
      setLoading(false);
    }
  }, [page, selectedSeller, statusFilter, datePreset, searchQuery]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  // Reset filters
  const handleResetFilters = () => {
    setSelectedSeller('');
    setStatusFilter('');
    setDatePreset('all');
    setSearchQuery('');
    setPage(1);
  };

  // Copy reference
  const handleCopy = (ref) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(ref);
      setCopiedRef(ref);
      setTimeout(() => setCopiedRef(null), 2000);
    }
  };

  // Helper formatting
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
      });
    } catch {
      return isoStr;
    }
  };

  const getStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    if (s === 'success') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-500"></span>
          Success
        </span>
      );
    }
    if (s === 'failed') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-rose-500"></span>
          Failed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
        <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-amber-500"></span>
        {status || 'Pending'}
      </span>
    );
  };

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

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Page Title */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Transaction History</h1>
            <p className="text-sm text-gray-500 mt-1">
              View customer payments, audit margin splits, and inspect Paystack webhook event logs.
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => fetchTransactions()}
              disabled={loading}
              className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none transition-colors"
            >
              <svg className={`h-4 w-4 mr-1.5 text-gray-500 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search Input */}
            <div className="md:col-span-1">
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
                Search Reference / Email
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="e.g. INCPAY- or email..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setPage(1);
                  }}
                  className="w-full text-sm px-3 py-2 pl-9 border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
                />
                <svg
                  className="w-4 h-4 text-gray-400 absolute left-3 top-2.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>

            {/* Seller Select */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
                Merchant / Seller
              </label>
              <select
                value={selectedSeller}
                onChange={(e) => {
                  setSelectedSeller(e.target.value);
                  setPage(1);
                }}
                className="w-full text-sm px-3 py-2 border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 bg-white"
              >
                <option value="">All Sellers</option>
                {sellers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.business_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Status Select */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full text-sm px-3 py-2 border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-900 focus:border-gray-900 bg-white"
              >
                <option value="">All Statuses</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
                <option value="pending">Pending</option>
              </select>
            </div>

            {/* Reset Button */}
            <div className="flex items-end">
              <button
                onClick={handleResetFilters}
                className="w-full text-sm py-2 px-3 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors font-medium"
              >
                Reset Filters
              </button>
            </div>
          </div>

          {/* Date Presets */}
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-gray-100">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider mr-2">
              Time Range:
            </span>
            {[
              { id: 'all', label: 'All Time' },
              { id: 'today', label: 'Today' },
              { id: '7d', label: 'Last 7 Days' },
              { id: '30d', label: 'Last 30 Days' },
            ].map((btn) => (
              <button
                key={btn.id}
                onClick={() => {
                  setDatePreset(btn.id);
                  setPage(1);
                }}
                className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
                  datePreset === btn.id
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md text-sm text-red-700 flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={fetchTransactions}
              className="font-medium underline hover:text-red-900 ml-4"
            >
              Retry
            </button>
          </div>
        )}

        {/* Transactions Table */}
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
              <thead className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <tr>
                  <th scope="col" className="px-6 py-3">Date &amp; Time</th>
                  <th scope="col" className="px-6 py-3">Reference</th>
                  <th scope="col" className="px-6 py-3">Merchant</th>
                  <th scope="col" className="px-6 py-3">Customer Email</th>
                  <th scope="col" className="px-6 py-3 text-right">Listed</th>
                  <th scope="col" className="px-6 py-3 text-right">Visible Disc.</th>
                  <th scope="col" className="px-6 py-3 text-right">Paid</th>
                  <th scope="col" className="px-6 py-3 text-right">IncPay Cut</th>
                  <th scope="col" className="px-6 py-3 text-right">Seller Payout</th>
                  <th scope="col" className="px-6 py-3 text-center">Status</th>
                  <th scope="col" className="px-6 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {loading ? (
                  <tr>
                    <td colSpan="11" className="px-6 py-12 text-center text-gray-500">
                      <div className="inline-flex items-center space-x-2">
                        <svg className="animate-spin h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span>Loading transactions...</span>
                      </div>
                    </td>
                  </tr>
                ) : transactions.length === 0 ? (
                  <tr>
                    <td colSpan="11" className="px-6 py-12 text-center text-gray-500">
                      <p className="font-medium text-gray-900 mb-1">No transactions found</p>
                      <p className="text-xs text-gray-500 mb-4">
                        Try adjusting your filters or date range.
                      </p>
                      <button
                        onClick={handleResetFilters}
                        className="text-xs font-semibold text-gray-900 bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-md"
                      >
                        Reset All Filters
                      </button>
                    </td>
                  </tr>
                ) : (
                  transactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-gray-50/75 transition-colors">
                      {/* Date */}
                      <td className="px-6 py-4 whitespace-nowrap text-gray-600 text-xs font-medium">
                        {formatDate(tx.created_at)}
                      </td>

                      {/* Reference with copy */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-1.5">
                          <span className="font-mono text-xs text-gray-900 font-medium">
                            {tx.paystack_reference}
                          </span>
                          <button
                            onClick={() => handleCopy(tx.paystack_reference)}
                            title="Copy Paystack Reference"
                            className="text-gray-400 hover:text-gray-600 p-0.5 rounded transition-colors"
                          >
                            {copiedRef === tx.paystack_reference ? (
                              <svg className="w-3.5 h-3.5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" />
                              </svg>
                            ) : (
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                            )}
                          </button>
                        </div>
                      </td>

                      {/* Seller */}
                      <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                        {tx.seller?.business_name || '—'}
                      </td>

                      {/* Customer Email */}
                      <td className="px-6 py-4 whitespace-nowrap text-gray-600 text-xs">
                        {tx.customer_email && tx.customer_email !== 'noreply@incpay.app' ? (
                          tx.customer_email
                        ) : (
                          <span className="text-gray-400 italic">No email</span>
                        )}
                      </td>

                      {/* Listed */}
                      <td className="px-6 py-4 whitespace-nowrap text-right font-medium text-gray-700">
                        {formatCedis(tx.listed_amount)}
                      </td>

                      {/* Discount */}
                      <td className="px-6 py-4 whitespace-nowrap text-right font-medium text-emerald-600">
                        -{formatCedis(tx.discount_amount)}
                      </td>

                      {/* Paid */}
                      <td className="px-6 py-4 whitespace-nowrap text-right font-bold text-gray-900">
                        {formatCedis(tx.amount_paid)}
                      </td>

                      {/* IncPay Cut */}
                      <td className="px-6 py-4 whitespace-nowrap text-right font-medium text-indigo-700 bg-indigo-50/30">
                        {formatCedis(tx.platform_cut)}
                      </td>

                      {/* Seller Payout */}
                      <td className="px-6 py-4 whitespace-nowrap text-right font-medium text-gray-900">
                        {formatCedis(tx.seller_payout)}
                      </td>

                      {/* Status */}
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        {getStatusBadge(tx.status)}
                      </td>

                      {/* Actions */}
                      <td className="px-6 py-4 whitespace-nowrap text-right text-xs">
                        <Link
                          to={`/admin/transactions/${tx.id}`}
                          className="inline-flex items-center px-2.5 py-1.5 border border-gray-300 text-xs font-semibold rounded text-gray-700 hover:bg-gray-100 transition-colors"
                        >
                          View Details
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="bg-gray-50 px-6 py-3 border-t border-gray-200 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-xs text-gray-600">
              Showing <span className="font-semibold">{total > 0 ? (page - 1) * pageSize + 1 : 0}</span> to{' '}
              <span className="font-semibold">{Math.min(page * pageSize, total)}</span> of{' '}
              <span className="font-semibold">{total}</span> transactions
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                disabled={page <= 1 || loading}
                className="px-3 py-1.5 border border-gray-300 rounded text-xs font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <span className="text-xs text-gray-600 px-2 font-medium">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                disabled={page >= totalPages || loading}
                className="px-3 py-1.5 border border-gray-300 rounded text-xs font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

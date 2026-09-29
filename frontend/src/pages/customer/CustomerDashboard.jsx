import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';
import Toast from '../../components/Toast';

const DEMO_QR_DATA_URL = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAUoAAAFKAQAAAABTUiuoAAACBUlEQVR4nO2aQYrjMBBFX40FWdrQB8hR5JvNmeYG9lFygAZr2SDzZyE5cZqhSQKODVO1MJb8Fh+KKpWqbOJBG389SoKjjjrqqKOObolatYD1AGM3m/Vp2e43F+DoM2iUJE1UR/2eGgGNJEn36DYCHH0GTTWEqsssoAEws/AeAY6+gJp1oIHZdhLg6BOohnQScQLrdxHg6A+25LlWQALi1BnQZEiwvjvvrtXRio5mZtaB9TTX2JpLSfgOAY4+YiW2ViE0nr9MkKnxtrUAR5+/b/XJjNHMpMtJZUkKy81rcwGOPmTXcysHi5oDtBmNZ2Ewm6CRbSnA0VcyYSNGq565ZUCDkLWlAEefQCntCk2NiMqUN1qVhwYalU7HsLtWR1feKo+hzfXDUDpPuSLurf3RxRWAhhJRGaIytzf31lHQlbeAazq8elAT7q3DoKXKWMrBadlOH9loP0MtFoftBDj6Qk2YOkQyRPqQ0WYgBaqjNhTg6AvoUgSanXPtwUdJkE5LnjyM1v8dvc2OiZcAcWpUehm0X97LOBp6PzsGZis14dg1Pjs+HHqdHZcyPp3EaGaQzDwTHhW1HmA855IOy7i/f6MAR3+w8M/deAmZmg4/g/cJj4J+nx2LZJQjC4D45+Tn1mFQ1v+gLWPjWnRI66X3MvZHv8+Odf8vxnq5u1ZHHXXUUUcd/QtbICbRjpvPpQAAAABJRU5ErkJggg==';


export default function CustomerDashboard({ isDemo = false }) {
  const [searchParams] = useSearchParams();
  const demoActive = isDemo || searchParams.get('demo') === 'true';

  const { signOut } = useAuth();
  const navigate = useNavigate();

  const demoCustomer = {
    id: 'demo-cust-123',
    full_name: 'Kwame Mensah',
    email: 'kwame.mensah@example.com',
    phone: '024 123 4567',
    coupon_token: 'cust_123.1727618400.9A8B7C6D',
    verbal_code: '9A8B7C6D',
    is_active: true,
  };

  const demoTxs = [
    {
      id: 'tx-1',
      created_at: '2026-09-29T10:15:00Z',
      business_name: 'Kofi Electronics Store',
      listed_amount: 120.00,
      customer_discount_amount: 12.00,
      amount_paid: 108.00,
      paystack_reference: 'INCPAY-E7A49F2D',
      status: 'success',
      receipt_url: '/api/public/receipt/INCPAY-E7A49F2D',
    },
    {
      id: 'tx-2',
      created_at: '2026-09-28T16:40:00Z',
      business_name: 'Accra Fresh Supermarket',
      listed_amount: 85.00,
      customer_discount_amount: 8.50,
      amount_paid: 76.50,
      paystack_reference: 'INCPAY-83C901B4',
      status: 'success',
      receipt_url: '/api/public/receipt/INCPAY-83C901B4',
    },
    {
      id: 'tx-3',
      created_at: '2026-09-25T12:00:00Z',
      business_name: 'Osu Fashion Hub',
      listed_amount: 250.00,
      customer_discount_amount: 37.50,
      amount_paid: 212.50,
      paystack_reference: 'INCPAY-49F18DA0',
      status: 'success',
      receipt_url: '/api/public/receipt/INCPAY-49F18DA0',
    },
  ];

  const [customer, setCustomer] = useState(demoActive ? demoCustomer : null);
  const [loadingCustomer, setLoadingCustomer] = useState(!demoActive);
  const [errorCustomer, setErrorCustomer] = useState('');

  const [transactions, setTransactions] = useState(demoActive ? demoTxs : []);
  const [totalCount, setTotalCount] = useState(demoActive ? 3 : 0);
  const [page, setPage] = useState(1);
  const limit = 10;
  const [loadingTxs, setLoadingTxs] = useState(!demoActive);
  const [qrFormat, setQrFormat] = useState('png');
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'info') => setToast({ message, type });


  // 1. Fetch customer profile
  useEffect(() => {
    if (demoActive) {
      return;
    }

    let isMounted = true;
    const fetchProfile = async () => {
      setLoadingCustomer(true);
      try {
        const res = await client.get('/api/customer/me');
        if (isMounted) {
          setCustomer(res.data);
        }
      } catch (err) {
        console.error('Error fetching customer profile:', err);
        if (isMounted) {
          setErrorCustomer('Unable to load customer profile.');
        }
      } finally {
        if (isMounted) {
          setLoadingCustomer(false);
        }
      }
    };

    fetchProfile();
    return () => {
      isMounted = false;
    };
  }, [demoActive]);

  // 2. Fetch customer transaction history
  useEffect(() => {
    if (demoActive) return;

    let isMounted = true;
    const fetchTransactions = async () => {
      setLoadingTxs(true);
      try {
        const res = await client.get(`/api/customer/me/transactions?page=${page}&limit=${limit}`);
        if (isMounted) {
          setTransactions(res.data.transactions || []);
          setTotalCount(res.data.total || 0);
        }
      } catch (err) {
        console.error('Error fetching customer transactions:', err);
      } finally {
        if (isMounted) {
          setLoadingTxs(false);
        }
      }
    };

    if (customer) {
      fetchTransactions();
    }

    return () => {
      isMounted = false;
    };
  }, [customer, page]);

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/customer/login');
    } catch (err) {
      console.error('Sign out error:', err);
    }
  };

  const downloadQr = async (fmt) => {
    try {
      const response = await client.get(`/api/customer/me/coupon-qr?format=${fmt}`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], {
        type: fmt === 'svg' ? 'image/svg+xml' : 'image/png',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `incpay-coupon-${customer?.verbal_code || 'card'}.${fmt}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      showToast(`Personal coupon QR code (${fmt.toUpperCase()}) downloaded.`, 'success');
    } catch (err) {
      console.error('Failed to download QR:', err);
      showToast(`Failed to download QR code (${fmt.toUpperCase()}). Please try again.`, 'error');
    }
  };

  const [downloadingRef, setDownloadingRef] = useState(null);

  const handleDownloadReceipt = async (paystackRef) => {
    if (!paystackRef) return;
    if (demoActive) {
      showToast('Demo Transaction: Official PDF receipts are automatically generated and downloadable for live customer payments.', 'info');
      return;
    }
    setDownloadingRef(paystackRef);
    try {
      const response = await client.get(`/api/public/receipt/${encodeURIComponent(paystackRef)}`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `receipt-${paystackRef}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      showToast(`Receipt for payment ${paystackRef} downloaded.`, 'success');
    } catch (err) {
      console.error('Failed to download receipt PDF:', err);
      showToast('Unable to download receipt. Please verify that this transaction succeeded.', 'error');
    } finally {
      setDownloadingRef(null);
    }
  };

  const totalPages = Math.ceil(totalCount / limit) || 1;

  if (loadingCustomer) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm font-medium text-slate-600">Loading your IncPay Coupon...</span>
        </div>
      </div>
    );
  }

  if (errorCustomer || !customer) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <div className="max-w-md w-full bg-white p-8 rounded-2xl shadow border border-slate-200 text-center">
          <p className="text-red-600 font-semibold mb-4">{errorCustomer || 'Customer account not found.'}</p>
          <button
            onClick={handleSignOut}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800"
          >
            Sign In Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Toast message={toast?.message} type={toast?.type} onClose={() => setToast(null)} />

      {/* Navigation Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <img src="/logo.png" alt="IncPay" className="h-7 w-auto object-contain" style={{ minWidth: '110px' }} />
            <span className="hidden sm:inline-block px-2.5 py-0.5 text-xs bg-slate-100 text-slate-700 border border-slate-200 rounded font-bold uppercase tracking-wider">
              Customer Portal
            </span>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right hidden sm:block">
              <div className="text-sm font-bold text-slate-800">{customer.full_name}</div>
              <div className="text-xs text-slate-500">{customer.email}</div>
            </div>
            <button
              onClick={handleSignOut}
              className="px-3.5 py-1.5 text-xs sm:text-sm font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition border border-slate-300 cursor-pointer"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Welcome Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-teal-950 rounded-3xl p-6 sm:p-8 text-white shadow-xl flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 text-center md:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/20 text-teal-300 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse"></span>
              Active Digital IncPay Coupon
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Welcome back, {customer.full_name}
            </h1>
            <p className="text-slate-300 text-sm max-w-xl">
              Show your digital coupon or give your verbal code at any IncPay merchant to receive your instant discount and auto-save receipts.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => downloadQr('png')}
              className="px-4 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 rounded-xl font-bold text-xs sm:text-sm shadow-md transition flex items-center gap-2 cursor-pointer"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download PNG
            </button>
            <button
              onClick={() => downloadQr('svg')}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl font-medium text-xs sm:text-sm transition flex items-center gap-2 cursor-pointer"
            >
              Download SVG
            </button>
          </div>
        </div>

        {/* Digital Coupon Section */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Coupon Card */}
          <div className="lg:col-span-1 bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900 rounded-3xl p-6 text-white shadow-xl flex flex-col justify-between relative overflow-hidden border border-teal-500/30">
            <div className="absolute top-0 right-0 -mt-6 -mr-6 w-32 h-32 bg-teal-500/10 rounded-full blur-2xl pointer-events-none"></div>

            <div>
              <div className="flex justify-between items-start mb-6">
                <div>
                  <div className="bg-white/95 px-2.5 py-1 rounded-lg inline-flex items-center mb-2 shadow-xs">
                    <img src="/logo.png" alt="IncPay" className="h-4 w-auto object-contain" style={{ minWidth: '70px' }} />
                  </div>
                  <h3 className="text-lg font-black tracking-tight text-white">Digital Customer Coupon</h3>
                </div>
                <div className="px-2.5 py-1 bg-teal-500/20 rounded-md border border-teal-400/30 text-teal-300 text-xs font-bold">
                  VERIFIED
                </div>
              </div>

              {/* QR Code Container */}
              <div className="bg-white p-4 rounded-2xl shadow-inner mx-auto max-w-[210px] aspect-square flex items-center justify-center mb-6">
                <img
                  src={demoActive ? DEMO_QR_DATA_URL : `/api/customer/me/coupon-qr?format=${qrFormat}`}
                  alt="Personal IncPay Coupon QR"
                  className="w-full h-full object-contain"
                />
              </div>

              {/* Verbal Code Display */}
              <div className="bg-slate-950/60 rounded-xl p-3.5 border border-slate-700/60 text-center mb-4">
                <span className="text-slate-400 text-xs block mb-1 uppercase tracking-wider font-semibold">
                  Verbal Verification Code
                </span>
                <span className="text-xl sm:text-2xl font-mono font-black tracking-wider text-teal-300">
                  {customer.verbal_code || 'INCPAY'}
                </span>
                <span className="text-[11px] text-slate-400 block mt-1">
                  Say this code to the cashier if scanning is unavailable
                </span>
              </div>
            </div>

            <div className="border-t border-slate-700/60 pt-4 flex justify-between items-center text-xs text-slate-400">
              <span className="truncate max-w-[150px]">{customer.full_name}</span>
              <span>All IncPay Merchants</span>
            </div>
          </div>

          {/* Quick Guide & Benefits */}
          <div className="lg:col-span-2 bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-slate-200/80 flex flex-col justify-between space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900 mb-2">How your IncPay coupon works</h2>
              <p className="text-slate-600 text-sm mb-6">
                Your coupon is your digital passport to instant savings across our entire merchant network.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 rounded-2xl bg-teal-50/60 border border-teal-100 flex items-start space-x-3">
                  <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                    1
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">Show at Checkout</h4>
                    <p className="text-xs text-slate-600 mt-1">
                      Present your personal QR code or recite your 8-character verbal code when making a purchase.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-teal-50/60 border border-teal-100 flex items-start space-x-3">
                  <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                    2
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">Instant Merchant Discount</h4>
                    <p className="text-xs text-slate-600 mt-1">
                      The merchant's agreed discount (D/2) is automatically deducted from your total bill.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-teal-50/60 border border-teal-100 flex items-start space-x-3">
                  <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                    3
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">Official PDF Receipt</h4>
                    <p className="text-xs text-slate-600 mt-1">
                      A verifiable PDF receipt is emailed directly to your inbox and logged to your dashboard.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-teal-50/60 border border-teal-100 flex items-start space-x-3">
                  <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                    4
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">Account Safety</h4>
                    <p className="text-xs text-slate-600 mt-1">
                      Your coupon is cryptographically signed with HMAC-SHA256 for secure, tamper-proof identification.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="text-xs text-slate-600 text-center sm:text-left">
                <strong>Need help or have questions?</strong> Reach out to IncPay support at support@incpay.app
              </div>
              <a
                href="#transactions"
                className="text-xs font-bold text-teal-600 hover:text-teal-700 whitespace-nowrap"
              >
                View Payment History ↓
              </a>
            </div>
          </div>
        </section>

        {/* Transaction History Section */}
        <section id="transactions" className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-slate-200/80">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-100 gap-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Payment History &amp; Receipts</h2>
              <p className="text-slate-500 text-xs sm:text-sm mt-0.5">
                All transactions linked to your IncPay customer profile.
              </p>
            </div>
            <div className="text-xs font-semibold px-3 py-1.5 bg-slate-100 text-slate-700 rounded-full w-max">
              Total Payments: {totalCount}
            </div>
          </div>

          {loadingTxs ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-3">
              <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-xs font-medium text-slate-500">Loading your payments...</span>
            </div>
          ) : transactions.length === 0 ? (
            <div className="py-16 text-center">
              <div className="w-14 h-14 bg-teal-50 text-teal-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-base font-bold text-slate-900">No transactions recorded yet</h3>
              <p className="text-slate-500 text-xs sm:text-sm max-w-md mx-auto mt-1">
                Show your coupon QR code or provide your verbal code when checking out at any participating merchant to save and track your payments.
              </p>
            </div>
          ) : (
            <div>
              {/* Desktop Table View */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                      <th className="py-3 px-4">Date</th>
                      <th className="py-3 px-4">Merchant</th>
                      <th className="py-3 px-4 text-right">Listed Price</th>
                      <th className="py-3 px-4 text-right">Discount</th>
                      <th className="py-3 px-4 text-right">Amount Paid</th>
                      <th className="py-3 px-4 text-center">Status</th>
                      <th className="py-3 px-4 text-right">Receipt</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {transactions.map((tx) => (
                      <tr key={tx.id} className="hover:bg-slate-50/70 transition">
                        <td className="py-3.5 px-4 text-xs text-slate-600 whitespace-nowrap">
                          {new Date(tx.created_at).toLocaleDateString('en-GB', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-slate-900 whitespace-nowrap">
                          {tx.business_name}
                        </td>
                        <td className="py-3.5 px-4 text-right text-slate-500">
                          ₵{Number(tx.listed_amount).toFixed(2)}
                        </td>
                        <td className="py-3.5 px-4 text-right text-teal-600 font-medium">
                          -₵{Number(tx.customer_discount_amount).toFixed(2)}
                        </td>
                        <td className="py-3.5 px-4 text-right font-bold text-slate-900">
                          ₵{Number(tx.amount_paid).toFixed(2)}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <span
                            className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              tx.status === 'success'
                                ? 'bg-emerald-100 text-emerald-800'
                                : tx.status === 'failed'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-amber-100 text-amber-800'
                            }`}
                          >
                            {tx.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right whitespace-nowrap">
                          {tx.status === 'success' ? (
                            <button
                              type="button"
                              onClick={() => handleDownloadReceipt(tx.paystack_reference)}
                              disabled={downloadingRef === tx.paystack_reference}
                              className="inline-flex items-center text-xs font-semibold text-teal-600 hover:text-teal-700 bg-teal-50 hover:bg-teal-100 px-2.5 py-1 rounded-md transition cursor-pointer disabled:opacity-50"
                            >
                              {downloadingRef === tx.paystack_reference ? (
                                <span className="flex items-center space-x-1">
                                  <span className="w-3 h-3 border-2 border-teal-600 border-t-transparent rounded-full animate-spin"></span>
                                  <span>Downloading...</span>
                                </span>
                              ) : (
                                'Download PDF'
                              )}
                            </button>
                          ) : (
                            <span className="text-xs text-slate-400">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile Card View */}
              <div className="md:hidden divide-y divide-slate-100">
                {transactions.map((tx) => (
                  <div key={tx.id} className="py-4 space-y-2">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-bold text-slate-900 text-sm">{tx.business_name}</h4>
                        <span className="text-xs text-slate-500">
                          {new Date(tx.created_at).toLocaleDateString('en-GB', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </span>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                          tx.status === 'success'
                            ? 'bg-emerald-100 text-emerald-800'
                            : tx.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {tx.status}
                      </span>
                    </div>

                    <div className="flex justify-between items-center text-xs pt-1">
                      <span className="text-slate-500">
                        Listed: ₵{Number(tx.listed_amount).toFixed(2)} (Save ₵{Number(tx.customer_discount_amount).toFixed(2)})
                      </span>
                      <span className="font-extrabold text-slate-900 text-sm">
                        ₵{Number(tx.amount_paid).toFixed(2)}
                      </span>
                    </div>

                    {tx.status === 'success' && (
                      <div className="pt-2">
                        <button
                          type="button"
                          onClick={() => handleDownloadReceipt(tx.paystack_reference)}
                          disabled={downloadingRef === tx.paystack_reference}
                          className="w-full block text-center py-2 text-xs font-bold text-teal-700 bg-teal-50 hover:bg-teal-100 rounded-lg transition cursor-pointer disabled:opacity-50"
                        >
                          {downloadingRef === tx.paystack_reference
                            ? 'Downloading PDF Receipt...'
                            : 'Download Official Receipt (PDF)'}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="px-3.5 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 transition cursor-pointer"
                  >
                    Previous
                  </button>
                  <span className="text-xs text-slate-500">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="px-3.5 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 transition cursor-pointer"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

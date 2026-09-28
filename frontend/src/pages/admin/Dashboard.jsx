import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';
import AdminLayout from '../../components/AdminLayout';

export default function Dashboard() {
  const { user } = useAuth();
  const [authStatus, setAuthStatus] = useState(null);
  const [verifying, setVerifying] = useState(false);

  const testBackendAuth = async () => {
    setVerifying(true);
    try {
      const response = await client.get('/api/auth/me');
      setAuthStatus({
        success: true,
        data: response.data,
      });
    } catch (err) {
      setAuthStatus({
        success: false,
        error: err.response?.data?.detail || err.message,
      });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <AdminLayout activeTab="dashboard">
      <div className="space-y-6">
        {/* Welcome Card */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 sm:p-6 shadow-xs">
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-1.5">
            Welcome, {user?.email || 'Admin'}
          </h2>
          <p className="text-xs sm:text-sm text-gray-600">
            IncPay payment-bridge platform administration shell.
          </p>
        </div>

        {/* Quick Actions & Navigation Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 sm:gap-6">
          {/* Sellers Card */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 sm:p-6 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-base font-bold text-gray-900">Seller Onboarding</h3>
                <span className="text-xs font-semibold px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                  Phase 3
                </span>
              </div>
              <p className="text-xs sm:text-sm text-gray-600 mb-6">
                Register merchant partners, configure agreed discount rates (D), and generate Paystack settlement subaccounts.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2.5 sm:gap-3">
              <Link
                to="/admin/sellers"
                className="flex-1 text-center py-2.5 px-4 bg-gray-900 hover:bg-gray-800 text-white text-sm font-medium rounded-lg transition-colors"
              >
                View Sellers
              </Link>
              <Link
                to="/admin/sellers/new"
                className="text-center py-2.5 px-4 border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-lg transition-colors"
              >
                + New Seller
              </Link>
            </div>
          </div>

          {/* Transactions Card */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 sm:p-6 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-base font-bold text-gray-900">Transaction Ledger</h3>
                <span className="text-xs font-semibold px-2 py-0.5 bg-purple-50 text-purple-700 rounded">
                  Phase 8
                </span>
              </div>
              <p className="text-xs sm:text-sm text-gray-600 mb-6">
                Live ledger of customer payments, margin splits, Paystack webhook event history, and receipt downloads.
              </p>
            </div>
            <div>
              <Link
                to="/admin/transactions"
                className="block text-center py-2.5 px-4 bg-gray-900 hover:bg-gray-800 text-white text-sm font-medium rounded-lg transition-colors"
              >
                View Transactions &rarr;
              </Link>
            </div>
          </div>

          {/* Token Verification Card */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 sm:p-6 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-base font-bold text-gray-900">API Authentication</h3>
                <span className="text-xs font-semibold px-2 py-0.5 bg-green-50 text-green-700 rounded">
                  Active
                </span>
              </div>
              <p className="text-xs sm:text-sm text-gray-600 mb-4">
                Verify Axios token interceptor and FastAPI <code>verify_admin</code> dependency against Supabase Auth.
              </p>
            </div>

            <div>
              <button
                onClick={testBackendAuth}
                disabled={verifying}
                className="w-full py-2.5 px-4 border border-gray-300 hover:bg-gray-50 disabled:bg-gray-100 text-gray-800 text-sm font-medium rounded-lg transition-colors"
              >
                {verifying ? 'Verifying Token...' : 'Test /api/auth/me Connection'}
              </button>

              {authStatus && (
                <div
                  className={`mt-3 p-2.5 rounded-lg text-xs ${
                    authStatus.success
                      ? 'bg-green-50 text-green-800 border border-green-200'
                      : 'bg-red-50 text-red-800 border border-red-200'
                  }`}
                >
                  {authStatus.success ? (
                    <span>
                      Token valid! User ID: <strong>{authStatus.data?.id}</strong>
                    </span>
                  ) : (
                    <span>Verification failed: {authStatus.error}</span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}

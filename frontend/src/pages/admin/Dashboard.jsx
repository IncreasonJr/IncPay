import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';

export default function Dashboard() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [authStatus, setAuthStatus] = useState(null);
  const [verifying, setVerifying] = useState(false);

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/login', { replace: true });
    } catch (err) {
      console.error('Sign out error:', err);
    }
  };

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
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
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
                className="text-sm font-medium text-gray-900 bg-gray-100 px-3 py-2 rounded-md"
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
                className="text-sm font-medium text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md transition-colors"
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
              onClick={handleSignOut}
              className="text-sm font-medium text-gray-700 hover:text-gray-900 px-3 py-1.5 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Welcome Card */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Welcome, {user?.email || 'Admin'}
          </h2>
          <p className="text-sm text-gray-600">
            IncPay payment-bridge platform administration shell.
          </p>
        </div>

        {/* Quick Actions & Navigation Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {/* Sellers Card */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-base font-semibold text-gray-900">Seller Onboarding</h3>
                <span className="text-xs font-semibold px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                  Phase 3
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-6">
                Register merchant partners, configure agreed discount percentage rates (D), and automatically generate Paystack settlement subaccounts.
              </p>
            </div>
            <div className="flex space-x-3">
              <Link
                to="/admin/sellers"
                className="flex-1 text-center py-2 px-4 bg-gray-900 hover:bg-gray-800 text-white text-sm font-medium rounded-md transition-colors"
              >
                View Sellers
              </Link>
              <Link
                to="/admin/sellers/new"
                className="py-2 px-4 border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-md transition-colors"
              >
                + New Seller
              </Link>
            </div>
          </div>

          {/* Transactions Card */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-base font-semibold text-gray-900">Transaction Ledger</h3>
                <span className="text-xs font-semibold px-2 py-0.5 bg-purple-50 text-purple-700 rounded">
                  Phase 8
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-6">
                Live ledger of customer payments, margin splits, Paystack webhook event history, PDF receipt downloads, and receipt resends.
              </p>
            </div>
            <div>
              <Link
                to="/admin/transactions"
                className="block text-center py-2 px-4 bg-gray-900 hover:bg-gray-800 text-white text-sm font-medium rounded-md transition-colors"
              >
                View Transactions &rarr;
              </Link>
            </div>
          </div>

          {/* Token Verification Card */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-base font-semibold text-gray-900">API Authentication</h3>
                <span className="text-xs font-semibold px-2 py-0.5 bg-green-50 text-green-700 rounded">
                  Active
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                Verify Axios token interceptor and FastAPI <code>verify_admin</code> dependency against Supabase Auth.
              </p>
            </div>

            <div>
              <button
                onClick={testBackendAuth}
                disabled={verifying}
                className="w-full py-2 px-4 border border-gray-300 hover:bg-gray-50 disabled:bg-gray-100 text-gray-800 text-sm font-medium rounded-md transition-colors"
              >
                {verifying ? 'Verifying Token...' : 'Test /api/auth/me Connection'}
              </button>

              {authStatus && (
                <div
                  className={`mt-3 p-2.5 rounded text-xs ${
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
      </main>
    </div>
  );
}

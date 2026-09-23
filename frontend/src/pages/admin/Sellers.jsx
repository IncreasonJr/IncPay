import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';
import QrModal from '../../components/QrModal';

export default function Sellers() {
  const { user, signOut } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sellers, setSellers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedQrSeller, setSelectedQrSeller] = useState(null);

  const fetchSellers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.get('/api/sellers');
      const loadedSellers = response.data || [];
      setSellers(loadedSellers);

      // Check if newly created seller ID passed in query param (?new=...)
      const newSellerId = searchParams.get('new');
      if (newSellerId) {
        const found = loadedSellers.find((s) => s.id === newSellerId);
        if (found) {
          setSelectedQrSeller(found);
          setSearchParams({}, { replace: true });
        }
      }
    } catch (err) {
      console.error('Failed to fetch sellers:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load sellers.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSellers();
  }, []);

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
                className="text-sm font-medium text-gray-900 bg-gray-100 px-3 py-2 rounded-md"
              >
                Sellers
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
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8 gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Sellers Directory</h1>
            <p className="text-sm text-gray-600 mt-1">
              Onboard and manage merchant partner subaccounts for automated split settlements.
            </p>
          </div>

          <Link
            to="/admin/sellers/new"
            className="inline-flex items-center justify-center px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white text-sm font-medium rounded-md shadow-sm transition-colors"
          >
            + Add Seller
          </Link>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-md bg-red-50 border border-red-200 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Sellers Table Card */}
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-sm text-gray-500">
              <div className="inline-block w-6 h-6 border-2 border-gray-900 border-t-transparent rounded-full animate-spin mb-2"></div>
              <p>Loading sellers...</p>
            </div>
          ) : sellers.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-gray-500 text-sm mb-4">No sellers have been onboarded yet.</p>
              <Link
                to="/admin/sellers/new"
                className="inline-flex items-center px-3.5 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                Onboard Your First Seller
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
                <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Business Name</th>
                    <th className="px-6 py-3 font-semibold">Contact</th>
                    <th className="px-6 py-3 font-semibold">Agreed (D)</th>
                    <th className="px-6 py-3 font-semibold">Customer (D/2)</th>
                    <th className="px-6 py-3 font-semibold">Paystack Subaccount</th>
                    <th className="px-6 py-3 font-semibold">Settlement</th>
                    <th className="px-6 py-3 font-semibold">Status</th>
                    <th className="px-6 py-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {sellers.map((seller) => {
                    const d = parseFloat(seller.agreed_discount || 0);
                    const customerDiscount = (d / 2).toFixed(2);
                    return (
                      <tr key={seller.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 font-medium text-gray-900">
                          {seller.business_name}
                        </td>
                        <td className="px-6 py-4 text-gray-600">
                          <div>{seller.contact_email}</div>
                          {seller.contact_phone && (
                            <div className="text-xs text-gray-400">{seller.contact_phone}</div>
                          )}
                        </td>
                        <td className="px-6 py-4 font-semibold text-gray-900">
                          {d.toFixed(1)}%
                        </td>
                        <td className="px-6 py-4 font-semibold text-green-700">
                          {customerDiscount}% off
                        </td>
                        <td className="px-6 py-4 font-mono text-xs text-gray-600">
                          {seller.paystack_subaccount_code ? (
                            <span className="bg-gray-100 px-2 py-1 rounded">
                              {seller.paystack_subaccount_code}
                            </span>
                          ) : (
                            <span className="text-gray-400 italic">None</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-xs text-gray-600">
                          <div className="capitalize font-medium text-gray-800">
                            {seller.settlement_type === 'mobile_money'
                              ? 'Mobile Money'
                              : 'Bank Transfer'}
                          </div>
                          <div>
                            {seller.settlement_bank_code} • {seller.settlement_account_number}
                          </div>
                          {seller.settlement_account_name && (
                            <div className="text-gray-400 text-xs">
                              {seller.settlement_account_name}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                              seller.is_active
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {seller.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right space-x-3">
                          <button
                            onClick={() => setSelectedQrSeller(seller)}
                            className="inline-flex items-center text-xs font-semibold px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded transition-colors"
                            title="View QR Code & Coupon"
                          >
                            QR
                          </button>
                          <Link
                            to={`/admin/sellers/${seller.id}/edit`}
                            className="text-sm font-medium text-gray-900 hover:text-gray-600 underline"
                          >
                            Edit
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* QR Code & Coupon Modal */}
      {selectedQrSeller && (
        <QrModal
          seller={selectedQrSeller}
          onClose={() => setSelectedQrSeller(null)}
        />
      )}
    </div>
  );
}

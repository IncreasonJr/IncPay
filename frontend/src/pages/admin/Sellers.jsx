import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import client from '../../api/client';
import QrModal from '../../components/QrModal';
import AdminLayout from '../../components/AdminLayout';

export default function Sellers() {
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
    <AdminLayout activeTab="sellers">
      <div className="space-y-6">
        {/* Page Title & Add Button */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Sellers Directory</h1>
            <p className="text-xs sm:text-sm text-gray-600 mt-1">
              Onboard and manage merchant partner subaccounts for automated split settlements.
            </p>
          </div>

          <Link
            to="/admin/sellers/new"
            className="inline-flex items-center justify-center px-4 py-2.5 bg-gray-900 hover:bg-gray-800 text-white text-sm font-semibold rounded-lg shadow-xs transition-colors shrink-0"
          >
            + Add Seller
          </Link>
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-xs sm:text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Sellers Listing */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-xs overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-sm text-gray-500">
              <div className="inline-block w-6 h-6 border-2 border-gray-900 border-t-transparent rounded-full animate-spin mb-2"></div>
              <p>Loading sellers...</p>
            </div>
          ) : sellers.length === 0 ? (
            <div className="p-10 sm:p-12 text-center">
              <p className="text-gray-500 text-sm mb-4">No sellers have been onboarded yet.</p>
              <Link
                to="/admin/sellers/new"
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                Onboard Your First Seller
              </Link>
            </div>
          ) : (
            <>
              {/* 1. Mobile Cards View (Visible on < md screens) */}
              <div className="md:hidden divide-y divide-gray-100">
                {sellers.map((seller) => {
                  const d = parseFloat(seller.agreed_discount || 0);
                  const customerDiscount = (d / 2).toFixed(2);
                  return (
                    <div key={seller.id} className="p-4 space-y-3.5">
                      {/* Business & Status */}
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h2 className="text-base font-bold text-gray-900">
                            {seller.business_name}
                          </h2>
                          <p className="text-xs text-gray-500 mt-0.5">{seller.contact_email}</p>
                          {seller.contact_phone && (
                            <p className="text-xs text-gray-400">{seller.contact_phone}</p>
                          )}
                        </div>
                        <span
                          className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full shrink-0 ${
                            seller.is_active
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {seller.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>

                      {/* Economics & Subaccount Grid */}
                      <div className="grid grid-cols-2 gap-2 bg-gray-50 p-3 rounded-lg text-xs">
                        <div>
                          <span className="text-gray-400 uppercase text-[10px] font-semibold block">Agreed (D)</span>
                          <span className="font-bold text-gray-900">{d.toFixed(1)}%</span>
                        </div>
                        <div>
                          <span className="text-gray-400 uppercase text-[10px] font-semibold block">Customer (D/2)</span>
                          <span className="font-bold text-emerald-700">{customerDiscount}% off</span>
                        </div>
                        <div className="col-span-2 pt-1 border-t border-gray-200">
                          <span className="text-gray-400 uppercase text-[10px] font-semibold block">Settlement Destination</span>
                          <span className="font-medium text-gray-800">
                            {seller.settlement_type === 'mobile_money' ? 'MoMo: ' : 'Bank: '}
                            {seller.settlement_bank_code} • {seller.settlement_account_number}
                          </span>
                          {seller.settlement_account_name && (
                            <span className="text-gray-500 block text-[11px]">({seller.settlement_account_name})</span>
                          )}
                        </div>
                        {seller.paystack_subaccount_code && (
                          <div className="col-span-2 pt-1 border-t border-gray-200">
                            <span className="text-gray-400 uppercase text-[10px] font-semibold block">Subaccount</span>
                            <span className="font-mono text-gray-700 font-semibold">{seller.paystack_subaccount_code}</span>
                          </div>
                        )}
                      </div>

                      {/* Action Buttons */}
                      <div className="flex items-center gap-2 pt-1">
                        <button
                          onClick={() => setSelectedQrSeller(seller)}
                          className="flex-1 py-2 px-3 bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-semibold rounded-lg transition-colors flex items-center justify-center space-x-1.5"
                        >
                          <span>📱</span>
                          <span>View QR &amp; Coupon</span>
                        </button>
                        <Link
                          to={`/admin/sellers/${seller.id}/edit`}
                          className="py-2 px-4 border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold rounded-lg transition-colors text-center"
                        >
                          Edit
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* 2. Desktop Table View (Visible on >= md screens) */}
              <div className="hidden md:block overflow-x-auto">
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
                          <td className="px-6 py-4 font-semibold text-gray-900">
                            {seller.business_name}
                          </td>
                          <td className="px-6 py-4 text-gray-600 text-xs">
                            <div className="font-medium text-gray-900">{seller.contact_email}</div>
                            {seller.contact_phone && (
                              <div className="text-gray-400">{seller.contact_phone}</div>
                            )}
                          </td>
                          <td className="px-6 py-4 font-semibold text-gray-900">
                            {d.toFixed(1)}%
                          </td>
                          <td className="px-6 py-4 font-semibold text-emerald-700">
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
                              className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${
                                seller.is_active
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : 'bg-gray-100 text-gray-800'
                              }`}
                            >
                              {seller.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right space-x-2">
                            <button
                              onClick={() => setSelectedQrSeller(seller)}
                              className="inline-flex items-center text-xs font-semibold px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded transition-colors"
                              title="View QR Code & Coupon"
                            >
                              QR
                            </button>
                            <Link
                              to={`/admin/sellers/${seller.id}/edit`}
                              className="text-xs font-semibold text-gray-900 hover:text-gray-600 underline"
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
            </>
          )}
        </div>
      </div>

      {/* QR Code & Coupon Modal */}
      {selectedQrSeller && (
        <QrModal
          seller={selectedQrSeller}
          onClose={() => setSelectedQrSeller(null)}
        />
      )}
    </AdminLayout>
  );
}

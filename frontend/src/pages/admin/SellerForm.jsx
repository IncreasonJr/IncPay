import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import client from '../../api/client';

export default function SellerForm() {
  const { id } = useParams();
  const isEditMode = Boolean(id);
  const navigate = useNavigate();
  const { user, signOut } = useAuth();

  // Form fields
  const [businessName, setBusinessName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [agreedDiscount, setAgreedDiscount] = useState('20.00');
  const [settlementType, setSettlementType] = useState('mobile_money');
  const [settlementBankCode, setSettlementBankCode] = useState('MTN');
  const [settlementAccountNumber, setSettlementAccountNumber] = useState('');
  const [settlementAccountName, setSettlementAccountName] = useState('');
  const [isActive, setIsActive] = useState(true);

  // Directory lists
  const [banks, setBanks] = useState([]);
  const [mobileProviders, setMobileProviders] = useState([]);

  // UI state
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // 1. Fetch bank and mobile money provider directories
  useEffect(() => {
    const fetchDirectories = async () => {
      try {
        const [banksRes, mmRes] = await Promise.all([
          client.get('/api/banks'),
          client.get('/api/mobile-money-providers'),
        ]);
        setBanks(banksRes.data || []);
        setMobileProviders(mmRes.data || []);
      } catch (err) {
        console.error('Failed to load bank/mobile directories:', err);
      }
    };

    fetchDirectories();
  }, []);

  // 2. Fetch seller details if in Edit mode
  useEffect(() => {
    if (!isEditMode) return;

    const fetchSeller = async () => {
      setLoading(true);
      try {
        const res = await client.get(`/api/sellers/${id}`);
        const seller = res.data;
        setBusinessName(seller.business_name || '');
        setContactEmail(seller.contact_email || '');
        setContactPhone(seller.contact_phone || '');
        setAgreedDiscount(seller.agreed_discount || '20.00');
        setSettlementType(seller.settlement_type || 'mobile_money');
        setSettlementBankCode(seller.settlement_bank_code || 'MTN');
        setSettlementAccountNumber(seller.settlement_account_number || '');
        setSettlementAccountName(seller.settlement_account_name || '');
        setIsActive(seller.is_active ?? true);
      } catch (err) {
        console.error('Failed to fetch seller:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to load seller.');
      } finally {
        setLoading(false);
      }
    };

    fetchSeller();
  }, [id, isEditMode]);

  // Adjust default bank code when settlement type changes
  const handleSettlementTypeChange = (type) => {
    setSettlementType(type);
    if (type === 'mobile_money') {
      setSettlementBankCode('MTN');
    } else if (banks.length > 0) {
      setSettlementBankCode(banks[0].code);
    }
  };

  // Live Math calculations
  const parsedD = parseFloat(agreedDiscount) || 0;
  const validD = parsedD > 0 && parsedD < 100;
  const customerDiscount = validD ? (parsedD / 2).toFixed(2) : '0.00';
  const percentageCharge = validD ? ((parsedD / (200 - parsedD)) * 100).toFixed(2) : '0.00';

  // Example sale based on ₵1,000 listed amount
  const exampleListed = 1000;
  const exampleCustomerDiscount = (exampleListed * (parsedD / 200)).toFixed(2);
  const exampleCustomerPaid = (exampleListed - parseFloat(exampleCustomerDiscount)).toFixed(2);
  const examplePlatformCut = exampleCustomerDiscount;
  const exampleSellerPayout = (exampleCustomerPaid - examplePlatformCut).toFixed(2);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const payload = {
      business_name: businessName.trim(),
      contact_email: contactEmail.trim(),
      contact_phone: contactPhone.trim() || null,
      agreed_discount: parseFloat(agreedDiscount),
      settlement_type: settlementType,
      settlement_bank_code: settlementBankCode,
      settlement_account_number: settlementAccountNumber.trim(),
      settlement_account_name: settlementAccountName.trim(),
      is_active: isActive,
    };

    try {
      if (isEditMode) {
        await client.put(`/api/sellers/${id}`, payload);
        navigate('/admin/sellers');
      } else {
        const res = await client.post('/api/sellers', payload);
        const newSellerId = res.data?.id;
        navigate(newSellerId ? `/admin/sellers?new=${newSellerId}` : '/admin/sellers');
      }
    } catch (err) {
      console.error('Error saving seller:', err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Failed to save seller. Please check the provided information.'
      );
    } finally {
      setSubmitting(false);
    }
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
                className="text-sm font-medium text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md"
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
            <span className="text-sm text-gray-600 hidden sm:inline-block">{user?.email}</span>
            <button
              onClick={signOut}
              className="text-sm font-medium text-gray-700 hover:text-gray-900 px-3 py-1.5 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <Link
            to="/admin/sellers"
            className="text-xs font-medium text-gray-500 hover:text-gray-900 flex items-center gap-1 mb-2"
          >
            ← Back to Sellers
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">
            {isEditMode ? 'Edit Seller Partner' : 'Onboard New Seller Partner'}
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            {isEditMode
              ? 'Update merchant settlement details and agreed discount rates.'
              : 'Configure merchant profile, agreed discount, and create their Paystack settlement subaccount.'}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-md bg-red-50 border border-red-200 text-sm text-red-700">
            <strong>Error: </strong>
            {error}
          </div>
        )}

        {loading ? (
          <div className="p-12 text-center text-sm text-gray-500 bg-white border border-gray-200 rounded-lg">
            Loading seller details...
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* 1. Business & Contact Information */}
            <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
              <h2 className="text-base font-semibold text-gray-900 mb-4">
                1. Merchant Business Details
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Business Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    placeholder="e.g. Accra Electronics Ltd"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Contact Email <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="email"
                    required
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    placeholder="merchant@example.com"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Contact Phone (Optional)
                  </label>
                  <input
                    type="text"
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    placeholder="+233 24 000 0000"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
                  />
                </div>
              </div>
            </div>

            {/* 2. Agreed Discount Rate & Live Preview */}
            <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
              <h2 className="text-base font-semibold text-gray-900 mb-2">
                2. Commercial Economics & Discount (D)
              </h2>
              <p className="text-xs text-gray-500 mb-4">
                Agreed discount percentage D provided by seller. IncPay grants D/2 to customer and retains D/2.
              </p>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Agreed Discount (D %) <span className="text-red-500">*</span>
                </label>
                <div className="flex items-center space-x-3">
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="99.99"
                    required
                    value={agreedDiscount}
                    onChange={(e) => setAgreedDiscount(e.target.value)}
                    className="w-32 px-3 py-2 border border-gray-300 rounded-md text-sm font-semibold focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
                  />
                  <span className="text-sm font-bold text-gray-700">%</span>
                </div>
              </div>

              {/* Live Preview Card */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                  Live Financial Split Preview
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
                  <div className="p-2.5 bg-white border border-gray-200 rounded">
                    <span className="block text-xs text-gray-500">Customer Discount (D/2)</span>
                    <span className="text-base font-bold text-green-700">{customerDiscount}% off</span>
                  </div>
                  <div className="p-2.5 bg-white border border-gray-200 rounded">
                    <span className="block text-xs text-gray-500">Paystack Charge Rate</span>
                    <span className="text-base font-bold text-gray-900">{percentageCharge}%</span>
                  </div>
                  <div className="p-2.5 bg-white border border-gray-200 rounded col-span-2 sm:col-span-1">
                    <span className="block text-xs text-gray-500">Currency</span>
                    <span className="text-base font-bold text-gray-900">Ghanaian Cedi (₵)</span>
                  </div>
                </div>

                <div className="text-xs text-gray-600 border-t border-gray-200 pt-3 space-y-1">
                  <div className="font-medium text-gray-700">Example on ₵1,000 listed order:</div>
                  <div className="flex justify-between">
                    <span>Customer pays (after {customerDiscount}% discount):</span>
                    <span className="font-semibold text-gray-900">₵{exampleCustomerPaid}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>IncPay platform cut (D/2 revenue):</span>
                    <span className="font-semibold text-blue-700">₵{examplePlatformCut}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Seller received payout:</span>
                    <span className="font-semibold text-green-700">₵{exampleSellerPayout}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 3. Settlement Destination */}
            <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
              <h2 className="text-base font-semibold text-gray-900 mb-4">
                3. Paystack Settlement Destination
              </h2>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Settlement Channel <span className="text-red-500">*</span>
                </label>
                <div className="flex items-center space-x-6">
                  <label className="inline-flex items-center text-sm font-medium text-gray-700 cursor-pointer">
                    <input
                      type="radio"
                      name="settlementType"
                      value="mobile_money"
                      checked={settlementType === 'mobile_money'}
                      onChange={() => handleSettlementTypeChange('mobile_money')}
                      className="h-4 w-4 text-gray-900 focus:ring-gray-900"
                    />
                    <span className="ml-2">Mobile Money</span>
                  </label>
                  <label className="inline-flex items-center text-sm font-medium text-gray-700 cursor-pointer">
                    <input
                      type="radio"
                      name="settlementType"
                      value="bank"
                      checked={settlementType === 'bank'}
                      onChange={() => handleSettlementTypeChange('bank')}
                      className="h-4 w-4 text-gray-900 focus:ring-gray-900"
                    />
                    <span className="ml-2">Bank Account</span>
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {settlementType === 'mobile_money' ? 'Telco Provider' : 'Bank Institution'}{' '}
                    <span className="text-red-500">*</span>
                  </label>
                  <select
                    required
                    value={settlementBankCode}
                    onChange={(e) => setSettlementBankCode(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
                  >
                    {settlementType === 'mobile_money'
                      ? mobileProviders.map((p) => (
                          <option key={p.code} value={p.code}>
                            {p.name} ({p.code})
                          </option>
                        ))
                      : banks.map((b) => (
                          <option key={b.code} value={b.code}>
                            {b.name}
                          </option>
                        ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {settlementType === 'mobile_money' ? 'Mobile Money Number' : 'Account Number'}{' '}
                    <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={settlementAccountNumber}
                    onChange={(e) => setSettlementAccountNumber(e.target.value)}
                    placeholder={settlementType === 'mobile_money' ? 'e.g. 0240000000' : 'e.g. 1029384756'}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Account Holder Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={settlementAccountName}
                    onChange={(e) => setSettlementAccountName(e.target.value)}
                    placeholder="Full name as registered with Bank or Telco"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
                  />
                </div>
              </div>
            </div>

            {/* Submit & Cancel Actions */}
            <div className="flex items-center justify-end space-x-4">
              <Link
                to="/admin/sellers"
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={submitting || !validD}
                className="px-6 py-2 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-400 text-white text-sm font-medium rounded-md shadow-sm transition-colors"
              >
                {submitting ? 'Creating Paystack Subaccount...' : isEditMode ? 'Save Changes' : 'Onboard Seller'}
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import client from '../api/client';
import { openPaystackCheckout } from '../api/paystack';

export default function Pay() {
  const { couponCode } = useParams();
  const navigate = useNavigate();

  // Coupon state
  const [coupon, setCoupon] = useState(null);
  const [loadingCoupon, setLoadingCoupon] = useState(true);
  const [couponError, setCouponError] = useState(null);

  // Form input state
  const [listedAmount, setListedAmount] = useState('');
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [paymentError, setPaymentError] = useState(null);
  const [cancelMessage, setCancelMessage] = useState(null);

  // 1. Fetch public coupon and merchant details on mount
  useEffect(() => {
    const fetchCoupon = async () => {
      setLoadingCoupon(true);
      setCouponError(null);
      try {
        const res = await client.get(`/api/public/coupon/${couponCode}`);
        setCoupon(res.data);
      } catch (err) {
        console.error('Failed to load coupon:', err);
        setCouponError(
          err.response?.data?.detail || 'This payment link or coupon code is invalid or has expired.'
        );
      } finally {
        setLoadingCoupon(false);
      }
    };

    if (couponCode) {
      fetchCoupon();
    } else {
      setCouponError('No coupon code provided in URL.');
      setLoadingCoupon(false);
    }
  }, [couponCode]);

  // Client-side live financial calculation for preview only
  const parsedListed = parseFloat(listedAmount) || 0;
  const agreedD = coupon ? parseFloat(coupon.agreed_discount || 0) : 0;
  const customerDiscountRate = coupon ? parseFloat(coupon.customer_discount || 0) : 0;

  const validAmount = parsedListed >= 1.0;
  const discountAmount = validAmount ? (parsedListed * (agreedD / 200)).toFixed(2) : '0.00';
  const totalToPay = validAmount
    ? (parsedListed - parseFloat(discountAmount)).toFixed(2)
    : '0.00';

  // 2. Handle Payment Submission
  const handlePayment = async (e) => {
    e.preventDefault();
    if (!validAmount) return;

    setSubmitting(true);
    setPaymentError(null);
    setCancelMessage(null);

    try {
      // Step A: Initialize payment on backend
      const payload = {
        coupon_code: couponCode,
        listed_amount: parsedListed,
        email: email.trim() || undefined,
      };

      const res = await client.post('/api/public/initialize-payment', payload);
      const { access_code, reference } = res.data;

      // Step B: Open Paystack Inline Checkout modal
      openPaystackCheckout({
        accessCode: access_code,
        onSuccess: (tx) => {
          const finalRef = tx?.reference || reference;
          navigate(`/pay/success?reference=${encodeURIComponent(finalRef)}`);
        },
        onCancel: () => {
          setSubmitting(false);
          setCancelMessage('Payment was cancelled. You can try again whenever you are ready.');
        },
        onError: (err) => {
          setSubmitting(false);
          setPaymentError(err.message || 'Payment processing failed. Please try again.');
        },
      });
    } catch (err) {
      console.error('Payment initialization error:', err);
      setSubmitting(false);
      setPaymentError(
        err.response?.data?.detail ||
          err.message ||
          'Failed to initialize checkout. Please check the amount and try again.'
      );
    }
  };

  // Render Loading State
  if (loadingCoupon) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 max-w-md w-full text-center">
          <div className="inline-block w-8 h-8 border-3 border-gray-900 border-t-transparent rounded-full animate-spin mb-4"></div>
          <h2 className="text-base font-semibold text-gray-900">Loading Checkout</h2>
          <p className="text-xs text-gray-500 mt-1">Connecting to merchant gateway...</p>
        </div>
      </div>
    );
  }

  // Render Invalid / Expired Coupon State
  if (couponError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 max-w-md w-full text-center">
          <div className="w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4 font-bold text-xl">
            ✕
          </div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Invalid Payment Link</h1>
          <p className="text-sm text-gray-600 mb-6">{couponError}</p>
          <div className="text-xs text-gray-400 bg-gray-50 border border-gray-200 rounded-lg p-3">
            Please ask the merchant to provide a new QR code or valid checkout link.
          </div>
        </div>
      </div>
    );
  }

  // Render Active Checkout Form
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 flex flex-col justify-between py-12 px-4 sm:px-6">
      <div className="max-w-md w-full mx-auto">
        {/* IncPay Platform Top Bar */}
        <div className="text-center mb-6">
          <span className="text-xs uppercase tracking-widest font-bold text-gray-400">
            IncPay Payment Bridge
          </span>
        </div>

        {/* Payment Card */}
        <div className="bg-white rounded-2xl shadow-md border border-gray-200 overflow-hidden">
          {/* Card Header: Merchant Info */}
          <div className="bg-gray-900 text-white p-6 text-center">
            <span className="text-xs uppercase font-semibold tracking-wider text-gray-400 block mb-1">
              Paying Merchant
            </span>
            <h1 className="text-2xl font-bold tracking-tight">
              {coupon?.business_name}
            </h1>
            <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1 bg-green-500/20 text-green-300 border border-green-500/30 rounded-full text-xs font-semibold">
              <span>🏷️</span>
              <span>{customerDiscountRate}% Instant Discount Applied</span>
            </div>
          </div>

          {/* Card Body */}
          <form onSubmit={handlePayment} className="p-6 space-y-6">
            {/* Feedback Notifications */}
            {paymentError && (
              <div className="p-3.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg">
                <strong>Error: </strong>
                {paymentError}
              </div>
            )}

            {cancelMessage && (
              <div className="p-3.5 bg-amber-50 border border-amber-200 text-amber-800 text-xs rounded-lg">
                {cancelMessage}
              </div>
            )}

            {/* 1. Listed Bill Amount */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1.5">
                Total Bill / Listed Amount <span className="text-red-500">*</span>
              </label>
              <div className="relative rounded-lg shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <span className="text-gray-500 text-base font-bold">₵</span>
                </div>
                <input
                  type="number"
                  step="0.01"
                  min="1"
                  required
                  placeholder="0.00"
                  value={listedAmount}
                  onChange={(e) => {
                    setListedAmount(e.target.value);
                    setCancelMessage(null);
                    setPaymentError(null);
                  }}
                  className="w-full pl-8 pr-4 py-3 border border-gray-300 rounded-lg text-lg font-bold text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-gray-900 focus:border-gray-900"
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Enter the original bill amount before any discount is applied.
              </p>
            </div>

            {/* 2. Customer Email (Optional) */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1.5">
                Your Email Address <span className="text-gray-400 font-normal">(Optional)</span>
              </label>
              <input
                type="email"
                placeholder="your-name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-gray-900 focus:border-gray-900"
              />
              <p className="text-xs text-gray-400 mt-1">
                We'll email you a payment receipt and confirmation.
              </p>
            </div>

            {/* 3. Live Financial Split Breakdown */}
            {validAmount && (
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-2.5">
                <div className="flex justify-between text-xs text-gray-600">
                  <span>Listed Original Bill:</span>
                  <span className="font-semibold text-gray-900">₵{parsedListed.toFixed(2)}</span>
                </div>

                <div className="flex justify-between text-xs text-green-700 font-medium">
                  <span>IncPay Discount ({customerDiscountRate}% off):</span>
                  <span>-₵{discountAmount}</span>
                </div>

                <div className="border-t border-gray-200 pt-2.5 flex justify-between items-baseline">
                  <span className="text-sm font-bold text-gray-900">Total to Pay:</span>
                  <div className="text-right">
                    <span className="text-2xl font-black text-gray-900">₵{totalToPay}</span>
                    <span className="block text-[10px] text-gray-500 uppercase tracking-wider">
                      Ghanaian Cedis
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting || !validAmount}
              className="w-full py-3.5 px-4 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-300 text-white font-bold text-base rounded-xl shadow-md transition-all flex items-center justify-center space-x-2"
            >
              {submitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Opening Secure Checkout...</span>
                </>
              ) : validAmount ? (
                <span>Pay ₵{totalToPay} Now</span>
              ) : (
                <span>Enter Bill Amount to Pay</span>
              )}
            </button>
          </form>

          {/* Secure Footer */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span>🔒</span> Secured 256-bit SSL
            </span>
            <span>Powered by Paystack</span>
          </div>
        </div>
      </div>

      {/* Footer Branding */}
      <footer className="mt-8 text-center text-xs text-gray-400">
        <p>IncPay Ghana — Direct Merchant Payment Bridge</p>
      </footer>
    </div>
  );
}

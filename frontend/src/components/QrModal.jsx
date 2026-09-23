import React, { useState, useEffect } from 'react';
import client from '../api/client';

export default function QrModal({ seller, onClose }) {
  const [couponData, setCouponData] = useState(null);
  const [qrBlobUrl, setQrBlobUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedCode, setCopiedCode] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [downloadingFormat, setDownloadingFormat] = useState(null);

  // Fetch coupon metadata and in-memory QR PNG blob
  const loadCouponAndQr = async () => {
    if (!seller?.id) return;
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch coupon metadata (code, payment_url)
      const couponRes = await client.get(`/api/sellers/${seller.id}/coupon`);
      setCouponData(couponRes.data);

      // 2. Fetch QR PNG as blob for direct display in modal
      const qrRes = await client.get(`/api/sellers/${seller.id}/qr?format=png`, {
        responseType: 'blob',
      });
      const blobUrl = URL.createObjectURL(qrRes.data);
      setQrBlobUrl(blobUrl);
    } catch (err) {
      console.error('Failed to load QR / coupon data:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load QR code.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCouponAndQr();

    return () => {
      if (qrBlobUrl) {
        URL.revokeObjectURL(qrBlobUrl);
      }
    };
  }, [seller?.id]);

  // Copy helpers
  const handleCopyCode = async () => {
    if (!couponData?.code) return;
    try {
      await navigator.clipboard.writeText(couponData.code);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    } catch (err) {
      console.error('Clipboard copy failed:', err);
    }
  };

  const handleCopyUrl = async () => {
    if (!couponData?.payment_url) return;
    try {
      await navigator.clipboard.writeText(couponData.payment_url);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    } catch (err) {
      console.error('Clipboard copy failed:', err);
    }
  };

  // Authenticated file download
  const handleDownload = async (format) => {
    if (!seller?.id) return;
    setDownloadingFormat(format);
    try {
      const res = await client.get(`/api/sellers/${seller.id}/qr?format=${format}`, {
        responseType: 'blob',
      });
      const blob = new Blob([res.data], {
        type: format === 'svg' ? 'image/svg+xml' : 'image/png',
      });
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `incpay-qr-${couponData?.code || seller.id}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error(`Download ${format.toUpperCase()} failed:`, err);
      alert(`Failed to download ${format.toUpperCase()}: ${err.message}`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  // Regenerate coupon code
  const handleRegenerate = async () => {
    const confirmed = window.confirm(
      `Are you sure you want to regenerate the coupon code for "${seller.business_name}"?\n\nThe previous QR code and coupon will immediately become inactive.`
    );
    if (!confirmed) return;

    setRegenerating(true);
    setError(null);
    try {
      const res = await client.post(`/api/sellers/${seller.id}/regenerate-coupon`);
      setCouponData(res.data);

      // Refresh QR PNG image
      const qrRes = await client.get(`/api/sellers/${seller.id}/qr?format=png`, {
        responseType: 'blob',
      });
      if (qrBlobUrl) URL.revokeObjectURL(qrBlobUrl);
      const newBlobUrl = URL.createObjectURL(qrRes.data);
      setQrBlobUrl(newBlobUrl);
    } catch (err) {
      console.error('Failed to regenerate coupon:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to regenerate coupon.');
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl max-w-lg w-full overflow-hidden transition-all transform"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-gray-900">
              {seller.business_name}
            </h3>
            <p className="text-xs text-gray-500">
              Merchant QR Code & Checkout Destination
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 rounded-lg p-1 hover:bg-gray-100 transition-colors"
          >
            <span className="sr-only">Close</span>
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-xs text-red-700">
              {error}
            </div>
          )}

          {loading ? (
            <div className="py-16 text-center text-sm text-gray-500">
              <div className="inline-block w-8 h-8 border-2 border-gray-900 border-t-transparent rounded-full animate-spin mb-3"></div>
              <p>Generating high-resolution QR code...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              {/* QR Image Frame */}
              <div className="w-64 h-64 bg-white p-3 border-2 border-gray-200 rounded-xl shadow-sm flex items-center justify-center mb-6">
                {qrBlobUrl ? (
                  <img
                    src={qrBlobUrl}
                    alt={`QR code for ${seller.business_name}`}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <span className="text-xs text-gray-400">QR unavailable</span>
                )}
              </div>

              {/* Coupon Code Pill */}
              <div className="w-full mb-4">
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                  Unique Coupon Code
                </label>
                <div className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-4 py-2.5">
                  <span className="font-mono text-base font-bold text-gray-900 tracking-wide">
                    {couponData?.code || '—'}
                  </span>
                  <button
                    onClick={handleCopyCode}
                    className="text-xs font-medium px-2.5 py-1 bg-white border border-gray-200 rounded hover:bg-gray-100 text-gray-700 transition-colors"
                  >
                    {copiedCode ? '✓ Copied' : 'Copy'}
                  </button>
                </div>
              </div>

              {/* Payment URL Pill */}
              <div className="w-full mb-6">
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                  Payment Destination URL
                </label>
                <div className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                  <span className="font-mono text-xs text-gray-600 truncate mr-2">
                    {couponData?.payment_url || '—'}
                  </span>
                  <button
                    onClick={handleCopyUrl}
                    className="text-xs font-medium px-2.5 py-1 bg-white border border-gray-200 rounded hover:bg-gray-100 text-gray-700 shrink-0 transition-colors"
                  >
                    {copiedUrl ? '✓ Copied' : 'Copy'}
                  </button>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="w-full grid grid-cols-2 gap-3 mb-3">
                <button
                  onClick={() => handleDownload('png')}
                  disabled={downloadingFormat === 'png'}
                  className="w-full py-2 px-3 bg-gray-900 hover:bg-gray-800 text-white text-xs font-semibold rounded-md shadow-sm transition-colors text-center"
                >
                  {downloadingFormat === 'png' ? 'Preparing PNG...' : 'Download PNG'}
                </button>
                <button
                  onClick={() => handleDownload('svg')}
                  disabled={downloadingFormat === 'svg'}
                  className="w-full py-2 px-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-800 text-xs font-semibold rounded-md shadow-sm transition-colors text-center"
                >
                  {downloadingFormat === 'svg' ? 'Preparing SVG...' : 'Download SVG'}
                </button>
              </div>

              {/* Regenerate Button */}
              <button
                onClick={handleRegenerate}
                disabled={regenerating}
                className="text-xs text-red-600 hover:text-red-700 font-medium py-1 transition-colors"
              >
                {regenerating ? 'Regenerating Coupon...' : '↻ Regenerate Coupon Code'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

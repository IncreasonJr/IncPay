import React, { useState, useEffect } from 'react';
import client from '../api/client';

export default function Home() {
  const [status, setStatus] = useState('Checking...');
  const [isOk, setIsOk] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const response = await client.get('/health');
      if (response.data && response.data.status === 'ok') {
        setStatus('Backend: OK');
        setIsOk(true);
      } else {
        setStatus('Backend: DOWN');
        setIsOk(false);
      }
    } catch (err) {
      console.error('Health check failed:', err);
      setStatus('Backend: DOWN');
      setIsOk(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50 text-gray-900">
      <div className="w-full max-w-md bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">IncPay</h1>
        <p className="text-sm text-gray-600 mb-6">
          Payment-bridge platform connecting sellers and customers.
        </p>

        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 rounded-md bg-gray-50 border border-gray-200">
            <span className="text-sm font-medium text-gray-700">Service Status</span>
            <span
              className={`text-sm font-semibold px-2.5 py-1 rounded-full ${
                loading
                  ? 'bg-yellow-100 text-yellow-800'
                  : isOk
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {status}
            </span>
          </div>

          <button
            onClick={checkHealth}
            disabled={loading}
            className="w-full py-2 px-4 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-400 text-white text-sm font-medium rounded-md transition-colors"
          >
            {loading ? 'Checking...' : 'Refresh Status'}
          </button>
        </div>
      </div>
    </div>
  );
}

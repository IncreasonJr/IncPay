import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const { signIn, session, loading } = useAuth();
  const navigate = useNavigate();

  // If already authenticated, redirect straight to admin dashboard
  useEffect(() => {
    if (!loading && session) {
      navigate('/admin', { replace: true });
    }
  }, [session, loading, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await signIn(email, password);
      navigate('/admin', { replace: true });
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message || 'Invalid credentials. Please verify your email and password.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50 text-gray-900">
      <div className="w-full max-w-md bg-white border border-gray-200 rounded-lg p-8 shadow-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">IncPay Admin</h1>
          <p className="text-sm text-gray-600 mt-1">
            Sign in with your administrator credentials
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Email Address
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@example.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-gray-900 focus:border-gray-900 text-sm"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-gray-900 focus:border-gray-900 text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 px-4 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-400 text-white text-sm font-medium rounded-md shadow-sm transition-colors mt-2"
          >
            {submitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}

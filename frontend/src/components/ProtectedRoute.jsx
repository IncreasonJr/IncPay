import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children }) {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-8 h-8 border-4 border-gray-900 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm font-medium text-gray-600">Verifying session...</span>
        </div>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

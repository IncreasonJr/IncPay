import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import client from '../api/client';

export default function CustomerProtectedRoute({ children }) {
  const { session, loading } = useAuth();
  const [verifying, setVerifying] = useState(true);
  const [isCustomer, setIsCustomer] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const checkCustomerStatus = async () => {
      if (!session) {
        if (isMounted) {
          setIsCustomer(false);
          setVerifying(false);
        }
        return;
      }

      try {
        const res = await client.get('/api/customer/me');
        if (isMounted) {
          if (res.data && res.data.id) {
            setIsCustomer(true);
          } else {
            setIsCustomer(false);
          }
        }
      } catch (err) {
        console.warn('Customer verification failed:', err);
        if (isMounted) {
          setIsCustomer(false);
        }
      } finally {
        if (isMounted) {
          setVerifying(false);
        }
      }
    };

    if (!loading) {
      checkCustomerStatus();
    }

    return () => {
      isMounted = false;
    };
  }, [session, loading]);

  if (loading || verifying) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm font-medium text-gray-600">Verifying customer account...</span>
        </div>
      </div>
    );
  }

  if (!session || !isCustomer) {
    return <Navigate to="/customer/login" replace />;
  }

  return children;
}

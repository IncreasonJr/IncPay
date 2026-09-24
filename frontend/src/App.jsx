import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Home from './pages/Home';
import Login from './pages/Login';
import Pay from './pages/Pay';
import PaySuccess from './pages/PaySuccess';
import Dashboard from './pages/admin/Dashboard';
import Sellers from './pages/admin/Sellers';
import SellerForm from './pages/admin/SellerForm';
import Transactions from './pages/admin/Transactions';
import TransactionDetail from './pages/admin/TransactionDetail';
import ProtectedRoute from './components/ProtectedRoute';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />

        {/* Public Customer Payment Routes */}
        <Route path="/pay/:couponCode" element={<Pay />} />
        <Route path="/pay/success" element={<PaySuccess />} />

        {/* Protected Admin Routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/sellers"
          element={
            <ProtectedRoute>
              <Sellers />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/sellers/new"
          element={
            <ProtectedRoute>
              <SellerForm />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/sellers/:id/edit"
          element={
            <ProtectedRoute>
              <SellerForm />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/transactions"
          element={
            <ProtectedRoute>
              <Transactions />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/transactions/:id"
          element={
            <ProtectedRoute>
              <TransactionDetail />
            </ProtectedRoute>
          }
        />
        {/* Fallback unknown routes to Home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

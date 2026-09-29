import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Landing from './pages/Landing';
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
import CustomerProtectedRoute from './components/CustomerProtectedRoute';
import CustomerSignup from './pages/customer/CustomerSignup';
import CustomerLogin from './pages/customer/CustomerLogin';
import CustomerDashboard from './pages/customer/CustomerDashboard';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Landing Page */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/status" element={<Home />} />

        {/* Public Customer Payment Routes */}
        <Route path="/pay/:couponCode" element={<Pay />} />
        <Route path="/pay/success" element={<PaySuccess />} />

        {/* Customer Portal Routes */}
        <Route path="/customer/signup" element={<CustomerSignup />} />
        <Route path="/customer/login" element={<CustomerLogin />} />
        <Route path="/customer/preview" element={<CustomerDashboard isDemo={true} />} />
        <Route
          path="/customer/dashboard"
          element={
            <CustomerProtectedRoute>
              <CustomerDashboard />
            </CustomerProtectedRoute>
          }
        />

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

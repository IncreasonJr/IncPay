import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function AdminLayout({ children, activeTab }) {
  const { user, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/login', { replace: true });
    } catch (err) {
      console.error('Sign out error:', err);
    }
  };

  const navItems = [
    { label: 'Dashboard', path: '/admin', id: 'dashboard' },
    { label: 'Sellers', path: '/admin/sellers', id: 'sellers' },
    { label: 'Transactions', path: '/admin/transactions', id: 'transactions' },
  ];

  const isActive = (item) => {
    if (activeTab) return activeTab === item.id;
    if (item.path === '/admin') return location.pathname === '/admin';
    return location.pathname.startsWith(item.path);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col text-gray-900">
      {/* Top Navbar */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Left: Brand Logo & Desktop Nav */}
            <div className="flex items-center space-x-6 sm:space-x-8">
              <Link to="/admin" className="flex items-center space-x-2.5 shrink-0">
                <img src="/logo.png" alt="IncPay" className="h-7 w-auto object-contain" />
                <span className="text-[11px] uppercase font-bold tracking-wider bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                  Admin
                </span>
              </Link>

              {/* Desktop Navigation Links */}
              <nav className="hidden md:flex items-center space-x-1">
                {navItems.map((item) => {
                  const active = isActive(item);
                  return (
                    <Link
                      key={item.id}
                      to={item.path}
                      className={`text-sm font-medium px-3 py-2 rounded-md transition-colors ${
                        active
                          ? 'bg-gray-100 text-gray-900 font-semibold'
                          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                      }`}
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>

            {/* Right: Desktop User Profile & Sign Out */}
            <div className="hidden md:flex items-center space-x-4">
              {user?.email && (
                <span className="text-xs text-gray-500 font-medium truncate max-w-xs" title={user.email}>
                  {user.email}
                </span>
              )}
              <button
                onClick={handleSignOut}
                className="text-xs font-semibold text-gray-700 hover:text-gray-900 px-3 py-1.5 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Sign Out
              </button>
            </div>

            {/* Mobile Hamburger Button */}
            <div className="flex items-center md:hidden">
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                type="button"
                className="inline-flex items-center justify-center p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-900"
                aria-controls="mobile-menu"
                aria-expanded={mobileMenuOpen}
              >
                <span className="sr-only">Open main menu</span>
                {mobileMenuOpen ? (
                  /* Close Icon */
                  <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                ) : (
                  /* Hamburger Icon */
                  <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Collapsible Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200 bg-white px-4 pt-2 pb-4 space-y-1 shadow-lg">
            {navItems.map((item) => {
              const active = isActive(item);
              return (
                <Link
                  key={item.id}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`block px-3 py-2.5 rounded-md text-base font-medium transition-colors ${
                    active
                      ? 'bg-gray-900 text-white font-semibold'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}

            <div className="pt-4 pb-2 border-t border-gray-100 mt-2">
              {user?.email && (
                <div className="px-3 text-xs text-gray-500 font-medium mb-2 truncate">
                  Signed in as <strong className="text-gray-700">{user.email}</strong>
                </div>
              )}
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleSignOut();
                }}
                className="w-full text-left px-3 py-2 rounded-md text-sm font-semibold text-rose-600 hover:bg-rose-50 transition-colors"
              >
                Sign Out
              </button>
            </div>
          </div>
        )}
      </header>

      {/* Main Content Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {children}
      </main>
    </div>
  );
}

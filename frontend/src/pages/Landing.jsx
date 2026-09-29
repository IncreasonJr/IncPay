import React from 'react';
import { Link } from 'react-router-dom';

function Logo({ className = "h-12 w-auto" }) {
  return (
    <img
      src="/logo.png"
      alt="IncPay"
      className={`object-contain ${className}`}
    />
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between text-slate-900">
      {/* Main Landing Content Container */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-10 sm:py-16 max-w-4xl mx-auto text-center w-full">
        {/* 1. IncPay logo */}
        <div className="flex justify-center mb-6 sm:mb-8">
          <Link to="/" className="inline-block transition-transform hover:scale-105">
            <Logo className="h-12 w-auto" />
          </Link>
        </div>

        {/* 2. Hero animation */}
        <div className="w-full max-w-2xl mx-auto rounded-2xl shadow-lg overflow-hidden border border-slate-200/80 bg-slate-950 mb-8">
          <video
            autoPlay
            muted
            loop
            playsInline
            poster="/hero-poster.jpg"
            preload="metadata"
            aria-hidden="true"
            className="w-full h-auto aspect-video object-cover rounded-2xl block"
          >
            <source src="/hero.mp4" type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>

        {/* 3. Headline */}
        <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-[#0A1F44] mb-4 max-w-2xl leading-tight">
          Seamless payments between sellers and customers.
        </h1>

        {/* 4. Subtext */}
        <p className="text-base sm:text-lg text-slate-600 max-w-xl mx-auto mb-8 sm:mb-10 leading-relaxed">
          IncPay bridges in-person and digital commerce with fast QR code payments, automatic receipt tracking, and instant digital coupon rewards.
        </p>

        {/* 5. Customer CTA button & 6. Admin Portal link */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5 sm:gap-4 w-full sm:w-auto">
          <Link
            to="/customer/login"
            className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-3.5 text-base font-bold rounded-xl text-white bg-[#00C2A8] hover:bg-[#00a892] shadow-md hover:shadow-lg transition-all duration-200 transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer"
          >
            Customer Login / Sign Up
          </Link>
          <Link
            to="/login"
            className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3.5 text-base font-semibold rounded-xl text-[#0A1F44] bg-white hover:bg-slate-100 border border-slate-300 shadow-xs transition-colors cursor-pointer"
          >
            Admin Portal
          </Link>
        </div>
      </main>

      {/* 7. Footer */}
      <footer className="w-full border-t border-slate-200 py-6 text-center text-xs sm:text-sm text-slate-500">
        <div className="max-w-4xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>&copy; {new Date().getFullYear()} IncPay. All rights reserved.</span>
          <div className="flex items-center space-x-4 text-xs text-slate-500">
            <Link to="/status" className="hover:text-slate-800 transition">
              System Status
            </Link>
            <span className="text-slate-300">&bull;</span>
            <Link to="/login" className="hover:text-slate-800 transition">
              Admin Portal
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

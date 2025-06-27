import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Navigation from './Navigation';
import Header from './Header';
import AccessibilityEventListener from './AccessibilityEventListener';

const AppLayout: React.FC = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  return (
    <div className="min-h-full bg-gray-50">
      <AccessibilityEventListener />
      
      {/* Header */}
      <Header onToggleMobileMenu={toggleMobileMenu} />
      
      <div className="flex">
        {/* Desktop Sidebar Navigation */}
        <Navigation 
          currentPath={location.pathname}
          isMobileMenuOpen={isMobileMenuOpen}
          onCloseMobileMenu={closeMobileMenu}
        />
        
        {/* Main content */}
        <main className="flex-1 relative overflow-y-auto focus:outline-none md:pl-64">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
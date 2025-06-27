import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';

interface NavigationProps {
  currentPath: string;
  isMobileMenuOpen: boolean;
  onCloseMobileMenu: () => void;
}

const Navigation: React.FC<NavigationProps> = ({ 
  currentPath, 
  isMobileMenuOpen, 
  onCloseMobileMenu 
}) => {
  const navigationItems = [
    {
      path: '/',
      name: 'Dashboard',
      icon: (
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4" />
        </svg>
      )
    },
    {
      path: '/config',
      name: 'Configuration',
      icon: (
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      )
    },
    {
      path: '/content',
      name: 'Content Management',
      icon: (
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      )
    }
  ];

  const isActive = (path: string) => {
    return currentPath === path || (path === '/config' && currentPath === '/configuration');
  };

  const getNavItemClasses = (path: string) => {
    if (isActive(path)) {
      return "bg-blue-50 border-r-4 border-blue-700 text-blue-700 group flex items-center px-2 py-2 text-sm font-medium rounded-md";
    }
    return "text-gray-700 hover:bg-gray-50 hover:text-gray-900 group flex items-center px-2 py-2 text-sm font-medium rounded-md";
  };

  const getIconClasses = (path: string) => {
    if (isActive(path)) {
      return "text-blue-500 mr-3 h-6 w-6";
    }
    return "text-gray-400 group-hover:text-gray-500 mr-3 h-6 w-6";
  };

  // Handle escape key for mobile menu
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMobileMenuOpen) {
        onCloseMobileMenu();
      }
    };

    if (isMobileMenuOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isMobileMenuOpen, onCloseMobileMenu]);

  return (
    <>
      {/* Desktop sidebar navigation */}
      <nav className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 md:pt-16 md:bg-white md:border-r md:border-gray-200">
        <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
          <div className="flex-1 px-3 py-4 space-y-1">
            {navigationItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={getNavItemClasses(item.path)}
              >
                <div className={getIconClasses(item.path)}>
                  {item.icon}
                </div>
                {item.name}
              </Link>
            ))}
          </div>
        </div>
      </nav>

      {/* Mobile menu overlay */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden">
          <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-xl z-50">
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-medium text-gray-900">Navigation</h2>
                <button 
                  type="button" 
                  className="p-2 rounded-md text-gray-400 hover:text-gray-500" 
                  onClick={onCloseMobileMenu}
                  aria-label="Close menu"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <nav className="mt-2 px-2">
              {navigationItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className="group flex items-center px-2 py-2 text-base font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  onClick={onCloseMobileMenu}
                >
                  <div className="mr-4 h-6 w-6">
                    {item.icon}
                  </div>
                  {item.name}
                </Link>
              ))}
            </nav>
          </div>
        </div>
      )}
    </>
  );
};

export default Navigation;
import React from 'react';
import ConnectionStatus from './ConnectionStatus';

interface HeaderProps {
  onToggleMobileMenu: () => void;
}

const Header: React.FC<HeaderProps> = ({ onToggleMobileMenu }) => {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200 fixed inset-x-0 top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <button 
              type="button" 
              className="md:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100" 
              onClick={onToggleMobileMenu}
              aria-label="Open main menu"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="ml-2 text-xl font-bold text-gray-900">DocAI Cache System</h1>
          </div>
          <div className="flex items-center">
            <div className="flex items-center space-x-4">
              <div className="hidden md:block">
                <ConnectionStatus />
              </div>
              <button className="bg-gray-100 p-2 rounded-full text-gray-400 hover:text-gray-500">
                <span className="sr-only">User profile</span>
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
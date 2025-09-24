import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { BellIcon, UserCircleIcon } from '@heroicons/react/24/outline';

const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center">
          <h2 className="text-xl font-semibold text-gray-800">
            Welcome back, {user?.business_name}
          </h2>
        </div>
        
        <div className="flex items-center space-x-4">
          <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
            <BellIcon className="w-6 h-6" />
          </button>
          
          <div className="relative group">
            <button className="flex items-center space-x-2 p-2 text-gray-700 hover:text-gray-900 transition-colors">
              <UserCircleIcon className="w-8 h-8" />
              <span className="text-sm font-medium">{user?.business_name}</span>
            </button>
            
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
              <div className="px-4 py-2 text-sm text-gray-700 border-b">
                <div className="font-medium">{user?.business_name}</div>
                <div className="text-gray-500">{user?.email}</div>
              </div>
              <button
                onClick={logout}
                className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
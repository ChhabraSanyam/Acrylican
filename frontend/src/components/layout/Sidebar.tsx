import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
  HomeIcon, 
  CubeIcon, 
  LinkIcon, 
  PencilSquareIcon, 
  ChartBarIcon, 
  Cog6ToothIcon 
} from '@heroicons/react/24/outline';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Products', href: '/products', icon: CubeIcon },
  { name: 'Platforms', href: '/platforms', icon: LinkIcon },
  { name: 'Posting', href: '/posting', icon: PencilSquareIcon },
  { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];

const Sidebar: React.FC = () => {
  const location = useLocation();

  return (
    <div className="flex flex-col w-64 bg-white shadow-lg">
      <div className="flex items-center justify-center h-16 px-4 bg-indigo-600">
        <h1 className="text-xl font-bold text-white">Acrylican</h1>
      </div>
      
      <nav className="flex-1 px-4 py-6 space-y-2">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={`flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                isActive
                  ? 'bg-indigo-100 text-indigo-700 border-r-2 border-indigo-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.name}
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
};

export default Sidebar;
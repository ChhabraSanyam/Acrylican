import React from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import LoginForm from '../components/auth/LoginForm';

const LoginPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  // Redirect to intended page or dashboard if already authenticated
  if (isAuthenticated) {
    const from = location.state?.from?.pathname || '/dashboard';
    return <Navigate to={from} replace />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h1 className="text-center text-3xl font-bold text-gray-900 mb-2">
            Acrylican
          </h1>
          <p className="text-center text-gray-600 mb-6">
            Promote your handcrafted products across multiple platforms
          </p>
          <h2 className="text-center text-2xl font-bold text-gray-900">
            Sign in to your account
          </h2>
        </div>
        
        <LoginForm />
        
        <div className="text-center">
          <p className="text-sm text-gray-600">
            Don't have an account?{' '}
            <Link
              to="/register"
              className="font-medium text-indigo-600 hover:text-indigo-500"
            >
              Create one here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
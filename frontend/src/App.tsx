import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import ErrorBoundary from './components/common/ErrorBoundary';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ProductsPage from './pages/ProductsPage';
import PlatformsPage from './pages/PlatformsPage';
import PostingPage from './pages/PostingPage';
import AnalyticsPage from './pages/AnalyticsPage';
import SettingsPage from './pages/SettingsPage';
import NotFoundPage from './pages/NotFoundPage';
import Layout from './components/layout/Layout';

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <AuthProvider>
          <div className="min-h-screen bg-gray-50">
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route 
                path="/*" 
                element={
                  <ProtectedRoute>
                    <Layout>
                      <Routes>
                        <Route path="/dashboard" element={<DashboardPage />} />
                        <Route path="/products" element={<ProductsPage />} />
                        <Route path="/platforms" element={<PlatformsPage />} />
                        <Route path="/posting" element={<PostingPage />} />
                        <Route path="/analytics" element={<AnalyticsPage />} />
                        <Route path="/settings" element={<SettingsPage />} />
                        <Route path="/" element={<Navigate to="/dashboard" replace />} />
                        <Route path="*" element={<NotFoundPage />} />
                      </Routes>
                    </Layout>
                  </ProtectedRoute>
                } 
              />
            </Routes>
          </div>
        </AuthProvider>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
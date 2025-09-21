import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User, UserLogin, UserRegistration, AuthContextType } from '../types/auth';
import { authService, tokenManager } from '../services/auth';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  // Initialize auth state on app load
  useEffect(() => {
    const initializeAuth = async () => {
      const token = tokenManager.getAccessToken();
      
      if (token && !tokenManager.isTokenExpired(token)) {
        try {
          const userData = await authService.getCurrentUser();
          setUser(userData);
        } catch (error) {
          console.error('Failed to get user info:', error);
          tokenManager.clearTokens();
        }
      }
      
      setIsLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (credentials: UserLogin): Promise<void> => {
    try {
      setIsLoading(true);
      const result = await authService.login(credentials);
      
      if (result.success && result.user) {
        setUser(result.user);
      } else {
        throw new Error(result.message || 'Login failed');
      }
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (userData: UserRegistration): Promise<void> => {
    try {
      setIsLoading(true);
      const result = await authService.register(userData);
      
      if (result.success && result.user) {
        setUser(result.user);
      } else {
        throw new Error(result.message || 'Registration failed');
      }
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = (): void => {
    authService.logout();
    setUser(null);
  };

  const refreshToken = async (): Promise<boolean> => {
    try {
      const tokens = await authService.refreshToken();
      tokenManager.setTokens(tokens.access_token, tokenManager.getRefreshToken() || '');
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
      return false;
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    refreshToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
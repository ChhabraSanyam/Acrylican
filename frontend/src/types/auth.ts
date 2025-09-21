export interface User {
  id: string;
  email: string;
  business_name: string;
  business_type: string;
  business_description?: string;
  website?: string;
  location?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthResult {
  success: boolean;
  user?: User;
  tokens?: TokenResponse;
  message?: string;
}

export interface UserRegistration {
  email: string;
  password: string;
  business_name: string;
  business_type: string;
  business_description?: string;
  website?: string;
  location?: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: UserLogin) => Promise<void>;
  register: (userData: UserRegistration) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<boolean>;
}
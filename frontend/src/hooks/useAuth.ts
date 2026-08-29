import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { User } from '../types';

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

const API_BASE = import.meta.env.VITE_API_URL || '';

export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    isLoading: true,
    error: null,
  });

  // Check if we have stored credentials (for auto-login)
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Try to get current user
        // Note: With HTTP Basic Auth, we need to send credentials
        const username = localStorage.getItem('scooper-username');
        const password = localStorage.getItem('scooper-password');
        
        if (username && password) {
          await login(username, password);
        } else {
          setAuthState({
            isAuthenticated: false,
            user: null,
            isLoading: false,
            error: null,
          });
        }
      } catch (error) {
        setAuthState({
          isAuthenticated: false,
          user: null,
          isLoading: false,
          error: 'Not authenticated',
        });
      }
    };

    checkAuth();
  }, []);

  const login = useCallback(async (username: string, password: string): Promise<User> => {
    try {
      // Test authentication by making a request to a protected endpoint
      const response = await axios.get(`${API_BASE}/cms/dashboard`, {
        auth: {
          username,
          password,
        },
      });

      // Store credentials for future requests
      localStorage.setItem('scooper-username', username);
      localStorage.setItem('scooper-password', password);

      // Set auth state
      setAuthState({
        isAuthenticated: true,
        user: response.data.user || { username, is_admin: true },
        isLoading: false,
        error: null,
      });

      return response.data.user || { username, is_admin: true };
    } catch (error: any) {
      // Clear any stored credentials
      localStorage.removeItem('scooper-username');
      localStorage.removeItem('scooper-password');

      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  }, []);

  const logout = useCallback(() => {
    // Clear credentials
    localStorage.removeItem('scooper-username');
    localStorage.removeItem('scooper-password');

    setAuthState({
      isAuthenticated: false,
      user: null,
      isLoading: false,
      error: null,
    });
  }, []);

  const getAuthHeaders = useCallback(() => {
    const username = localStorage.getItem('scooper-username');
    const password = localStorage.getItem('scooper-password');
    
    if (username && password) {
      return {
        auth: {
          username,
          password,
        },
      };
    }
    
    return {};
  }, []);

  return {
    ...authState,
    login,
    logout,
    getAuthHeaders,
  };
}

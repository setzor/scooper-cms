import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import axios from 'axios';
import { User } from '../types';

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = import.meta.env.VITE_API_URL || '';

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<{
    isAuthenticated: boolean;
    user: User | null;
    isLoading: boolean;
    error: string | null;
  }>({
    isAuthenticated: false,
    user: null,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const username = localStorage.getItem('scooper-username');
        const password = localStorage.getItem('scooper-password');

        if (username && password) {
          // Verify credentials
          const response = await axios.get(`${API_BASE}/cms/dashboard`, {
            auth: {
              username,
              password,
            },
          });

          setState({
            isAuthenticated: true,
            user: response.data.user,
            isLoading: false,
            error: null,
          });
        } else {
          setState({
            isAuthenticated: false,
            user: null,
            isLoading: false,
            error: null,
          });
        }
      } catch (error: any) {
        // Clear invalid credentials
        localStorage.removeItem('scooper-username');
        localStorage.removeItem('scooper-password');

        setState({
          isAuthenticated: false,
          user: null,
          isLoading: false,
          error: null,
        });
      }
    };

    checkAuth();
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    try {
      // Test authentication
      const response = await axios.get(`${API_BASE}/cms/dashboard`, {
        auth: {
          username,
          password,
        },
      });

      // Store credentials
      localStorage.setItem('scooper-username', username);
      localStorage.setItem('scooper-password', password);

      setState({
        isAuthenticated: true,
        user: response.data.user,
        isLoading: false,
        error: null,
      });
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('scooper-username');
    localStorage.removeItem('scooper-password');

    setState({
      isAuthenticated: false,
      user: null,
      isLoading: false,
      error: null,
    });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}

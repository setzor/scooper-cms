import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Create axios instance with base URL
const api = axios.create({
  baseURL: API_BASE,
});

// Request interceptor to add auth headers
api.interceptors.request.use(
  (config) => {
    const username = localStorage.getItem('scooper-username');
    const password = localStorage.getItem('scooper-password');

    if (username && password) {
      config.auth = {
        username,
        password,
      };
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear credentials on 401
      localStorage.removeItem('scooper-username');
      localStorage.removeItem('scooper-password');
      window.location.href = '/cms/login';
    }
    return Promise.reject(error);
  }
);

export default api;

export async function fetchWithAuth(url: string, options?: RequestInit): Promise<Response> {
  const username = localStorage.getItem('scooper-username');
  const password = localStorage.getItem('scooper-password');

  const headers: HeadersInit = {
    ...options?.headers,
  };

  if (username && password) {
    const authString = btoa(`${username}:${password}`);
    headers['Authorization'] = `Basic ${authString}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem('scooper-username');
    localStorage.removeItem('scooper-password');
    window.location.href = '/cms/login';
  }

  return response;
}

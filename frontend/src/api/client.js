import axios from 'axios';
import { supabase } from './supabase';

const baseURL = import.meta.env.VITE_API_URL || '';

const client = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Interceptor attaching Supabase JWT bearer token if session exists
client.interceptors.request.use(
  async (config) => {
    try {
      const { data } = await supabase.auth.getSession();
      const token = data?.session?.access_token;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (err) {
      console.error('Error fetching Supabase auth session in Axios interceptor:', err);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default client;

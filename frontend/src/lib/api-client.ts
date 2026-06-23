import axios from 'axios';

// Fallback to your local FastAPI server if the env variable isn't set
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 10000, // 10-second timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Optional: Add global error handling interceptors later
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);
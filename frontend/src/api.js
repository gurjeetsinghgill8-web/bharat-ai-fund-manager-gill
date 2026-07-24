// src/api.js — Centralized API client for Bharat AI Fund Manager Gill
// Talks to FastAPI backend (Hugging Face Spaces)

import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL !== undefined ? import.meta.env.VITE_API_BASE_URL : '';
const API_KEY  = import.meta.env.VITE_API_KEY || 'bharat-ai-secret-2026';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // 2 min — scan can take time
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': API_KEY,
  },
});

// ── Health & Wake ────────────────────────────────────────────
export const getHealth      = () => api.get('/health');
export const wakeBackend    = () => api.get('/api/wake');

// ── Scan ─────────────────────────────────────────────────────
export const getScanStatus  = () => api.get('/api/scan/status');
export const triggerScan    = (universe = 0) => api.post(`/api/scan/run?universe=${universe}`);
export const getGurjas1     = () => api.get('/api/scan/results/gurjas1');
export const getGurjas2     = () => api.get('/api/scan/results/gurjas2');
export const getStockData   = (ticker) => api.get(`/api/scan/cache/${ticker}`);

// ── Stocks List (for auto-complete) ──────────────────────────
export const getStocks      = () => api.get('/api/stocks');

// ── Users ─────────────────────────────────────────────────────
export const getUsers       = () => api.get('/api/users');
export const createUser     = (name, email) => api.post('/api/users', { name, email });
export const updateEmail    = (userId, email) => api.put(`/api/users/${userId}/email`, { email });

// ── Portfolio ─────────────────────────────────────────────────
export const getPortfolio   = (userId) => api.get(`/api/portfolio/${userId}`);
export const addHolding     = (userId, symbol, buy_price, quantity) =>
  api.post(`/api/portfolio/${userId}/add`, { user_id: userId, symbol, buy_price, quantity });
export const removeHolding  = (userId, symbol) =>
  api.delete(`/api/portfolio/${userId}/${symbol}`);
export const syncPortfolios = () => api.post('/api/portfolio/sync');

// ── AI Analysis ───────────────────────────────────────────────
export const getAnalysis    = (symbol) => api.get(`/api/analysis/${symbol}`);

export default api;

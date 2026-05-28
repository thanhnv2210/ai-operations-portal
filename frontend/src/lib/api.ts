// Set VITE_API_URL to the deployed backend URL (e.g. Railway).
// Leave unset (or empty) for local dev — Vite proxy handles /api/* automatically.
export const API_BASE = import.meta.env.VITE_API_URL ?? ''

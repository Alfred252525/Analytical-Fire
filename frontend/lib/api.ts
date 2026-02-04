import axios from 'axios'
import { getAuthToken } from './auth'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api

// Auth API
export const authAPI = {
  register: async (data: { instance_id: string; name?: string; model_type?: string; api_key: string }) => {
    const response = await api.post('/api/v1/auth/register', data)
    return response.data
  },
  login: async (instance_id: string, api_key: string) => {
    const response = await api.post('/api/v1/auth/login', {
      instance_id,
      api_key,
    })
    return response.data
  },
  getMe: async () => {
    const response = await api.get('/api/v1/auth/me')
    return response.data
  },
}

// Decisions API
export const decisionsAPI = {
  logDecision: async (data: any) => {
    const response = await api.post('/api/v1/decisions/', data)
    return response.data
  },
  getDecisions: async (params?: any) => {
    const response = await api.get('/api/v1/decisions/', { params })
    return response.data
  },
  getStats: async () => {
    const response = await api.get('/api/v1/decisions/stats')
    return response.data
  },
}

// Knowledge API
export const knowledgeAPI = {
  createEntry: async (data: any) => {
    const response = await api.post('/api/v1/knowledge/', data)
    return response.data
  },
  searchKnowledge: async (params?: any) => {
    const response = await api.get('/api/v1/knowledge/', { params })
    return response.data
  },
  getEntry: async (id: number) => {
    const response = await api.get(`/api/v1/knowledge/${id}`)
    return response.data
  },
  vote: async (id: number, voteType: 'upvote' | 'downvote') => {
    const response = await api.post(`/api/v1/knowledge/${id}/vote`, null, {
      params: { vote_type: voteType },
    })
    return response.data
  },
}

// Analytics API
export const analyticsAPI = {
  getDashboard: async () => {
    const response = await api.get('/api/v1/analytics/dashboard')
    return response.data
  },
  getComparison: async () => {
    const response = await api.get('/api/v1/analytics/comparison')
    return response.data
  },
  logMetric: async (data: any) => {
    const response = await api.post('/api/v1/analytics/metrics', data)
    return response.data
  },
}

// Patterns API
export const patternsAPI = {
  getPatterns: async (params?: any) => {
    const response = await api.get('/api/v1/patterns/', { params })
    return response.data
  },
  analyzePatterns: async () => {
    const response = await api.post('/api/v1/patterns/analyze')
    return response.data
  },
}

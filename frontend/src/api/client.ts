import axios from 'axios'
import type { UploadResponse, Job, AnalysisResponse, ExtractedDoc, CompanyProfile } from '../types/financial'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 120_000,
})

export const api = {
  upload: async (
    files: File[],
    period: string,
    onProgress?: (pct: number) => void,
  ): Promise<UploadResponse> => {
    const form = new FormData()
    files.forEach(f => form.append('files', f))
    form.append('period', period)
    const { data } = await http.post<UploadResponse>('/api/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    })
    return data
  },

  submitJob: async (uploadId: string, period: string): Promise<Job> => {
    const { data } = await http.post<Job>('/api/jobs', { uploadId, period })
    return data
  },

  getJob: async (jobId: string): Promise<Job> => {
    const { data } = await http.get<Job>(`/api/jobs/${jobId}`)
    return data
  },

  analyze: async (period: string): Promise<AnalysisResponse> => {
    const { data } = await http.post<AnalysisResponse>('/api/analyze', { period })
    return data
  },

  getReport: async (period: string): Promise<AnalysisResponse> => {
    const { data } = await http.get<AnalysisResponse>(`/api/reports/${period}`)
    return data
  },

  getPeriods: async (): Promise<{ periods: string[] }> => {
    const { data } = await http.get<{ periods: string[] }>('/api/periods')
    return data
  },

  deletePeriod: async (period: string): Promise<{ deleted: number; period: string }> => {
    const { data } = await http.delete(`/api/periods/${period}`)
    return data
  },

  getDocuments: async (period: string): Promise<{ period: string; documents: ExtractedDoc[] }> => {
    const { data } = await http.get(`/api/documents/${period}`)
    return data
  },

  getCompanyProfile: async (): Promise<CompanyProfile> => {
    const { data } = await http.get<CompanyProfile>('/api/company-profile')
    return data
  },

  updateDocuments: async (period: string, documents: ExtractedDoc[]): Promise<{ period: string; documents: number }> => {
    const { data } = await http.put(`/api/documents/${period}`, { documents })
    return data
  },
}

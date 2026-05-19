import axios from 'axios';
import type { Config } from '../types/agent';

const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5 minutes for long processing
});

export interface UploadResponse {
  filename: string;
  path: string;
}

export interface ProcessResponse {
  job_id: string;
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<UploadResponse>('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function deleteFile(filename: string): Promise<void> {
  await api.delete(`/upload/${encodeURIComponent(filename)}`);
}

export async function listFiles(): Promise<string[]> {
  const response = await api.get<{ files: string[] }>('/files');
  return response.data.files;
}

export interface FlowchartStatus {
  slug: string;
  name: string;
  local_stand: string | null;
  online_stand: string | null;
  onkopedia_url: string;
  status: 'current' | 'outdated' | 'unknown' | 'error';
  message: string | null;
}

export interface FlowchartStatusResponse {
  checked_at: string;
  flowcharts: FlowchartStatus[];
}

export async function checkFlowchartStatus(): Promise<FlowchartStatusResponse> {
  const response = await api.get<FlowchartStatusResponse>('/flowchart-status');
  return response.data;
}

export async function startProcessing(
  files: string[],
  config: Config
): Promise<ProcessResponse> {
  const response = await api.post<ProcessResponse>('/process', {
    llm_mode: config.llmMode,
    decision_model: config.decisionModel,
    files,
  });
  return response.data;
}

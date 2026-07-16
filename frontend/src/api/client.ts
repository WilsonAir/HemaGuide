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

export async function uploadText(
  text: string,
  filename?: string
): Promise<UploadResponse> {
  const response = await api.post<UploadResponse>('/upload-text', {
    text,
    filename: filename || undefined,
  });
  return response.data;
}

export interface ParseTextResponse {
  filename: string;
  path: string;
  extracted: {
    document_id?: string;
    entity_slug?: string;
    source_file?: string;
    sections?: Record<string, unknown>;
    [key: string]: unknown;
  };
}

export async function parseText(
  text: string,
  options?: { filename?: string; llmMode?: string; forceExtract?: boolean }
): Promise<ParseTextResponse> {
  const response = await api.post<ParseTextResponse>('/parse-text', {
    text,
    filename: options?.filename || undefined,
    llm_mode: options?.llmMode || 'openai',
    force_extract: options?.forceExtract ?? true,
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

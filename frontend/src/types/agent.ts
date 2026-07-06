export interface VariantClassification {
  gene: string;
  variant: string;
  aa_change: string;
  gnomad: {
    af: number | null;
    exome_af?: number | null;
    genome_af?: number | null;
    found: boolean;
    source?: string | null;
  };
  criteria_met: Array<{
    code: string;
    points: number;
    description: string;
  }>;
  total_points: number;
  classification: 'Oncogenic' | 'Likely Oncogenic' | 'VUS' | 'Likely Benign' | 'Benign';
}

export interface AgentResult {
  mode: 'GUIDELINE' | 'ADVANCED' | 'MOLECULAR';
  routing_reasoning: string;
  konferenzbeschluss: string;
  begründung: string;

  // GUIDELINE mode
  flowchart_path?: string;
  flowchart_used?: number;

  // ADVANCED mode
  similar_cases_count?: number;
  similar_cases_used?: number;
  pubmed_articles_count?: number;
  case_synthesis?: string;
  pubmed_synthesis?: string;
  context_tailored?: boolean;
  synthesis?: string;

  // MOLECULAR mode
  mol_info_count?: number;
  variants_classified?: number;
  fish_count?: number;
  translation_errors?: string[];
  classification_results?: VariantClassification[];
  report_text?: string;

  // Metadata
  source_file?: string;
  input_document_id?: string;
  input_diagnosis?: string;
  extraction_timestamp?: string;
  model?: string;
  metadata?: {
    temperature?: number;
    tokens_used?: number;
  };
}

export type LLMMode = 'openai' | 'ollama-local' | 'vllm';

export interface Config {
  llmMode: LLMMode;
  decisionModel: string;
}

export type ProcessingStatus =
  | 'idle'
  | 'queued'
  | 'uploading'
  | 'extracting'
  | 'routing'
  | 'generating'
  | 'complete'
  | 'error';

export interface CaseResult {
  case_id: string;
  case_name: string;
  mode: 'GUIDELINE' | 'ADVANCED' | 'MOLECULAR';
  konferenzbeschluss: string;
  begründung: string;
  completed_at: string;
}

export interface StatusUpdate {
  status: ProcessingStatus;
  message?: string;
  progress?: number;
  current_case?: number;
  total_cases?: number;
  log?: string;
  logs?: string[];
  case_result?: CaseResult;
  case_results?: CaseResult[];
  result?: AgentResult;
}


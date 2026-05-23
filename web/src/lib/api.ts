// src/lib/api.ts — API client for BOT backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ColumnMeta {
  name: string;
  sql_type: string;
  role: string;
  sample_values: string[];
  nullable: boolean;
  is_unique: boolean;
  null_pct: number;
}

export interface TableMeta {
  table_name: string;
  columns: ColumnMeta[];
  row_count: number;
  col_count: number;
  primary_key_candidates: string[];
  date_columns: string[];
  metric_columns: string[];
}

export interface RelationshipMeta {
  left_table: string;
  left_column: string;
  right_table: string;
  right_column: string;
  confidence: number;
  relationship_type: string;
}

export interface SchemaResponse {
  tables: TableMeta[];
  relationships: RelationshipMeta[];
}

export interface ChatResponse {
  answer: string;
  sql: string;
  tables_used: string[];
  explanation: string;
  result_preview: Record<string, unknown>[];
  query_complexity: string;
  was_repaired: boolean;
  error?: string;
}

export interface HealthResponse {
  status: string;
  tables_loaded: number;
  duckdb_connected: boolean;
}

export interface UploadResponse {
  success: boolean;
  tables_loaded: string[];
  row_counts: Record<string, number>;
  message: string;
}

async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: (): Promise<HealthResponse> =>
    request<HealthResponse>("/health"),

  schema: (): Promise<SchemaResponse> =>
    request<SchemaResponse>("/schema"),

  chat: (message: string, session_id = "web"): Promise<ChatResponse> =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id }),
    }),

  upload: async (file: File): Promise<UploadResponse> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  reload: (): Promise<UploadResponse> =>
    request<UploadResponse>("/reload-data", { method: "POST" }),
};

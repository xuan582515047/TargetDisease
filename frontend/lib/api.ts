export type User = {
  id: string;
  email: string;
  role: string;
  status: string;
};

export type CredentialStatus = {
  configured: boolean;
  validated: boolean;
  last4: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type Project = {
  id: string;
  name: string;
  primary_disease: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type DiseaseInfo = {
  id: string;
  source_id: string | null;
  name_zh: string;
  name: string;
  aliases: string[];
};

export type Catalog = {
  version: string;
  diseases: DiseaseInfo[];
};

export type DiseaseSearchHit = {
  id: string;
  name: string;
  description: string | null;
  imported: boolean;
};

export type TargetCandidate = {
  target_id: string;
  node_id: string | null;
  symbol: string | null;
  source: "seed" | "extended";
  reason: string | null;
  n_score: number | null;
  relevance_score: number | null;
  mechanism: string | null;
  in_network: boolean | null;
  review_decision?: string | null;
  review_comment?: string | null;
};

export type AgentTrace = {
  key: string;
  name: string;
  status: "completed" | "fallback" | "failed";
  summary: string;
  output: unknown;
  model: string | null;
  duration_ms: number;
  total_tokens: number | null;
  error: string | null;
};

export type TargetAnalysisResult = {
  disease: { name: string; id: string };
  question: string;
  question_summary: string;
  seeds: TargetCandidate[];
  extended_candidates: TargetCandidate[];
  candidates: TargetCandidate[];
  rankings: {
    model: TargetCandidate[];
    extended: TargetCandidate[];
    all: TargetCandidate[];
  };
  limitations: string[];
  hypotheses: string[];
  agents?: AgentTrace[];
  report_markdown: string;
  candidates_csv: string;
  network_error?: string | null;
  model_name?: string;
  prompt_version?: string;
  params?: {
    alpha: number;
    max_iter: number;
    tol: number;
    string_threshold: number;
    string_hops: number;
    max_nodes: number;
  };
  generated_at?: string;
};

export type Run = {
  id: string;
  project_id: string;
  status: string;
  current_step: string | null;
  error_code: string | null;
  error_message: string | null;
  workflow_version: string | null;
  results_json: TargetAnalysisResult | null;
  intermediate_json: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
};

export type NetworkNode = {
  id: string;
  type: string;
  label: string;
  gene_id: string | null;
  n_score: number | null;
  relevance_score: number | null;
};

export type NetworkEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  score: number;
  source_id: string | null;
  version: string | null;
};

export type NetworkView = {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  total_nodes: number;
  total_edges: number;
  display_nodes: number;
  display_edges: number;
  truncated: boolean;
  threshold: number;
  min_score: number | null;
};

// Endpoints where a 401 means "bad credentials / no session", not "session expired".
const NO_REFRESH_PATHS = new Set([
  "/api/v1/auth/login",
  "/api/v1/auth/register",
  "/api/v1/auth/logout",
  "/api/v1/auth/refresh",
]);

let refreshInFlight: Promise<boolean> | null = null;

function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    })
      .then((res) => res.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

async function request<T>(path: string, init?: RequestInit, allowRefresh = true): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (res.status === 401 && allowRefresh && !NO_REFRESH_PATHS.has(path)) {
    if (await refreshSession()) return request<T>(path, init, false);
  }
  if (!res.ok) {
    const body: unknown = await res.json().catch(() => ({}));
    const detail = (body as { detail?: unknown }).detail;
    let message = res.statusText || "请求失败";
    if (typeof detail === "string") message = detail;
    else if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: unknown } | undefined;
      if (typeof first?.msg === "string") message = first.msg;
    }
    if (res.status === 401 && !NO_REFRESH_PATHS.has(path)) {
      message = "登录状态已过期，请重新登录";
    }
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  me: () => request<User>("/api/v1/auth/me"),
  login: (email: string, password: string) =>
    request<User>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string) =>
    request<User>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<{ ok: boolean }>("/api/v1/auth/logout", { method: "POST" }),

  credentials: {
    status: () => request<CredentialStatus>("/api/v1/credentials/deepseek"),
    save: (api_key: string) =>
      request<CredentialStatus>("/api/v1/credentials/deepseek", {
        method: "PUT",
        body: JSON.stringify({ api_key }),
      }),
    validate: () =>
      request<CredentialStatus>("/api/v1/credentials/deepseek/validate", { method: "POST" }),
    remove: () =>
      request<CredentialStatus>("/api/v1/credentials/deepseek", { method: "DELETE" }),
  },

  projects: {
    list: () => request<Project[]>("/api/v1/projects"),
    create: (data: { name: string; primary_disease?: string | null; notes?: string | null }) =>
      request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }),
    remove: (id: string) => request<void>(`/api/v1/projects/${id}`, { method: "DELETE" }),
  },

  runs: {
    list: (params?: { project_id?: string }) => {
      const qs = new URLSearchParams();
      if (params?.project_id) qs.set("project_id", params.project_id);
      const s = qs.toString();
      return request<Run[]>(`/api/v1/runs${s ? `?${s}` : ""}`);
    },
    get: (id: string) => request<Run>(`/api/v1/runs/${id}`),
    artifacts: (id: string) => request<{ path: string; size: number }[]>(`/api/v1/runs/${id}/artifacts`),
  },

  targetAnalysis: {
    catalog: () => request<Catalog>("/api/v1/target-analysis/catalog"),
    searchDiseases: (q: string, size = 20) =>
      request<{ query: string; translated_query?: string | null; diseases: DiseaseSearchHit[] }>(
        `/api/v1/target-analysis/disease-search?q=${encodeURIComponent(q)}&size=${size}`
      ),
    create: (data: {
      project_id: string;
      question: string;
      mechanism_keywords?: string[];
    }) =>
      request<Run>("/api/v1/target-analysis/runs", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    get: (id: string) => request<Run>(`/api/v1/target-analysis/runs/${id}`),
    network: (id: string, params?: { threshold?: number; layers?: number; include_background?: boolean }) => {
      const qs = new URLSearchParams();
      if (params?.threshold != null) qs.set("threshold", String(params.threshold));
      if (params?.layers != null) qs.set("layers", String(params.layers));
      if (params?.include_background != null) qs.set("include_background", String(params.include_background));
      const s = qs.toString();
      return request<NetworkView>(`/api/v1/target-analysis/runs/${id}/network${s ? `?${s}` : ""}`);
    },
    stability: (id: string) =>
      request<unknown>(`/api/v1/target-analysis/runs/${id}/stability`),
    report: (id: string, format: "md" | "csv") =>
      request<{ content?: string }>(`/api/v1/target-analysis/runs/${id}/report?format=${format}`),
  },
};

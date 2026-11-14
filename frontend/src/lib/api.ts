import axios, { AxiosError } from "axios";
import type {
  DealAnalysisRequest,
  DocumentIntelligenceReport,
  DocumentSummary,
  RAGAnswer,
  RAGQueryRequest,
  SensitivityGrid,
  SensitivityRequest,
  Token,
  UnifiedDealReport,
  UserPublic,
} from "./types";

// Override with VITE_API_BASE_URL in frontend/.env.local, e.g. when port 8000 is taken.
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

const TOKEN_STORAGE_KEY = "pe_analyst_token";

// In-memory copy avoids a localStorage read on every request; localStorage keeps
// the session alive across a page reload.
let inMemoryToken: string | null = localStorage.getItem(TOKEN_STORAGE_KEY);

export function getToken(): string | null {
  return inMemoryToken;
}

export function setToken(token: string | null): void {
  inMemoryToken = token;
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

// Fired on a 401 so the app shell can redirect to /login without this module
// needing to import React Router directly.
type UnauthorizedListener = () => void;
let unauthorizedListener: UnauthorizedListener | null = null;
export function onUnauthorized(listener: UnauthorizedListener): void {
  unauthorizedListener = listener;
}

export const client = axios.create({ baseURL: API_BASE_URL });

client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      setToken(null);
      unauthorizedListener?.();
    }
    return Promise.reject(error);
  },
);

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // FastAPI/Pydantic validation errors: a list of {loc, msg, type}.
      return detail
        .map((item) => (typeof item === "object" && item && "msg" in item ? String((item as { msg: unknown }).msg) : JSON.stringify(item)))
        .join("; ");
    }
    if (error.message) return error.message;
  }
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred.";
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function registerUser(email: string, password: string): Promise<UserPublic> {
  const { data } = await client.post<UserPublic>("/auth/register", { email, password });
  return data;
}

export async function login(email: string, password: string): Promise<Token> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const { data } = await client.post<Token>("/auth/token", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export async function uploadDocument(file: File): Promise<DocumentIntelligenceReport> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client.post<DocumentIntelligenceReport>("/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  const { data } = await client.get<DocumentSummary[]>("/documents");
  return data;
}

export async function getDocument(documentId: string): Promise<DocumentIntelligenceReport> {
  const { data } = await client.get<DocumentIntelligenceReport>(`/documents/${documentId}`);
  return data;
}

// ---------------------------------------------------------------------------
// RAG
// ---------------------------------------------------------------------------

export async function queryRag(request: RAGQueryRequest): Promise<RAGAnswer> {
  const { data } = await client.post<RAGAnswer>("/rag/query", request);
  return data;
}

// ---------------------------------------------------------------------------
// Deals
// ---------------------------------------------------------------------------

export async function analyzeDeal(request: DealAnalysisRequest): Promise<UnifiedDealReport> {
  const { data } = await client.post<UnifiedDealReport>("/deals/analyze", request);
  return data;
}

export async function sensitivityGrid(request: SensitivityRequest): Promise<SensitivityGrid> {
  const { data } = await client.post<SensitivityGrid>("/deals/sensitivity", request);
  return data;
}

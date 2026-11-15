import axios, { AxiosError } from "axios";
import type {
  AnalysisComparison,
  DealAnalysisRecord,
  DealAnalysisRequest,
  DealAnalysisSummary,
  DealRoomDetail,
  DealRoomMember,
  DealRoomSummary,
  SuggestedInputs,
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

/** Uploads a PDF. Pass dealRoomId to file it in a deal, sharing it with that deal's team. */
export async function uploadDocument(file: File, dealRoomId?: string): Promise<DocumentIntelligenceReport> {
  const form = new FormData();
  form.append("file", file);
  if (dealRoomId) form.append("deal_room_id", dealRoomId);
  const { data } = await client.post<DocumentIntelligenceReport>("/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

/** Documents the user may read; pass dealRoomId to list one deal's documents only. */
export async function listDocuments(dealRoomId?: string): Promise<DocumentSummary[]> {
  const { data } = await client.get<DocumentSummary[]>("/documents", {
    params: dealRoomId ? { deal_room_id: dealRoomId } : undefined,
  });
  return data;
}

/** The original PDF. Fetched as a blob because the request needs the auth header. */
export async function fetchDocumentFile(documentId: string): Promise<Blob> {
  const { data } = await client.get<Blob>(`/documents/${documentId}/file`, { responseType: "blob" });
  return data;
}

/** Files a document in a deal, or takes it out of its deal with null. */
export async function assignDocumentDealRoom(documentId: string, dealRoomId: string | null): Promise<DocumentSummary> {
  const { data } = await client.put<DocumentSummary>(`/documents/${documentId}/deal-room`, {
    deal_room_id: dealRoomId,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Deal rooms
// ---------------------------------------------------------------------------

export async function listDealRooms(): Promise<DealRoomSummary[]> {
  const { data } = await client.get<DealRoomSummary[]>("/deal-rooms");
  return data;
}

export async function createDealRoom(name: string, description?: string): Promise<DealRoomDetail> {
  const { data } = await client.post<DealRoomDetail>("/deal-rooms", { name, description: description || null });
  return data;
}

export async function getDealRoom(roomId: string): Promise<DealRoomDetail> {
  const { data } = await client.get<DealRoomDetail>(`/deal-rooms/${roomId}`);
  return data;
}

export async function deleteDealRoom(roomId: string): Promise<void> {
  await client.delete(`/deal-rooms/${roomId}`);
}

export async function addDealRoomMember(roomId: string, email: string): Promise<DealRoomMember> {
  const { data } = await client.post<DealRoomMember>(`/deal-rooms/${roomId}/members`, { email });
  return data;
}

export async function removeDealRoomMember(roomId: string, userId: string): Promise<void> {
  await client.delete(`/deal-rooms/${roomId}/members/${userId}`);
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

/** Runs an analysis and waits for it. Prefer startAnalysis: a narrated run can take minutes. */
export async function analyzeDeal(request: DealAnalysisRequest): Promise<UnifiedDealReport> {
  const { data } = await client.post<UnifiedDealReport>("/deals/analyze", request);
  return data;
}

/** Starts an analysis in the background; poll getAnalysis(id) until it completes or fails. */
export async function startAnalysis(request: DealAnalysisRequest): Promise<DealAnalysisSummary> {
  const { data } = await client.post<DealAnalysisSummary>("/deals/analyses", request);
  return data;
}

/** Analyses the user may read; pass dealRoomId to list one deal's analyses only. */
export async function listAnalyses(dealRoomId?: string): Promise<DealAnalysisSummary[]> {
  const { data } = await client.get<DealAnalysisSummary[]>("/deals/analyses", {
    params: dealRoomId ? { deal_room_id: dealRoomId } : undefined,
  });
  return data;
}

/** Proposes financials and valuation assumptions from documents, for the analyst to confirm. */
export async function suggestInputs(documentIds: string[]): Promise<SuggestedInputs> {
  const { data } = await client.post<SuggestedInputs>("/deals/suggest-inputs", { document_ids: documentIds });
  return data;
}

export type ExportFormat = "pdf" | "docx";

/**
 * Downloads a server-built PDF or Word file and saves it under the name the server gives it.
 * Fetched as a blob because the request needs the auth header a plain link cannot send.
 */
export async function downloadExport(
  path: string,
  format: ExportFormat,
  params: Record<string, string> = {},
): Promise<void> {
  const response = await client.get<Blob>(path, { params: { ...params, format }, responseType: "blob" });
  const disposition = String(response.headers["content-disposition"] ?? "");
  const filename = /filename="?([^";]+)"?/.exec(disposition)?.[1] ?? `report.${format}`;
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/** What changed between two saved runs, in the inputs and in the outcome. */
export async function compareAnalyses(baseId: string, otherId: string): Promise<AnalysisComparison> {
  const { data } = await client.get<AnalysisComparison>("/deals/analyses/compare", {
    params: { base: baseId, other: otherId },
  });
  return data;
}

export async function getAnalysis(analysisId: string): Promise<DealAnalysisRecord> {
  const { data } = await client.get<DealAnalysisRecord>(`/deals/analyses/${analysisId}`);
  return data;
}

export async function deleteAnalysis(analysisId: string): Promise<void> {
  await client.delete(`/deals/analyses/${analysisId}`);
}

export async function sensitivityGrid(request: SensitivityRequest): Promise<SensitivityGrid> {
  const { data } = await client.post<SensitivityGrid>("/deals/sensitivity", request);
  return data;
}

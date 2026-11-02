import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { getToken, login as apiLogin, onUnauthorized, registerUser, setToken } from "../lib/api";

interface DecodedUser {
  sub: string;
  role: string;
}

// The backend's JWT carries only `sub` (user id) and `role` -- no email claim --
// so the email the user typed at login/register is cached separately for display.
const EMAIL_STORAGE_KEY = "pe_analyst_email";

function decodeJwt(token: string): DecodedUser | null {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
    const json = atob(padded);
    return JSON.parse(json) as DecodedUser;
  } catch {
    return null;
  }
}

interface AuthState {
  token: string | null;
  email: string | null;
  role: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getToken());
  const [email, setEmailState] = useState<string | null>(localStorage.getItem(EMAIL_STORAGE_KEY));

  const decoded = useMemo(() => (token ? decodeJwt(token) : null), [token]);

  const logout = useCallback(() => {
    setToken(null);
    setTokenState(null);
    localStorage.removeItem(EMAIL_STORAGE_KEY);
    setEmailState(null);
  }, []);

  useEffect(() => {
    onUnauthorized(() => {
      setTokenState(null);
    });
  }, []);

  const login = useCallback(async (loginEmail: string, password: string) => {
    const result = await apiLogin(loginEmail, password);
    setToken(result.access_token);
    setTokenState(result.access_token);
    localStorage.setItem(EMAIL_STORAGE_KEY, loginEmail);
    setEmailState(loginEmail);
  }, []);

  const register = useCallback(async (registerEmail: string, password: string) => {
    await registerUser(registerEmail, password);
    await login(registerEmail, password);
  }, [login]);

  const value: AuthState = {
    token,
    email,
    role: decoded?.role ?? null,
    isAuthenticated: Boolean(token),
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

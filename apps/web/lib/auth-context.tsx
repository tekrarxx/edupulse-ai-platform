"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { AuthApiError, type AuthUser, login as apiLogin, logout as apiLogout, refreshSession } from "@/lib/auth";

type AuthContextValue = {
  user: AuthUser | null;
  accessToken: string | null;
  status: "loading" | "authenticated" | "unauthenticated";
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  // Deliberately never persisted to localStorage/sessionStorage — kept only
  // in memory so an XSS payload cannot read it out of browser storage (§78).
  // A page reload silently re-derives it from the httpOnly refresh cookie.
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [status, setStatus] = useState<AuthContextValue["status"]>("loading");

  useEffect(() => {
    refreshSession()
      .then((token) => {
        setUser(token.user);
        setAccessToken(token.access_token);
        setStatus("authenticated");
      })
      .catch(() => {
        setStatus("unauthenticated");
      });
  }, []);

  const login: AuthContextValue["login"] = async (email, password) => {
    const token = await apiLogin({ email, password });
    setUser(token.user);
    setAccessToken(token.access_token);
    setStatus("authenticated");
  };

  const logout: AuthContextValue["logout"] = async () => {
    await apiLogout();
    setUser(null);
    setAccessToken(null);
    setStatus("unauthenticated");
  };

  return (
    <AuthContext.Provider value={{ user, accessToken, status, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

export { AuthApiError };

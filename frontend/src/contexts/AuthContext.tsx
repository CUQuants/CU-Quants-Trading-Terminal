import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AUTH_EXPIRED_EVENT } from "../api/client";
import * as authApi from "../api/auth";
import type { Credentials, Operator } from "../api/auth";

type AuthStatus = "loading" | "anon" | "authed";

export interface AuthContextValue {
  status: AuthStatus;
  operator: Operator | null;
  /** Set when the trader was signed out without asking (expiry, revocation). */
  notice: string | null;
  login: (creds: Credentials) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [operator, setOperator] = useState<Operator | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const statusRef = useRef(status);
  statusRef.current = status;

  const signedOut = useCallback(
    (why: string | null) => {
      queryClient.clear(); // never show one trader's cached data to the next
      setOperator(null);
      setNotice(why);
      setStatus("anon");
    },
    [queryClient],
  );

  // Is there already a session (cookie from an earlier visit)?
  useEffect(() => {
    let cancelled = false;
    authApi
      .fetchMe()
      .then((me) => {
        if (cancelled) return;
        if (me) {
          setOperator(me);
          setStatus("authed");
        } else {
          setStatus("anon");
        }
      })
      .catch(() => !cancelled && setStatus("anon"));
    return () => {
      cancelled = true;
    };
  }, []);

  // Any 401 elsewhere: confirm with the server before dropping to sign-in, so
  // a route-specific 401 (e.g. the reporting API) doesn't sign anyone out.
  useEffect(() => {
    let checking = false;
    const onExpired = async () => {
      if (checking || statusRef.current !== "authed") return;
      checking = true;
      try {
        const me = await authApi.fetchMe();
        if (!me) signedOut("Your session ended. Please sign in again.");
      } catch {
        /* server unreachable: stay put, requests will keep failing visibly */
      } finally {
        checking = false;
      }
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, [signedOut]);

  const login = useCallback(
    async (creds: Credentials) => {
      const me = await authApi.login(creds);
      queryClient.clear();
      setOperator(me);
      setNotice(null);
      setStatus("authed");
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    await authApi.logout();
    signedOut(null);
  }, [signedOut]);

  const value = useMemo(
    () => ({ status, operator, notice, login, logout }),
    [status, operator, notice, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";

import { ApiError, ApiTimeoutError, apiRequest } from "../lib/api/client";

export type AuthUser = {
  id: string;
  email: string | null;
  phone_number: string | null;
  full_name: string | null;
  preferred_language: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type LoginPayload = {
  email: string;
  password: string;
};

type SignupPayload = {
  email: string;
  password: string;
  full_name?: string | null;
  phone_number?: string | null;
  preferred_language?: string;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
};

type AuthStatus = "checking" | "authenticated" | "anonymous" | "error";

type AuthState = {
  status: AuthStatus;
  token: string | null;
  user: AuthUser | null;
  error: string | null;
  notice: string | null;
  isSubmitting: boolean;
};

type AuthContextValue = {
  state: AuthState;
  login: (payload: LoginPayload) => Promise<void>;
  signup: (payload: SignupPayload) => Promise<void>;
  logout: () => void;
  retrySession: () => Promise<void>;
  clearError: () => void;
};

const TOKEN_STORAGE_KEY = "ai-agronomist.access-token";
const AUTH_REQUEST_TIMEOUT_MS = 60000;

const initialState: AuthState = {
  status: "checking",
  token: null,
  user: null,
  error: null,
  notice: null,
  isSubmitting: false,
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredToken(): string | null {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

function storeToken(token: string): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

function clearStoredToken(): void {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}

async function fetchCurrentUser(token: string): Promise<AuthUser> {
  return apiRequest<AuthUser>("/users/me", {
    method: "GET",
    authToken: token,
    timeoutMs: AUTH_REQUEST_TIMEOUT_MS,
  });
}

function logAuthTiming(label: string, startedAt: number) {
  if (!import.meta.env.DEV) {
    return;
  }
  console.info(`[auth] ${label}`, {
    elapsedMs: Math.round(performance.now() - startedAt),
  });
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<AuthState>(initialState);
  const loginPromiseRef = useRef<Promise<void> | null>(null);

  const bootstrapSession = async () => {
    const storedToken = readStoredToken();

    if (!storedToken) {
      setState({
        status: "anonymous",
        token: null,
        user: null,
        error: null,
        notice: null,
        isSubmitting: false,
      });
      return;
    }

    setState((current) => ({
      ...current,
      status: "checking",
      token: storedToken,
      error: null,
      notice: null,
    }));

    try {
      const currentUserStartedAt = performance.now();
      const user = await fetchCurrentUser(storedToken);
      logAuthTiming("current-user request", currentUserStartedAt);
      setState({
        status: "authenticated",
        token: storedToken,
        user,
        error: null,
        notice: null,
        isSubmitting: false,
      });
    } catch (error) {
      if (
        error instanceof ApiError &&
        (error.status === 401 || error.status === 403)
      ) {
        clearStoredToken();
        setState({
          status: "anonymous",
          token: null,
          user: null,
          error: null,
          notice: null,
          isSubmitting: false,
        });
        return;
      }

      setState({
        status: "error",
        token: storedToken,
        user: null,
        error:
          error instanceof Error
            ? error.message
            : "Unable to verify the current session.",
        notice: null,
        isSubmitting: false,
      });
    }
  };

  useEffect(() => {
    void bootstrapSession();
  }, []);

  const clearError = () => {
    setState((current) => ({
      ...current,
      error: null,
      notice: null,
    }));
  };

  const login = async (payload: LoginPayload) => {
    if (loginPromiseRef.current) {
      return loginPromiseRef.current;
    }

    const loginPromise = (async () => {
      setState((current) => ({
        ...current,
        isSubmitting: true,
        error: null,
        notice: null,
      }));

      try {
        let tokenResponse: TokenResponse | null = null;
        for (let attempt = 0; attempt < 2; attempt += 1) {
          try {
            const authStartedAt = performance.now();
            tokenResponse = await apiRequest<TokenResponse>("/auth/login", {
              method: "POST",
              body: payload,
              timeoutMs: AUTH_REQUEST_TIMEOUT_MS,
            });
            logAuthTiming("authentication request", authStartedAt);
            break;
          } catch (error) {
            if (error instanceof ApiTimeoutError && attempt === 0) {
              setState((current) => ({
                ...current,
                notice: "Starting server, please wait...",
              }));
              continue;
            }
            throw error;
          }
        }

        if (!tokenResponse) {
          throw new Error("Unable to sign in right now.");
        }

        const accessToken = tokenResponse.access_token;
        const tokenPersistenceStartedAt = performance.now();
        storeToken(accessToken);
        logAuthTiming("token persistence", tokenPersistenceStartedAt);
        setState({
          status: "authenticated",
          token: accessToken,
          user: null,
          error: null,
          notice: null,
          isSubmitting: false,
        });

        void (async () => {
          try {
            const currentUserStartedAt = performance.now();
            const user = await fetchCurrentUser(accessToken);
            logAuthTiming("current-user request", currentUserStartedAt);
            setState((current) =>
              current.token === accessToken
                ? {
                    ...current,
                    user,
                    error: null,
                    notice: null,
                    isSubmitting: false,
                  }
                : current,
            );
          } catch (error) {
            if (import.meta.env.DEV) {
              console.error("Current-user request failed after login", error);
            }
            setState((current) =>
              current.token === accessToken
                ? {
                    ...current,
                    error:
                      error instanceof Error
                        ? error.message
                        : "Unable to load the current user.",
                  }
                : current,
            );
          }
        })();
      } catch (error) {
        clearStoredToken();
        setState({
          status: "anonymous",
          token: null,
          user: null,
          error:
            error instanceof Error ? error.message : "Unable to sign in right now.",
          notice: null,
          isSubmitting: false,
        });
        throw error;
      } finally {
        loginPromiseRef.current = null;
      }
    })();

    loginPromiseRef.current = loginPromise;
    return loginPromise;
  };

  const signup = async (payload: SignupPayload) => {
    setState((current) => ({
      ...current,
      isSubmitting: true,
      error: null,
    }));

    try {
      await apiRequest<AuthUser>("/auth/signup", {
        method: "POST",
        body: payload,
      });

      await login({
        email: payload.email,
        password: payload.password,
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        status: current.token ? current.status : "anonymous",
        error:
          error instanceof Error ? error.message : "Unable to create the account.",
        notice: null,
        isSubmitting: false,
      }));
      throw error;
    }
  };

  const logout = () => {
    clearStoredToken();
    setState({
      status: "anonymous",
      token: null,
      user: null,
      error: null,
      notice: null,
      isSubmitting: false,
    });
  };

  const retrySession = async () => {
    await bootstrapSession();
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      login,
      signup,
      logout,
      retrySession,
      clearError,
    }),
    [state],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import { ApiError, apiRequest } from "../lib/api/client";

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

const initialState: AuthState = {
  status: "checking",
  token: null,
  user: null,
  error: null,
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
  });
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<AuthState>(initialState);

  const bootstrapSession = async () => {
    const storedToken = readStoredToken();

    if (!storedToken) {
      setState({
        status: "anonymous",
        token: null,
        user: null,
        error: null,
        isSubmitting: false,
      });
      return;
    }

    setState((current) => ({
      ...current,
      status: "checking",
      token: storedToken,
      error: null,
    }));

    try {
      const user = await fetchCurrentUser(storedToken);
      setState({
        status: "authenticated",
        token: storedToken,
        user,
        error: null,
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
    }));
  };

  const login = async (payload: LoginPayload) => {
    setState((current) => ({
      ...current,
      isSubmitting: true,
      error: null,
    }));

    try {
      const tokenResponse = await apiRequest<TokenResponse>("/auth/login", {
        method: "POST",
        body: payload,
      });

      storeToken(tokenResponse.access_token);
      const user = await fetchCurrentUser(tokenResponse.access_token);
      setState({
        status: "authenticated",
        token: tokenResponse.access_token,
        user,
        error: null,
        isSubmitting: false,
      });
    } catch (error) {
      clearStoredToken();
      setState({
        status: "anonymous",
        token: null,
        user: null,
        error:
          error instanceof Error ? error.message : "Unable to sign in right now.",
        isSubmitting: false,
      });
      throw error;
    }
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

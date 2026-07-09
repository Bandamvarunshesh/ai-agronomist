import {
  createContext,
  useContext,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

type ToastTone = "info" | "success" | "warning" | "error";

type ToastInput = {
  title: string;
  message?: string;
  tone?: ToastTone;
};

type ToastRecord = ToastInput & {
  id: number;
  tone: ToastTone;
};

type ToastContextValue = {
  pushToast: (toast: ToastInput) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: PropsWithChildren) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);

  const pushToast = (toast: ToastInput) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    const tone = toast.tone ?? "info";

    setToasts((current) => [...current, { ...toast, tone, id }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id));
    }, 3600);
  };

  const value = useMemo<ToastContextValue>(
    () => ({
      pushToast,
    }),
    [],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-region">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`toast toast-${toast.tone}`}
            role="status"
          >
            <div className="toast-title">{toast.title}</div>
            {toast.message ? (
              <div className="toast-message">{toast.message}</div>
            ) : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }

  return context;
}

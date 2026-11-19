import { useState, type FormEvent, type ReactNode } from "react";
import quantsLogo from "../assets/quants_dark.png";
import { useAuth } from "../contexts/AuthContext";
import { LoginError, type CredentialField, type Credentials } from "../api/auth";

/** Non-secret fields remembered between visits. The secret never is. */
const REMEMBER_KEY = "terminal_login_prefill";
type Remembered = Omit<Credentials, "api_secret">;

const API_KEY_RE = /^cuq_op_[A-Za-z0-9]{16,}$/;
const OPERATOR_ID_RE = /^cuq-[0-9]{3,5}$/;

function loadRemembered(): Remembered {
  const empty = { api_key: "", operator_id: "", operator_name: "" };
  try {
    const raw = localStorage.getItem(REMEMBER_KEY);
    if (!raw) return empty;
    const parsed = JSON.parse(raw) as Partial<Remembered>;
    return {
      api_key: typeof parsed.api_key === "string" ? parsed.api_key : "",
      operator_id: typeof parsed.operator_id === "string" ? parsed.operator_id : "",
      operator_name: typeof parsed.operator_name === "string" ? parsed.operator_name : "",
    };
  } catch {
    return empty;
  }
}

function saveRemembered(r: Remembered) {
  try {
    localStorage.setItem(REMEMBER_KEY, JSON.stringify(r));
  } catch {
    /* storage blocked: nothing to remember */
  }
}

function formatHint(field: CredentialField, value: string): string | null {
  const v = value.trim();
  if (!v) return null;
  if (field === "api_key" && !API_KEY_RE.test(v)) return "Should look like cuq_op_…";
  if (field === "operator_id" && !OPERATOR_ID_RE.test(v)) return "Should look like cuq-016";
  if (field === "api_secret" && /\s/.test(v)) return "Contains spaces. Paste it exactly as issued.";
  return null;
}

interface FieldProps {
  id: CredentialField;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  type?: string;
  autoComplete: string;
  error: string | null;
  autoFocus?: boolean;
  trailing?: ReactNode;
}

function Field({ id, label, value, onChange, placeholder, type = "text", autoComplete, error, autoFocus, trailing }: FieldProps) {
  return (
    <label htmlFor={id} className="flex flex-col gap-1.5">
      <span className="text-xs font-medium uppercase tracking-wider text-white/50">{label}</span>
      <div className="relative">
        <input
          id={id}
          name={id}
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          autoFocus={autoFocus}
          spellCheck={false}
          autoCapitalize="off"
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          className={`w-full rounded-lg bg-white/[0.04] border px-3 py-2.5 text-sm text-white font-mono placeholder:text-white/20 outline-none transition-colors focus:bg-white/[0.06] ${
            trailing ? "pr-16" : ""
          } ${error ? "border-red-500/60 focus:border-red-500" : "border-white/10 focus:border-white/30"}`}
        />
        {trailing}
      </div>
      {error && (
        <span id={`${id}-error`} className="text-xs text-red-400">
          {error}
        </span>
      )}
    </label>
  );
}

export function LoginPage() {
  const { login, notice } = useAuth();
  const [remembered] = useState(loadRemembered);
  const [form, setForm] = useState<Credentials>({ ...remembered, api_secret: "" });
  const [showSecret, setShowSecret] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<{ message: string; field?: CredentialField; requestId?: string } | null>(null);

  const set = (field: CredentialField) => (v: string) => {
    setForm((f) => ({ ...f, [field]: v }));
    if (error?.field === field) setError(null);
  };

  const hints: Record<CredentialField, string | null> = {
    api_key: formatHint("api_key", form.api_key),
    api_secret: formatHint("api_secret", form.api_secret),
    operator_id: formatHint("operator_id", form.operator_id),
    operator_name: null,
  };
  const fieldError = (f: CredentialField) => (error?.field === f ? error.message : hints[f]);
  const complete = (Object.keys(form) as CredentialField[]).every((k) => form[k].trim() !== "");
  const canSubmit = complete && !submitting && !Object.values(hints).some(Boolean);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await login(form);
      saveRemembered({
        api_key: form.api_key.trim(),
        operator_id: form.operator_id.trim(),
        operator_name: form.operator_name.trim(),
      });
    } catch (err) {
      if (err instanceof LoginError) {
        setError({ message: err.message, field: err.field, requestId: err.requestId });
      } else {
        setError({ message: "Sign-in failed. Try again." });
      }
      setForm((f) => ({ ...f, api_secret: "" }));
      setSubmitting(false);
    }
  }

  const firstEmpty = (["api_key", "api_secret", "operator_id", "operator_name"] as CredentialField[]).find(
    (k) => !form[k],
  );

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center px-4 py-10 bg-[radial-gradient(ellipse_at_top,rgba(255,255,255,0.05),transparent_60%)]">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 mb-8 justify-center">
          <img src={quantsLogo} alt="" className="h-11 w-auto object-contain" />
          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl font-bold tracking-tight leading-tight">SharkLazer</h1>
            <span className="text-xs text-white/50 font-medium">by CU Quants</span>
          </div>
        </div>

        <form
          onSubmit={onSubmit}
          noValidate
          className="rounded-xl border border-white/10 bg-white/[0.02] p-6 flex flex-col gap-5 shadow-2xl shadow-black"
        >
          <div className="flex flex-col gap-1">
            <h2 className="text-base font-semibold">Sign in to the trading terminal</h2>
            <p className="text-sm text-white/50 leading-relaxed">
              Use your CU Quants gateway credential: the four values under{" "}
              <code className="font-mono text-white/70 bg-white/[0.06] px-1 py-0.5 rounded">proxy:</code> in your
              xlrts <code className="font-mono text-white/70">config.yaml</code>.
            </p>
          </div>

          {notice && !error && (
            <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-3 py-2 text-sm text-yellow-200/90">
              {notice}
            </div>
          )}

          <Field
            id="api_key"
            label="API key"
            value={form.api_key}
            onChange={set("api_key")}
            placeholder="cuq_op_…"
            autoComplete="username"
            error={fieldError("api_key")}
            autoFocus={firstEmpty === "api_key"}
          />
          <Field
            id="api_secret"
            label="API secret"
            type={showSecret ? "text" : "password"}
            value={form.api_secret}
            onChange={set("api_secret")}
            placeholder="Paste your secret"
            autoComplete="current-password"
            error={fieldError("api_secret")}
            autoFocus={firstEmpty === "api_secret"}
            trailing={
              <button
                type="button"
                onClick={() => setShowSecret((s) => !s)}
                className="absolute right-2 top-1/2 -translate-y-1/2 cursor-pointer rounded px-2 py-1 text-xs text-white/50 hover:text-white hover:bg-white/10"
                aria-label={showSecret ? "Hide secret" : "Show secret"}
              >
                {showSecret ? "Hide" : "Show"}
              </button>
            }
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Field
              id="operator_id"
              label="Operator ID"
              value={form.operator_id}
              onChange={set("operator_id")}
              placeholder="cuq-016"
              autoComplete="off"
              error={fieldError("operator_id")}
              autoFocus={firstEmpty === "operator_id"}
            />
            <Field
              id="operator_name"
              label="Operator name"
              value={form.operator_name}
              onChange={set("operator_name")}
              placeholder="Your name"
              autoComplete="name"
              error={fieldError("operator_name")}
              autoFocus={firstEmpty === "operator_name"}
            />
          </div>

          {error && !error.field && (
            <div role="alert" className="rounded-lg border border-red-500/25 bg-red-500/5 px-3 py-2.5 text-sm text-red-300">
              {error.message}
              {error.requestId && (
                <div className="mt-1 text-xs text-red-300/60 font-mono">request_id {error.requestId}</div>
              )}
            </div>
          )}

          <button
            type="submit"
            disabled={!canSubmit}
            className="cursor-pointer rounded-lg bg-white text-black font-semibold text-sm py-2.5 transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-30"
          >
            {submitting ? "Checking with the gateway…" : "Sign in"}
          </button>

          <p className="text-xs text-white/30 leading-relaxed">
            Your secret is held only in the terminal server's memory while you're signed in. The terminal never
            stores it in this browser.
          </p>
        </form>
      </div>
    </div>
  );
}

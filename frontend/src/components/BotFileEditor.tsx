import { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import type { BotFileKind } from "../types/bots";
import { readBotFile, saveBotFile } from "../api/bots";
import { ApiError } from "../api/client";

interface Props {
  market: string;
  kind: BotFileKind;
  root: string;
  onClose: () => void;
}

/**
 * Edit a market's config (.yaml) or subaccount (.json) on the box.
 *
 * A save names the version it was edited from (the sha256 of what was
 * loaded); if someone saved in the meantime the gateway refuses it rather
 * than discarding their edit. No backup copy is kept on the box. Save is
 * refused until a load succeeded, so a failed load can never blank the file.
 */
export function BotFileEditor({ market, kind, root, onClose }: Props) {
  const filename = `${market}${kind === "config" ? ".yaml" : ".json"}`;
  const display = `${root || "~/speedbyte"}/data/${kind === "config" ? "configs" : "subaccounts"}/${filename}`;

  const [content, setContent] = useState("");
  const [base, setBase] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [stale, setStale] = useState(false);
  const [status, setStatus] = useState<{ text: string; error: boolean }>({ text: "Loading…", error: false });
  const textRef = useRef<HTMLTextAreaElement>(null);

  const load = useCallback(async () => {
    setStatus({ text: "Loading…", error: false });
    setLoaded(false);
    try {
      const f = await readBotFile(market, kind);
      setContent(f.content);
      setBase(f.sha256);
      setLoaded(true);
      setDirty(false);
      setStale(false);
      setStatus({ text: `Loaded — ${filename}`, error: false });
      textRef.current?.focus();
    } catch (e) {
      setStatus({ text: `Error loading: ${e instanceof Error ? e.message : String(e)}`, error: true });
    }
  }, [market, kind, filename]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = useCallback(async () => {
    if (!loaded) {
      setStatus({ text: "Not saved: the file never loaded", error: true });
      return;
    }
    if (saving) return;
    setSaving(true);
    setStatus({ text: "Saving…", error: false });
    try {
      const res = await saveBotFile(market, kind, content, base);
      // What is on the box now is what we just wrote: the next save edits it.
      setBase(res.sha256);
      setDirty(false);
      const ts = new Date().toLocaleTimeString(undefined, { hour12: false });
      setStatus({ text: `Saved ${ts}`, error: false });
      toast.success(`${filename} saved`);
      if (res.backup) {
        // The gateway predates `backup: false` and kept a copy anyway.
        toast(`The gateway still kept a backup (${res.backup}) — it needs updating.`, { icon: "⚠" });
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if (e instanceof ApiError && e.status === 409 && msg.includes("changed since")) setStale(true);
      setStatus({ text: `Save error: ${msg}`, error: true });
    } finally {
      setSaving(false);
    }
  }, [loaded, saving, market, kind, content, base, filename]);

  const close = useCallback(() => {
    if (dirty && !window.confirm(`Discard unsaved changes to ${filename}?`)) return;
    onClose();
  }, [dirty, filename, onClose]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void save();
      } else if (e.key === "Escape") {
        close();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [save, close]);

  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-40" onClick={close} />
      <div className="fixed inset-6 md:inset-x-[10%] md:inset-y-12 z-50 flex flex-col rounded-lg border border-white/10 bg-[#0d0d12] shadow-2xl">
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-white/10 bg-white/[0.03]">
          <span className="font-mono text-sm text-white/90 truncate" title={display}>
            {display}
            {dirty && <span className="text-amber-400 ml-1">●</span>}
          </span>
          <div className="flex-1" />
          <span className={`text-xs truncate max-w-[50%] ${status.error ? "text-red-400" : "text-white/40"}`} title={status.text}>
            {status.text}
          </span>
          {stale && (
            <button
              onClick={() => {
                if (!dirty || window.confirm("Reload from the box? Your edit here will be lost.")) void load();
              }}
              className="cursor-pointer rounded-md px-3 py-1 text-xs border border-amber-400/30 text-amber-300 hover:bg-amber-400/[0.1]"
            >
              Reload
            </button>
          )}
          <button
            onClick={() => void save()}
            disabled={!loaded || saving}
            className="cursor-pointer rounded-md px-4 py-1 text-xs font-semibold border border-emerald-400/30 text-emerald-300 bg-emerald-400/[0.08] hover:bg-emerald-400/[0.15] disabled:opacity-40 disabled:cursor-not-allowed"
            title="Save (Ctrl/⌘+S)"
          >
            {saving ? "Saving…" : "Save"}
          </button>
          <button
            onClick={close}
            className="cursor-pointer rounded-md px-2 py-1 text-white/40 hover:text-white/80"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <textarea
          ref={textRef}
          value={content}
          onChange={(e) => {
            setContent(e.target.value);
            setDirty(true);
          }}
          readOnly={!loaded}
          spellCheck={false}
          wrap="off"
          className="flex-1 resize-none bg-transparent p-4 font-mono text-[13px] leading-relaxed text-white/90 outline-none"
        />
      </div>
    </>
  );
}

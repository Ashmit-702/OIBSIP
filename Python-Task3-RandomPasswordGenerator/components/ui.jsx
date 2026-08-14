"use client";

import { useState, useRef } from "react";

export function Panel({ children, className = "" }) {
  return (
    <div
      className={`rounded-lg bg-panel border border-line shadow-vault ${className}`}
    >
      {children}
    </div>
  );
}

export function Button({ children, onClick, variant = "primary", className = "", ...rest }) {
  const base =
    "font-body font-medium text-sm px-4 py-2.5 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-brass text-ink hover:bg-brass-bright",
    ghost: "bg-transparent border border-line text-ink2 hover:border-brass-dim hover:text-brass-bright",
    danger: "bg-transparent border border-coral/40 text-coral hover:bg-coral/10",
  };
  return (
    <button onClick={onClick} className={`${base} ${variants[variant]} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function Checkbox({ checked, onChange, label }) {
  return (
    <label className="flex items-center gap-2.5 py-1.5 cursor-pointer select-none group">
      <span
        className={`w-4 h-4 rounded-[3px] border flex items-center justify-center shrink-0 transition-colors ${
          checked ? "bg-brass border-brass" : "border-line group-hover:border-brass-dim"
        }`}
      >
        {checked && (
          <svg viewBox="0 0 12 12" className="w-2.5 h-2.5 fill-none stroke-ink stroke-[2.5]">
            <path d="M2 6l3 3 5-6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </span>
      <input type="checkbox" className="sr-only" checked={checked} onChange={onChange} />
      <span className="text-sm text-ink2">{label}</span>
    </label>
  );
}

export function SectionLabel({ children }) {
  return (
    <div className="font-mono text-[11px] uppercase tracking-[0.15em] text-muted mb-2">
      {children}
    </div>
  );
}

export function CopyButton({ text, onStatus, className = "", children }) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef(null);

  function handleCopy() {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      onStatus?.("Copied — clipboard clears automatically in 20s.");
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setCopied(false), 1600);

      const clearTimer = setTimeout(async () => {
        try {
          const current = await navigator.clipboard.readText();
          if (current === text) {
            await navigator.clipboard.writeText("");
            onStatus?.("Clipboard auto-cleared for security.");
          }
        } catch {
          // Clipboard read permission may be denied; that's fine.
        }
      }, 20_000);
      return () => clearTimeout(clearTimer);
    });
  }

  return (
    <Button onClick={handleCopy} disabled={!text} className={className}>
      {copied ? "Copied ✓" : children ?? "Copy"}
    </Button>
  );
}

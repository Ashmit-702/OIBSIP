"use client";

import { useEffect, useState } from "react";
import {
  vaultExists,
  createVault,
  unlockVault,
  saveEntries,
  deleteVault,
  VaultLockedError,
} from "@/lib/vault";
import { Panel, Button, SectionLabel, CopyButton } from "./ui";

const DAY_MS = 24 * 60 * 60 * 1000;
const REMINDER_OPTIONS = [
  { label: "No reminder", value: 0 },
  { label: "30 days", value: 30 },
  { label: "90 days", value: 90 },
  { label: "180 days", value: 180 },
  { label: "365 days", value: 365 },
];

function rotationStatus(entry) {
  if (!entry.reminderDays) return null;
  const dueAt = entry.createdAt + entry.reminderDays * DAY_MS;
  const daysLeft = Math.ceil((dueAt - Date.now()) / DAY_MS);
  if (daysLeft < 0) return { label: `overdue by ${Math.abs(daysLeft)}d`, tone: "coral" };
  if (daysLeft <= 14) return { label: `rotate in ${daysLeft}d`, tone: "amber" };
  return { label: `rotate in ${daysLeft}d`, tone: "muted" };
}

export default function VaultTab({ onStatus, lastPassword }) {
  const [exists, setExists] = useState(false);
  const [masterPassword, setMasterPassword] = useState("");
  const [unlocked, setUnlocked] = useState(false);
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState("");

  const [newLabel, setNewLabel] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newReminder, setNewReminder] = useState(90);
  const [revealed, setRevealed] = useState({});

  useEffect(() => {
    setExists(vaultExists());
  }, []);

  async function handleUnlockOrCreate() {
    setError("");
    if (!masterPassword) {
      setError("Enter a master password first.");
      return;
    }
    try {
      if (exists) {
        const loaded = await unlockVault(masterPassword);
        setEntries(loaded);
        onStatus?.("Vault unlocked.");
      } else {
        if (masterPassword.length < 8) {
          setError("Use at least 8 characters for your master password.");
          return;
        }
        await createVault(masterPassword);
        setEntries([]);
        setExists(true);
        onStatus?.("New encrypted vault created.");
      }
      setUnlocked(true);
    } catch (err) {
      if (err instanceof VaultLockedError) setError(err.message);
      else setError(err.message || "Failed to unlock vault.");
    }
  }

  function handleLock() {
    setUnlocked(false);
    setEntries([]);
    setMasterPassword("");
    setRevealed({});
    onStatus?.("Vault locked.");
  }

  async function handleAddEntry() {
    if (!newPassword) {
      setError("Enter or paste a password to save.");
      return;
    }
    const updated = [
      ...entries,
      { password: newPassword, label: newLabel || "unlabeled", createdAt: Date.now(), reminderDays: newReminder },
    ];
    await saveEntries(masterPassword, updated);
    setEntries(updated);
    setNewLabel("");
    setNewPassword("");
    setError("");
    onStatus?.("Saved to vault.");
  }

  async function handleDelete(index) {
    const updated = entries.filter((_, i) => i !== index);
    await saveEntries(masterPassword, updated);
    setEntries(updated);
    onStatus?.("Entry deleted.");
  }

  async function handleMarkRotated(index) {
    const updated = entries.map((e, i) => (i === index ? { ...e, createdAt: Date.now() } : e));
    await saveEntries(masterPassword, updated);
    setEntries(updated);
    onStatus?.("Marked as rotated today.");
  }

  function handleResetVault() {
    if (!confirm("This permanently deletes the encrypted vault from this browser. Continue?")) return;
    deleteVault();
    setExists(false);
    setUnlocked(false);
    setEntries([]);
    setMasterPassword("");
    onStatus?.("Vault reset.");
  }

  if (!unlocked) {
    return (
      <div className="grid gap-4">
        <Panel className="p-6">
          <SectionLabel>{exists ? "Unlock your vault" : "Create a new encrypted vault"}</SectionLabel>
          <div className="flex flex-col sm:flex-row gap-3 mt-2">
            <input
              type="password"
              value={masterPassword}
              onChange={(e) => setMasterPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleUnlockOrCreate()}
              placeholder="Master password"
              className="flex-1 bg-raised border border-line rounded-md px-4 py-3 font-mono focus:outline-none focus:border-brass-dim"
            />
            <Button onClick={handleUnlockOrCreate}>{exists ? "Unlock" : "Create vault"}</Button>
          </div>
          {error && <p className="text-coral text-sm mt-2 font-mono">{error}</p>}
        </Panel>

        <Panel className="p-5">
          <p className="text-sm text-muted leading-relaxed">
            Encrypted locally in this browser with AES-256-GCM, using a key derived via
            PBKDF2-HMAC-SHA256 (480,000 iterations) from your master password. Nothing is
            ever sent to a server — the vault lives only in this browser&rsquo;s local
            storage. Clearing site data or switching browsers will lose it; there is no
            recovery if you forget the master password. That&rsquo;s the honest tradeoff
            of a fully client-side vault.
          </p>
          {exists && (
            <button
              onClick={handleResetVault}
              className="text-coral text-xs font-mono mt-4 hover:underline"
            >
              Reset vault (delete permanently)
            </button>
          )}
        </Panel>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <Panel className="p-5">
        <div className="flex flex-col sm:flex-row gap-2 sm:items-end flex-wrap">
          <div className="flex-1 min-w-[140px]">
            <SectionLabel>Label</SectionLabel>
            <input
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              placeholder="e.g. Gmail"
              className="w-full bg-raised border border-line rounded-md px-3 py-2.5 text-sm focus:outline-none focus:border-brass-dim"
            />
          </div>
          <div className="flex-1 min-w-[160px]">
            <SectionLabel>Password</SectionLabel>
            <div className="flex gap-2">
              <input
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Paste a password"
                className="flex-1 bg-raised border border-line rounded-md px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-brass-dim"
              />
              {lastPassword && (
                <button
                  onClick={() => setNewPassword(lastPassword)}
                  title="Use last generated password"
                  className="text-xs font-mono text-brass-bright border border-brass-dim rounded-md px-2 hover:bg-brass/10 shrink-0"
                >
                  use last
                </button>
              )}
            </div>
          </div>
          <div className="min-w-[140px]">
            <SectionLabel>Rotate reminder</SectionLabel>
            <select
              value={newReminder}
              onChange={(e) => setNewReminder(Number(e.target.value))}
              className="w-full bg-raised border border-line rounded-md px-2 py-2.5 text-sm font-mono"
            >
              {REMINDER_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <Button onClick={handleAddEntry}>Save entry</Button>
        </div>
        {error && <p className="text-coral text-sm mt-2 font-mono">{error}</p>}
      </Panel>

      <Panel className="p-2">
        <div className="flex items-center justify-between px-3 py-2">
          <SectionLabel>{entries.length} saved {entries.length === 1 ? "entry" : "entries"}</SectionLabel>
          <Button variant="danger" onClick={handleLock}>Lock vault</Button>
        </div>
        <div className="grid gap-1 max-h-96 overflow-y-auto scrollbar-thin p-2 pt-0">
          {entries.length === 0 && (
            <p className="text-sm text-muted px-2 py-6 text-center">No saved passwords yet.</p>
          )}
          {entries.map((entry, i) => {
            const status = rotationStatus(entry);
            const toneClass = { coral: "text-coral", amber: "text-amber", muted: "text-muted" }[status?.tone] || "text-muted";
            return (
              <div key={i} className="flex items-center gap-3 bg-raised rounded-md px-3 py-2.5 flex-wrap">
                <span className="text-sm font-medium w-28 truncate shrink-0">{entry.label}</span>
                <span className="flex-1 font-mono text-sm text-teal truncate min-w-[80px]">
                  {revealed[i] ? entry.password : "•".repeat(Math.min(entry.password.length, 20))}
                </span>
                {status && (
                  <span className={`font-mono text-[10px] uppercase tracking-wide shrink-0 ${toneClass}`}>
                    {status.label}
                  </span>
                )}
                {status?.tone !== "muted" && status && (
                  <button
                    onClick={() => handleMarkRotated(i)}
                    className="text-muted hover:text-teal text-xs shrink-0"
                    title="Mark as rotated today"
                  >
                    rotated ✓
                  </button>
                )}
                <button
                  onClick={() => setRevealed((r) => ({ ...r, [i]: !r[i] }))}
                  className="text-muted hover:text-brass-bright text-xs shrink-0"
                >
                  {revealed[i] ? "hide" : "show"}
                </button>
                <button
                  onClick={() => navigator.clipboard.writeText(entry.password).then(() => onStatus?.("Copied."))}
                  className="text-muted hover:text-brass-bright text-xs shrink-0"
                >
                  copy
                </button>
                <button
                  onClick={() => handleDelete(i)}
                  className="text-muted hover:text-coral text-xs shrink-0"
                >
                  delete
                </button>
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}

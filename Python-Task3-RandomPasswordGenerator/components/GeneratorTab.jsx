"use client";

import { useEffect, useRef, useState } from "react";
import { generatePassword, generateMany, PasswordPolicyError } from "@/lib/generator";
import { estimateStrength } from "@/lib/strength";
import { checkPasswordBreach } from "@/lib/breach";
import StrengthGauge from "./StrengthGauge";
import QrCode from "./QrCode";
import { Panel, Button, Checkbox, SectionLabel, CopyButton } from "./ui";

const MAX_HISTORY = 5;
const MIN_LENGTH = 8;
const MAX_LENGTH = 128;
const MIN_CHAR_TYPES = 2;

export default function GeneratorTab({ onStatus, onPasswordGenerated }) {
  const [length, setLength] = useState(16);
  const [lengthInput, setLengthInput] = useState("16"); // free-text mirror of the slider, for explicit validation
  const [useLower, setUseLower] = useState(true);
  const [useUpper, setUseUpper] = useState(true);
  const [useDigits, setUseDigits] = useState(true);
  const [useSymbols, setUseSymbols] = useState(true);
  const [excludeAmbiguous, setExcludeAmbiguous] = useState(false);
  const [noConsecutiveRepeats, setNoConsecutiveRepeats] = useState(true);
  const [noRepeatedChars, setNoRepeatedChars] = useState(false);

  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [lengthInputError, setLengthInputError] = useState("");
  const [strength, setStrength] = useState(estimateStrength(""));
  const [breach, setBreach] = useState(null);
  const [checkingBreach, setCheckingBreach] = useState(false);
  const [batch, setBatch] = useState([]);
  const [batchCount, setBatchCount] = useState(5);
  const [history, setHistory] = useState([]); // session-only, in-memory, never persisted

  const containerRef = useRef(null);

  const selectedTypeCount = [useLower, useUpper, useDigits, useSymbols].filter(Boolean).length;
  const notEnoughTypes = selectedTypeCount < MIN_CHAR_TYPES;
  const canGenerate = !notEnoughTypes && !lengthInputError;

  const options = {
    length,
    useLower,
    useUpper,
    useDigits,
    useSymbols,
    excludeAmbiguous,
    noConsecutiveRepeats,
    noRepeatedChars,
  };

  function regenerate(announce = false) {
    if (notEnoughTypes) {
      setError(`Select at least ${MIN_CHAR_TYPES} character types to generate a password.`);
      return;
    }
    if (lengthInputError) {
      setError(lengthInputError);
      return;
    }
    try {
      const pw = generatePassword(options);
      setPassword(pw);
      setStrength(estimateStrength(pw));
      setBreach(null);
      setError("");
      onPasswordGenerated?.(pw);
      setHistory((prev) => {
        if (prev[0] === pw) return prev;
        return [pw, ...prev].slice(0, MAX_HISTORY);
      });
      if (announce) onStatus?.("New password generated.");
    } catch (err) {
      if (err instanceof PasswordPolicyError) {
        setError(err.message);
      } else {
        throw err;
      }
    }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { regenerate(false); }, [length, useLower, useUpper, useDigits, useSymbols, excludeAmbiguous, noConsecutiveRepeats, noRepeatedChars]);

  // Keyboard shortcut: press "R" or Space to regenerate, but never while
  // the user is typing in a text field (batch count select, etc).
  useEffect(() => {
    function handleKey(e) {
      const tag = document.activeElement?.tagName;
      const isTyping = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
      if (isTyping) return;
      if (e.code === "Space" || e.key === "r" || e.key === "R") {
        e.preventDefault();
        regenerate(true);
      }
    }
    const node = containerRef.current;
    node?.addEventListener("keydown", handleKey);
    return () => node?.removeEventListener("keydown", handleKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [length, useLower, useUpper, useDigits, useSymbols, excludeAmbiguous, noConsecutiveRepeats, noRepeatedChars, notEnoughTypes, lengthInputError]);

  function handleSlider(value) {
    setLength(value);
    setLengthInput(String(value));
    setLengthInputError("");
  }

  // Explicit input validation on the free-text length field: rejects
  // non-numeric input, and anything outside [MIN_LENGTH, MAX_LENGTH],
  // with a clear inline message rather than silently clamping.
  function handleLengthInputChange(raw) {
    setLengthInput(raw);
    if (raw.trim() === "") {
      setLengthInputError("Enter a password length.");
      return;
    }
    if (!/^\d+$/.test(raw.trim())) {
      setLengthInputError("Length must be a whole number.");
      return;
    }
    const n = parseInt(raw, 10);
    if (n < MIN_LENGTH) {
      setLengthInputError(`Minimum length is ${MIN_LENGTH} characters.`);
      return;
    }
    if (n > MAX_LENGTH) {
      setLengthInputError(`Maximum length is ${MAX_LENGTH} characters.`);
      return;
    }
    setLengthInputError("");
    setLength(n);
  }

  function generateBatch() {
    if (!canGenerate) {
      setError(
        notEnoughTypes
          ? `Select at least ${MIN_CHAR_TYPES} character types to generate a password.`
          : lengthInputError
      );
      return;
    }
    try {
      setBatch(generateMany(options, batchCount));
      onStatus?.(`Generated ${batchCount} independent passwords.`);
    } catch (err) {
      if (err instanceof PasswordPolicyError) setError(err.message);
    }
  }

  async function runBreachCheck() {
    setCheckingBreach(true);
    setBreach(null);
    const result = await checkPasswordBreach(password);
    setBreach(result);
    setCheckingBreach(false);
  }

  return (
    <div className="grid gap-4" ref={containerRef} tabIndex={-1}>
      <Panel className="p-5">
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            readOnly
            value={error ? "" : password}
            placeholder={error || ""}
            className="flex-1 bg-raised border border-line rounded-md px-4 py-3 font-mono text-lg tracking-wide text-teal focus:outline-none focus:border-brass-dim"
          />
          <CopyButton text={password} onStatus={onStatus} />
        </div>
        {error && <p className="text-coral text-sm mt-2 font-mono">⚠ {error}</p>}
        <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
          <QrCode text={password} />
          <p className="font-mono text-[11px] text-muted">press <kbd className="px-1.5 py-0.5 rounded bg-raised border border-line">space</kbd> or <kbd className="px-1.5 py-0.5 rounded bg-raised border border-line">R</kbd> to regenerate</p>
        </div>
      </Panel>

      <Panel className="p-5">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <StrengthGauge score={strength.score} label={strength.label} entropyBits={strength.entropyBits} />
          <div className="flex-1 min-w-0">
            <SectionLabel>Estimated crack time</SectionLabel>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-xs text-muted">
              <div>Online, throttled</div>
              <div className="text-ink2">{strength.crackTimes["Online, throttled (10/sec)"]}</div>
              <div>Offline, fast GPU hash</div>
              <div className="text-ink2">{strength.crackTimes["Offline, fast hash e.g. MD5/GPU (10B/sec)"]}</div>
            </div>
            {strength.warnings.length > 0 && (
              <p className="text-amber text-xs mt-3">⚠ {strength.warnings.join("  •  ")}</p>
            )}
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-line flex items-center gap-3 flex-wrap">
          <Button variant="ghost" onClick={runBreachCheck} disabled={!password || checkingBreach}>
            {checkingBreach ? "Checking…" : "Check against known breaches"}
          </Button>
          {breach && (
            <span
              className={`text-sm font-mono ${
                breach.error ? "text-amber" : breach.isBreached ? "text-coral" : "text-teal"
              }`}
            >
              {breach.error
                ? `⚠ ${breach.error}`
                : breach.isBreached
                ? `✕ found in ${breach.timesSeen.toLocaleString()} known breaches`
                : "✓ not found in known breaches"}
            </span>
          )}
        </div>
      </Panel>

      <Panel className="p-5">
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <SectionLabel>Length (minimum {MIN_LENGTH})</SectionLabel>
            <input
              type="text"
              inputMode="numeric"
              value={lengthInput}
              onChange={(e) => handleLengthInputChange(e.target.value)}
              className={`w-16 bg-raised border rounded-md px-2 py-1 text-sm font-mono text-right focus:outline-none ${
                lengthInputError ? "border-coral text-coral" : "border-line text-brass-bright focus:border-brass-dim"
              }`}
            />
          </div>
          <input
            type="range"
            min={MIN_LENGTH}
            max={MAX_LENGTH}
            value={length}
            onChange={(e) => handleSlider(Number(e.target.value))}
            className="w-full accent-brass h-1.5"
          />
          {lengthInputError && (
            <p className="text-coral text-xs mt-1.5 font-mono">⚠ {lengthInputError}</p>
          )}
        </div>

        <SectionLabel>
          Character types ({selectedTypeCount} of 4 selected — minimum {MIN_CHAR_TYPES} required)
        </SectionLabel>
        <div className="grid sm:grid-cols-2 gap-x-6">
          <Checkbox checked={useLower} onChange={(e) => setUseLower(e.target.checked)} label="Lowercase (a-z)" />
          <Checkbox checked={useUpper} onChange={(e) => setUseUpper(e.target.checked)} label="Uppercase (A-Z)" />
          <Checkbox checked={useDigits} onChange={(e) => setUseDigits(e.target.checked)} label="Digits (0-9)" />
          <Checkbox checked={useSymbols} onChange={(e) => setUseSymbols(e.target.checked)} label="Symbols (!@#$…)" />
        </div>
        {notEnoughTypes && (
          <p className="text-coral text-xs mt-2 font-mono">
            ⚠ Select at least {MIN_CHAR_TYPES} character types to generate a password.
          </p>
        )}

        <div className="grid sm:grid-cols-2 gap-x-6 mt-4 pt-4 border-t border-line">
          <Checkbox
            checked={excludeAmbiguous}
            onChange={(e) => setExcludeAmbiguous(e.target.checked)}
            label="Exclude ambiguous (l,1,I,O,0)"
          />
          <Checkbox
            checked={noConsecutiveRepeats}
            onChange={(e) => setNoConsecutiveRepeats(e.target.checked)}
            label="No consecutive repeats"
          />
          <Checkbox
            checked={noRepeatedChars}
            onChange={(e) => setNoRepeatedChars(e.target.checked)}
            label="No character reused at all"
          />
        </div>

        <div className="flex items-center gap-3 mt-5 pt-4 border-t border-line flex-wrap">
          <Button onClick={() => regenerate(true)} disabled={!canGenerate}>Generate password</Button>
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-muted font-mono">batch</span>
            <select
              value={batchCount}
              onChange={(e) => setBatchCount(Number(e.target.value))}
              className="bg-raised border border-line rounded-md px-2 py-2 text-sm font-mono"
            >
              {[5, 10, 20].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <Button variant="ghost" onClick={generateBatch} disabled={!canGenerate}>Generate batch</Button>
          </div>
        </div>

        {batch.length > 0 && (
          <div className="mt-4 pt-4 border-t border-line">
            <SectionLabel>Batch results</SectionLabel>
            <div className="grid gap-1.5 max-h-48 overflow-y-auto scrollbar-thin pr-1">
              {batch.map((pw, i) => (
                <div key={i} className="flex items-center justify-between bg-raised rounded px-3 py-2">
                  <span className="font-mono text-sm text-teal truncate">{pw}</span>
                  <CopyButton text={pw} onStatus={onStatus} className="!px-2 !py-1 !text-xs shrink-0 ml-3" />
                </div>
              ))}
            </div>
          </div>
        )}
      </Panel>

      {history.length > 1 && (
        <Panel className="p-5">
          <SectionLabel>This session&rsquo;s history (last {MAX_HISTORY}, never saved)</SectionLabel>
          <div className="grid gap-1.5">
            {history.slice(1).map((pw, i) => (
              <div key={i} className="flex items-center justify-between bg-raised rounded px-3 py-2 opacity-80">
                <span className="font-mono text-sm text-muted truncate">{pw}</span>
                <CopyButton text={pw} onStatus={onStatus} className="!px-2 !py-1 !text-xs shrink-0 ml-3" />
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}

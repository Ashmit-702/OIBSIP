"use client";

import { useState } from "react";
import { Panel, SectionLabel } from "./ui";

const SECTIONS = [
  {
    title: "Why crypto.getRandomValues(), not Math.random()",
    body: `Math.random() is fast and well-distributed, but it's not
cryptographically secure — its internal PRNG state can be reconstructed
from a handful of observed outputs, after which every future value it
produces is predictable. crypto.getRandomValues() is backed by the
operating system's CSPRNG (the same guarantee Python's \`secrets\` module
gives via os.urandom()). Every password and passphrase in this app is
built entirely on top of it — see lib/random.js.`,
  },
  {
    title: "How the breach check protects your password (k-Anonymity)",
    body: `Checking a password against HaveIBeenPwned's 800M+ breach
corpus without exposing it requires care. This app hashes the password
locally with SHA-1 (Web Crypto), then sends only the first 5 characters
of that 40-character hash to the server. The server returns every known
breached hash suffix starting with those 5 characters — several hundred
candidates — and the real match is found by comparing locally, offline.
The full password, and even the full hash, never leave your browser.`,
  },
  {
    title: "How the vault is encrypted",
    body: `Your master password is never stored. Instead, it's run through
PBKDF2-HMAC-SHA256 with 480,000 iterations (in line with OWASP's current
password-storage guidance) to derive an AES-256 key, unique per vault via
a random salt. Entries are encrypted with AES-256-GCM — authenticated
encryption, so a tampered or corrupted vault file fails to decrypt
instead of silently returning garbage. The encrypted blob lives only in
this browser's localStorage; nothing is sent to a server.`,
  },
  {
    title: "Why passphrases can beat character passwords",
    body: `A 6-word passphrase drawn from the EFF's 7,776-word diceware
list carries about 77.5 bits of entropy — comparable to a 12-13 character
fully-random password — while being dramatically easier to type and
remember. This is the classic XKCD 936 argument: humans are bad at
remembering "Tr0ub4dor&3" but fine at remembering "correct horse battery
staple." Both approaches are offered here because they suit different
situations (a password manager entry vs. a phrase you'll type by hand).`,
  },
  {
    title: "What never leaves your browser",
    body: `Password/passphrase generation, strength scoring, and vault
encryption are 100% client-side — no network call is made for any of
them. The single exception is the breach check, which sends a 5-character
hash prefix (never the password) to this app's own serverless function,
which forwards it to HaveIBeenPwned. There is no analytics, telemetry, or
account system anywhere in this app.`,
  },
];

export default function SecurityTab() {
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <div className="grid gap-4">
      <Panel className="p-5">
        <SectionLabel>How this app actually works</SectionLabel>
        <p className="text-sm text-muted leading-relaxed">
          Every design choice below exists to close a specific, real gap in
          typical student password-generator projects. Expand any section
          for the full reasoning.
        </p>
      </Panel>

      {SECTIONS.map((s, i) => {
        const open = openIndex === i;
        return (
          <Panel key={i} className="overflow-hidden">
            <button
              onClick={() => setOpenIndex(open ? -1 : i)}
              className="w-full flex items-center justify-between px-5 py-4 text-left"
            >
              <span className="font-display text-base text-ink2 pr-4">{s.title}</span>
              <span
                className={`font-mono text-brass shrink-0 transition-transform ${open ? "rotate-45" : ""}`}
              >
                +
              </span>
            </button>
            {open && (
              <div className="px-5 pb-5 -mt-1">
                <p className="text-sm text-muted leading-relaxed whitespace-pre-line">{s.body}</p>
              </div>
            )}
          </Panel>
        );
      })}
    </div>
  );
}

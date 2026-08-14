"use client";

import { useState } from "react";
import Tabs from "@/components/Tabs";
import GeneratorTab from "@/components/GeneratorTab";
import PassphraseTab from "@/components/PassphraseTab";
import VaultTab from "@/components/VaultTab";
import SecurityTab from "@/components/SecurityTab";

const TABS = [
  { id: "generate", label: "Generate" },
  { id: "passphrase", label: "Passphrase" },
  { id: "vault", label: "Vault" },
  { id: "security", label: "Security" },
];

export default function Page() {
  const [active, setActive] = useState("generate");
  const [status, setStatus] = useState("Ready.");
  const [lastPassword, setLastPassword] = useState("");

  return (
    <main className="min-h-screen flex flex-col">
      <div className="max-w-3xl w-full mx-auto px-5 pt-10 pb-6 flex-1 flex flex-col">
        <header className="mb-8">
          <div className="flex items-baseline gap-3 flex-wrap">
            <h1 className="font-display text-3xl sm:text-[34px] font-semibold text-ink2">
              SecurePass <span className="text-brass italic">Toolkit</span>
            </h1>
            <span className="font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
              vault console
            </span>
          </div>
          <p className="text-muted text-sm mt-2 max-w-xl">
            CSPRNG-based generation, live entropy scoring, breach checking, and an
            encrypted local vault — all running in your browser. Nothing is sent
            anywhere except an anonymized 5-character hash prefix for breach checks.
          </p>
        </header>

        <div className="rounded-lg border border-line bg-panel/40 overflow-hidden">
          <Tabs tabs={TABS} active={active} onChange={setActive} />
          <div className="p-4 sm:p-6">
            {active === "generate" && (
              <GeneratorTab onStatus={setStatus} onPasswordGenerated={setLastPassword} />
            )}
            {active === "passphrase" && <PassphraseTab onStatus={setStatus} />}
            {active === "vault" && <VaultTab onStatus={setStatus} lastPassword={lastPassword} />}
            {active === "security" && <SecurityTab />}
          </div>
        </div>

        <footer className="mt-6 flex items-center justify-between flex-wrap gap-2">
          <p className="font-mono text-xs text-muted">{status}</p>
          <p className="font-mono text-xs text-muted/70">
            secrets-grade CSPRNG · zero telemetry · open source
          </p>
        </footer>
      </div>
    </main>
  );
}

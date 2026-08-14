"use client";

import { useEffect, useState } from "react";
import { generatePassphrase, passphraseEntropyBits, wordlistSize } from "@/lib/passphrase";
import QrCode from "./QrCode";
import { Panel, Button, Checkbox, SectionLabel, CopyButton } from "./ui";

export default function PassphraseTab({ onStatus }) {
  const [numWords, setNumWords] = useState(6);
  const [separator, setSeparator] = useState("-");
  const [capitalize, setCapitalize] = useState(true);
  const [appendNumber, setAppendNumber] = useState(true);
  const [phrase, setPhrase] = useState("");

  function regenerate() {
    const p = generatePassphrase({ numWords, separator: separator === "none" ? "" : separator, capitalize, appendNumber });
    setPhrase(p);
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { regenerate(); }, [numWords, separator, capitalize, appendNumber]);

  const bits = passphraseEntropyBits(numWords, appendNumber);

  return (
    <div className="grid gap-4">
      <Panel className="p-5">
        <SectionLabel>Diceware-style passphrase — EFF Large Wordlist ({wordlistSize().toLocaleString()} words)</SectionLabel>
        <div className="flex flex-col sm:flex-row gap-3 mt-2">
          <input
            readOnly
            value={phrase}
            className="flex-1 bg-raised border border-line rounded-md px-4 py-3 font-mono text-base sm:text-lg tracking-wide text-teal focus:outline-none focus:border-brass-dim"
          />
          <CopyButton text={phrase} onStatus={onStatus} />
        </div>
        <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
          <QrCode text={phrase} />
          <p className="font-mono text-xs text-muted">~{bits.toFixed(1)} bits of entropy</p>
        </div>
      </Panel>

      <Panel className="p-5">
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <SectionLabel>Number of words</SectionLabel>
            <span className="font-mono text-brass-bright text-sm">{numWords}</span>
          </div>
          <input
            type="range"
            min={3}
            max={10}
            value={numWords}
            onChange={(e) => setNumWords(Number(e.target.value))}
            className="w-full accent-brass h-1.5"
          />
        </div>

        <div className="mb-4">
          <SectionLabel>Separator</SectionLabel>
          <div className="flex gap-2 flex-wrap">
            {["-", "_", ".", " ", "none"].map((s) => (
              <button
                key={s}
                onClick={() => setSeparator(s)}
                className={`px-3 py-1.5 rounded-md text-sm font-mono border transition-colors ${
                  separator === s
                    ? "bg-brass text-ink border-brass"
                    : "border-line text-muted hover:text-ink2 hover:border-brass-dim"
                }`}
              >
                {s === " " ? "space" : s}
              </button>
            ))}
          </div>
        </div>

        <Checkbox checked={capitalize} onChange={(e) => setCapitalize(e.target.checked)} label="Capitalize each word" />
        <Checkbox checked={appendNumber} onChange={(e) => setAppendNumber(e.target.checked)} label="Append a random digit" />

        <div className="mt-5 pt-4 border-t border-line">
          <Button onClick={regenerate}>Generate passphrase</Button>
        </div>
      </Panel>

      <Panel className="p-5">
        <p className="text-sm text-muted leading-relaxed">
          Why passphrases? Long random word sequences are easier to type and remember
          than character soup, while still reaching high entropy — the classic
          <span className="text-ink2"> XKCD 936</span> &ldquo;correct horse battery
          staple&rdquo; argument. Each word is drawn independently from the EFF&rsquo;s
          public 7,776-word diceware list using the browser&rsquo;s CSPRNG.
        </p>
      </Panel>
    </div>
  );
}

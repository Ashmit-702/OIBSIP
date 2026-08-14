# 🔐 SecurePass Toolkit — Web (Vercel-ready)

The web port of the SecurePass Toolkit desktop app. Same security model,
running entirely in the browser as a Next.js app, deployable to Vercel
with zero configuration.

## Why a rewrite, not just "wrap the Python app"

Desktop GUI apps (Tkinter, in the original version) can't run on Vercel —
Vercel serves web requests, not native window binaries. Rather than fake
it, this is a genuine port: every security-critical function from the
Python `core/` package has a line-for-line JavaScript equivalent, built on
browser-native cryptographic primitives instead of Python's `secrets` /
`cryptography` packages.

| Python (desktop) | Web (this app) | Guarantee preserved |
|---|---|---|
| `secrets` module | `crypto.getRandomValues()` (Web Crypto) | OS-backed CSPRNG, not a predictable PRNG |
| `hashlib.sha1` + urllib | `crypto.subtle.digest('SHA-1')` + `fetch` | k-Anonymity breach check, password never leaves the device |
| `cryptography.fernet` + PBKDF2 | `crypto.subtle` AES-256-GCM + PBKDF2 | Authenticated encryption, tamper-evident vault |
| Local encrypted JSON file | Encrypted blob in `localStorage` | Vault never touches a server |
| Tkinter GUI | Next.js App Router + Tailwind | — |

**Nothing runs on the server except one thing**: the HaveIBeenPwned proxy
route (`app/api/breach-check/route.js`), and even that never sees your
password — only a 5-character hash prefix, computed client-side. See that
file's docstring for the full reasoning.

## Features

- **Character-based generator** — adjustable length (4–64), toggle
  lowercase/uppercase/digits/symbols, exclude visually-ambiguous characters,
  forbid consecutive repeats, forbid any character reuse, batch-generate.
- **Passphrase generator** — EFF Large Wordlist (7,776 words), adjustable
  word count, separator, capitalization, and an appended random digit.
- **Live strength meter** — analog vault-dial gauge, entropy in bits, and
  estimated crack time under four attacker models.
- **Breach checker** — HaveIBeenPwned k-Anonymity check, one click.
- **Encrypted vault** with **rotation reminders** — save entries locally
  (AES-256-GCM + PBKDF2), tag each with a 30/90/180/365-day reminder, and
  see overdue/due-soon badges computed live.
- **QR code export** — render any password/passphrase as a QR code for
  quick transfer to a phone, generated entirely client-side.
- **Session history** — last 5 passwords generated this session, in
  memory only, never persisted.
- **Keyboard shortcuts** — Space or R to regenerate.
- **In-app Security tab** — a plain-language explainer of every
  cryptographic choice in the app (CSPRNG, k-anonymity, PBKDF2/AES-GCM,
  passphrase entropy), useful for walking a reviewer through the reasoning
  live instead of only in this README.
- **Installable / offline-capable (PWA)** — manifest + service worker so
  generation, strength scoring, and the vault keep working offline after
  the first visit. The breach check correctly still requires a connection,
  since that data must be live.

## Project structure

```
securepass-web/
├── app/
│   ├── page.js                  # main UI (tabs, layout)
│   ├── layout.js                # fonts + metadata + PWA registration
│   ├── globals.css
│   └── api/breach-check/route.js  # serverless HIBP proxy (Node runtime)
├── components/
│   ├── GeneratorTab.jsx
│   ├── PassphraseTab.jsx
│   ├── VaultTab.jsx              # includes rotation reminders
│   ├── SecurityTab.jsx           # in-app crypto-design explainer
│   ├── StrengthGauge.jsx         # signature analog-dial strength meter
│   ├── QrCode.jsx                # client-side QR export
│   ├── PWARegister.jsx           # registers the service worker
│   ├── Tabs.jsx
│   └── ui.jsx                    # shared Panel/Button/Checkbox/CopyButton
├── lib/
│   ├── random.js                # CSPRNG helpers (crypto.getRandomValues)
│   ├── generator.js             # character-based password generator
│   ├── passphrase.js            # EFF diceware passphrase generator
│   ├── strength.js               # entropy + crack-time estimation
│   ├── breach.js                 # client-side k-anonymity hashing/fetch
│   ├── vault.js                  # PBKDF2 + AES-GCM encrypted vault
│   └── wordlist.json             # EFF Large Wordlist, 7,776 words
├── public/
│   ├── manifest.json             # PWA manifest
│   ├── sw.js                     # offline app-shell service worker
│   └── icon-192.png, icon-512.png, apple-touch-icon.png
└── package.json
```

`lib/` has zero React/Next dependency — every function is a plain module
you could unit test with any JS test runner, same design principle as the
Python version's `core/` package.

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Deploy to Vercel

**Option A — CLI (fastest):**
```bash
npm install -g vercel
vercel
```
Follow the prompts (link or create a project). Vercel auto-detects
Next.js — no configuration needed. Re-run `vercel --prod` to promote to
production.

**Option B — GitHub (recommended for a portfolio/demo link):**
1. Push this folder to a new GitHub repo.
2. Go to https://vercel.com/new, import the repo.
3. Framework preset auto-detects as **Next.js** — leave build settings
   default (`next build`, output handled automatically).
4. Click **Deploy**. You'll get a live `https://<project>.vercel.app` URL.

No environment variables, database, or secrets are required — the app is
entirely self-contained.

## A note on fonts

The UI uses self-hosted fonts (`@fontsource/fraunces`, `@fontsource/inter`,
`@fontsource/jetbrains-mono`) bundled as regular npm packages, rather than
`next/font/google`'s build-time Google Fonts fetch. This makes the build
fully offline-reproducible and avoids failures on networks/CI runners that
block `fonts.googleapis.com`.

## Design

The strength meter is rendered as an analog vault-dial gauge (see
`components/StrengthGauge.jsx`) rather than a generic progress bar —
intentional, to match the "vault console" visual language (brass/ink/teal
palette, Fraunces display serif + JetBrains Mono for data readouts) used
throughout the app.

## Known npm audit noise

`npm audit` reports advisories against Next.js's *optional, bundled*
`sharp` (image-optimization) and internal `postcss` copies. This app does
not use `next/image` or any image optimization, so these paths are never
exercised; npm's suggested "fix" (downgrading to Next 9) would be a
regression, not a fix. Worth knowing if a reviewer runs `npm audit`.

## License

MIT. The EFF wordlist is used under the EFF's public terms
(https://www.eff.org/dice).

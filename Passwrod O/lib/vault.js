/**
 * lib/vault.js
 * ==============
 * Browser-side port of core/vault.py. Same shape, different primitives:
 *
 *   - Key derivation: PBKDF2-HMAC-SHA256, 480,000 iterations, via Web
 *     Crypto's crypto.subtle.deriveKey -- matching OWASP's password-
 *     storage guidance for PBKDF2, same iteration count as the Python
 *     version so the two are directly comparable.
 *   - Encryption: AES-256-GCM (authenticated encryption -- a tampered
 *     ciphertext fails to decrypt rather than silently returning garbage,
 *     same guarantee Fernet gave the Python vault).
 *   - Storage: browser localStorage, scoped to this origin. Nothing is
 *     ever sent to any server -- this is a purely local, offline vault,
 *     which is the correct trust boundary for a client-only deployment.
 *
 * If the user clears site data or switches browsers, the vault is gone --
 * this is disclosed in the UI, since it's a real, honest limitation of a
 * browser-only vault (unlike a real password manager with sync).
 */

const STORAGE_KEY = "securepass_vault_v1";
const PBKDF2_ITERATIONS = 480_000;

function bufToB64(buf) {
  return btoa(String.fromCharCode(...new Uint8Array(buf)));
}
function b64ToBuf(b64) {
  return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
}

async function deriveKey(masterPassword, salt) {
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(masterPassword),
    "PBKDF2",
    false,
    ["deriveKey"]
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: PBKDF2_ITERATIONS, hash: "SHA-256" },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}

export class VaultLockedError extends Error {}

export function vaultExists() {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(STORAGE_KEY) !== null;
}

export async function createVault(masterPassword) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  await saveEntries(masterPassword, [], salt);
}

export async function unlockVault(masterPassword) {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) throw new Error("No vault found. Create one first.");

  const { salt: saltB64, iv: ivB64, ciphertext } = JSON.parse(raw);
  const salt = b64ToBuf(saltB64);
  const iv = b64ToBuf(ivB64);
  const key = await deriveKey(masterPassword, salt);

  try {
    const plaintext = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv },
      key,
      b64ToBuf(ciphertext)
    );
    return JSON.parse(new TextDecoder().decode(plaintext));
  } catch (err) {
    throw new VaultLockedError("Incorrect master password, or the vault is corrupted.");
  }
}

export async function saveEntries(masterPassword, entries, existingSalt = null) {
  const salt = existingSalt ?? crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(masterPassword, salt);

  const plaintext = new TextEncoder().encode(JSON.stringify(entries));
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, plaintext);

  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      salt: bufToB64(salt),
      iv: bufToB64(iv),
      ciphertext: bufToB64(ciphertext),
      kdfIterations: PBKDF2_ITERATIONS,
    })
  );
}

export async function getSalt() {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  return b64ToBuf(JSON.parse(raw).salt);
}

export function deleteVault() {
  window.localStorage.removeItem(STORAGE_KEY);
}

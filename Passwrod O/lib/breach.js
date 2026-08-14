/**
 * lib/breach.js
 * ===============
 * Client-side half of the k-Anonymity breach check. Hashes the password
 * locally with Web Crypto (SHA-1 -- required by the HIBP API format, not
 * used for anything security-critical here), sends only the first 5 hex
 * characters to our own /api/breach-check proxy, and compares the
 * returned suffix list locally. The password itself never leaves the
 * browser in any form.
 */

async function sha1Hex(text) {
  const enc = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-1", enc);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
    .toUpperCase();
}

export async function checkPasswordBreach(password) {
  if (!password) {
    return { checked: false, isBreached: false, timesSeen: 0, error: "No password provided." };
  }

  const hash = await sha1Hex(password);
  const prefix = hash.slice(0, 5);
  const suffix = hash.slice(5);

  let res;
  try {
    res = await fetch(`/api/breach-check?prefix=${prefix}`);
  } catch (err) {
    return { checked: false, isBreached: false, timesSeen: 0, error: "Network error reaching breach-check service." };
  }

  if (!res.ok) {
    let msg = `Breach-check service error (${res.status}).`;
    try {
      const j = await res.json();
      if (j.error) msg = j.error;
    } catch {}
    return { checked: false, isBreached: false, timesSeen: 0, error: msg };
  }

  const body = await res.text();
  for (const line of body.split("\n")) {
    if (!line.includes(":")) continue;
    const [lineSuffix, countStr] = line.trim().split(":");
    if (lineSuffix === suffix) {
      const count = parseInt(countStr, 10) || 0;
      if (count > 0) {
        return { checked: true, isBreached: true, timesSeen: count, error: null };
      }
    }
  }
  return { checked: true, isBreached: false, timesSeen: 0, error: null };
}

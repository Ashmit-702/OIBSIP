/**
 * lib/random.js
 * ===============
 * The browser equivalent of Python's `secrets` module.
 *
 * WHY crypto.getRandomValues() AND NOT Math.random()
 * ----------------------------------------------------
 * Math.random() in V8 (Chrome/Node) and most other JS engines is backed by
 * xorshift128+ -- a fast, well-distributed PRNG, but NOT cryptographically
 * secure. Its full internal state can be recovered from a small number of
 * observed outputs, after which every future "random" value it produces is
 * predictable. It is explicitly documented by MDN as unsuitable for
 * anything security-related.
 *
 * crypto.getRandomValues() (the Web Crypto API, available in every modern
 * browser and in a secure context on Vercel's HTTPS deployment) is backed
 * by the operating system's CSPRNG -- the same guarantee Python's `secrets`
 * module provides via os.urandom(). This file is the only place in the
 * app that touches raw randomness; every generator builds on top of it.
 */

/**
 * Returns a cryptographically secure random integer in [0, maxExclusive)
 * with no modulo bias, via rejection sampling.
 */
export function secureRandomInt(maxExclusive) {
  if (maxExclusive <= 0) throw new Error("maxExclusive must be positive");
  if (maxExclusive > 0xffffffff) throw new Error("maxExclusive too large for 32-bit sampling");

  const range = maxExclusive;
  // Largest multiple of `range` that fits in 32 bits -- values drawn above
  // this threshold are rejected and re-rolled, which removes modulo bias.
  const limit = Math.floor(0x100000000 / range) * range;

  const buf = new Uint32Array(1);
  let value;
  do {
    crypto.getRandomValues(buf);
    value = buf[0];
  } while (value >= limit);

  return value % range;
}

/** Cryptographically secure choice from an array-like of items. */
export function secureChoice(items) {
  return items[secureRandomInt(items.length)];
}

/** Fisher-Yates shuffle using the CSPRNG. Mutates and returns `arr`. */
export function secureShuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = secureRandomInt(i + 1);
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/** A single random digit 0-9 as a string, CSPRNG-backed. */
export function secureDigit() {
  return String(secureRandomInt(10));
}

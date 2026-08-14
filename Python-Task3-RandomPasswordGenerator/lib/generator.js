/**
 * lib/generator.js
 * ==================
 * Direct port of the Python project's core/generator.py, built on the
 * CSPRNG helpers in lib/random.js. Same guarantees:
 *   - at least one character from every selected class (when required)
 *   - optional "no two identical characters adjacent"
 *   - optional "no character reused anywhere in the string"
 */

import { secureRandomInt, secureChoice, secureShuffle } from "./random";

export const AMBIGUOUS_CHARS = "il1Lo0O|";
export const LOWERCASE = "abcdefghijklmnopqrstuvwxyz";
export const UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
export const DIGITS = "0123456789";
export const SYMBOLS = "!@#$%^&*()-_=+[]{}:;,.?";

export class PasswordPolicyError extends Error {}

export const DEFAULT_OPTIONS = {
  length: 16,
  useLower: true,
  useUpper: true,
  useDigits: true,
  useSymbols: true,
  excludeAmbiguous: false,
  noRepeatedChars: false,
  noConsecutiveRepeats: true,
  customExclude: "",
  requireEachSelectedClass: true,
};

function selectedClasses(opts) {
  const classes = [];
  if (opts.useLower) classes.push(LOWERCASE);
  if (opts.useUpper) classes.push(UPPERCASE);
  if (opts.useDigits) classes.push(DIGITS);
  if (opts.useSymbols) classes.push(SYMBOLS);
  return classes;
}

function filtered(chars, opts) {
  let out = chars;
  if (opts.excludeAmbiguous) {
    out = [...out].filter((c) => !AMBIGUOUS_CHARS.includes(c)).join("");
  }
  if (opts.customExclude) {
    const ex = new Set(opts.customExclude);
    out = [...out].filter((c) => !ex.has(c)).join("");
  }
  return out;
}

function characterPool(opts) {
  let pool = "";
  if (opts.useLower) pool += LOWERCASE;
  if (opts.useUpper) pool += UPPERCASE;
  if (opts.useDigits) pool += DIGITS;
  if (opts.useSymbols) pool += SYMBOLS;

  if (!pool) {
    throw new PasswordPolicyError(
      "At least one character class (lower/upper/digits/symbols) must be enabled."
    );
  }
  pool = filtered(pool, opts);
  if (!pool) {
    throw new PasswordPolicyError("Exclusion rules removed every character from the pool.");
  }
  return pool;
}

function hasConsecutiveRepeat(chars) {
  for (let i = 1; i < chars.length; i++) {
    if (chars[i] === chars[i - 1]) return true;
  }
  return false;
}

function coversAllClasses(chars, requiredClasses) {
  const set = new Set(chars);
  return requiredClasses.every((cls) => [...cls].some((c) => set.has(c)));
}

export function generatePassword(userOptions = {}) {
  const opts = { ...DEFAULT_OPTIONS, ...userOptions };

  if (opts.length < 4) {
    throw new PasswordPolicyError("Length must be at least 4 characters.");
  }

  const pool = [...characterPool(opts)];

  if (opts.noRepeatedChars && opts.length > pool.length) {
    throw new PasswordPolicyError(
      `Cannot generate a ${opts.length}-character password with no repeated ` +
        `characters from a pool of only ${pool.length} characters. Increase the ` +
        `pool (enable more character classes) or reduce the length.`
    );
  }

  let requiredClasses = opts.requireEachSelectedClass
    ? selectedClasses(opts).map((c) => filtered(c, opts)).filter(Boolean)
    : [];

  if (requiredClasses.length > opts.length) {
    throw new PasswordPolicyError(
      "Password length is shorter than the number of required character classes."
    );
  }

  for (let attempt = 0; attempt < 500; attempt++) {
    let chars;

    if (opts.noRepeatedChars) {
      const workingPool = secureShuffle([...pool]);
      chars = workingPool.slice(0, opts.length);

      if (requiredClasses.length) {
        for (const cls of selectedClasses(opts)) {
          const clsFiltered = filtered(cls, opts);
          const hasOne = [...clsFiltered].some((c) => chars.includes(c));
          if (!hasOne) {
            const candidates = [...clsFiltered].filter((c) => !chars.includes(c));
            if (candidates.length === 0) continue;
            const idx = secureRandomInt(chars.length);
            chars[idx] = secureChoice(candidates);
          }
        }
      }
      secureShuffle(chars);
    } else {
      chars = Array.from({ length: opts.length }, () => secureChoice(pool));
      if (requiredClasses.length) {
        const positions = secureShuffle(
          Array.from({ length: opts.length }, (_, i) => i)
        ).slice(0, requiredClasses.length);
        positions.forEach((pos, i) => {
          chars[pos] = secureChoice([...requiredClasses[i]]);
        });
      }
    }

    if (opts.noConsecutiveRepeats && hasConsecutiveRepeat(chars)) continue;
    if (requiredClasses.length && !coversAllClasses(chars, requiredClasses)) continue;

    return chars.join("");
  }

  throw new PasswordPolicyError(
    "Could not satisfy all constraints after many attempts. Try relaxing " +
      "'no repeated characters' or 'no consecutive repeats', or increase the length."
  );
}

export function generateMany(options, count) {
  if (count < 1) throw new PasswordPolicyError("count must be >= 1");
  return Array.from({ length: count }, () => generatePassword(options));
}

/**
 * lib/strength.js
 * =================
 * Port of core/strength.py: pool-based Shannon entropy with pattern
 * penalties (dictionary words, sequences, repeats), plus crack-time
 * estimates against four attacker models. See the Python module for the
 * full rationale -- this mirrors it exactly so the two implementations
 * stay auditable against each other.
 */

const COMMON_SEQUENCES = [
  "0123456789",
  "abcdefghijklmnopqrstuvwxyz",
  "qwertyuiop",
  "asdfghjkl",
  "zxcvbnm",
];

const COMMON_WORDS = [
  "password", "letmein", "admin", "welcome", "qwerty", "iloveyou",
  "dragon", "monkey", "football", "baseball", "master", "login",
  "princess", "sunshine", "shadow", "superman", "trustno1",
];

export const CRACK_SPEEDS = {
  "Online, throttled (10/sec)": 10,
  "Online, unthrottled (1k/sec)": 1_000,
  "Offline, slow hash e.g. bcrypt (10k/sec)": 10_000,
  "Offline, fast hash e.g. MD5/GPU (10B/sec)": 10_000_000_000,
};

function poolSize(password) {
  let pool = 0;
  if (/[a-z]/.test(password)) pool += 26;
  if (/[A-Z]/.test(password)) pool += 26;
  if (/[0-9]/.test(password)) pool += 10;
  if (/[^a-zA-Z0-9]/.test(password)) pool += 33;
  return Math.max(pool, 1);
}

function hasSequence(password) {
  const lowered = password.toLowerCase();
  for (const seq of COMMON_SEQUENCES) {
    for (let i = 0; i <= seq.length - 3; i++) {
      const chunk = seq.slice(i, i + 3);
      const rev = [...chunk].reverse().join("");
      if (lowered.includes(chunk) || lowered.includes(rev)) return true;
    }
  }
  return false;
}

function hasRepeats(password) {
  return /(.)\1\1/.test(password);
}

function containsCommonWord(password) {
  const lowered = password.toLowerCase();
  return COMMON_WORDS.some((w) => lowered.includes(w));
}

function scoreFromBits(bits) {
  if (bits < 28) return [0, "Very Weak"];
  if (bits < 36) return [1, "Weak"];
  if (bits < 60) return [2, "Fair"];
  if (bits < 80) return [3, "Strong"];
  return [4, "Very Strong"];
}

function formatTime(bits, guessesPerSec) {
  const totalGuesses = Math.pow(2, bits);
  const seconds = totalGuesses / 2 / guessesPerSec;
  if (seconds < 1) return "instantly";

  const units = [
    ["century", 60 * 60 * 24 * 365 * 100],
    ["year", 60 * 60 * 24 * 365],
    ["day", 60 * 60 * 24],
    ["hour", 60 * 60],
    ["minute", 60],
    ["second", 1],
  ];
  for (const [name, unitSeconds] of units) {
    if (seconds >= unitSeconds) {
      const value = seconds / unitSeconds;
      if (name === "century" && value > 1_000_000) return "effectively forever";
      return `~${value.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${name}${value !== 1 ? "s" : ""}`;
    }
  }
  return "instantly";
}

export function estimateStrength(password) {
  if (!password) {
    const crackTimes = {};
    Object.keys(CRACK_SPEEDS).forEach((k) => (crackTimes[k] = "instant"));
    return {
      entropyBits: 0,
      score: 0,
      label: "Empty",
      crackTimes,
      warnings: ["No password entered."],
      suggestions: ["Enter or generate a password."],
    };
  }

  const pool = poolSize(password);
  const rawBits = password.length * Math.log2(pool);

  const warnings = [];
  let penaltyBits = 0;

  if (password.length < 8) {
    warnings.push("Shorter than 8 characters -- easy to brute force.");
    penaltyBits += 10;
  }
  if (hasSequence(password)) {
    warnings.push("Contains a common sequence (e.g. 'abc', '123', 'qwerty').");
    penaltyBits += 12;
  }
  if (hasRepeats(password)) {
    warnings.push("Contains 3+ repeated characters in a row.");
    penaltyBits += 8;
  }
  if (containsCommonWord(password)) {
    warnings.push("Contains a very common password/word fragment.");
    penaltyBits += 15;
  }
  if (/^[a-zA-Z]+$/.test(password)) {
    warnings.push("Letters only -- add numbers or symbols.");
    penaltyBits += 6;
  }
  if (/^[0-9]+$/.test(password)) {
    warnings.push("Digits only -- this is guessed extremely quickly.");
    penaltyBits += 20;
  }

  const effectiveBits = Math.max(rawBits - penaltyBits, 0);
  const [score, label] = scoreFromBits(effectiveBits);

  const crackTimes = {};
  Object.entries(CRACK_SPEEDS).forEach(([model, speed]) => {
    crackTimes[model] = formatTime(effectiveBits, speed);
  });

  const suggestions = [];
  if (score < 3) {
    if (password.length < 12) suggestions.push("Use at least 12-16 characters.");
    if (!/[^a-zA-Z0-9]/.test(password)) suggestions.push("Add symbols to widen the character pool.");
    if (!/[A-Z]/.test(password) || !/[a-z]/.test(password))
      suggestions.push("Mix uppercase and lowercase letters.");
    suggestions.push("Prefer a randomly generated password or passphrase over anything memorized.");
  }

  return {
    entropyBits: Math.round(effectiveBits * 10) / 10,
    score,
    label,
    crackTimes,
    warnings,
    suggestions,
  };
}

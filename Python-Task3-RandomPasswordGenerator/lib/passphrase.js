/**
 * lib/passphrase.js
 * ===================
 * Diceware-style passphrase generation using the EFF Large Wordlist
 * (7,776 words = 6^5, the classic diceware design constraint -- each word
 * is selectable by rolling five six-sided dice). Every word contributes
 * log2(7776) ~= 12.925 bits of entropy via a CSPRNG selection.
 *
 * Source: EFF, "Deep Dive: EFF's New Wordlists for Random Passphrases"
 * https://www.eff.org/dice
 */

import wordlist from "./wordlist.json";
import { secureChoice, secureRandomInt, secureDigit } from "./random";

export const BITS_PER_WORD = Math.log2(wordlist.length);

export function generatePassphrase({
  numWords = 6,
  separator = "-",
  capitalize = true,
  appendNumber = true,
} = {}) {
  if (numWords < 3) throw new Error("Use at least 3 words for a meaningful passphrase.");

  let chosen = Array.from({ length: numWords }, () => secureChoice(wordlist));
  if (capitalize) {
    chosen = chosen.map((w) => w[0].toUpperCase() + w.slice(1));
  }
  if (appendNumber) {
    const idx = secureRandomInt(chosen.length);
    chosen[idx] = chosen[idx] + secureDigit();
  }
  return chosen.join(separator);
}

export function passphraseEntropyBits(numWords, appendNumber = true) {
  let bits = numWords * BITS_PER_WORD;
  if (appendNumber) bits += Math.log2(10);
  return bits;
}

export function wordlistSize() {
  return wordlist.length;
}

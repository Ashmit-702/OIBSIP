/**
 * app/api/breach-check/route.js
 * ================================
 * Server-side proxy to the HaveIBeenPwned Pwned Passwords API, running as
 * a Vercel serverless function (Node.js runtime).
 *
 * WHY A SERVER PROXY INSTEAD OF CALLING HIBP DIRECTLY FROM THE BROWSER
 * -----------------------------------------------------------------------
 * The k-Anonymity model itself does not require a server: only a 5-char
 * SHA-1 prefix is ever sent, so calling the API directly from the client
 * would still be safe. This proxy exists for robustness, not secrecy:
 *   - it works even if HIBP's CORS policy changes,
 *   - it lets us set a descriptive User-Agent (HIBP asks API consumers to
 *     identify themselves), and
 *   - it keeps all outbound network calls behind one auditable file.
 *
 * The full password NEVER reaches this route or this server -- the
 * browser hashes it locally (Web Crypto SHA-1) and only sends the 5-char
 * prefix as a query param. See lib/breach.js for the client side of this.
 */

export const runtime = "nodejs";

const HIBP_URL = "https://api.pwnedpasswords.com/range/";
const USER_AGENT = "SecurePass-Toolkit-Internship-Project";

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const prefix = (searchParams.get("prefix") || "").toUpperCase();

  if (!/^[0-9A-F]{5}$/.test(prefix)) {
    return Response.json(
      { error: "Invalid hash prefix." },
      { status: 400 }
    );
  }

  try {
    const upstream = await fetch(HIBP_URL + prefix, {
      headers: { "User-Agent": USER_AGENT, "Add-Padding": "true" },
      signal: AbortSignal.timeout(6000),
    });

    if (!upstream.ok) {
      return Response.json(
        { error: `Breach-check service returned ${upstream.status}` },
        { status: 502 }
      );
    }

    const body = await upstream.text();
    return new Response(body, {
      status: 200,
      headers: { "content-type": "text/plain" },
    });
  } catch (err) {
    return Response.json(
      { error: `Could not reach breach-check service: ${err.message}` },
      { status: 502 }
    );
  }
}

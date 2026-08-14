"use client";

import { useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import { Button } from "./ui";

/**
 * Renders an on-demand QR code for the given text (e.g. to move a
 * generated password/passphrase to a phone without typing it). Generated
 * entirely client-side via the `qrcode` package -- the value never
 * leaves the browser. Hidden by default since a QR code is effectively
 * a plaintext copy of the secret rendered as an image; showing it takes
 * an explicit click.
 */
export default function QrCode({ text }) {
  const [visible, setVisible] = useState(false);
  const canvasRef = useRef(null);

  useEffect(() => {
    if (visible && text && canvasRef.current) {
      QRCode.toCanvas(canvasRef.current, text, {
        width: 176,
        margin: 1,
        color: { dark: "#0C0F14", light: "#E7E3DA" },
      }).catch(() => {});
    }
  }, [visible, text]);

  if (!text) return null;

  return (
    <div>
      <Button variant="ghost" onClick={() => setVisible((v) => !v)}>
        {visible ? "Hide QR code" : "Show as QR code"}
      </Button>
      {visible && (
        <div className="mt-3 inline-flex flex-col items-center gap-2 bg-raised border border-line rounded-md p-4">
          <canvas ref={canvasRef} className="rounded" />
          <p className="font-mono text-[10px] text-muted max-w-[176px] text-center">
            Generated locally — scan with a phone camera, don&rsquo;t screenshot or share
          </p>
        </div>
      )}
    </div>
  );
}

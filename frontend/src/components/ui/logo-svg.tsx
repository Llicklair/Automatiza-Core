"use client";

const LOGO_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f172a"/>
      <stop offset="100%" style="stop-color:#1e293b"/>
    </linearGradient>
    <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#3b82f6"/>
      <stop offset="100%" style="stop-color:#8b5cf6"/>
    </linearGradient>
    <linearGradient id="g2" x1="100%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#60a5fa"/>
      <stop offset="100%" style="stop-color:#a78bfa"/>
    </linearGradient>
    <linearGradient id="g3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#60a5fa"/>
      <stop offset="50%" style="stop-color:#818cf8"/>
      <stop offset="100%" style="stop-color:#a78bfa"/>
    </linearGradient>
    <radialGradient id="aura" cx="50%" cy="50%" r="45%">
      <stop offset="0%" style="stop-color:#818cf8;stop-opacity:0.2"/>
      <stop offset="100%" style="stop-color:#818cf8;stop-opacity:0"/>
    </radialGradient>
    <radialGradient id="topAura" cx="50%" cy="0%" r="60%">
      <stop offset="0%" style="stop-color:#60a5fa;stop-opacity:0.12"/>
      <stop offset="100%" style="stop-color:#60a5fa;stop-opacity:0"/>
    </radialGradient>
    <filter id="gl"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <filter id="gl2"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <filter id="sm"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>
  <rect width="512" height="512" rx="96" ry="96" fill="url(#bgGrad)"/>
  <circle cx="256" cy="256" r="190" fill="url(#aura)"/>
  <circle cx="256" cy="150" r="120" fill="url(#topAura)"/>
  <g filter="url(#gl)">
    <line x1="148" y1="370" x2="256" y2="110" stroke="url(#g1)" stroke-width="8" stroke-linecap="round" opacity="0.9"/>
    <line x1="364" y1="370" x2="256" y2="110" stroke="url(#g1)" stroke-width="8" stroke-linecap="round" opacity="0.9"/>
  </g>
  <g filter="url(#sm)"><ellipse cx="256" cy="256" rx="155" ry="52" fill="none" stroke="url(#g2)" stroke-width="3.5" opacity="0.8"/></g>
  <g filter="url(#sm)"><ellipse cx="256" cy="256" rx="140" ry="50" fill="none" stroke="url(#g2)" stroke-width="2.5" opacity="0.45" transform="rotate(60 256 256)"/></g>
  <g filter="url(#sm)"><ellipse cx="256" cy="256" rx="140" ry="50" fill="none" stroke="url(#g2)" stroke-width="2.5" opacity="0.45" transform="rotate(-60 256 256)"/></g>
  <g filter="url(#gl2)"><circle cx="256" cy="256" r="24" fill="url(#g3)"/></g>
  <circle cx="251" cy="250" r="9" fill="white" opacity="0.1"/>
  <circle cx="256" cy="256" r="5" fill="white" opacity="0.25"/>
  <g filter="url(#gl2)"><circle cx="256" cy="110" r="14" fill="url(#g3)"/></g>
  <circle cx="254" cy="107" r="5" fill="white" opacity="0.12"/>
  <circle cx="256" cy="110" r="3" fill="white" opacity="0.25"/>
  <line x1="256" y1="124" x2="256" y2="232" stroke="url(#g2)" stroke-width="1.5" opacity="0.25" stroke-dasharray="5 4"/>
  <g filter="url(#sm)"><circle cx="105" cy="238" r="9" fill="#3b82f6" opacity="0.9"/><circle cx="105" cy="238" r="4" fill="white" opacity="0.3"/></g>
  <g filter="url(#sm)"><circle cx="407" cy="270" r="9" fill="#a78bfa" opacity="0.9"/><circle cx="407" cy="270" r="4" fill="white" opacity="0.3"/></g>
  <g filter="url(#sm)"><circle cx="168" cy="148" r="8" fill="#818cf8" opacity="0.85"/><circle cx="168" cy="148" r="3.5" fill="white" opacity="0.25"/></g>
  <g filter="url(#sm)"><circle cx="348" cy="150" r="8" fill="#6366f1" opacity="0.85"/><circle cx="348" cy="150" r="3.5" fill="white" opacity="0.25"/></g>
  <g filter="url(#sm)"><circle cx="178" cy="365" r="8" fill="#7c3aed" opacity="0.85"/><circle cx="178" cy="365" r="3.5" fill="white" opacity="0.25"/></g>
  <g filter="url(#sm)"><circle cx="338" cy="362" r="8" fill="#4f46e5" opacity="0.85"/><circle cx="338" cy="362" r="3.5" fill="white" opacity="0.25"/></g>
  <g filter="url(#sm)"><circle cx="256" cy="308" r="7" fill="#60a5fa" opacity="0.75"/><circle cx="256" cy="308" r="3" fill="white" opacity="0.2"/></g>
  <g filter="url(#sm)"><circle cx="148" cy="370" r="5" fill="#3b82f6" opacity="0.45"/><circle cx="364" cy="370" r="5" fill="#8b5cf6" opacity="0.45"/></g>
  <circle cx="88" cy="130" r="1.5" fill="#60a5fa" opacity="0.2"/>
  <circle cx="430" cy="125" r="1.5" fill="#a78bfa" opacity="0.18"/>
  <circle cx="80" cy="430" r="1.2" fill="#818cf8" opacity="0.15"/>
  <circle cx="435" cy="435" r="1.2" fill="#6366f1" opacity="0.15"/>
</svg>`;

/**
 * Logo de AutomatizaCore inline.
 *
 * Por qué inline en vez de /logo.svg con next/image: la app desktop (Electron)
 * sirve el frontend via file://, donde las rutas absolutas como /logo.svg se
 * resuelven a la raíz del filesystem y dan 404. Inlinear el SVG evita el
 * problema en cualquier protocolo.
 */
export function LogoSvg({
  className,
  size = 56,
  ariaLabel = "AutomatizaCore",
}: {
  className?: string;
  size?: number;
  ariaLabel?: string;
}) {
  return (
    <div
      role="img"
      aria-label={ariaLabel}
      className={className}
      style={{ width: size, height: size, display: "inline-block" }}
      dangerouslySetInnerHTML={{ __html: LOGO_SVG }}
    />
  );
}

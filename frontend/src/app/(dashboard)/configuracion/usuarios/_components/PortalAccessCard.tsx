"use client";

import { useState } from "react";
import { Wifi, WifiOff, Copy, Check, Smartphone } from "lucide-react";

import type { LanAccess } from "../_hooks/useLanAccess";

/**
 * Tarjeta que muestra la URL para que los empleados accedan a su portal desde
 * el móvil dentro de la red de la oficina (misma Wi-Fi). El enlace `localhost`
 * NO sirve desde otro dispositivo; aquí se ofrece la URL por IP de LAN y, como
 * alternativa estable, por nombre de equipo.
 */
function CopyRow({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* noop */
    }
  }
  return (
    <div>
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <div className="flex items-center gap-2">
        <input
          type="text"
          readOnly
          value={value}
          onClick={(e) => e.currentTarget.select()}
          className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 font-mono text-xs text-foreground outline-none"
        />
        <button
          type="button"
          onClick={copy}
          className="shrink-0 inline-flex items-center gap-1.5 rounded-xl border border-border bg-card px-3 py-2.5 text-xs hover:bg-accent transition-colors"
        >
          {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          {copied ? "Copiado" : "Copiar"}
        </button>
      </div>
    </div>
  );
}

export default function PortalAccessCard({ lan }: { lan: LanAccess }) {
  // En navegador (no escritorio) no hay info de red local; no mostramos nada.
  if (!lan.isDesktop) return null;

  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <div className="flex items-start gap-3">
        <Smartphone className="w-5 h-5 text-primary mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-foreground">Acceso de empleados desde el móvil</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            En la red de la oficina (mismo Wi-Fi), tus empleados entran a su portal con esta dirección.
            El enlace <code className="font-mono">localhost</code> solo funciona en este ordenador.
          </p>

          {!lan.enabled && (
            <div className="mt-3 flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
              <WifiOff className="w-4 h-4 shrink-0" />
              <span>
                La <strong>Red local</strong> está desactivada. Actívala en <strong>Escáner → Red local</strong> para que
                los móviles puedan conectar.
              </span>
            </div>
          )}

          {lan.enabled && !lan.lanBase && (
            <div className="mt-3 flex items-center gap-2 rounded-lg border border-border bg-muted px-3 py-2 text-xs text-muted-foreground">
              <WifiOff className="w-4 h-4 shrink-0" />
              <span>No se detecta una IP de red local. Conecta este equipo a la Wi-Fi de la oficina.</span>
            </div>
          )}

          {lan.enabled && lan.lanBase && (
            <div className="mt-3 space-y-3">
              <div className="flex items-center gap-2 text-xs text-emerald-400">
                <Wifi className="w-4 h-4" />
                <span>Red local activa</span>
              </div>
              <CopyRow label="Enlace para los empleados (por IP)" value={lan.lanBase} />
              {lan.lanHostBase && (
                <CopyRow
                  label="Alternativa estable (por nombre de equipo, aguanta cambios de IP)"
                  value={lan.lanHostBase}
                />
              )}
              <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-1">
                <li>El móvil debe estar en la <strong>misma Wi-Fi</strong> y este ordenador encendido con la app abierta.</li>
                <li>La primera vez, permite los puertos <strong>3000 y 8080</strong> en el firewall de Windows.</li>
                <li>Para que la IP no cambie, pide al router una <strong>IP reservada</strong> para este equipo.</li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

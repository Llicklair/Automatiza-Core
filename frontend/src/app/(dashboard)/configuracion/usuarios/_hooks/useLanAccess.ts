"use client";

import { useEffect, useState } from "react";

/**
 * Acceso desde la red local (oficina) para que los empleados entren al portal
 * desde su móvil. La info de red la provee el contenedor de escritorio
 * (Electron) por IPC; en modo web (navegador) no está disponible.
 *
 * La IP se lee EN VIVO cada vez que se monta, así que el host siempre muestra
 * la IP actual aunque DHCP la haya cambiado. `lanHostBase` (por nombre de
 * equipo) es una alternativa estable que sobrevive a cambios de IP si la red
 * soporta mDNS/NetBIOS.
 */
type NetUrls = { local?: string; lan?: string; lanHost?: string; hostname?: string };
type NetStatus = { localNetworkEnabled: boolean; lanIP: string; urls?: NetUrls };

function getElectronAPI() {
  if (typeof window === "undefined") return null;
  return (
    window as unknown as {
      electronAPI?: { getNetworkStatus?: () => Promise<NetStatus> };
    }
  ).electronAPI ?? null;
}

export interface LanAccess {
  isDesktop: boolean;        // corre dentro de la app de escritorio
  enabled: boolean;          // toggle "Red local" activo (backend en 0.0.0.0)
  lanIP: string | null;      // 192.168.x.x (null si no hay LAN o es loopback)
  lanBase: string | null;    // http://192.168.x.x:3000
  lanHostBase: string | null;// http://NOMBRE-PC:3000 (estable ante cambios de IP)
}

export function useLanAccess(): LanAccess {
  const [net, setNet] = useState<NetStatus | null>(null);
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const api = getElectronAPI();
    setIsDesktop(!!api?.getNetworkStatus);
    if (!api?.getNetworkStatus) return;
    void api.getNetworkStatus().then(setNet).catch(() => {});
  }, []);

  const lanIP = net?.lanIP && net.lanIP !== "127.0.0.1" ? net.lanIP : null;
  const lanBase = lanIP ? (net?.urls?.lan ?? `http://${lanIP}:3000`) : null;
  const lanHostBase = net?.urls?.lanHost ?? null;

  return {
    isDesktop,
    enabled: !!net?.localNetworkEnabled,
    lanIP,
    lanBase,
    lanHostBase,
  };
}

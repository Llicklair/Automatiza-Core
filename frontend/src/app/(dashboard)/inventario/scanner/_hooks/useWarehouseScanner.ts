"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";

export function useWarehouseScanner() {
    const t = useTranslations("inventario");
    const [token, setToken] = useState<{ token: string; expires_at: string; scope: string } | null>(null);
    const [loading, setLoading] = useState(false);
    const [copied, setCopied] = useState(false);
    const [timeLeft, setTimeLeft] = useState(0);
    // Origen alcanzable desde el móvil: la IP de LAN del equipo (no `localhost`,
    // que el teléfono no puede resolver). La pide al proceso Electron.
    const [lanOrigin, setLanOrigin] = useState<string | null>(null);
    // Override de URL pública (p.ej. túnel Cloudflare): certificado de confianza
    // real → la cámara del móvil funciona sin instalar nada. Tiene prioridad.
    const [publicBase, setPublicBaseState] = useState<string>(() => {
        if (typeof window === "undefined") return "";
        try {
            return window.localStorage.getItem("automatiza.tpv.publicBase") || "";
        } catch {
            return "";
        }
    });
    const setPublicBase = (v: string) => {
        const clean = v.trim().replace(/\/+$/, "");
        setPublicBaseState(clean);
        try {
            window.localStorage.setItem("automatiza.tpv.publicBase", clean);
        } catch {
            /* modo privado */
        }
    };
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    useEffect(() => {
        const electron = window.electronAPI;
        if (!electron?.getNetworkStatus) return;
        electron
            .getNetworkStatus()
            .then((st) => {
                // Preferimos HTTPS (habilita la cámara del móvil); si no, http LAN.
                if (st?.httpsUrl) setLanOrigin(st.httpsUrl);
                else if (st?.lanIP)
                    setLanOrigin(`http://${st.lanIP}:${window.location.port || "3000"}`);
            })
            .catch(() => {});
    }, []);

    const generateToken = async () => {
        setLoading(true);
        try {
            const data = await api.scanner.generateQR();
            setToken(data);
        } catch (e: any) {
            useToastStore.getState().error(e?.message || t("scanner.tokenError"));
        }
        setLoading(false);
    };

    useEffect(() => {
        if (!token) return;
        const updateTimer = () => {
            const exp = new Date(token.expires_at).getTime();
            const now = Date.now();
            const remaining = Math.max(0, Math.floor((exp - now) / 1000));
            setTimeLeft(remaining);
            if (remaining <= 0 && intervalRef.current) {
                clearInterval(intervalRef.current);
                setToken(null);
            }
        };
        updateTimer();
        intervalRef.current = setInterval(updateTimer, 1000);
        return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
    }, [token]);

    const copyToken = () => {
        if (!token) return;
        navigator.clipboard.writeText(token.token);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const scannerUrl = token
        ? `${publicBase || lanOrigin || window.location.origin}/mobile-scanner?token=${token.token}`
        : null;

    return {
        token,
        loading,
        copied,
        timeLeft,
        scannerUrl,
        generateToken,
        copyToken,
        publicBase,
        setPublicBase,
    };
}

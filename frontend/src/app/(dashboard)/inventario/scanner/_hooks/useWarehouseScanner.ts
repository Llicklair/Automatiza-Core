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
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
        ? `${window.location.origin}/mobile-scanner?token=${token.token}`
        : null;

    return { token, loading, copied, timeLeft, scannerUrl, generateToken, copyToken };
}

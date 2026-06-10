"use client";

import { useEffect, useState, useCallback } from "react";
import { api, IntegrationStatus } from "@/lib/api";
import type { EmailConnectInput } from "@/lib/api/integrations";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

export function useIntegraciones() {
    const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
    const [loading, setLoading] = useState(true);
    const [feedback, setFeedback] = useState<{ type: "success" | "error"; msg: string } | null>(null);

    const [psd2Id, setPsd2Id] = useState("");
    const [psd2Key, setPsd2Key] = useState("");
    const [connectingPsd2, setConnectingPsd2] = useState(false);
    const [disconnectingPsd2, setDisconnectingPsd2] = useState(false);

    const [connectingGoogle, setConnectingGoogle] = useState(false);
    const [connectingMicrosoft, setConnectingMicrosoft] = useState(false);

    const [connectingEmail, setConnectingEmail] = useState(false);
    const [disconnectingEmail, setDisconnectingEmail] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.integrations.list();
            setIntegrations(data);
        } catch (err) {
            logError("integraciones/page", err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const connected = params.get("connected");
        if (connected) {
            setFeedback({ type: "success", msg: `${connected === "google" ? "Google" : "Microsoft"} conectado correctamente` });
            window.history.replaceState({}, "", "/integraciones");
            load();
        }
    }, [load]);

    const getStatus = (type: string) => integrations.find(i => i.integration_type === type);
    const isConnected = (type: string) => getStatus(type)?.is_active ?? false;

    async function connectPsd2(e: React.FormEvent) {
        e.preventDefault();
        setConnectingPsd2(true); setFeedback(null);
        try {
            await api.integrations.connectPsd2(psd2Id, psd2Key);
            setFeedback({ type: "success", msg: "Banco (PSD2) conectado correctamente" });
            setPsd2Id(""); setPsd2Key("");
            load();
        } catch (err: unknown) {
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error desconocido" });
        } finally {
            setConnectingPsd2(false);
        }
    }

    async function disconnectPsd2() {
        if (!await showConfirm({ message: "¿Desconectar tu Banco?", confirmLabel: "Desconectar", confirmVariant: "danger" })) return;
        setDisconnectingPsd2(true); setFeedback(null);
        try {
            await api.integrations.disconnectPsd2();
            setFeedback({ type: "success", msg: "Banco desconectado" });
            load();
        } catch (err: unknown) {
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error" });
        } finally {
            setDisconnectingPsd2(false);
        }
    }

    async function connectOAuth(provider: "google" | "microsoft") {
        const setConnecting = provider === "google" ? setConnectingGoogle : setConnectingMicrosoft;
        const statusCheck = provider === "google" ? "gmail" : "outlook";
        setConnecting(true); setFeedback(null);
        try {
            const data = await api.integrations.oauthUrl(provider);
            window.open(data.auth_url, "_blank");
            let attempts = 0;
            const poll = setInterval(async () => {
                attempts++;
                try {
                    const list = await api.integrations.list();
                    const connected = list.some(i => i.integration_type === statusCheck && i.is_active);
                    if (connected) {
                        clearInterval(poll);
                        setConnecting(false);
                        setFeedback({ type: "success", msg: `${provider === "google" ? "Google" : "Microsoft"} conectado correctamente` });
                        load();
                    }
                } catch { /* polling OAuth: errores transitorios esperados, reintenta en 2s */ }
                if (attempts >= 60) {
                    clearInterval(poll);
                    setConnecting(false);
                }
            }, 2000);
        } catch (err: unknown) {
            setConnecting(false);
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error" });
        }
    }

    async function disconnectIntegration(type: string, label: string) {
        if (!await showConfirm({ message: `¿Desconectar ${label}?`, confirmLabel: "Desconectar", confirmVariant: "danger" })) return;
        setFeedback(null);
        try {
            await api.integrations.disconnect(type);
            setFeedback({ type: "success", msg: `${label} desconectado` });
            load();
        } catch (err: unknown) {
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error" });
        }
    }

    async function connectEmail(payload: EmailConnectInput) {
        setConnectingEmail(true); setFeedback(null);
        try {
            await api.integrations.connectEmail(payload);
            setFeedback({ type: "success", msg: "Correo IMAP/SMTP conectado correctamente" });
            load();
            return true;
        } catch (err: unknown) {
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error desconocido" });
            return false;
        } finally {
            setConnectingEmail(false);
        }
    }

    async function disconnectEmail() {
        if (!await showConfirm({ message: "¿Desconectar tu correo IMAP/SMTP?", confirmLabel: "Desconectar", confirmVariant: "danger" })) return;
        setDisconnectingEmail(true); setFeedback(null);
        try {
            await api.integrations.disconnectEmail();
            setFeedback({ type: "success", msg: "Correo IMAP/SMTP desconectado" });
            load();
        } catch (err: unknown) {
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error" });
        } finally {
            setDisconnectingEmail(false);
        }
    }

    return {
        integrations, loading, feedback,
        psd2Id, setPsd2Id, psd2Key, setPsd2Key,
        connectingPsd2, disconnectingPsd2,
        connectingGoogle, connectingMicrosoft,
        connectingEmail, disconnectingEmail,
        getStatus, isConnected,
        connectPsd2, disconnectPsd2, connectOAuth, disconnectIntegration,
        connectEmail, disconnectEmail,
    };
}

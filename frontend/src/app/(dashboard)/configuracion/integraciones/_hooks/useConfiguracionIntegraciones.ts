"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { TelegramStatus } from "@/lib/api/messaging";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

export function useConfiguracionIntegraciones() {
    const show = useToastStore((s) => s.show);

    const [tgStatus, setTgStatus] = useState<TelegramStatus | null>(null);
    const [tgLoading, setTgLoading] = useState(false);
    const [linkUrl, setLinkUrl] = useState<string | null>(null);

    const loadTelegram = useCallback(async () => {
        try {
            const st = await api.messaging.telegram.status();
            setTgStatus(st);
        } catch {
            setTgStatus(null);
        }
    }, []);

    useEffect(() => {
        loadTelegram();
    }, [loadTelegram]);

    const handleTelegramConnect = async () => {
        setTgLoading(true);
        try {
            const res = await api.messaging.telegram.connect();
            setLinkUrl(res.link_url);
            show("Token generado. Abre el enlace en Telegram para vincular.", "success");
            let attempts = 0;
            const poll = setInterval(async () => {
                attempts++;
                const st = await api.messaging.telegram.status();
                if (st.connected) {
                    clearInterval(poll);
                    setTgStatus(st);
                    setLinkUrl(null);
                    show("Telegram vinculado correctamente", "success");
                }
                if (attempts > 20) clearInterval(poll);
            }, 3000);
        } catch (e: any) {
            show(e.message || "Error conectando Telegram", "error");
        } finally {
            setTgLoading(false);
        }
    };

    const handleTelegramDisconnect = async () => {
        if (!(await showConfirm({
            message: "¿Desconectar Telegram? El chat dejará de recibir respuestas.",
            confirmLabel: "Desconectar",
            confirmVariant: "danger",
        }))) return;
        setTgLoading(true);
        try {
            await api.messaging.telegram.disconnect();
            setTgStatus({ connected: false, chat_id: null, username: null });
            show("Telegram desconectado", "success");
        } catch (e: any) {
            show(e.message || "Error desconectando", "error");
        } finally {
            setTgLoading(false);
        }
    };

    return {
        tgStatus,
        tgLoading,
        linkUrl,
        handleTelegramConnect,
        handleTelegramDisconnect,
    };
}

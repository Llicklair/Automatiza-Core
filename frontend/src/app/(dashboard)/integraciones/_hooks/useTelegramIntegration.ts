"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { TelegramStatus } from "@/lib/api/messaging";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

export function useTelegramIntegration() {
    // Claves i18n heredadas de la antigua página Configuración → Mensajería
    // (fusionada en /integraciones el 2026-07-02).
    const t = useTranslations("configuracion");
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

    // El poll de vinculación se cancela al desmontar: sin esto seguía pidiendo
    // el estado cada 3s hasta un minuto después de salir de la página.
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    useEffect(
        () => () => {
            if (pollRef.current) clearInterval(pollRef.current);
        },
        [],
    );

    const handleTelegramConnect = async () => {
        setTgLoading(true);
        try {
            const res = await api.messaging.telegram.connect();
            setLinkUrl(res.link_url);
            show(t("integraciones.tokenGenerated"), "success");
            if (pollRef.current) clearInterval(pollRef.current);
            let attempts = 0;
            pollRef.current = setInterval(async () => {
                attempts++;
                const st = await api.messaging.telegram.status();
                if (st.connected) {
                    if (pollRef.current) clearInterval(pollRef.current);
                    setTgStatus(st);
                    setLinkUrl(null);
                    show(t("integraciones.telegramLinked"), "success");
                }
                if (attempts > 20 && pollRef.current) clearInterval(pollRef.current);
            }, 3000);
        } catch (e: any) {
            show(e.message || t("integraciones.connectError"), "error");
        } finally {
            setTgLoading(false);
        }
    };

    const handleTelegramDisconnect = async () => {
        if (!(await showConfirm({
            message: t("integraciones.disconnectConfirm"),
            confirmLabel: t("integraciones.disconnect"),
            confirmVariant: "danger",
        }))) return;
        setTgLoading(true);
        try {
            await api.messaging.telegram.disconnect();
            setTgStatus({ connected: false, chat_id: null, username: null });
            show(t("integraciones.telegramDisconnected"), "success");
        } catch (e: any) {
            show(e.message || t("integraciones.disconnectError"), "error");
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

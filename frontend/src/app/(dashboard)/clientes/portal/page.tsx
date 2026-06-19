"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Copy, Link2, ShieldOff, Loader2, ExternalLink, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import type { Client } from "@/lib/api/erp";
import { clientPortalAdmin } from "@/lib/api/client_portal";
import type { PortalTokenStatus } from "@/lib/api/client_portal";
import { PageHeader } from "@/components/shared";
import { showConfirm } from "@/stores/confirm";
import { useToastStore } from "@/stores/toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";

const fmtDate = (d: string | null) =>
    d ? new Date(d).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" }) : "—";

function PortalStatusBadge({ status }: { status: PortalTokenStatus | undefined | null }) {
    const t = useTranslations("clientes");
    if (status === undefined)
        return <span className="text-xs text-muted-foreground">…</span>;
    if (!status?.has_token)
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-muted/40 text-muted-foreground">{t("portal.statusNoAccess")}</span>;
    const isExpired = status.expires_at && new Date(status.expires_at) < new Date();
    if (isExpired)
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-red-500/10 text-red-400">{t("portal.statusExpired")}</span>;
    return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-emerald-500/10 text-emerald-400">{t("portal.statusActive")}</span>;
}

export default function PortalClientesPage() {
    const t = useTranslations("clientes");
    const toast = useToastStore();
    const [clients, setClients] = useState<Client[]>([]);
    const [statuses, setStatuses] = useState<Record<string, PortalTokenStatus | null>>({});
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [generating, setGenerating] = useState<string | null>(null);
    const [revoking, setRevoking] = useState<string | null>(null);
    const [generatedUrl, setGeneratedUrl] = useState<string | null>(null);
    const [generatedUrlIsLocal, setGeneratedUrlIsLocal] = useState(false);
    const [copied, setCopied] = useState(false);

    const loadStatuses = useCallback(async (clientList: Client[]) => {
        const results = await Promise.allSettled(
            clientList.map((c) => clientPortalAdmin.getTokenStatus(c.id))
        );
        const map: Record<string, PortalTokenStatus | null> = {};
        results.forEach((r, i) => {
            map[clientList[i].id] = r.status === "fulfilled" ? r.value : null;
        });
        setStatuses(map);
    }, []);

    useEffect(() => {
        (async () => {
            try {
                const list = await api.erp.clients.list();
                setClients(list);
                await loadStatuses(list);
            } finally {
                setLoading(false);
            }
        })();
    }, [loadStatuses]);

    const isUrlLocalOnly = (url: string) => {
        try {
            const { hostname } = new URL(url);
            return (
                hostname === "localhost" ||
                hostname === "127.0.0.1" ||
                hostname === "::1" ||
                hostname.endsWith(".local")
            );
        } catch {
            return true;
        }
    };

    const handleGenerate = async (client: Client) => {
        const current = statuses[client.id];
        const hasActive =
            current?.has_token && current.expires_at && new Date(current.expires_at) > new Date();
        if (hasActive) {
            const ok = await showConfirm({
                title: t("portal.regenerateTitle"),
                message: t("portal.regenerateMessage"),
                confirmLabel: t("portal.regenerate"),
                confirmVariant: "warning",
            });
            if (!ok) return;
        }

        setGenerating(client.id);
        try {
            const res = await clientPortalAdmin.generateToken(client.id);
            // El backend devuelve portal_url si PORTAL_PUBLIC_URL está configurada.
            // Si no, caemos a window.location.origin (que solo sirve si admin y cliente
            // comparten red/máquina — útil para piloto local, no para producción).
            const url =
                res.portal_url ??
                `${window.location.origin}/portal-cliente?token=${res.raw_token}`;
            setGeneratedUrl(url);
            setGeneratedUrlIsLocal(isUrlLocalOnly(url));
            const updated = await clientPortalAdmin.getTokenStatus(client.id);
            setStatuses((prev) => ({ ...prev, [client.id]: updated }));
        } catch {
            toast.error(t("portal.errorGenerate"));
        } finally {
            setGenerating(null);
        }
    };

    const handleRevoke = async (clientId: string) => {
        if (!(await showConfirm({
            message: t("portal.revokeMessage"),
            confirmLabel: t("portal.revoke"),
            confirmVariant: "danger",
        }))) return;
        setRevoking(clientId);
        try {
            await clientPortalAdmin.revokeToken(clientId);
            setStatuses((prev) => ({
                ...prev,
                [clientId]: { has_token: false, expires_at: null, created_at: null, last_used_at: null },
            }));
        } catch {
            toast.error(t("portal.errorRevoke"));
        } finally {
            setRevoking(null);
        }
    };

    const handleCopy = async (url: string) => {
        await navigator.clipboard.writeText(url);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const filtered = clients.filter(
        (c) =>
            c.name.toLowerCase().includes(search.toLowerCase()) ||
            (c.email ?? "").toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6">
            <PageHeader
                title={t("portal.title")}
                description={t("portal.description")}
            />

            <Input
                placeholder={t("portal.searchPlaceholder")}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="max-w-xs"
            />

            {loading ? (
                <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">{t("portal.loading")}</span>
                </div>
            ) : (
                <div className="rounded-xl border bg-card overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b text-muted-foreground text-xs uppercase tracking-wide">
                                <th className="px-4 py-3 text-left">{t("typeClient")}</th>
                                <th className="px-4 py-3 text-left">{t("emailColumn")}</th>
                                <th className="px-4 py-3 text-center">{t("portal.statusColumn")}</th>
                                <th className="px-4 py-3 text-left">{t("portal.expiresColumn")}</th>
                                <th className="px-4 py-3 text-left">{t("portal.lastAccessColumn")}</th>
                                <th className="px-4 py-3 text-right">{t("portal.actionsColumn")}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y">
                            {filtered.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="px-4 py-10 text-center text-muted-foreground text-sm">
                                        {t("portal.empty")}
                                    </td>
                                </tr>
                            )}
                            {filtered.map((client) => {
                                const st = statuses[client.id];
                                const hasActive =
                                    st?.has_token && st.expires_at && new Date(st.expires_at) > new Date();
                                return (
                                    <tr key={client.id} className="hover:bg-muted/30">
                                        <td className="px-4 py-3 font-medium">{client.name}</td>
                                        <td className="px-4 py-3 text-muted-foreground">{client.email ?? "—"}</td>
                                        <td className="px-4 py-3 text-center">
                                            <PortalStatusBadge status={st} />
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">
                                            {st?.has_token ? fmtDate(st.expires_at) : "—"}
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">
                                            {st?.last_used_at ? fmtDate(st.last_used_at) : t("portal.never")}
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                <Button
                                                    size="sm"
                                                    variant={hasActive ? "outline" : "default"}
                                                    onClick={() => handleGenerate(client)}
                                                    disabled={generating === client.id}
                                                    className="h-7 text-xs gap-1"
                                                >
                                                    {generating === client.id
                                                        ? <Loader2 className="w-3 h-3 animate-spin" />
                                                        : <Link2 className="w-3 h-3" />}
                                                    {hasActive ? t("portal.regenerate") : t("portal.generateLink")}
                                                </Button>
                                                {hasActive && (
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => handleRevoke(client.id)}
                                                        disabled={revoking === client.id}
                                                        className="h-7 text-xs text-destructive hover:text-destructive gap-1"
                                                    >
                                                        {revoking === client.id
                                                            ? <Loader2 className="w-3 h-3 animate-spin" />
                                                            : <ShieldOff className="w-3 h-3" />}
                                                        {t("portal.revoke")}
                                                    </Button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            <Dialog open={!!generatedUrl} onOpenChange={() => { setGeneratedUrl(null); setCopied(false); setGeneratedUrlIsLocal(false); }}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>{t("portal.linkGeneratedTitle")}</DialogTitle>
                    </DialogHeader>
                    <p className="text-sm text-muted-foreground">
                        {t("portal.shareLink")}
                    </p>
                    {generatedUrlIsLocal && (
                        <div className="flex gap-2 p-3 rounded-lg border border-amber-500/40 bg-amber-500/10 text-xs text-amber-200">
                            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-400" />
                            <div className="space-y-1">
                                <p className="font-medium">{t("portal.localOnlyWarning")}</p>
                                <p className="text-amber-200/80">
                                    {t("portal.configureBefore")}{" "}
                                    <code className="px-1 rounded bg-amber-500/20">PORTAL_PUBLIC_URL</code>{" "}
                                    {t("portal.configureMiddle")} <code className="px-1 rounded bg-amber-500/20">.env</code>{" "}
                                    {t("portal.configureAfter")}
                                </p>
                            </div>
                        </div>
                    )}
                    <div className="p-3 rounded-lg bg-muted/50 font-mono text-xs break-all">
                        {generatedUrl}
                    </div>
                    <div className="flex gap-2 justify-end">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => window.open(generatedUrl!, "_blank")}
                            className="gap-1.5"
                        >
                            <ExternalLink className="w-3.5 h-3.5" /> {t("portal.open")}
                        </Button>
                        <Button
                            size="sm"
                            onClick={() => handleCopy(generatedUrl!)}
                            className="gap-1.5"
                        >
                            <Copy className="w-3.5 h-3.5" />
                            {copied ? t("portal.copied") : t("portal.copyLink")}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}

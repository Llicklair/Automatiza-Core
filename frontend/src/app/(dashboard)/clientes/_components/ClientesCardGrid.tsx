"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Client } from "@/lib/api";

import { StatusBadge } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Building2, Eye, Pencil, Trash2, Mail, Phone } from "lucide-react";

import { getInitials, clientHealth, HEALTH_CONFIG, HealthLevel, ClientTypeMap } from "./clientHealth";

interface ClientesCardGridProps {
    clients: Client[];
    deleting: boolean;
    clientTypeMap: ClientTypeMap;
    openClientDrawer: (client: Client) => void;
    openEditClient: (client: Client) => void;
    handleDeleteClient: (client: Client) => void;
}

export function ClientesCardGrid({
    clients,
    deleting,
    clientTypeMap,
    openClientDrawer,
    openEditClient,
    handleDeleteClient,
}: ClientesCardGridProps) {
    const t = useTranslations("clientes");
    const [cardSearch, setCardSearch] = useState("");

    const filteredForCards = useMemo(() => {
        if (!cardSearch.trim()) return clients;
        const q = cardSearch.toLowerCase();
        return clients.filter(c =>
            c.name.toLowerCase().includes(q) ||
            c.email?.toLowerCase().includes(q) ||
            c.nif?.toLowerCase().includes(q)
        );
    }, [clients, cardSearch]);

    return (
        /* ── Card view ────────────────────────────────────────── */
        <div className="space-y-4">
            {/* Search for card mode */}
            <Input
                placeholder={t("searchPlaceholder")}
                value={cardSearch}
                onChange={(e) => setCardSearch(e.target.value)}
                className="max-w-sm"
            />

            {/* Health legend */}
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                {(Object.entries(HEALTH_CONFIG) as [HealthLevel, typeof HEALTH_CONFIG[HealthLevel]][]).map(([, cfg]) => (
                    <div key={cfg.label} className="flex items-center gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                        {cfg.label}
                    </div>
                ))}
            </div>

            {filteredForCards.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">{t("noMatchFilter")}</p>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {filteredForCards.map((client) => {
                        const h = clientHealth(client);
                        const cfg = HEALTH_CONFIG[h];
                        const ct = clientTypeMap[client.client_type];
                        return (
                            <div
                                key={client.id}
                                className="bg-card border border-border rounded-2xl p-5 flex flex-col gap-3 hover:border-primary/30 transition-colors group"
                            >
                                {/* Top row */}
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex items-center gap-3 min-w-0">
                                        <div className={`relative shrink-0 w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 ring-2 ${cfg.ring} flex items-center justify-center`}>
                                            {client.client_type === "company" || client.client_type === "supplier"
                                                ? <Building2 className="h-4 w-4 text-primary" />
                                                : <span className="text-xs font-bold text-primary">{getInitials(client.name)}</span>
                                            }
                                            <span className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-card ${cfg.dot}`} title={cfg.label} />
                                        </div>
                                        <div className="min-w-0">
                                            <p className="text-sm font-semibold text-foreground truncate">{client.name}</p>
                                            {client.city && <p className="text-xs text-muted-foreground truncate">{client.city}</p>}
                                        </div>
                                    </div>
                                    {ct && <StatusBadge status={client.client_type} label={ct.label} />}
                                </div>

                                {/* Contact info */}
                                <div className="space-y-1.5 min-h-[40px]">
                                    {client.email ? (
                                        <div className="flex items-center gap-2 text-xs text-muted-foreground truncate">
                                            <Mail className="h-3 w-3 shrink-0" />
                                            <span className="truncate">{client.email}</span>
                                        </div>
                                    ) : null}
                                    {client.phone ? (
                                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                            <Phone className="h-3 w-3 shrink-0" />
                                            <span>{client.phone}</span>
                                        </div>
                                    ) : null}
                                    {!client.email && !client.phone && (
                                        <p className="text-xs text-red-400/70 italic">Sin datos de contacto</p>
                                    )}
                                </div>

                                {/* NIF */}
                                {client.nif && (
                                    <span className="text-xs font-mono bg-muted border border-border text-muted-foreground px-2 py-0.5 rounded w-fit">
                                        {client.nif}
                                    </span>
                                )}

                                {/* Actions */}
                                <div className="flex items-center gap-1 pt-1 border-t border-border mt-auto">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="flex-1 text-xs h-7"
                                        onClick={() => openClientDrawer(client)}
                                    >
                                        <Eye className="h-3 w-3 mr-1" />
                                        {t("view")}
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-7 w-7 text-muted-foreground hover:text-foreground"
                                        onClick={() => openEditClient(client)}
                                    >
                                        <Pencil className="h-3 w-3" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-7 w-7 text-red-400/60 hover:text-red-400 hover:bg-red-500/10"
                                        onClick={() => handleDeleteClient(client)}
                                        disabled={deleting}
                                    >
                                        <Trash2 className="h-3 w-3" />
                                    </Button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

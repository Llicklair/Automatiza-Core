"use client";

import { useTranslations } from "next-intl";
import { Trash2 } from "lucide-react";

import type { Invitation } from "@/lib/api";

import { roleLabels } from "../roles";

export default function PendingInvitationsTable({
    invitations,
    busyId,
    onRevoke,
}: {
    invitations: Invitation[];
    busyId: string | null;
    onRevoke: (inv: Invitation) => void;
}) {
    const t = useTranslations("configuracion");
    const roleLabel = roleLabels(t);
    return (
        <section className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("usuarios.pendingInvitations", { count: invitations.length })}
            </h2>
            <div className="bg-card border border-border rounded-2xl overflow-hidden">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
                            <th className="text-left font-medium px-5 py-3">{t("usuarios.email")}</th>
                            <th className="text-left font-medium px-5 py-3">{t("usuarios.role")}</th>
                            <th className="text-left font-medium px-5 py-3">{t("usuarios.expires")}</th>
                            <th className="text-right font-medium px-5 py-3">{t("usuarios.actions")}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {invitations.map((inv) => (
                            <tr key={inv.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                                <td className="px-5 py-3 text-foreground">{inv.email}</td>
                                <td className="px-5 py-3 text-muted-foreground">{roleLabel[inv.role] ?? inv.role}</td>
                                <td className="px-5 py-3 text-muted-foreground text-xs">
                                    {new Date(inv.expires_at).toLocaleString()}
                                </td>
                                <td className="px-5 py-3">
                                    <div className="flex items-center justify-end gap-2">
                                        <button
                                            onClick={() => onRevoke(inv)}
                                            disabled={busyId === inv.id}
                                            title={t("usuarios.revokeAction")}
                                            className="p-1.5 rounded-lg border border-destructive/30 text-destructive hover:bg-destructive/10 disabled:opacity-40"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

"use client";

import { Trash2 } from "lucide-react";

import type { Invitation } from "@/lib/api";

import { ROLE_LABEL } from "../roles";

export default function PendingInvitationsTable({
    invitations,
    busyId,
    onRevoke,
}: {
    invitations: Invitation[];
    busyId: string | null;
    onRevoke: (inv: Invitation) => void;
}) {
    return (
        <section className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Invitaciones pendientes ({invitations.length})
            </h2>
            <div className="bg-card border border-border rounded-2xl overflow-hidden">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
                            <th className="text-left font-medium px-5 py-3">Email</th>
                            <th className="text-left font-medium px-5 py-3">Rol</th>
                            <th className="text-left font-medium px-5 py-3">Caduca</th>
                            <th className="text-right font-medium px-5 py-3">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {invitations.map((inv) => (
                            <tr key={inv.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                                <td className="px-5 py-3 text-foreground">{inv.email}</td>
                                <td className="px-5 py-3 text-muted-foreground">{ROLE_LABEL[inv.role] ?? inv.role}</td>
                                <td className="px-5 py-3 text-muted-foreground text-xs">
                                    {new Date(inv.expires_at).toLocaleString()}
                                </td>
                                <td className="px-5 py-3">
                                    <div className="flex items-center justify-end gap-2">
                                        <button
                                            onClick={() => onRevoke(inv)}
                                            disabled={busyId === inv.id}
                                            title="Revocar"
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

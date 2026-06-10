"use client";

import { useState } from "react";

import { Copy, Check } from "lucide-react";

import type { InvitationCreated } from "@/lib/api";

import { Modal, Field } from "./Modal";

function buildShareUrl(token: string, base?: string | null): string {
    // En la app de escritorio, window.location.origin es localhost (no sirve en
    // el móvil del empleado). Si tenemos la base de LAN, se usa esa.
    const origin = base || (typeof window === "undefined" ? "" : window.location.origin);
    return `${origin}/aceptar-invitacion/${token}`;
}

export default function ShareInvitationModal({
    invitation,
    lanBase,
    onClose,
}: {
    invitation: InvitationCreated;
    lanBase?: string | null;
    onClose: () => void;
}) {
    const [copied, setCopied] = useState(false);
    // Si hay red local, el enlace usa la IP de LAN para que funcione en el móvil
    // del empleado (no localhost, que solo vale en este ordenador).
    const url = buildShareUrl(invitation.token, lanBase);

    async function copy() {
        try {
            await navigator.clipboard.writeText(url);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // Fallback: select the input
        }
    }

    return (
        <Modal title="Enlace de invitación generado" onClose={onClose}>
            <div className="space-y-4">
                <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300">
                    <strong>Importante:</strong> este enlace solo se muestra una vez. Cópialo ahora y envíalo a {invitation.email} por el medio que prefieras.
                </div>

                <Field label="Enlace para compartir">
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            readOnly
                            value={url}
                            onClick={(e) => e.currentTarget.select()}
                            className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 font-mono text-xs text-foreground focus:border-primary/20 outline-none"
                        />
                        <button
                            type="button"
                            onClick={copy}
                            className="flex items-center gap-1 bg-primary text-primary-foreground px-3 py-2.5 rounded-xl text-sm font-medium hover:opacity-90 shrink-0"
                        >
                            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                            {copied ? "Copiado" : "Copiar"}
                        </button>
                    </div>
                </Field>

                <div className="flex items-center justify-end pt-1">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 rounded-xl text-sm bg-muted border border-border text-foreground hover:bg-muted/70"
                    >
                        Hecho
                    </button>
                </div>
            </div>
        </Modal>
    );
}

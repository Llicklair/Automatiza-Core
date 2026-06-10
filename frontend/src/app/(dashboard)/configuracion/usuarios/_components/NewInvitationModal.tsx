"use client";

import { useState } from "react";

import { INVITE_ROLES, ROLE_LABEL } from "../roles";
import { Modal, ModalActions, Field } from "./Modal";

export default function NewInvitationModal({
    onCancel,
    onSubmit,
}: {
    onCancel: () => void;
    onSubmit: (email: string, role: string, ttl_days: number) => Promise<void>;
}) {
    const [email, setEmail] = useState("");
    const [role, setRole] = useState<string>("employee");
    const [ttlDays, setTtlDays] = useState<number>(7);
    const [submitting, setSubmitting] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setSubmitting(true);
        try {
            await onSubmit(email.trim(), role, ttlDays);
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <Modal title="Invitar por email" onClose={onCancel}>
            <p className="text-xs text-muted-foreground -mt-1">
                Genera un enlace de invitación. Tras crearlo te lo mostraremos para que lo copies y lo envíes a la persona como prefieras.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
                <Field label="Email del invitado" required>
                    <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                        placeholder="empleado@empresa.com"
                    />
                </Field>

                <Field label="Rol al aceptar">
                    <select
                        value={role}
                        onChange={(e) => setRole(e.target.value)}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                    >
                        {INVITE_ROLES.map((r) => (
                            <option key={r} value={r}>{ROLE_LABEL[r] ?? r}</option>
                        ))}
                    </select>
                </Field>

                <Field label="Caducidad">
                    <select
                        value={ttlDays}
                        onChange={(e) => setTtlDays(Number(e.target.value))}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                    >
                        <option value={1}>1 día</option>
                        <option value={3}>3 días</option>
                        <option value={7}>7 días (recomendado)</option>
                        <option value={14}>14 días</option>
                        <option value={30}>30 días</option>
                    </select>
                </Field>

                <ModalActions onCancel={onCancel} submitting={submitting} submitLabel="Generar enlace" />
            </form>
        </Modal>
    );
}

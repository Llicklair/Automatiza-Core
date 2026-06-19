"use client";

import { useState } from "react";

import { useTranslations } from "next-intl";

import { INVITE_ROLES, roleLabels } from "../roles";
import { Modal, ModalActions, Field } from "./Modal";

export default function NewInvitationModal({
    onCancel,
    onSubmit,
}: {
    onCancel: () => void;
    onSubmit: (email: string, role: string, ttl_days: number) => Promise<void>;
}) {
    const t = useTranslations("configuracion");
    const roleLabel = roleLabels(t);
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
        <Modal title={t("usuarios.inviteByEmail")} onClose={onCancel}>
            <p className="text-xs text-muted-foreground -mt-1">
                {t("usuarios.inviteHelp")}
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
                <Field label={t("usuarios.inviteeEmail")} required>
                    <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                        placeholder="empleado@empresa.com"
                    />
                </Field>

                <Field label={t("usuarios.roleOnAccept")}>
                    <select
                        value={role}
                        onChange={(e) => setRole(e.target.value)}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                    >
                        {INVITE_ROLES.map((r) => (
                            <option key={r} value={r}>{roleLabel[r] ?? r}</option>
                        ))}
                    </select>
                </Field>

                <Field label={t("usuarios.expiry")}>
                    <select
                        value={ttlDays}
                        onChange={(e) => setTtlDays(Number(e.target.value))}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                    >
                        <option value={1}>{t("usuarios.ttl1")}</option>
                        <option value={3}>{t("usuarios.ttl3")}</option>
                        <option value={7}>{t("usuarios.ttl7")}</option>
                        <option value={14}>{t("usuarios.ttl14")}</option>
                        <option value={30}>{t("usuarios.ttl30")}</option>
                    </select>
                </Field>

                <ModalActions onCancel={onCancel} submitting={submitting} submitLabel={t("usuarios.generateLink")} />
            </form>
        </Modal>
    );
}

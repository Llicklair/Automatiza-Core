"use client";

import { useState } from "react";

import type { UserCreate } from "@/lib/api";

import { USER_ROLES, ROLE_LABEL } from "../roles";
import { Modal, ModalActions, Field } from "./Modal";

export default function NewUserModal({
    onCancel,
    onSubmit,
}: {
    onCancel: () => void;
    onSubmit: (data: UserCreate) => Promise<void>;
}) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [firstName, setFirstName] = useState("");
    const [lastName, setLastName] = useState("");
    const [role, setRole] = useState<string>("user");
    const [submitting, setSubmitting] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setSubmitting(true);
        try {
            await onSubmit({
                email: email.trim(),
                password,
                first_name: firstName.trim() || undefined,
                last_name: lastName.trim() || undefined,
                role,
            });
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <Modal title="Crear usuario con contraseña" onClose={onCancel}>
            <form onSubmit={handleSubmit} className="space-y-4">
                <Field label="Email" required>
                    <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                    />
                </Field>

                <Field label="Contraseña" required>
                    <input
                        type="password"
                        required
                        minLength={8}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                    />
                </Field>

                <div className="grid grid-cols-2 gap-3">
                    <Field label="Nombre">
                        <input
                            type="text"
                            value={firstName}
                            onChange={(e) => setFirstName(e.target.value)}
                            className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                        />
                    </Field>
                    <Field label="Apellidos">
                        <input
                            type="text"
                            value={lastName}
                            onChange={(e) => setLastName(e.target.value)}
                            className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                        />
                    </Field>
                </div>

                <Field label="Rol">
                    <select
                        value={role}
                        onChange={(e) => setRole(e.target.value)}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                    >
                        {USER_ROLES.map((r) => (
                            <option key={r} value={r}>{ROLE_LABEL[r] ?? r}</option>
                        ))}
                    </select>
                </Field>

                <ModalActions onCancel={onCancel} submitting={submitting} submitLabel="Crear usuario" />
            </form>
        </Modal>
    );
}

"use client";

import { useTranslations } from "next-intl";
import { Loader2, X } from "lucide-react";

export function Modal({
    title,
    children,
    onClose,
}: {
    title: string;
    children: React.ReactNode;
    onClose: () => void;
}) {
    const tc = useTranslations("common");
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-md p-6 space-y-5">
                <div className="flex items-start justify-between">
                    <h2 className="text-xl font-bold text-foreground">{title}</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label={tc("close")}>
                        <X className="w-5 h-5" aria-hidden="true" />
                    </button>
                </div>
                {children}
            </div>
        </div>
    );
}

export function ModalActions({
    onCancel,
    submitting,
    submitLabel,
}: {
    onCancel: () => void;
    submitting: boolean;
    submitLabel: string;
}) {
    const tc = useTranslations("common");
    return (
        <div className="flex items-center justify-end gap-2 pt-2">
            <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground"
            >
                {tc("cancel")}
            </button>
            <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm font-medium hover:opacity-90 disabled:opacity-50"
            >
                {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                {submitLabel}
            </button>
        </div>
    );
}

export function Field({
    label,
    required,
    children,
}: {
    label: string;
    required?: boolean;
    children: React.ReactNode;
}) {
    return (
        <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {label} {required && <span className="text-destructive">*</span>}
            </label>
            {children}
        </div>
    );
}

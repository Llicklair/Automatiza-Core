"use client";

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface FormModalProps {
    open: boolean;
    onClose: () => void;
    title: string;
    description?: string;
    onSubmit?: (e: React.FormEvent) => void;
    isSubmitting?: boolean;
    submitLabel?: string;
    cancelLabel?: string;
    children: React.ReactNode;
    className?: string;
}

export function FormModal({
    open,
    onClose,
    title,
    description,
    onSubmit,
    isSubmitting = false,
    submitLabel = "Guardar",
    cancelLabel = "Cancelar",
    children,
    className,
}: FormModalProps) {
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit?.(e);
    };

    return (
        <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
            <DialogContent className={className}>
                <form onSubmit={handleSubmit}>
                    <DialogHeader>
                        <DialogTitle>{title}</DialogTitle>
                        {description && <DialogDescription>{description}</DialogDescription>}
                    </DialogHeader>
                    <div className="grid gap-4 py-4">{children}</div>
                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
                            {cancelLabel}
                        </Button>
                        <Button type="submit" disabled={isSubmitting}>
                            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {submitLabel}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

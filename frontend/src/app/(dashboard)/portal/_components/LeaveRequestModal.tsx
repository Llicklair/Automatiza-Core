"use client";
import type { Dispatch, SetStateAction } from "react";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LEAVE_TYPES } from "./constants";
import type { LeaveFormState } from "../_hooks/usePortal";

interface LeaveRequestModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    leaveForm: LeaveFormState;
    setLeaveForm: Dispatch<SetStateAction<LeaveFormState>>;
    saving: boolean;
    leaveError: string | null;
    onSubmit: () => void;
}

export function LeaveRequestModal({
    open, onOpenChange, leaveForm, setLeaveForm, saving, leaveError, onSubmit,
}: LeaveRequestModalProps) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-sm">
                <DialogHeader>
                    <DialogTitle>Solicitud de ausencia</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-1.5">
                        <Label>Tipo *</Label>
                        <Select value={leaveForm.leave_type} onValueChange={(v) => setLeaveForm((f) => ({ ...f, leave_type: v }))}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {LEAVE_TYPES.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label>Fecha inicio *</Label>
                            <Input type="date" value={leaveForm.start_date} onChange={(e) => setLeaveForm((f) => ({ ...f, start_date: e.target.value }))} />
                        </div>
                        <div className="space-y-1.5">
                            <Label>Fecha fin *</Label>
                            <Input type="date" value={leaveForm.end_date} onChange={(e) => setLeaveForm((f) => ({ ...f, end_date: e.target.value }))} />
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <Label>Notas</Label>
                        <Input value={leaveForm.notes} onChange={(e) => setLeaveForm((f) => ({ ...f, notes: e.target.value }))} placeholder="Opcional…" />
                    </div>
                    {leaveError && <p className="text-xs text-destructive">{leaveError}</p>}
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>Cancelar</Button>
                    <Button onClick={onSubmit} disabled={saving}>{saving ? "Enviando…" : "Enviar"}</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

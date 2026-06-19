"use client";
import type { Dispatch, SetStateAction } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LEAVE_TYPE_VALUES } from "./constants";
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
    const t = useTranslations("portal");
    const tc = useTranslations("common");
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-sm">
                <DialogHeader>
                    <DialogTitle>{t("leaveModal.title")}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-1.5">
                        <Label>{t("leaveModal.type")}</Label>
                        <Select value={leaveForm.leave_type} onValueChange={(v) => setLeaveForm((f) => ({ ...f, leave_type: v }))}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {LEAVE_TYPE_VALUES.map((v) => <SelectItem key={v} value={v}>{t(`leaveTypes.${v}`)}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label>{t("leaveModal.startDate")}</Label>
                            <Input type="date" value={leaveForm.start_date} onChange={(e) => setLeaveForm((f) => ({ ...f, start_date: e.target.value }))} />
                        </div>
                        <div className="space-y-1.5">
                            <Label>{t("leaveModal.endDate")}</Label>
                            <Input type="date" value={leaveForm.end_date} onChange={(e) => setLeaveForm((f) => ({ ...f, end_date: e.target.value }))} />
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <Label>{t("leaveModal.notes")}</Label>
                        <Input value={leaveForm.notes} onChange={(e) => setLeaveForm((f) => ({ ...f, notes: e.target.value }))} placeholder={t("leaveModal.notesPlaceholder")} />
                    </div>
                    {leaveError && <p className="text-xs text-destructive">{leaveError}</p>}
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>{tc("cancel")}</Button>
                    <Button onClick={onSubmit} disabled={saving}>{saving ? t("leaveModal.submitting") : tc("send")}</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

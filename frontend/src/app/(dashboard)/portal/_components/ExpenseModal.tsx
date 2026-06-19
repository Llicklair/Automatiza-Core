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
import { EXPENSE_CATEGORY_VALUES } from "./constants";
import type { ExpenseFormState } from "../_hooks/usePortal";

interface ExpenseModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    expenseForm: ExpenseFormState;
    setExpenseForm: Dispatch<SetStateAction<ExpenseFormState>>;
    expenseSaving: boolean;
    expenseError: string | null;
    onSubmit: () => void;
}

export function ExpenseModal({
    open, onOpenChange, expenseForm, setExpenseForm, expenseSaving, expenseError, onSubmit,
}: ExpenseModalProps) {
    const t = useTranslations("portal");
    const tc = useTranslations("common");
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-sm">
                <DialogHeader>
                    <DialogTitle>{t("expenseModal.title")}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label>{t("expenseModal.amount")}</Label>
                            <Input
                                type="number" step="0.01" min="0"
                                value={expenseForm.amount}
                                onChange={(e) => setExpenseForm((f) => ({ ...f, amount: e.target.value }))}
                                placeholder={t("expenseModal.amountPlaceholder")}
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label>{t("expenseModal.date")}</Label>
                            <Input
                                type="date"
                                value={expenseForm.date}
                                onChange={(e) => setExpenseForm((f) => ({ ...f, date: e.target.value }))}
                            />
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <Label>{t("expenseModal.category")}</Label>
                        <Select value={expenseForm.category} onValueChange={(v) => setExpenseForm((f) => ({ ...f, category: v }))}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {EXPENSE_CATEGORY_VALUES.map((c) => (
                                    <SelectItem key={c} value={c}>{t(`expenseCategories.${c}`)}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1.5">
                        <Label>{t("expenseModal.description")}</Label>
                        <Input
                            value={expenseForm.description}
                            onChange={(e) => setExpenseForm((f) => ({ ...f, description: e.target.value }))}
                            placeholder={t("expenseModal.descriptionPlaceholder")}
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label>{t("expenseModal.notes")}</Label>
                        <Input
                            value={expenseForm.notes}
                            onChange={(e) => setExpenseForm((f) => ({ ...f, notes: e.target.value }))}
                            placeholder={t("expenseModal.notesPlaceholder")}
                        />
                    </div>
                    {expenseError && <p className="text-xs text-destructive">{expenseError}</p>}
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={expenseSaving}>{tc("cancel")}</Button>
                    <Button onClick={onSubmit} disabled={expenseSaving}>
                        {expenseSaving ? t("expenseModal.submitting") : tc("send")}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

"use client";

import { useTranslations } from "next-intl";
import type { Client } from "@/lib/api";
import { FormModal, FormField } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select";

interface Props {
    open: boolean;
    onClose: () => void;
    clients: Client[];
    supplierId: string; setSupplierId: (v: string) => void;
    supplierName: string; setSupplierName: (v: string) => void;
    useExisting: boolean; setUseExisting: (v: boolean) => void;
    invoiceNumber: string; setInvoiceNumber: (v: string) => void;
    amount: string; setAmount: (v: string) => void;
    taxPct: string; setTaxPct: (v: string) => void;
    date: string; setDate: (v: string) => void;
    dueDate: string; setDueDate: (v: string) => void;
    invStatus: string; setInvStatus: (v: string) => void;
    fiscalRegime: string; setFiscalRegime: (v: string) => void;
    retencionRate: string; setRetencionRate: (v: string) => void;
    submitting: boolean;
    onSubmit: (e: React.FormEvent) => void;
}

export function RegistrarFacturaModal({
    open, onClose, clients,
    supplierId, setSupplierId, supplierName, setSupplierName,
    useExisting, setUseExisting, invoiceNumber, setInvoiceNumber,
    amount, setAmount, taxPct, setTaxPct, date, setDate,
    dueDate, setDueDate, invStatus, setInvStatus,
    fiscalRegime, setFiscalRegime, retencionRate, setRetencionRate,
    submitting, onSubmit,
}: Props) {
    const t = useTranslations("compras.facturas.modal");
    return (
        <FormModal
            open={open}
            onClose={onClose}
            title={t("title")}
            description={t("description")}
            onSubmit={onSubmit}
            isSubmitting={submitting}
            submitLabel={t("submit")}
            className="sm:max-w-lg"
        >
            <FormField label={t("supplier")} required>
                <div className="flex gap-2 mb-2">
                    <Button type="button" size="sm" variant={useExisting ? "default" : "outline"} onClick={() => setUseExisting(true)}>
                        {t("existing")}
                    </Button>
                    <Button type="button" size="sm" variant={!useExisting ? "default" : "outline"} onClick={() => setUseExisting(false)}>
                        {t("new")}
                    </Button>
                </div>
                {useExisting ? (
                    <Select value={supplierId} onValueChange={setSupplierId}>
                        <SelectTrigger><SelectValue placeholder={t("selectSupplier")} /></SelectTrigger>
                        <SelectContent>
                            {clients.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                        </SelectContent>
                    </Select>
                ) : (
                    <Input
                        required={!useExisting}
                        value={supplierName}
                        onChange={e => setSupplierName(e.target.value)}
                        placeholder={t("supplierNamePlaceholder")}
                    />
                )}
            </FormField>

            <div className="grid grid-cols-2 gap-4">
                <FormField label={t("invoiceNumber")}>
                    <Input value={invoiceNumber} onChange={e => setInvoiceNumber(e.target.value)} placeholder={t("optional")} />
                </FormField>
                <FormField label={t("status")}>
                    <Select value={invStatus} onValueChange={setInvStatus}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="pending">{t("statusOptions.pending")}</SelectItem>
                            <SelectItem value="paid">{t("statusOptions.paid")}</SelectItem>
                            <SelectItem value="draft">{t("statusOptions.draft")}</SelectItem>
                        </SelectContent>
                    </Select>
                </FormField>
                <FormField label={t("baseAmount")} required>
                    <Input type="number" required min="0" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} placeholder="0.00" />
                </FormField>
                <FormField label={t("vat")}>
                    <Select value={taxPct} onValueChange={setTaxPct}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="21">21%</SelectItem>
                            <SelectItem value="10">10%</SelectItem>
                            <SelectItem value="4">4%</SelectItem>
                            <SelectItem value="0">0%</SelectItem>
                        </SelectContent>
                    </Select>
                </FormField>
                <FormField label={t("date")} required>
                    <Input type="date" required value={date} onChange={e => setDate(e.target.value)} />
                </FormField>
                <FormField label={t("dueDate")}>
                    <Input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} />
                </FormField>
                <FormField label={t("fiscalRegime")}>
                    <Select value={fiscalRegime || "general"} onValueChange={v => setFiscalRegime(v === "general" ? "" : v)}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="general">{t("fiscalRegimeOptions.general")}</SelectItem>
                            <SelectItem value="intracomunitario">{t("fiscalRegimeOptions.intracomunitario")}</SelectItem>
                            <SelectItem value="isp">{t("fiscalRegimeOptions.isp")}</SelectItem>
                        </SelectContent>
                    </Select>
                </FormField>
                <FormField label={t("retention")}>
                    <Input type="number" min="0" max="47" step="0.5" value={retencionRate}
                        onChange={e => setRetencionRate(e.target.value)} placeholder={t("retentionPlaceholder")} />
                </FormField>
            </div>
        </FormModal>
    );
}

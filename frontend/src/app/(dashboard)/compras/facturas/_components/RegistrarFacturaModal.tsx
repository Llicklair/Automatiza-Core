"use client";

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
    submitting: boolean;
    onSubmit: (e: React.FormEvent) => void;
}

export function RegistrarFacturaModal({
    open, onClose, clients,
    supplierId, setSupplierId, supplierName, setSupplierName,
    useExisting, setUseExisting, invoiceNumber, setInvoiceNumber,
    amount, setAmount, taxPct, setTaxPct, date, setDate,
    dueDate, setDueDate, invStatus, setInvStatus,
    submitting, onSubmit,
}: Props) {
    return (
        <FormModal
            open={open}
            onClose={onClose}
            title="Registrar Factura Recibida"
            description="Completa los datos de la factura de compra."
            onSubmit={onSubmit}
            isSubmitting={submitting}
            submitLabel="Registrar"
            className="sm:max-w-lg"
        >
            <FormField label="Proveedor" required>
                <div className="flex gap-2 mb-2">
                    <Button type="button" size="sm" variant={useExisting ? "default" : "outline"} onClick={() => setUseExisting(true)}>
                        Existente
                    </Button>
                    <Button type="button" size="sm" variant={!useExisting ? "default" : "outline"} onClick={() => setUseExisting(false)}>
                        Nuevo
                    </Button>
                </div>
                {useExisting ? (
                    <Select value={supplierId} onValueChange={setSupplierId}>
                        <SelectTrigger><SelectValue placeholder="Seleccionar proveedor..." /></SelectTrigger>
                        <SelectContent>
                            {clients.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                        </SelectContent>
                    </Select>
                ) : (
                    <Input
                        required={!useExisting}
                        value={supplierName}
                        onChange={e => setSupplierName(e.target.value)}
                        placeholder="Nombre del proveedor"
                    />
                )}
            </FormField>

            <div className="grid grid-cols-2 gap-4">
                <FormField label="Nº Factura">
                    <Input value={invoiceNumber} onChange={e => setInvoiceNumber(e.target.value)} placeholder="Opcional" />
                </FormField>
                <FormField label="Estado">
                    <Select value={invStatus} onValueChange={setInvStatus}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="pending">Pendiente</SelectItem>
                            <SelectItem value="paid">Pagada</SelectItem>
                            <SelectItem value="draft">Borrador</SelectItem>
                        </SelectContent>
                    </Select>
                </FormField>
                <FormField label="Importe base (€)" required>
                    <Input type="number" required min="0" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} placeholder="0.00" />
                </FormField>
                <FormField label="% IVA">
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
                <FormField label="Fecha" required>
                    <Input type="date" required value={date} onChange={e => setDate(e.target.value)} />
                </FormField>
                <FormField label="Vencimiento">
                    <Input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} />
                </FormField>
            </div>
        </FormModal>
    );
}

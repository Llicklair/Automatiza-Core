"use client";

import { useEffect, useState } from "react";
import { api, type JournalEntry, type JournalLine } from "@/lib/api";
import { logError } from "@/lib/logger";
import { useToastStore } from "@/stores/toast";

export type NewEntryState = {
    date: string;
    description: string;
    lines: Partial<JournalLine>[];
};

const defaultEntry = (): NewEntryState => ({
    date: new Date().toISOString().split('T')[0],
    description: '',
    lines: [
        { account_code: '', account_name: '', debit: 0, credit: 0 },
        { account_code: '', account_name: '', debit: 0, credit: 0 },
    ],
});

export function useLibroDiario() {
    const toast = useToastStore();
    const [entries, setEntries] = useState<JournalEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setModalOpen] = useState(false);
    const [newEntry, setNewEntry] = useState<NewEntryState>(defaultEntry());

    const loadData = async () => {
        setLoading(true);
        try {
            const data = await api.accounting.journal.list();
            setEntries(data);
        } catch (error) {
            logError("contabilidad/libro-diario/page", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); }, []);

    const exportCSV = () => {
        const rows = [["Fecha", "Concepto", "Cuenta", "Nombre", "Debe", "Haber"]];
        for (const entry of entries) {
            for (const line of entry.lines) {
                rows.push([
                    new Date(entry.date).toLocaleDateString("es-ES"),
                    entry.description,
                    line.account_code,
                    line.account_name || "",
                    Number(line.debit) > 0 ? String(Number(line.debit).toFixed(2)) : "",
                    Number(line.credit) > 0 ? String(Number(line.credit).toFixed(2)) : "",
                ]);
            }
        }
        const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(";")).join("\n");
        const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `libro-diario-${new Date().toISOString().split("T")[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const handleAddLine = () => {
        setNewEntry(prev => ({
            ...prev,
            lines: [...prev.lines, { account_code: '', account_name: '', debit: 0, credit: 0 }],
        }));
    };

    const handleRemoveLine = (index: number) => {
        if (newEntry.lines.length <= 2) return;
        setNewEntry(prev => ({ ...prev, lines: prev.lines.filter((_, i) => i !== index) }));
    };

    const handleLineChange = (index: number, field: keyof JournalLine, value: any) => {
        setNewEntry(prev => {
            const newLines = [...prev.lines];
            newLines[index] = { ...newLines[index], [field]: value };
            return { ...prev, lines: newLines };
        });
    };

    const totalDebit = newEntry.lines.reduce((acc, curr) => acc + (Number(curr.debit) || 0), 0);
    const totalCredit = newEntry.lines.reduce((acc, curr) => acc + (Number(curr.credit) || 0), 0);
    const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01 && totalDebit > 0;

    const deleteEntry = async (id: string) => {
        if (!confirm("¿Eliminar este asiento contable? Esta acción no se puede deshacer.")) return;
        try {
            await api.accounting.journal.delete(id);
            loadData();
        } catch (err: any) { toast.error("Error eliminando el asiento: " + err.message); }
    };

    const createEntry = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!isBalanced) { toast.warning("El asiento está descuadrado. El Debe debe ser igual al Haber."); return; }
        try {
            await api.accounting.journal.create(newEntry as any);
            setModalOpen(false);
            setNewEntry(defaultEntry());
            loadData();
        } catch (err: any) { toast.error("Error creando el asiento: " + err.message); }
    };

    return {
        entries, loading, isModalOpen, setModalOpen,
        newEntry, setNewEntry,
        exportCSV, handleAddLine, handleRemoveLine, handleLineChange,
        totalDebit, totalCredit, isBalanced,
        deleteEntry, createEntry,
    };
}

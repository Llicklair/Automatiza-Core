"use client";

import { useEffect, useState } from "react";
import { api, type JournalEntry, type JournalLine } from "@/lib/api";
import { FileDown, Plus, PlusCircle, AlertCircle, BookOpen, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";

export default function LibroDiarioPage() {
    const toast = useToastStore();
    const [entries, setEntries] = useState<JournalEntry[]>([]);
    const [loading, setLoading] = useState(true);

    const [isModalOpen, setModalOpen] = useState(false);
    const [newEntry, setNewEntry] = useState<{
        date: string;
        description: string;
        lines: Partial<JournalLine>[];
    }>({
        date: new Date().toISOString().split('T')[0],
        description: '',
        lines: [
            { account_code: '', account_name: '', debit: 0, credit: 0 },
            { account_code: '', account_name: '', debit: 0, credit: 0 }
        ]
    });

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

    const handleAddLine = () => {
        setNewEntry(prev => ({
            ...prev,
            lines: [...prev.lines, { account_code: '', account_name: '', debit: 0, credit: 0 }]
        }));
    };

    const handleRemoveLine = (index: number) => {
        if (newEntry.lines.length <= 2) return;
        setNewEntry(prev => ({
            ...prev,
            lines: prev.lines.filter((_, i) => i !== index)
        }));
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
            setNewEntry({
                date: new Date().toISOString().split('T')[0],
                description: '',
                lines: [
                    { account_code: '', account_name: '', debit: 0, credit: 0 },
                    { account_code: '', account_name: '', debit: 0, credit: 0 }
                ]
            });
            loadData();
        } catch (err: any) { toast.error("Error creando el asiento: " + err.message); }
    };

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Libro Diario</h1>
                    <p className="text-zinc-400">Registro cronológico de todos los asientos y movimientos contables.</p>
                </div>
                <div className="flex gap-3">
                    <button onClick={exportCSV} disabled={entries.length === 0} className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 text-white rounded-lg transition-colors font-medium border border-[#27272a]">
                        <FileDown className="w-4 h-4" /> Exportar CSV
                    </button>
                    <button onClick={() => setModalOpen(true)} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors font-medium shadow-lg shadow-indigo-500/20">
                        <Plus className="w-4 h-4" /> Nuevo Asiento
                    </button>
                </div>
            </div>

            {/* List */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden shadow-2xl">
                {loading ? (
                    <div className="p-12 text-center text-zinc-500 bg-white/5 animate-pulse">Cargando apuntes contables...</div>
                ) : entries.length === 0 ? (
                    <div className="p-16 text-center">
                        <BookOpen className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-white mb-1">Libro Vacío</h3>
                        <p className="text-zinc-500">No se han registrado asientos contables aún.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-[#18181b] text-zinc-400 border-b border-[#27272a]">
                                <tr>
                                    <th className="px-6 py-4 font-medium w-40">Fecha</th>
                                    <th className="px-6 py-4 font-medium">Concepto</th>
                                    <th className="px-6 py-4 font-medium w-48">Cuenta</th>
                                    <th className="px-6 py-4 font-medium w-64">Nombre</th>
                                    <th className="px-6 py-4 font-medium text-right w-32">Debe</th>
                                    <th className="px-6 py-4 font-medium text-right w-32">Haber</th>
                                    <th className="px-6 py-4 font-medium w-12"></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[#27272a]/50">
                                {entries.map((entry) => (
                                    <tr key={entry.id} className="group hover:bg-white/[0.02] transition-colors">
                                        <td className="px-6 py-4 align-top">
                                            <div className="font-medium text-zinc-300">{new Date(entry.date).toLocaleDateString()}</div>
                                            <div className="text-[10px] text-zinc-600 mt-1 font-mono">ID: {entry.id.split('-')[0]}</div>
                                        </td>
                                        <td className="px-6 py-4 align-top text-white font-medium">
                                            {entry.description}
                                        </td>

                                        {/* Líneas anidadas en las celdas */}
                                        <td className="px-6 py-4 p-0" colSpan={4}>
                                            <table className="w-full">
                                                <tbody>
                                                    {entry.lines.map((line) => (
                                                        <tr key={line.id} className="border-b border-transparent group-hover:border-[#27272a]/30 last:border-0">
                                                            <td className="w-48 py-2 text-indigo-400 font-mono text-xs">{line.account_code}</td>
                                                            <td className="w-64 py-2 text-zinc-400 truncate pr-4">{line.account_name || '-'}</td>
                                                            <td className="w-32 py-2 text-right text-emerald-400 font-medium">
                                                                {Number(line.debit) > 0 ? Number(line.debit).toLocaleString('es-ES', { minimumFractionDigits: 2 }) : ''}
                                                            </td>
                                                            <td className="w-32 py-2 text-right text-rose-400 font-medium">
                                                                {Number(line.credit) > 0 ? Number(line.credit).toLocaleString('es-ES', { minimumFractionDigits: 2 }) : ''}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </td>
                                        <td className="px-2 py-4 align-top">
                                            <button
                                                onClick={() => deleteEntry(entry.id)}
                                                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-all"
                                                title="Eliminar asiento"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Modal de Asiento Manual */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl w-full max-w-4xl shadow-2xl p-6 max-h-[90vh] flex flex-col">
                        <h3 className="text-xl font-bold text-white mb-6">Nuevo Asiento Contable</h3>

                        <form onSubmit={createEntry} className="flex-1 overflow-auto flex flex-col">
                            <div className="grid grid-cols-3 gap-6 mb-8">
                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-2">Fecha contable</label>
                                    <input required type="date" className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-indigo-500 transition-colors"
                                        value={newEntry.date} onChange={e => setNewEntry({ ...newEntry, date: e.target.value })} />
                                </div>
                                <div className="col-span-2">
                                    <label className="block text-sm font-medium text-zinc-400 mb-2">Concepto</label>
                                    <input required type="text" placeholder="Ej: Nómina Agosto, Factura Venta XYZ..." className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-indigo-500 transition-colors"
                                        value={newEntry.description} onChange={e => setNewEntry({ ...newEntry, description: e.target.value })} />
                                </div>
                            </div>

                            <div className="flex-1">
                                <div className="flex items-center justify-between mb-3">
                                    <h4 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Apuntes (Líneas)</h4>
                                    <button type="button" onClick={handleAddLine} className="text-xs flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 font-medium">
                                        <PlusCircle className="w-4 h-4" /> Añadir apunte
                                    </button>
                                </div>

                                <div className="bg-black/20 border border-[#27272a] rounded-xl overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-[#18181b] text-zinc-500 border-b border-[#27272a]">
                                            <tr>
                                                <th className="px-4 py-3 font-medium text-left w-40">Cuenta</th>
                                                <th className="px-4 py-3 font-medium text-left">Referencia / Nombre</th>
                                                <th className="px-4 py-3 font-medium text-right w-36">Debe (€)</th>
                                                <th className="px-4 py-3 font-medium text-right w-36">Haber (€)</th>
                                                <th className="px-4 py-3 w-12"></th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-[#27272a]">
                                            {newEntry.lines.map((line, idx) => (
                                                <tr key={idx}>
                                                    <td className="p-2">
                                                        <input required type="text" placeholder="Ej: 430" className="w-full bg-transparent border border-transparent hover:border-white/10 focus:border-indigo-500 rounded px-3 py-1.5 text-white outline-none transition-colors font-mono"
                                                            value={line.account_code || ''} onChange={e => handleLineChange(idx, 'account_code', e.target.value)} />
                                                    </td>
                                                    <td className="p-2">
                                                        <input type="text" placeholder="Opcional..." className="w-full bg-transparent border border-transparent hover:border-white/10 focus:border-indigo-500 rounded px-3 py-1.5 text-white outline-none transition-colors"
                                                            value={line.account_name || ''} onChange={e => handleLineChange(idx, 'account_name', e.target.value)} />
                                                    </td>
                                                    <td className="p-2">
                                                        <input type="number" step="0.01" min="0" className="w-full bg-transparent border border-transparent hover:border-white/10 focus:border-emerald-500 rounded px-3 py-1.5 text-emerald-400 font-medium text-right outline-none transition-colors"
                                                            value={line.debit || ''} onChange={e => handleLineChange(idx, 'debit', Number(e.target.value))} />
                                                    </td>
                                                    <td className="p-2">
                                                        <input type="number" step="0.01" min="0" className="w-full bg-transparent border border-transparent hover:border-white/10 focus:border-rose-500 rounded px-3 py-1.5 text-rose-400 font-medium text-right outline-none transition-colors"
                                                            value={line.credit || ''} onChange={e => handleLineChange(idx, 'credit', Number(e.target.value))} />
                                                    </td>
                                                    <td className="p-2 text-center">
                                                        <button type="button" onClick={() => handleRemoveLine(idx)} disabled={newEntry.lines.length <= 2} className="p-1.5 text-zinc-600 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors disabled:opacity-30">
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                        <tfoot className="bg-[#18181b] border-t border-[#27272a]">
                                            <tr>
                                                <td colSpan={2} className="px-4 py-3 text-right font-medium text-zinc-400">Total:</td>
                                                <td className={cn("px-4 py-3 text-right font-bold text-lg", isBalanced ? "text-emerald-500" : "text-zinc-300")}>
                                                    {totalDebit.toLocaleString('es-ES', { minimumFractionDigits: 2 })}
                                                </td>
                                                <td className={cn("px-4 py-3 text-right font-bold text-lg", isBalanced ? "text-emerald-500" : "text-zinc-300")}>
                                                    {totalCredit.toLocaleString('es-ES', { minimumFractionDigits: 2 })}
                                                </td>
                                                <td></td>
                                            </tr>
                                        </tfoot>
                                    </table>
                                </div>

                                {!isBalanced && (
                                    <div className="mt-4 flex items-center gap-2 text-amber-500 bg-amber-500/10 px-4 py-3 rounded-lg border border-amber-500/20">
                                        <AlertCircle className="w-5 h-5 shrink-0" />
                                        <span className="text-sm font-medium">Asiento descuadrado. La diferencia actual es de <strong>{Math.abs(totalDebit - totalCredit).toLocaleString('es-ES')} €</strong>.</span>
                                    </div>
                                )}
                            </div>

                            <div className="flex justify-end gap-3 pt-6 mt-6 border-t border-[#27272a]">
                                <button type="button" onClick={() => setModalOpen(false)} className="px-6 py-2.5 text-zinc-400 font-medium hover:bg-white/5 rounded-xl transition-colors">Cancelar</button>
                                <button type="submit" disabled={!isBalanced} className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:hover:bg-indigo-600 text-white rounded-xl font-medium transition-all shadow-lg shadow-indigo-500/20">Registrar Asiento</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

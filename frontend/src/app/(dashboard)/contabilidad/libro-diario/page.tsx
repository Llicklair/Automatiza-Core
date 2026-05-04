"use client";

import { FileDown, Plus, BookOpen, Trash2 } from "lucide-react";
import { useLibroDiario } from "./_hooks/useLibroDiario";
import { AsientoModal } from "./_components/AsientoModal";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";

export default function LibroDiarioPage() {
    const {
        entries, loading, isModalOpen, setModalOpen,
        newEntry, setNewEntry,
        exportCSV, handleAddLine, handleRemoveLine, handleLineChange,
        totalDebit, totalCredit, isBalanced,
        deleteEntry, createEntry,
    } = useLibroDiario();

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6 animate-in fade-in duration-500">
            <PageHeader
                title="Libro Diario"
                description="Registro cronológico de todos los asientos y movimientos contables."
                icon={BookOpen}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={exportCSV} disabled={entries.length === 0}>
                            <FileDown className="w-4 h-4 mr-2" /> Exportar CSV
                        </Button>
                        <Button onClick={() => setModalOpen(true)}>
                            <Plus className="w-4 h-4 mr-2" /> Nuevo Asiento
                        </Button>
                    </div>
                }
            />

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl">
                {loading ? (
                    <div className="p-12 text-center text-muted-foreground bg-accent/50 animate-pulse">Cargando apuntes contables...</div>
                ) : entries.length === 0 ? (
                    <div className="p-16 text-center">
                        <BookOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-foreground mb-1">Libro Vacío</h3>
                        <p className="text-muted-foreground">No se han registrado asientos contables aún.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-card text-muted-foreground border-b border-border">
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
                            <tbody className="divide-y divide-border">
                                {entries.map((entry) => (
                                    <tr key={entry.id} className="group hover:bg-accent/50 transition-colors">
                                        <td className="px-6 py-4 align-top">
                                            <div className="font-medium text-foreground">{new Date(entry.date).toLocaleDateString()}</div>
                                            <div className="text-[10px] text-muted-foreground mt-1 font-mono">ID: {entry.id.split('-')[0]}</div>
                                        </td>
                                        <td className="px-6 py-4 align-top text-foreground font-medium">
                                            {entry.description}
                                        </td>
                                        <td className="px-6 py-4 p-0" colSpan={4}>
                                            <table className="w-full">
                                                <tbody>
                                                    {entry.lines.map((line) => (
                                                        <tr key={line.id} className="border-b border-transparent group-hover:border-border/30 last:border-0">
                                                            <td className="w-48 py-2 text-primary font-mono text-xs">{line.account_code}</td>
                                                            <td className="w-64 py-2 text-muted-foreground truncate pr-4">{line.account_name || '-'}</td>
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
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-7 w-7 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400 hover:bg-red-500/10"
                                                onClick={() => deleteEntry(entry.id)}
                                                title="Eliminar asiento"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {isModalOpen && (
                <AsientoModal
                    newEntry={newEntry}
                    setNewEntry={setNewEntry}
                    totalDebit={totalDebit}
                    totalCredit={totalCredit}
                    isBalanced={isBalanced}
                    onClose={() => setModalOpen(false)}
                    onSubmit={createEntry}
                    onAddLine={handleAddLine}
                    onRemoveLine={handleRemoveLine}
                    onLineChange={handleLineChange}
                />
            )}
        </div>
    );
}

"use client";

import { Plus, Loader2, FileText, Trash2, Download, FileEdit, Search } from "lucide-react";
import { useAlbaranes, STATUS_LABELS, fmt } from "./_hooks/useAlbaranes";
import { AlbaranModal } from "./_components/AlbaranModal";

export default function AlbaranesPage() {
    const {
        loading, search, setSearch, filterStatus, setFilterStatus,
        showModal, setShowModal, saving,
        clientName, setClientName, date, setDate, notes, setNotes, lines, setLines,
        resetModal, handleCreate, handleDelete, handleStatusChange, handleDownloadPdf, handleConvertToInvoice,
        filtered,
    } = useAlbaranes();

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-foreground mb-1">Albaranes</h1>
                    <p className="text-muted-foreground text-sm">Gestión de albaranes y notas de entrega.</p>
                </div>
                <button
                    onClick={() => setShowModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary text-foreground rounded-lg transition-colors font-medium shadow-lg shadow-primary/20"
                >
                    <Plus className="w-4 h-4" /> Nuevo Albarán
                </button>
            </div>

            <div className="flex gap-3 flex-wrap">
                <div className="relative flex-1 min-w-[200px]">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        value={search} onChange={e => setSearch(e.target.value)}
                        placeholder="Buscar por número..."
                        className="w-full pl-9 pr-3 py-2 rounded-lg bg-card border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50"
                    />
                </div>
                <select
                    value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
                    className="px-3 py-2 rounded-lg bg-card border border-border text-sm text-foreground focus:outline-none focus:border-primary/50"
                >
                    <option value="">Todos los estados</option>
                    <option value="draft">Borrador</option>
                    <option value="confirmed">Confirmado</option>
                    <option value="delivered">Entregado</option>
                </select>
            </div>

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl">
                {loading ? (
                    <div className="p-12 flex items-center justify-center gap-3 text-muted-foreground">
                        <Loader2 className="w-5 h-5 animate-spin" /> Cargando albaranes...
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="p-16 text-center">
                        <FileText className="w-12 h-12 text-muted-foreground/60 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-foreground mb-1">Sin albaranes</h3>
                        <p className="text-muted-foreground text-sm">Crea el primero con el botón &ldquo;Nuevo Albarán&rdquo;.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-card text-muted-foreground border-b border-border">
                                <tr>
                                    <th className="px-6 py-4 font-medium">Nº Albarán</th>
                                    <th className="px-6 py-4 font-medium">Fecha</th>
                                    <th className="px-6 py-4 font-medium">Cliente</th>
                                    <th className="px-6 py-4 font-medium">Estado</th>
                                    <th className="px-6 py-4 font-medium text-right">Total</th>
                                    <th className="px-6 py-4 font-medium w-48">Acciones</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {filtered.map(albaran => {
                                    const st = STATUS_LABELS[albaran.status] || STATUS_LABELS.draft;
                                    return (
                                        <tr key={albaran.id} className="group hover:bg-accent/50 transition-colors">
                                            <td className="px-6 py-4 font-mono text-primary font-medium">{albaran.albaran_number}</td>
                                            <td className="px-6 py-4 text-foreground">{new Date(albaran.date).toLocaleDateString("es-ES")}</td>
                                            <td className="px-6 py-4 text-foreground">{albaran.client_id ? "—" : "Sin cliente"}</td>
                                            <td className="px-6 py-4">
                                                <select
                                                    value={albaran.status}
                                                    onChange={e => handleStatusChange(albaran.id, e.target.value)}
                                                    className={`text-xs px-2 py-1 rounded-full border font-medium bg-transparent cursor-pointer focus:outline-none ${st.color}`}
                                                >
                                                    <option value="draft">Borrador</option>
                                                    <option value="confirmed">Confirmado</option>
                                                    <option value="delivered">Entregado</option>
                                                </select>
                                            </td>
                                            <td className="px-6 py-4 text-right font-medium text-foreground">{fmt(albaran.amount_total)}</td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button
                                                        onClick={() => handleDownloadPdf(albaran.id)}
                                                        className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all"
                                                        title="Descargar PDF"
                                                    ><Download className="w-3.5 h-3.5" /></button>
                                                    {albaran.status === "confirmed" && (
                                                        <button
                                                            onClick={() => handleConvertToInvoice(albaran)}
                                                            className="p-1.5 rounded-lg text-muted-foreground hover:text-emerald-400 hover:bg-emerald-500/10 transition-all"
                                                            title="Convertir a Factura"
                                                        ><FileEdit className="w-3.5 h-3.5" /></button>
                                                    )}
                                                    <button
                                                        onClick={() => handleDelete(albaran.id)}
                                                        className="p-1.5 rounded-lg text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-all"
                                                        title="Eliminar"
                                                    ><Trash2 className="w-3.5 h-3.5" /></button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {showModal && (
                <AlbaranModal
                    saving={saving}
                    clientName={clientName}
                    setClientName={setClientName}
                    date={date}
                    setDate={setDate}
                    notes={notes}
                    setNotes={setNotes}
                    lines={lines}
                    setLines={setLines}
                    onClose={() => { setShowModal(false); resetModal(); }}
                    onSubmit={handleCreate}
                />
            )}
        </div>
    );
}

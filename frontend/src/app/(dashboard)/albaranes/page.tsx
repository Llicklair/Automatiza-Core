"use client";

import { useTranslations } from "next-intl";
import { Plus, Loader2, FileText, Trash2, Download, FileEdit, Search, Printer } from "lucide-react";
import { useState } from "react";
import { useAlbaranes, STATUS_COLORS, fmt } from "./_hooks/useAlbaranes";
import { AlbaranModal } from "./_components/AlbaranModal";
import { MostradorModal } from "./_components/MostradorModal";
import { PageContainer } from "@/components/shared/PageContainer";

export default function AlbaranesPage() {
    const t = useTranslations("albaranes");
    const tc = useTranslations("common");
    const {
        loading, search, setSearch, filterStatus, setFilterStatus,
        showModal, setShowModal, saving,
        clientName, setClientName, date, setDate, notes, setNotes, lines, setLines,
        resetModal, handleCreate, handleDelete, handleStatusChange, handleDownloadPdf, handleConvertToInvoice, handlePrintTicket,
        reload,
        filtered,
    } = useAlbaranes();
    const [showMostrador, setShowMostrador] = useState(false);

    return (
        <PageContainer className="animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-foreground mb-1">{t("title")}</h1>
                    <p className="text-muted-foreground text-sm">{t("subtitle")}</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowMostrador(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors font-medium shadow-lg shadow-cyan-500/20"
                    >
                        <Printer className="w-4 h-4" /> {t("mostrador.boton")}
                    </button>
                    <button
                        onClick={() => setShowModal(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary text-foreground rounded-lg transition-colors font-medium shadow-lg shadow-primary/20"
                    >
                        <Plus className="w-4 h-4" /> {t("newAlbaran")}
                    </button>
                </div>
            </div>

            <div className="flex gap-3 flex-wrap">
                <div className="relative flex-1 min-w-[200px]">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        value={search} onChange={e => setSearch(e.target.value)}
                        placeholder={t("searchPlaceholder")}
                        className="w-full pl-9 pr-3 py-2 rounded-lg bg-card border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50"
                    />
                </div>
                <select
                    value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
                    className="px-3 py-2 rounded-lg bg-card border border-border text-sm text-foreground focus:outline-none focus:border-primary/50"
                >
                    <option value="">{t("filter.allStatuses")}</option>
                    <option value="draft">{t("status.draft")}</option>
                    <option value="confirmed">{t("status.confirmed")}</option>
                    <option value="recibido">{t("status.recibido")}</option>
                    <option value="en_proceso">{t("status.en_proceso")}</option>
                    <option value="listo">{t("status.listo")}</option>
                    <option value="delivered">{t("status.delivered")}</option>
                    <option value="anulado">{t("status.anulado")}</option>
                </select>
            </div>

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl">
                {loading ? (
                    <div className="p-12 flex items-center justify-center gap-3 text-muted-foreground">
                        <Loader2 className="w-5 h-5 animate-spin" /> {t("loading")}
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="p-16 text-center">
                        <FileText className="w-12 h-12 text-muted-foreground/60 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-foreground mb-1">{t("empty.title")}</h3>
                        <p className="text-muted-foreground text-sm">{t("empty.hint")}</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-card text-muted-foreground border-b border-border">
                                <tr>
                                    <th className="px-6 py-4 font-medium">{t("table.number")}</th>
                                    <th className="px-6 py-4 font-medium">{t("table.date")}</th>
                                    <th className="px-6 py-4 font-medium">{t("table.client")}</th>
                                    <th className="px-6 py-4 font-medium">{t("table.status")}</th>
                                    <th className="px-6 py-4 font-medium text-right">{t("table.total")}</th>
                                    <th className="px-6 py-4 font-medium w-48">{t("table.actions")}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {filtered.map(albaran => {
                                    const stColor = STATUS_COLORS[albaran.status] || STATUS_COLORS.draft;
                                    return (
                                        <tr key={albaran.id} className="group hover:bg-accent/50 transition-colors">
                                            <td className="px-6 py-4 font-mono text-primary font-medium">{albaran.albaran_number}</td>
                                            <td className="px-6 py-4 text-foreground">{new Date(albaran.date).toLocaleDateString("es-ES")}</td>
                                            <td className="px-6 py-4 text-foreground">{albaran.client_id ? "—" : t("table.noClient")}</td>
                                            <td className="px-6 py-4">
                                                <select
                                                    value={albaran.status}
                                                    onChange={e => handleStatusChange(albaran.id, e.target.value)}
                                                    className={`text-xs px-2 py-1 rounded-full border font-medium bg-transparent cursor-pointer focus:outline-none ${stColor}`}
                                                >
                                                    <option value="draft">{t("status.draft")}</option>
                                                    <option value="confirmed">{t("status.confirmed")}</option>
                                                    <option value="recibido">{t("status.recibido")}</option>
                                                    <option value="en_proceso">{t("status.en_proceso")}</option>
                                                    <option value="listo">{t("status.listo")}</option>
                                                    <option value="delivered">{t("status.delivered")}</option>
                                                    <option value="anulado">{t("status.anulado")}</option>
                                                </select>
                                            </td>
                                            <td className="px-6 py-4 text-right font-medium text-foreground">{fmt(albaran.amount_total)}</td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button
                                                        onClick={() => handlePrintTicket(albaran.id)}
                                                        className="p-1.5 rounded-lg text-muted-foreground hover:text-cyan-400 hover:bg-cyan-500/10 transition-all"
                                                        title={t("actions.printTicket")}
                                                    ><Printer className="w-3.5 h-3.5" /></button>
                                                    <button
                                                        onClick={() => handleDownloadPdf(albaran.id)}
                                                        className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all"
                                                        title={t("actions.downloadPdf")}
                                                    ><Download className="w-3.5 h-3.5" /></button>
                                                    {albaran.status === "confirmed" && (
                                                        <button
                                                            onClick={() => handleConvertToInvoice(albaran)}
                                                            className="p-1.5 rounded-lg text-muted-foreground hover:text-emerald-400 hover:bg-emerald-500/10 transition-all"
                                                            title={t("actions.convertToInvoice")}
                                                        ><FileEdit className="w-3.5 h-3.5" /></button>
                                                    )}
                                                    <button
                                                        onClick={() => handleDelete(albaran.id)}
                                                        className="p-1.5 rounded-lg text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-all"
                                                        title={tc("delete")}
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

            {showMostrador && (
                <MostradorModal onClose={() => setShowMostrador(false)} onCreated={reload} />
            )}

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
        </PageContainer>
    );
}

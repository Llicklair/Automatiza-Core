"use client";

import { useEffect, useState } from "react";
import { api, Opportunity, Client } from "@/lib/api";
import { Users, Plus, Search, Building2, MoreHorizontal, DollarSign, Sparkles, UserPlus, X, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useToastStore } from "@/stores/toast";

const STAGES = [
    { id: "new", label: "Nuevos", color: "blue" },
    { id: "qualified", label: "Cualificados", color: "indigo" },
    { id: "proposal", label: "Propuesta", color: "emerald" },
    { id: "won", label: "Ganados", color: "emerald" },
    { id: "lost", label: "Perdidos", color: "red" },
];

export default function CRMPipelinePage() {
    const toast = useToastStore();
    const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [search, setSearch] = useState("");
    const [taskLoading, setTaskLoading] = useState(false);

    const [title, setTitle] = useState("");
    const [expectedValue, setExpectedValue] = useState("");
    const [clientId, setClientId] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { loadData(); }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [oppRes, cliRes] = await Promise.all([api.crm.opportunities.list(), api.erp.clients.list()]);
            setOpportunities(oppRes);
            setClients(cliRes);
            if (cliRes.length > 0 && !clientId) setClientId(cliRes[0].id);
        } catch (e) { console.error(e); }
        finally { setIsLoading(false); }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            await api.crm.opportunities.create({ title, expected_value: parseFloat(expectedValue), client_id: clientId, stage: "new" });
            setShowModal(false);
            setTitle(""); setExpectedValue("");
            await loadData();
        } catch { toast.error("Error al crear la oportunidad"); }
        finally { setIsSubmitting(false); }
    };

    const handleStageChange = async (oppId: string, newStage: string) => {
        setOpportunities(opps => opps.map(o => o.id === oppId ? { ...o, stage: newStage as any } : o));
        try { await api.crm.opportunities.update(oppId, { stage: newStage as any }); }
        catch { await loadData(); }
    };

    const handleDelete = async (oppId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm("\u00bfEliminar esta oportunidad?")) return;
        try { await api.crm.opportunities.delete(oppId); await loadData(); }
        catch (err) { console.error(err); }
    };

    const handleAiQualify = async () => {
        setTaskLoading(true);
        try {
            await api.tasks.create("crm", "Analiza todas mis oportunidades nuevas y cualifícalas según su valor y potencial. Dame un resumen de cuáles debo priorizar esta semana.");
            toast.info("Tarea de análisis CRM enviada a la IA. Revisa /tareas para ver el resultado.");
        } catch (e) { console.error(e); toast.error("Error al enviar tarea a la IA"); }
        finally { setTaskLoading(false); }
    };

    const formatCurrency = (val: number) => new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(val);

    const handleDragStart = (e: React.DragEvent, oppId: string) => { e.dataTransfer.setData("oppId", oppId); };
    const handleDrop = (e: React.DragEvent, stageId: string) => {
        e.preventDefault();
        const oppId = e.dataTransfer.getData("oppId");
        if (oppId) {
            const opp = opportunities.find(o => o.id === oppId);
            if (opp && opp.stage !== stageId) handleStageChange(oppId, stageId);
        }
    };
    const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); };

    const filteredOpps = opportunities.filter(o => {
        if (!search) return true;
        const clientName = clients.find(c => c.id === o.client_id)?.name ?? "";
        return o.title.toLowerCase().includes(search.toLowerCase()) || clientName.toLowerCase().includes(search.toLowerCase());
    });

    return (
        <div className="min-h-screen bg-[#09090b] text-white p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-white flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/10 rounded-xl"><Users className="w-8 h-8 text-indigo-400" /></div>
                        Embudo de Ventas (CRM)
                    </h1>
                    <p className="text-zinc-400 mt-2 ml-14 text-sm">Gestiona tus leads o deja que la IA los cualifique.</p>
                </div>
                <div className="flex gap-3">
                    <div className="relative">
                        <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input type="text" placeholder="Buscar oportunidad..." value={search} onChange={e => setSearch(e.target.value)}
                            className="bg-[#111113] border border-zinc-800 text-sm text-white rounded-full pl-10 pr-4 py-2.5 focus:outline-none focus:border-indigo-500 w-64" />
                    </div>
                    <button onClick={() => setShowModal(true)} className="flex items-center gap-2 bg-white hover:bg-zinc-200 text-black px-5 py-2.5 rounded-full font-medium transition-colors">
                        <Plus className="w-4 h-4" /> Nuevo Trato
                    </button>
                    <button onClick={handleAiQualify} disabled={taskLoading} className="flex items-center gap-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 border border-indigo-500/20 px-5 py-2.5 rounded-full font-medium transition-colors disabled:opacity-50">
                        <Sparkles className="w-4 h-4" /> {taskLoading ? "Enviando..." : "Pedir a la IA"}
                    </button>
                </div>
            </div>

            <div className="flex gap-6 overflow-x-auto pb-8 h-[calc(100vh-200px)]">
                {STAGES.map(stage => {
                    const stageOpps = filteredOpps.filter(o => o.stage === stage.id);
                    const totalValue = stageOpps.reduce((sum, o) => sum + o.expected_value, 0);
                    return (
                        <div key={stage.id} className="flex flex-col min-w-[320px] max-w-[320px] bg-[#111113] border border-zinc-800/50 rounded-2xl overflow-hidden"
                            onDrop={(e) => handleDrop(e, stage.id)} onDragOver={handleDragOver}>
                            <div className="p-4 border-b border-zinc-800/50 bg-[#161618]">
                                <div className="flex justify-between items-center mb-1">
                                    <h3 className="font-medium text-zinc-200">{stage.label}</h3>
                                    <span className="text-xs font-semibold bg-zinc-800 text-zinc-400 px-2.5 py-1 rounded-full">{stageOpps.length}</span>
                                </div>
                                <p className="text-sm font-medium text-emerald-400">{formatCurrency(totalValue)}</p>
                            </div>
                            <div className="flex-1 p-3 space-y-3 overflow-y-auto">
                                {stageOpps.map(opp => (
                                    <div key={opp.id} draggable onDragStart={(e) => handleDragStart(e, opp.id)}
                                        className="bg-[#09090b] border border-zinc-800 hover:border-indigo-500/50 p-4 rounded-xl cursor-grab active:cursor-grabbing transition-colors group relative">
                                        <div className="flex justify-between items-start mb-2">
                                            <h4 className="font-medium text-white text-sm leading-tight pr-6">{opp.title}</h4>
                                            <button onClick={(e) => handleDelete(opp.id, e)} className="text-zinc-700 hover:text-red-400 transition-colors absolute right-4 top-4">
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-zinc-500 mb-4">
                                            <Building2 className="w-3 h-3" />
                                            <span className="truncate">{clients.find(c => c.id === opp.client_id)?.name || "Cliente desconocido"}</span>
                                        </div>
                                        <div className="flex items-center justify-between pt-3 border-t border-zinc-800/50">
                                            <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-400">
                                                <DollarSign className="w-3.5 h-3.5" />
                                                {formatCurrency(opp.expected_value)}
                                            </div>
                                            <span className="text-[10px] text-zinc-600">{format(new Date(opp.created_at), "d MMM", { locale: es })}</span>
                                        </div>
                                    </div>
                                ))}
                                {stageOpps.length === 0 && (
                                    <div className="h-24 border-2 border-dashed border-zinc-800/50 rounded-xl flex items-center justify-center text-zinc-600 text-sm">
                                        Arrastra un trato aqu\u00ed
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {showModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-[#111113] border border-zinc-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
                        <div className="p-6 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                            <h2 className="text-xl font-medium text-white flex items-center gap-2">
                                <UserPlus className="w-5 h-5 text-indigo-400" /> Nueva Oportunidad
                            </h2>
                            <button onClick={() => setShowModal(false)} className="text-zinc-400 hover:text-white"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleCreate} className="p-6 space-y-5">
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Nombre del Trato</label>
                                <input type="text" required value={title} onChange={e => setTitle(e.target.value)}
                                    placeholder="Ej: Renovaci\u00f3n Licencias Anuales"
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500" />
                            </div>
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Cliente Relacionado</label>
                                <select required value={clientId} onChange={e => setClientId(e.target.value)}
                                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500">
                                    <option value="" disabled>Selecciona un cliente</option>
                                    {clients.map(c => <option key={c.id} value={c.id}>{c.name} ({c.nif || "Sin NIF"})</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Valor Esperado (\u20ac)</label>
                                <div className="relative">
                                    <DollarSign className="w-4 h-4 text-zinc-500 absolute left-4 top-1/2 -translate-y-1/2" />
                                    <input type="number" required min="0" step="0.01" value={expectedValue} onChange={e => setExpectedValue(e.target.value)}
                                        placeholder="0.00"
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg pl-11 pr-4 py-2.5 text-white focus:outline-none focus:border-indigo-500" />
                                </div>
                            </div>
                            <div className="pt-4 flex justify-end gap-3 border-t border-zinc-800/50">
                                <button type="button" onClick={() => setShowModal(false)} className="px-5 py-2.5 text-zinc-300 hover:text-white font-medium">Cancelar</button>
                                <button type="submit" disabled={isSubmitting || !clientId}
                                    className="bg-white hover:bg-zinc-200 text-black px-6 py-2.5 rounded-lg font-medium disabled:opacity-50">
                                    {isSubmitting ? "Creando..." : "Crear Trato"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

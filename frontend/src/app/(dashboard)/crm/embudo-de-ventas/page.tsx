"use client";

import { useEffect, useState } from "react";
import { api, Opportunity, Client } from "@/lib/api";
import { Users, Plus, Search, Building2, DollarSign, Sparkles, UserPlus, X, Trash2, GripVertical } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const STAGES: { id: string; label: string; variant: "info" | "default" | "success" | "destructive" | "warning" }[] = [
    { id: "new", label: "Nuevos", variant: "info" },
    { id: "qualified", label: "Cualificados", variant: "default" },
    { id: "proposal", label: "Propuesta", variant: "warning" },
    { id: "won", label: "Ganados", variant: "success" },
    { id: "lost", label: "Perdidos", variant: "destructive" },
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
        } catch (e) { logError("crm/embudo-de-ventas/page", e); }
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
        if (!await showConfirm({ message: "¿Eliminar esta oportunidad?", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        try { await api.crm.opportunities.delete(oppId); await loadData(); }
        catch (err) { logError("crm/embudo-de-ventas/page", err); }
    };

    const handleAiQualify = async () => {
        setTaskLoading(true);
        try {
            await api.tasks.create("crm", "Analiza todas mis oportunidades nuevas y cualifícalas según su valor y potencial. Dame un resumen de cuáles debo priorizar esta semana.");
            toast.info("Tarea de análisis CRM enviada a la IA. Revisa /tareas para ver el resultado.");
        } catch (e) { logError("crm/embudo-de-ventas/page", e); toast.error("Error al enviar tarea a la IA"); }
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
        <div className="min-h-screen bg-background text-foreground p-8">
            <PageHeader
                title="Embudo de Ventas (CRM)"
                description="Gestiona tus leads o deja que la IA los cualifique."
                icon={Users}
                actions={
                    <div className="flex items-center gap-2">
                        <div className="relative">
                            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                            <Input
                                type="text"
                                placeholder="Buscar oportunidad..."
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                className="pl-10 w-64"
                            />
                        </div>
                        <Button onClick={() => setShowModal(true)} variant="secondary">
                            <Plus className="w-4 h-4 mr-2" /> Nuevo Trato
                        </Button>
                        <Button onClick={handleAiQualify} disabled={taskLoading} variant="outline">
                            <Sparkles className="w-4 h-4 mr-2" /> {taskLoading ? "Enviando..." : "Pedir a la IA"}
                        </Button>
                    </div>
                }
            />

            <div className="flex gap-4 overflow-x-auto pb-8 mt-6 h-[calc(100vh-200px)]">
                {STAGES.map(stage => {
                    const stageOpps = filteredOpps.filter(o => o.stage === stage.id);
                    const totalValue = stageOpps.reduce((sum, o) => sum + o.expected_value, 0);
                    return (
                        <Card
                            key={stage.id}
                            className="flex flex-col min-w-[320px] max-w-[320px] overflow-hidden"
                            onDrop={(e) => handleDrop(e, stage.id)}
                            onDragOver={handleDragOver}
                        >
                            <CardHeader className="p-4 pb-3 bg-muted/50 border-b border-border space-y-1">
                                <div className="flex justify-between items-center">
                                    <CardTitle className="text-sm font-medium text-foreground">{stage.label}</CardTitle>
                                    <Badge variant="secondary" className="text-xs">
                                        {stageOpps.length}
                                    </Badge>
                                </div>
                                <p className="text-sm font-medium text-primary">{formatCurrency(totalValue)}</p>
                            </CardHeader>
                            <CardContent className="flex-1 p-3 space-y-3 overflow-y-auto">
                                {stageOpps.map(opp => (
                                    <Card
                                        key={opp.id}
                                        draggable
                                        onDragStart={(e) => handleDragStart(e, opp.id)}
                                        className="hover:border-primary/30 cursor-grab active:cursor-grabbing transition-colors group relative"
                                    >
                                        <CardContent className="p-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <h4 className="font-medium text-foreground text-sm leading-tight pr-6">{opp.title}</h4>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-6 w-6 absolute right-3 top-3 text-muted-foreground hover:text-destructive"
                                                    onClick={(e) => handleDelete(opp.id, e)}
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </Button>
                                            </div>
                                            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4">
                                                <Building2 className="w-3 h-3" />
                                                <span className="truncate">{clients.find(c => c.id === opp.client_id)?.name || "Cliente desconocido"}</span>
                                            </div>
                                            <div className="flex items-center justify-between pt-3 border-t border-border">
                                                <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
                                                    <DollarSign className="w-3.5 h-3.5" />
                                                    {formatCurrency(opp.expected_value)}
                                                </div>
                                                <span className="text-[10px] text-muted-foreground">{format(new Date(opp.created_at), "d MMM", { locale: es })}</span>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                                {stageOpps.length === 0 && (
                                    <div className="h-24 border-2 border-dashed border-border rounded-lg flex items-center justify-center text-muted-foreground text-sm">
                                        Arrastra un trato aquí
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            {/* Create Opportunity Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <Card className="w-full max-w-lg overflow-hidden shadow-2xl">
                        <CardHeader className="p-6 border-b border-border bg-muted/50 flex-row items-center justify-between space-y-0">
                            <CardTitle className="text-lg font-medium text-foreground flex items-center gap-2">
                                <UserPlus className="w-5 h-5 text-primary" /> Nueva Oportunidad
                            </CardTitle>
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setShowModal(false)}>
                                <X className="w-5 h-5" />
                            </Button>
                        </CardHeader>
                        <form onSubmit={handleCreate} className="p-6 space-y-5">
                            <div className="space-y-1.5">
                                <Label htmlFor="deal-title">Nombre del Trato</Label>
                                <Input
                                    id="deal-title"
                                    type="text"
                                    required
                                    value={title}
                                    onChange={e => setTitle(e.target.value)}
                                    placeholder="Ej: Renovación Licencias Anuales"
                                />
                            </div>
                            <div className="space-y-1.5">
                                <Label htmlFor="deal-client">Cliente Relacionado</Label>
                                <select
                                    id="deal-client"
                                    required
                                    value={clientId}
                                    onChange={e => setClientId(e.target.value)}
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                                >
                                    <option value="" disabled>Selecciona un cliente</option>
                                    {clients.map(c => <option key={c.id} value={c.id}>{c.name} ({c.nif || "Sin NIF"})</option>)}
                                </select>
                            </div>
                            <div className="space-y-1.5">
                                <Label htmlFor="deal-value">Valor Esperado (&euro;)</Label>
                                <div className="relative">
                                    <DollarSign className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                                    <Input
                                        id="deal-value"
                                        type="number"
                                        required
                                        min="0"
                                        step="0.01"
                                        value={expectedValue}
                                        onChange={e => setExpectedValue(e.target.value)}
                                        placeholder="0.00"
                                        className="pl-10"
                                    />
                                </div>
                            </div>
                            <div className="pt-4 flex justify-end gap-3 border-t border-border">
                                <Button type="button" variant="ghost" onClick={() => setShowModal(false)}>
                                    Cancelar
                                </Button>
                                <Button type="submit" disabled={isSubmitting || !clientId}>
                                    {isSubmitting ? "Creando..." : "Crear Trato"}
                                </Button>
                            </div>
                        </form>
                    </Card>
                </div>
            )}
        </div>
    );
}

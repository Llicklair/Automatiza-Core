"use client";

import { useEffect, useState } from "react";
import { api, Opportunity, Client } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

export function useEmbudoDeVentas() {
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

    return {
        opportunities, clients, isLoading,
        showModal, setShowModal,
        search, setSearch,
        taskLoading,
        title, setTitle,
        expectedValue, setExpectedValue,
        clientId, setClientId,
        isSubmitting,
        handleCreate, handleStageChange, handleDelete, handleAiQualify,
        formatCurrency, handleDragStart, handleDrop, handleDragOver,
        filteredOpps,
    };
}

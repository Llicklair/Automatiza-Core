"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, Activity, Client } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { Phone, Mail, StickyNote, Bot, CalendarCheck } from "lucide-react";

export function useActividades() {
    const t = useTranslations("crm");
    const toast = useToastStore();
    const [activities, setActivities] = useState<Activity[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);

    const [selectedClient, setSelectedClient] = useState("");
    const [type, setType] = useState("note");
    const [description, setDescription] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [actRes, cliRes] = await Promise.all([
                api.crm.activities.list(),
                api.erp.clients.list()
            ]);
            setActivities(actRes);
            setClients(cliRes);
        } catch (error) {
            logError("crm/actividades/page", error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            await api.crm.activities.create({
                client_id: selectedClient || null,
                type: type,
                description: description,
                metadata_json: { source: "manual" }
            });
            setShowModal(false);
            setDescription("");
            setType("note");
            setSelectedClient("");
            await loadData();
        } catch (error) {
            logError("crm/actividades/page", error);
            toast.error(t("actividades.createError"));
        } finally {
            setIsSubmitting(false);
        }
    };

    const deleteActivity = async (id: string) => {
        if (!await showConfirm({ message: t("actividades.deleteConfirm"), confirmLabel: t("actividades.delete"), confirmVariant: "danger" })) return;
        try {
            await api.crm.activities.delete(id);
            setActivities(prev => prev.filter(a => a.id !== id));
        } catch {
            toast.error(t("actividades.deleteError"));
        }
    };

    const getActivityIcon = (actType: string, source?: string) => {
        if (source === "ai") return <Bot className="w-5 h-5 text-primary" />;
        switch (actType) {
            case "call": return <Phone className="w-5 h-5 text-emerald-400" />;
            case "email": return <Mail className="w-5 h-5 text-blue-400" />;
            case "meeting_log": return <CalendarCheck className="w-5 h-5 text-purple-400" />;
            default: return <StickyNote className="w-5 h-5 text-amber-400" />;
        }
    };

    const getClientName = (clientId: string | null) => {
        if (!clientId) return t("actividades.unassigned");
        const c = clients.find(c => c.id === clientId);
        return c ? c.name : t("actividades.unknownClient");
    };

    return {
        activities, clients, isLoading,
        showModal, setShowModal,
        selectedClient, setSelectedClient,
        type, setType,
        description, setDescription,
        isSubmitting,
        handleCreate, deleteActivity,
        getActivityIcon, getClientName,
    };
}

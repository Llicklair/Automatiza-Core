"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { templatesApi, DocumentTemplate, PreviewRequest } from "@/lib/api/templates";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { EMPTY_FORM } from "../_components/templateOptions";

type ActiveType = "invoice" | "payroll" | "excel" | "albaran" | "contract";

export function usePlantillas() {
    const t = useTranslations("plantillas");
    const { show: showToast } = useToastStore();
    const [activeType, setActiveType] = useState<ActiveType>("invoice");
    const [templates, setTemplates]   = useState<DocumentTemplate[]>([]);
    const [loading, setLoading]       = useState(true);
    const [showForm, setShowForm]     = useState(false);
    const [editingId, setEditingId]   = useState<string | null>(null);
    const [form, setForm]             = useState({ ...EMPTY_FORM });
    const [saving, setSaving]         = useState(false);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [previewing, setPreviewing] = useState(false);
    const previewDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

    const load = async () => {
        setLoading(true);
        try {
            const data = await templatesApi.list(activeType);
            setTemplates(data);
        } catch {
            showToast(t("toasts.loadError"), "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { if (activeType !== "contract") load(); }, [activeType]); // eslint-disable-line react-hooks/exhaustive-deps

    const handleSeedDefaults = async () => {
        try {
            await templatesApi.seedDefaults(activeType);
            showToast(t("toasts.seedSuccess"), "success");
            load();
        } catch {
            showToast(t("toasts.seedError"), "error");
        }
    };

    const openNew = () => {
        setEditingId(null);
        const t = activeType === "contract" ? "invoice" : activeType;
        setForm({ ...EMPTY_FORM, template_type: t });
        setPreviewUrl(null);
        setShowForm(true);
    };

    const openEdit = (tpl: DocumentTemplate) => {
        setEditingId(tpl.id);
        setForm({ ...tpl });
        setPreviewUrl(null);
        setShowForm(true);
    };

    const handleSave = async () => {
        if (!form.name.trim()) { showToast(t("toasts.nameRequired"), "warning"); return; }
        setSaving(true);
        try {
            if (editingId) {
                await templatesApi.update(editingId, form);
                await templatesApi.setDefault(editingId);
                showToast(t("toasts.savedDefault"), "success");
            } else {
                const created = await templatesApi.create(form);
                await templatesApi.setDefault(created.id);
                showToast(t("toasts.createdDefault"), "success");
            }
            setShowForm(false);
            await load();
        } catch {
            showToast(t("toasts.saveError"), "error");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (tpl: DocumentTemplate) => {
        const confirmed = await showConfirm({
            title: t("confirmDelete.title"),
            message: t("confirmDelete.message", { name: tpl.name }),
            confirmLabel: t("confirmDelete.confirmLabel"),
            confirmVariant: "danger",
        });
        if (!confirmed) return;
        try {
            await templatesApi.delete(tpl.id);
            showToast(t("toasts.deleteSuccess"), "success");
            await load();
        } catch {
            showToast(t("toasts.deleteError"), "error");
        }
    };

    const handleSetDefault = async (tpl: DocumentTemplate) => {
        try {
            await templatesApi.setDefault(tpl.id);
            showToast(t("toasts.setDefaultSuccess", { name: tpl.name }), "success");
            await load();
        } catch {
            showToast(t("toasts.setDefaultError"), "error");
        }
    };

    const handlePreview = async () => {
        setPreviewing(true);
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        try {
            const url = await templatesApi.preview(form as PreviewRequest);
            setPreviewUrl(url);
        } catch {
            showToast(t("toasts.previewError"), "error");
        } finally {
            setPreviewing(false);
        }
    };

    // Auto-refresh preview when form changes (only if preview was already opened)
    useEffect(() => {
        if (!showForm || !previewUrl) return;
        if (previewDebounce.current) clearTimeout(previewDebounce.current);
        previewDebounce.current = setTimeout(() => { handlePreview(); }, 1200);
        return () => { if (previewDebounce.current) clearTimeout(previewDebounce.current); };
    }, [form]); // eslint-disable-line react-hooks/exhaustive-deps

    const setField = (key: keyof typeof form, value: any) =>
        setForm(f => ({ ...f, [key]: value }));

    const switchType = (type: ActiveType) => {
        setActiveType(type);
        setShowForm(false);
    };

    const closePreview = () => {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setPreviewUrl(null);
    };

    return {
        activeType, switchType,
        templates, loading, load,
        showForm, setShowForm,
        editingId, form, setField,
        saving, previewUrl, previewing,
        openNew, openEdit,
        handleSave, handleDelete, handleSetDefault, handlePreview, closePreview,
        handleSeedDefaults,
    };
}

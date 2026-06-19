"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";

export function useConfiguracionEmpresa() {
    const t = useTranslations("configuracion");
    const [name, setName] = useState("");
    const [nif, setNif] = useState("");
    const [address, setAddress] = useState("");
    const [phone, setPhone] = useState("");
    const [contactEmail, setContactEmail] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    useEffect(() => {
        let mounted = true;
        api.tenant.me()
            .then((t) => {
                if (!mounted) return;
                setName(t.name);
                setNif(t.nif);
                setAddress(t.address || "");
                setPhone(t.phone || "");
                setContactEmail(t.contact_email || "");
            })
            .catch((e: any) => {
                if (!mounted) return;
                setError(e?.message || t("empresa.errorLoad"));
            })
            .finally(() => {
                if (mounted) setLoading(false);
            });
        return () => { mounted = false; };
    }, [t]);

    async function handleSave(e: React.FormEvent) {
        e.preventDefault();
        setError(null);
        setSuccess(null);
        try {
            setSaving(true);
            const updated = await api.tenant.updateMe({
                name,
                nif,
                address,
                phone,
                contact_email: contactEmail,
            });
            setName(updated.name);
            setNif(updated.nif);
            setAddress(updated.address || "");
            setPhone(updated.phone || "");
            setContactEmail(updated.contact_email || "");
            setSuccess(t("empresa.saveSuccess"));
        } catch (e: any) {
            setError(e?.message || t("empresa.errorSave"));
        } finally {
            setSaving(false);
        }
    }

    return {
        name, setName,
        nif, setNif,
        address, setAddress,
        phone, setPhone,
        contactEmail, setContactEmail,
        loading,
        saving,
        error,
        success,
        handleSave,
    };
}

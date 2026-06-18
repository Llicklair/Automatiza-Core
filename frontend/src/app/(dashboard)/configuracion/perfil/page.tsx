"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import {
    User, ArrowLeft, Save, Loader2, CheckCircle2, AlertTriangle,
} from "lucide-react";
import { PageContainer } from "@/components/shared/PageContainer";

export default function PerfilPage() {
    const t = useTranslations("configuracion");
    const router = useRouter();
    const [name, setName] = useState("");
    const [nif, setNif] = useState("");
    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

    useEffect(() => {
        api.tenant.me().then(d => { setName(d.name || ""); setNif(d.nif || ""); }).catch(() => {});
    }, []);

    async function save() {
        setSaving(true);
        setMsg(null);
        try {
            await api.tenant.updateMe({ name, nif });
            setMsg({ type: "ok", text: t("perfil.saveOk") });
        } catch {
            setMsg({ type: "err", text: t("perfil.saveError") });
        } finally {
            setSaving(false);
        }
    }

    return (
        <PageContainer width="full" className="max-w-lg mx-auto">
            <button
                onClick={() => router.back()}
                className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition mb-6"
            >
                <ArrowLeft className="w-4 h-4" /> {t("perfil.back")}
            </button>

            <div className="bg-card border border-border rounded-2xl p-6">
                <h1 className="text-xl font-bold text-foreground flex items-center gap-2 mb-6">
                    <User className="w-5 h-5 text-primary" /> {t("perfil.title")}
                </h1>

                <div className="space-y-4">
                    <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">{t("perfil.companyName")}</label>
                        <input
                            value={name}
                            onChange={e => setName(e.target.value)}
                            className="w-full px-3 py-2.5 rounded-lg bg-muted border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary/20 transition"
                            placeholder={t("perfil.companyNamePlaceholder")}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">{t("perfil.nifLabel")}</label>
                        <input
                            value={nif}
                            onChange={e => setNif(e.target.value)}
                            className="w-full px-3 py-2.5 rounded-lg bg-muted border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary/20 transition"
                            placeholder="B12345678"
                        />
                    </div>
                </div>

                {msg && (
                    <p className={`mt-4 text-xs flex items-center gap-1.5 ${msg.type === "ok" ? "text-emerald-400" : "text-red-400"}`}>
                        {msg.type === "ok" ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                        {msg.text}
                    </p>
                )}

                <div className="flex justify-end mt-6">
                    <button
                        onClick={save}
                        disabled={saving}
                        className="flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-primary hover:bg-primary disabled:opacity-50 text-foreground text-sm font-medium transition"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        {t("perfil.save")}
                    </button>
                </div>
            </div>
        </PageContainer>
    );
}

"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { BadgeCheck, Stamp, ShieldCheck, FileText, Archive } from "lucide-react";
import { ModoVerifactuPanel } from "./ModoVerifactuPanel";
import { ApoderamientoPanel } from "./ApoderamientoPanel";
import { FirmaDigitalPanel } from "./FirmaDigitalPanel";
import { DeclaracionResponsablePanel } from "./DeclaracionResponsablePanel";
import { ExportPanel } from "./ExportPanel";
import { PageContainer } from "@/components/shared/PageContainer";

type Tab = "verifactu" | "apoderamiento" | "firma" | "declaracion" | "export";

export default function ConfiguracionFiscalPage() {
    const t = useTranslations("configuracion");
    const searchParams = useSearchParams();
    const initial = searchParams.get("tab");
    const [tab, setTab] = useState<Tab>(
        initial === "apoderamiento" || initial === "firma" || initial === "declaracion" || initial === "export"
            ? initial
            : "verifactu"
    );

    const tabs: { key: Tab; label: string; icon: typeof BadgeCheck }[] = [
        { key: "verifactu", label: t("verifactu.tabVerifactu"), icon: BadgeCheck },
        { key: "apoderamiento", label: t("verifactu.tabApoderamiento"), icon: Stamp },
        { key: "firma", label: t("verifactu.tabFirma"), icon: ShieldCheck },
        { key: "declaracion", label: t("verifactu.tabDeclaracion"), icon: FileText },
        { key: "export", label: t("verifactu.tabExport"), icon: Archive },
    ];

    return (
        <PageContainer width="3xl">
            <div>
                <h1 className="text-xl font-bold text-foreground">{t("verifactu.pageTitle")}</h1>
                <p className="text-sm text-muted-foreground mt-1">
                    {t("verifactu.pageSubtitle")}
                </p>
            </div>

            <div className="flex items-center gap-1 border-b border-border">
                {tabs.map(t => {
                    const Icon = t.icon;
                    const active = tab === t.key;
                    return (
                        <button
                            key={t.key}
                            onClick={() => setTab(t.key)}
                            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                                active
                                    ? "border-primary text-foreground"
                                    : "border-transparent text-muted-foreground hover:text-foreground"
                            }`}>
                            <Icon className="w-4 h-4" /> {t.label}
                        </button>
                    );
                })}
            </div>

            {tab === "verifactu" && <ModoVerifactuPanel />}
            {tab === "apoderamiento" && <ApoderamientoPanel />}
            {tab === "firma" && <FirmaDigitalPanel />}
            {tab === "declaracion" && <DeclaracionResponsablePanel />}
            {tab === "export" && <ExportPanel />}
        </PageContainer>
    );
}

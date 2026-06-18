"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import {
    Users2, FileText, Package, Bot, Zap, Building2,
    ShoppingCart, BarChart3, KeyRound
} from "lucide-react";
import { api } from "@/lib/api";

export interface Step {
    id: string;
    title: string;
    description: string;
    detail: string;
    icon: any;
    color: string;
    href?: string;
    hrefLabel?: string;
    tips: string[];
    prerequisite?: string;
}

export const buildSteps = (t: ReturnType<typeof useTranslations>): Step[] => [
    {
        id: "empresa",
        title: t("steps.empresa.title"),
        description: t("steps.empresa.description"),
        detail: t("steps.empresa.detail"),
        icon: Building2,
        color: "indigo",
        href: "/configuracion/empresa",
        hrefLabel: t("steps.empresa.hrefLabel"),
        tips: [
            t("steps.empresa.tips.0"),
            t("steps.empresa.tips.1"),
        ],
    },
    {
        id: "api_keys",
        title: t("steps.apiKeys.title"),
        description: t("steps.apiKeys.description"),
        detail: t("steps.apiKeys.detail"),
        icon: KeyRound,
        color: "violet",
        href: "/configuracion/api-keys",
        hrefLabel: t("steps.apiKeys.hrefLabel"),
        tips: [
            t("steps.apiKeys.tips.0"),
            t("steps.apiKeys.tips.1"),
        ],
        prerequisite: "empresa",
    },
    {
        id: "clientes",
        title: t("steps.clientes.title"),
        description: t("steps.clientes.description"),
        detail: t("steps.clientes.detail"),
        icon: Users2,
        color: "blue",
        href: "/clientes",
        hrefLabel: t("steps.clientes.hrefLabel"),
        tips: [
            t("steps.clientes.tips.0"),
            t("steps.clientes.tips.1"),
        ],
        prerequisite: "api_keys",
    },
    {
        id: "catalogo",
        title: t("steps.catalogo.title"),
        description: t("steps.catalogo.description"),
        detail: t("steps.catalogo.detail"),
        icon: Package,
        color: "emerald",
        href: "/catalogo",
        hrefLabel: t("steps.catalogo.hrefLabel"),
        tips: [
            t("steps.catalogo.tips.0"),
            t("steps.catalogo.tips.1"),
        ],
        prerequisite: "clientes",
    },
    {
        id: "factura",
        title: t("steps.factura.title"),
        description: t("steps.factura.description"),
        detail: t("steps.factura.detail"),
        icon: FileText,
        color: "violet",
        href: "/ventas/facturas/nueva",
        hrefLabel: t("steps.factura.hrefLabel"),
        tips: [
            t("steps.factura.tips.0"),
            t("steps.factura.tips.1"),
        ],
        prerequisite: "catalogo",
    },
    {
        id: "ia",
        title: t("steps.ia.title"),
        description: t("steps.ia.description"),
        detail: t("steps.ia.detail"),
        icon: Bot,
        color: "amber",
        tips: [
            t("steps.ia.tips.0"),
            t("steps.ia.tips.1"),
            t("steps.ia.tips.2"),
        ],
        prerequisite: "factura",
    },
    {
        id: "compras",
        title: t("steps.compras.title"),
        description: t("steps.compras.description"),
        detail: t("steps.compras.detail"),
        icon: ShoppingCart,
        color: "rose",
        href: "/compras/facturas",
        hrefLabel: t("steps.compras.hrefLabel"),
        tips: [
            t("steps.compras.tips.0"),
            t("steps.compras.tips.1"),
        ],
        prerequisite: "ia",
    },
    {
        id: "automatizaciones",
        title: t("steps.automatizaciones.title"),
        description: t("steps.automatizaciones.description"),
        detail: t("steps.automatizaciones.detail"),
        icon: Zap,
        color: "orange",
        href: "/automatizaciones",
        hrefLabel: t("steps.automatizaciones.hrefLabel"),
        tips: [
            t("steps.automatizaciones.tips.0"),
            t("steps.automatizaciones.tips.1"),
            t("steps.automatizaciones.tips.2"),
        ],
        prerequisite: "compras",
    },
    {
        id: "analítica",
        title: t("steps.analitica.title"),
        description: t("steps.analitica.description"),
        detail: t("steps.analitica.detail"),
        icon: BarChart3,
        color: "teal",
        href: "/analitica",
        hrefLabel: t("steps.analitica.hrefLabel"),
        tips: [
            t("steps.analitica.tips.0"),
            t("steps.analitica.tips.1"),
        ],
        prerequisite: "compras",
    },
];

export const COLOR_MAP: Record<string, { bg: string; border: string; text: string; ring: string; dot: string }> = {
    indigo: { bg: "bg-primary/10", border: "border-primary/20", text: "text-primary", ring: "ring-primary/30", dot: "bg-primary" },
    blue:   { bg: "bg-blue-500/10",   border: "border-blue-500/20",   text: "text-blue-400",   ring: "ring-blue-500/30",   dot: "bg-blue-500" },
    emerald:{ bg: "bg-emerald-500/10",border: "border-emerald-500/20",text: "text-emerald-400",ring: "ring-emerald-500/30",dot: "bg-emerald-500" },
    violet: { bg: "bg-violet-500/10", border: "border-violet-500/20", text: "text-violet-400", ring: "ring-violet-500/30", dot: "bg-violet-500" },
    amber:  { bg: "bg-amber-500/10",  border: "border-amber-500/20",  text: "text-amber-400",  ring: "ring-amber-500/30",  dot: "bg-amber-500" },
    rose:   { bg: "bg-rose-500/10",   border: "border-rose-500/20",   text: "text-rose-400",   ring: "ring-rose-500/30",   dot: "bg-rose-500" },
    orange: { bg: "bg-orange-500/10", border: "border-orange-500/20", text: "text-orange-400", ring: "ring-orange-500/30", dot: "bg-orange-500" },
    teal:   { bg: "bg-teal-500/10",   border: "border-teal-500/20",   text: "text-teal-400",   ring: "ring-teal-500/30",   dot: "bg-teal-500" },
};

export const buildIaExamples = (t: ReturnType<typeof useTranslations>): string[] => [
    t("iaExamples.0"),
    t("iaExamples.1"),
    t("iaExamples.2"),
    t("iaExamples.3"),
    t("iaExamples.4"),
    t("iaExamples.5"),
];

const IA_EXAMPLES_COUNT = 6;

export function usePrimerosPassos() {
    const t = useTranslations("primerosPasos");
    const steps = buildSteps(t);
    const iaExamples = buildIaExamples(t);

    const [completed, setCompleted] = useState<Set<string>>(new Set());
    const [expanded, setExpanded] = useState<string | null>("empresa");
    const [iaExample, setIaExample] = useState(0);

    useEffect(() => {
        const saved = localStorage.getItem("onboarding_completed");
        const base = new Set<string>(saved ? JSON.parse(saved) : []);

        Promise.all([api.tenant.me(), api.tenant.getLlmConfig()])
            .then(([tenant, llm]) => {
                if (tenant.nif && tenant.name) base.add("empresa");
                else base.delete("empresa");
                // claude_code funciona con el CLI (sin key); en otro caso, el
                // proveedor activo debe tener clave. (Igual que el banner.)
                const active = llm.active_llm_provider;
                const configured =
                    active === "claude_code" || Boolean(llm.providers?.[active]?.has_key);
                if (configured) base.add("api_keys");
                else base.delete("api_keys");
                setCompleted(new Set(base));
            })
            .catch(() => setCompleted(new Set(base)));
    }, []);

    const toggle = (id: string) => {
        setCompleted(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            localStorage.setItem("onboarding_completed", JSON.stringify(Array.from(next)));
            return next;
        });
    };

    const expand = (id: string) => setExpanded(prev => prev === id ? null : id);

    useEffect(() => {
        const timer = setInterval(() => setIaExample(i => (i + 1) % IA_EXAMPLES_COUNT), 3000);
        return () => clearInterval(timer);
    }, []);

    const completedCount = completed.size;
    const totalSteps = steps.length;
    const pct = Math.round((completedCount / totalSteps) * 100);

    const isLocked = (step: Step) => {
        if (!step.prerequisite) return false;
        return !completed.has(step.prerequisite);
    };

    return { steps, iaExamples, completed, expanded, iaExample, toggle, expand, completedCount, totalSteps, pct, isLocked };
}

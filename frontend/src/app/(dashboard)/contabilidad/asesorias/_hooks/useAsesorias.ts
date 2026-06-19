import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { logError } from "@/lib/logger";

const CALENDAR_TYPES: Record<string, string[]> = {
    fiscal: ["iva", "irpf_fraccionado", "informativo_anual", "iva_anual"],
    laboral: ["retenciones", "retenciones_anual"],
    mercantil: [],
};

export function useAsesorias() {
    const t = useTranslations("contabilidad");
    const [news, setNews] = useState<any[]>([]);
    const [events, setEvents] = useState<any[]>([]);
    const [guides, setGuides] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("fiscal");
    const [expandedGuide, setExpandedGuide] = useState<number | null>(null);
    const [newsSearch, setNewsSearch] = useState("");

    // Chat context
    const [chatMessages, setChatMessages] = useState<{ role: "user" | "ai", content: string }[]>([]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);

    useEffect(() => {
        async function fetchAdvisory() {
            setLoading(true);
            setExpandedGuide(null);
            try {
                const [n, e, g] = await Promise.all([
                    api.advisory.boe(filter, 8),
                    api.advisory.calendar(90),
                    api.advisory.guides(filter),
                ]);
                setNews(n || []);
                const tipos = CALENDAR_TYPES[filter] || [];
                setEvents(tipos.length > 0 ? (e || []).filter((ev: any) => tipos.includes(ev.tipo)) : []);
                setGuides(g || []);
            } catch (err) {
                logError("contabilidad/asesorias/page", err);
            } finally {
                setLoading(false);
            }
        }
        fetchAdvisory();
    }, [filter]);

    async function handleChat(e: React.FormEvent) {
        e.preventDefault();
        const prompt = chatInput.trim();
        if (!prompt) return;

        setChatInput("");
        setChatMessages(prev => [...prev, { role: "user", content: prompt }]);
        setChatLoading(true);

        try {
            const task = await api.tasks.create("compliance", prompt);
            let current = task;

            while (current.status !== "done" && current.status !== "failed" && current.status !== "cancelled") {
                await new Promise(r => setTimeout(r, 2000));
                current = await api.tasks.get(task.id);
            }

            if (current.status === "done" && current.agent_results?.length) {
                const results: any[] = current.agent_results;
                const answer = results.slice().reverse().find(
                    (r: any) => r.action_taken && r.action_taken !== "Invocando herramientas de compliance" && r.action_taken !== "Operación compliance completada."
                )?.action_taken;
                setChatMessages(prev => [...prev, { role: "ai", content: answer || t("asesorias.chatNoAnswer") }]);
            } else {
                setChatMessages(prev => [...prev, { role: "ai", content: current.error_message || t("asesorias.chatTaskFailed") }]);
            }
        } catch (err: any) {
            setChatMessages(prev => [...prev, { role: "ai", content: t("asesorias.chatConnectionError", { message: err.message }) }]);
        } finally {
            setChatLoading(false);
        }
    }

    const filteredNews = (() => {
        const q = newsSearch.toLowerCase();
        return q ? news.filter(item =>
            (item.titulo || "").toLowerCase().includes(q) ||
            (item.descripcion || "").toLowerCase().includes(q) ||
            (item.identificador || "").toLowerCase().includes(q)
        ) : news;
    })();

    return {
        news, events, guides, loading, filter, setFilter,
        expandedGuide, setExpandedGuide, newsSearch, setNewsSearch,
        chatMessages, chatInput, setChatInput, chatLoading, handleChat,
        filteredNews,
    };
}

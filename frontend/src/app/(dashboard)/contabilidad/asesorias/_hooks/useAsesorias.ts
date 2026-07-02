import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { waitForTask, TaskTimeoutError } from "@/lib/api/tasks";
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
            // Antes: bucle infinito cada 2s sin timeout. waitForTask añade el
            // timeout unificado (120s por defecto, mismo intervalo de 2s).
            const current = await waitForTask(task.id);

            if (current.status === "done" && current.agent_results?.length) {
                const results: any[] = current.agent_results;
                // La respuesta del agente va en output.response / summary, NO en
                // action_taken (que es solo una etiqueta de estado y no existe en
                // los resultados de dispatcher). Antes se leía action_taken y por eso
                // el widget mostraba siempre "No pude obtener una respuesta" pese a
                // completarse la tarea correctamente.
                const placeholders = ["Invocando herramientas de compliance", "Operación compliance completada."];
                const answer = results.slice().reverse()
                    .map((r: any) => r?.output?.response || r?.output?.message || r?.summary || r?.action_taken)
                    .find((txt: any) => typeof txt === "string" && txt.trim() && !placeholders.includes(txt));
                setChatMessages(prev => [...prev, { role: "ai", content: answer || t("asesorias.chatNoAnswer") }]);
            } else {
                setChatMessages(prev => [...prev, { role: "ai", content: current.error_message || t("asesorias.chatTaskFailed") }]);
            }
        } catch (err: any) {
            // En timeout se muestra el mismo texto que cuando la task no
            // termina en "done" (sin claves i18n nuevas).
            const content = err instanceof TaskTimeoutError
                ? t("asesorias.chatTaskFailed")
                : t("asesorias.chatConnectionError", { message: err.message });
            setChatMessages(prev => [...prev, { role: "ai", content }]);
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

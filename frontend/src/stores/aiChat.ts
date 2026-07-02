import { create } from "zustand";
import { api } from "@/lib/api";
import { waitForTask, TaskTimeoutError } from "@/lib/api/tasks";

export type AiChatMessage = { role: "user" | "assistant"; content: string };

/** Textos localizados que el store no puede resolver (no tiene locale). */
export interface AiChatTexts {
    noResponse: string;
    timeout: string;
    sendError: string;
}

interface AiChatStore {
    /** Hilo ÚNICO de conversación con la IA (dominio "chat"), compartido por
     *  todas las superficies (AiChatBar del dashboard y ChatSection de
     *  mi-equipo). Antes cada una tenía su propio historial inconexo. */
    messages: AiChatMessage[];
    sending: boolean;
    activeTaskId: string | null;
    setMessages: (msgs: AiChatMessage[]) => void;
    /** Cierra el envío en curso desde fuera (botón Detener) añadiendo un aviso. */
    markStopped: (content: string) => void;
    send: (text: string, texts: AiChatTexts) => Promise<void>;
}

export const useAiChatStore = create<AiChatStore>((set, get) => ({
    messages: [],
    sending: false,
    activeTaskId: null,

    setMessages: (msgs) => set({ messages: msgs }),

    markStopped: (content) =>
        set((s) => ({
            sending: false,
            activeTaskId: null,
            messages: [...s.messages, { role: "assistant", content }],
        })),

    send: async (text, texts) => {
        const msg = text.trim();
        if (!msg || get().sending) return;
        set((s) => ({
            sending: true,
            messages: [...s.messages, { role: "user", content: msg }],
        }));
        let answer = "";
        try {
            const task = await api.tasks.create("chat", msg);
            set({ activeTaskId: task.id });
            const finished = await waitForTask(task.id, { timeoutMs: 30_000, intervalMs: 1_000 });
            const results = finished.agent_results as Array<{ output?: { response?: string } }> | undefined;
            if (Array.isArray(results)) {
                for (let j = results.length - 1; j >= 0; j--) {
                    if (results[j]?.output?.response) {
                        answer = results[j].output!.response!;
                        break;
                    }
                }
            }
            if (!answer) {
                if (finished.error_message) {
                    // Una petición de aclaración no es un error: se muestra tal cual.
                    const isClarification = Boolean(
                        (finished.additional_metadata as Record<string, unknown> | null)?.clarification,
                    );
                    answer = isClarification ? finished.error_message : `Error: ${finished.error_message}`;
                } else {
                    answer = texts.noResponse;
                }
            }
        } catch (e) {
            answer = e instanceof TaskTimeoutError ? texts.timeout : texts.sendError;
        } finally {
            // Si "Detener" ya cerró el envío (markStopped), no duplicar la respuesta.
            if (get().sending) {
                set((s) => ({
                    sending: false,
                    activeTaskId: null,
                    messages: [...s.messages, { role: "assistant", content: answer }],
                }));
            }
        }
    },
}));

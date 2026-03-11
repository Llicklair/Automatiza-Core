"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
    KeyRound, ArrowLeft, Save, Loader2, Eye, EyeOff, CheckCircle2,
} from "lucide-react";

const API_KEY_FIELDS = [
    { key: "GROQ_API_KEY", label: "Groq API Key", placeholder: "gsk_..." },
    { key: "OPENAI_API_KEY", label: "OpenAI API Key", placeholder: "sk-proj-..." },
    { key: "OPENROUTER_API_KEY", label: "OpenRouter API Key", placeholder: "sk-or-..." },
    { key: "ANTHROPIC_API_KEY", label: "Anthropic API Key", placeholder: "sk-ant-..." },
];

export default function ApiKeysPage() {
    const router = useRouter();
    const [values, setValues] = useState<Record<string, string>>({});
    const [visible, setVisible] = useState<Record<string, boolean>>({});
    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState("");

    useEffect(() => {
        const stored: Record<string, string> = {};
        for (const f of API_KEY_FIELDS) {
            stored[f.key] = localStorage.getItem(`apikey_${f.key}`) || "";
        }
        setValues(stored);
    }, []);

    function save() {
        setSaving(true);
        for (const f of API_KEY_FIELDS) {
            if (values[f.key]) {
                localStorage.setItem(`apikey_${f.key}`, values[f.key]);
            } else {
                localStorage.removeItem(`apikey_${f.key}`);
            }
        }
        setTimeout(() => { setSaving(false); setMsg("Claves guardadas localmente"); }, 400);
    }

    return (
        <div className="p-8 max-w-lg mx-auto">
            <button
                onClick={() => router.back()}
                className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-white transition mb-6"
            >
                <ArrowLeft className="w-4 h-4" /> Volver
            </button>

            <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6">
                <h1 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
                    <KeyRound className="w-5 h-5 text-indigo-400" /> Claves API
                </h1>
                <p className="text-xs text-zinc-500 mb-6">
                    Las claves se almacenan en el navegador para desarrollo local. En producción,
                    configúralas en el archivo <code className="text-indigo-400">.env</code> del servidor.
                </p>

                <div className="space-y-4">
                    {API_KEY_FIELDS.map(f => (
                        <div key={f.key}>
                            <label className="block text-xs font-medium text-zinc-400 mb-1">{f.label}</label>
                            <div className="relative">
                                <input
                                    type={visible[f.key] ? "text" : "password"}
                                    value={values[f.key] || ""}
                                    onChange={e => setValues(prev => ({ ...prev, [f.key]: e.target.value }))}
                                    placeholder={f.placeholder}
                                    className="w-full pr-9 px-3 py-2.5 rounded-lg bg-black/40 border border-[#3f3f46] text-white text-xs placeholder-zinc-600 font-mono focus:outline-none focus:border-indigo-500/50 transition"
                                />
                                <button
                                    type="button"
                                    onClick={() => setVisible(prev => ({ ...prev, [f.key]: !prev[f.key] }))}
                                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                                >
                                    {visible[f.key] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                {msg && (
                    <p className="mt-4 text-xs text-emerald-400 flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5" /> {msg}
                    </p>
                )}

                <div className="flex justify-end mt-6">
                    <button
                        onClick={save}
                        disabled={saving}
                        className="flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        Guardar
                    </button>
                </div>
            </div>
        </div>
    );
}

"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { AIEmployee, ActivityEntry, AvailableSkill } from "@/lib/api/ai_employees";
import { Bot, RefreshCw, Plus, Users2, AlertCircle, MessageSquare, X, Loader2, Send } from "lucide-react";

const STATUS_CONFIG = {
    idle:    { label: "Disponible",     color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", dot: "bg-emerald-400" },
    working: { label: "Trabajando…",    color: "bg-blue-500/10 text-blue-400 border-blue-500/20",          dot: "bg-blue-400 animate-pulse" },
    paused:  { label: "Pausado",        color: "bg-zinc-700/50 text-zinc-500 border-zinc-700",              dot: "bg-zinc-600" },
    blocked: { label: "Requiere firma", color: "bg-amber-500/10 text-amber-400 border-amber-500/20",        dot: "bg-amber-400 animate-pulse" },
} as const;

const DOMAIN_ICON: Record<string, string> = {
    billing: "💰", hr: "👥", email: "📧", crm: "🤝",
    banking: "🏦", compliance: "⚖️", excel: "📊", documents: "📄",
};

const DOMAINS = ["billing", "hr", "email", "crm", "banking", "compliance", "excel", "documents"];

// ── Modal Dar Instrucción ────────────────────────────────────────────────��────
function InstructModal({ employee, onClose, onSent }: {
    employee: AIEmployee; onClose: () => void; onSent: () => void;
}) {
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSend = async () => {
        if (!message.trim()) return;
        setLoading(true); setError(null);
        try {
            await api.aiEmployees.instruct(employee.id, message.trim());
            onSent(); onClose();
        } catch (e: any) { setError(e?.message ?? "Error al enviar instrucción"); }
        finally { setLoading(false); }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
            <div className="bg-[#18181b] border border-[#27272a] rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="font-semibold text-white text-sm">Instrucción → {employee.name}</h2>
                    <button onClick={onClose} className="p-1 hover:bg-zinc-800 rounded-lg"><X className="w-4 h-4 text-zinc-500" /></button>
                </div>
                <p className="text-xs text-zinc-500">La instrucción pasará por el coordinador, que decidirá cómo ejecutarla.</p>
                <textarea
                    autoFocus value={message} onChange={e => setMessage(e.target.value)}
                    placeholder="Ej: Genera la nómina de enero para todos los empleados activos…"
                    rows={4}
                    className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50 resize-none"
                />
                {error && <p className="text-xs text-red-400">{error}</p>}
                <div className="flex justify-end gap-2">
                    <button onClick={onClose} className="px-4 py-2 text-sm text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg">Cancelar</button>
                    <button onClick={handleSend} disabled={!message.trim() || loading}
                        className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors">
                        {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                        Enviar
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Modal Nueva IA ────────────────────────────────────────────────────────────
function NewEmployeeModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void; }) {
    const [skills, setSkills] = useState<AvailableSkill[]>([]);
    const [form, setForm] = useState({ name: "", role: "", domain: "billing", system_prompt: "", budget_limit_usd: 10 });
    const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => { api.aiEmployees.availableSkills().then(setSkills).catch(() => {}); }, []);

    const toggleSkill = (module: string) =>
        setSelectedSkills(prev => prev.includes(module) ? prev.filter(s => s !== module) : [...prev, module]);

    const handleCreate = async () => {
        if (!form.name.trim() || !form.role.trim() || !form.system_prompt.trim()) {
            setError("Nombre, rol y prompt son obligatorios"); return;
        }
        setLoading(true); setError(null);
        try { await api.aiEmployees.create({ ...form, skills: selectedSkills }); onCreated(); onClose(); }
        catch (e: any) { setError(e?.message ?? "Error al crear empleado"); }
        finally { setLoading(false); }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 overflow-y-auto">
            <div className="bg-[#18181b] border border-[#27272a] rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4 my-8">
                <div className="flex items-center justify-between">
                    <h2 className="font-semibold text-white text-sm">Nuevo empleado IA</h2>
                    <button onClick={onClose} className="p-1 hover:bg-zinc-800 rounded-lg"><X className="w-4 h-4 text-zinc-500" /></button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                    {[["Nombre", "name", "Ej: Laura García"], ["Rol / Cargo", "role", "Ej: Analista de CRM"]].map(([label, key, ph]) => (
                        <div key={key} className="space-y-1">
                            <label className="text-xs font-medium text-zinc-400">{label}</label>
                            <input value={(form as any)[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} placeholder={ph}
                                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
                        </div>
                    ))}
                </div>
                <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-zinc-400">Dominio</label>
                        <select value={form.domain} onChange={e => setForm(f => ({ ...f, domain: e.target.value }))}
                            className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-violet-500/50">
                            {DOMAINS.map(d => <option key={d} value={d}>{DOMAIN_ICON[d]} {d}</option>)}
                        </select>
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-zinc-400">Presupuesto máx. (USD/mes)</label>
                        <input type="number" min={0} value={form.budget_limit_usd}
                            onChange={e => setForm(f => ({ ...f, budget_limit_usd: Number(e.target.value) }))}
                            className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
                    </div>
                </div>
                <div className="space-y-1">
                    <label className="text-xs font-medium text-zinc-400">Prompt del sistema</label>
                    <textarea value={form.system_prompt} onChange={e => setForm(f => ({ ...f, system_prompt: e.target.value }))}
                        placeholder="Eres Laura García, analista de CRM. Tu trabajo es…" rows={3}
                        className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50 resize-none" />
                </div>
                {skills.length > 0 && (
                    <div className="space-y-2">
                        <label className="text-xs font-medium text-zinc-400">Skills autorizadas</label>
                        <div className="grid grid-cols-2 gap-1 max-h-40 overflow-y-auto pr-1">
                            {skills.map(s => (
                                <label key={s.module} className="flex items-center gap-2 text-xs cursor-pointer hover:bg-zinc-800 p-1.5 rounded-lg text-zinc-400">
                                    <input type="checkbox" checked={selectedSkills.includes(s.module)} onChange={() => toggleSkill(s.module)}
                                        className="rounded text-violet-600 bg-zinc-800 border-zinc-600" />
                                    {s.label}
                                </label>
                            ))}
                        </div>
                    </div>
                )}
                {error && <p className="text-xs text-red-400">{error}</p>}
                <div className="flex justify-end gap-2 pt-1">
                    <button onClick={onClose} className="px-4 py-2 text-sm text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg">Cancelar</button>
                    <button onClick={handleCreate} disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors">
                        {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Crear empleado
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Employee Card ─────────────────────────────────────────────────────────────
function EmployeeCard({ employee, onToggle, onInstruct }: {
    employee: AIEmployee; onToggle: (id: string, current: AIEmployee["status"]) => void; onInstruct: (e: AIEmployee) => void;
}) {
    const s = STATUS_CONFIG[employee.status] ?? STATUS_CONFIG.idle;
    const icon = DOMAIN_ICON[employee.domain] ?? "🤖";

    return (
        <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-4 flex flex-col gap-3 hover:border-zinc-600 transition-colors">
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-lg">{icon}</div>
                    <div>
                        <p className="font-semibold text-white text-sm">{employee.name}</p>
                        <p className="text-xs text-zinc-500">{employee.role}</p>
                    </div>
                </div>
                <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border ${s.color}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                    {s.label}
                </span>
            </div>
            <div className="flex items-center justify-between pt-2 border-t border-[#27272a] gap-2">
                <span className="text-[10px] text-zinc-600 capitalize">{employee.domain}</span>
                <div className="flex items-center gap-1">
                    <button onClick={() => onInstruct(employee)} disabled={employee.status === "paused"}
                        className="flex items-center gap-1 text-[10px] px-2 py-1 rounded-md border border-violet-500/30 text-violet-400 hover:bg-violet-500/10 disabled:opacity-40 transition-colors">
                        <MessageSquare className="w-3 h-3" /> Instrucción
                    </button>
                    <button onClick={() => onToggle(employee.id, employee.status)}
                        className={`text-[10px] px-2 py-1 rounded-md border transition-colors ${
                            employee.status === "paused"
                                ? "border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
                                : "border-zinc-700 text-zinc-500 hover:bg-zinc-800"
                        }`}>
                        {employee.status === "paused" ? "Activar" : "Pausar"}
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Barra global de instrucciones ─────────────────────────────────────────────
function CoordinatorBar({ onSent }: { onSent: () => void }) {
    const [text, setText] = useState("");
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState(false);

    const handleSend = async () => {
        if (!text.trim() || loading) return;
        setLoading(true);
        try {
            await api.tasks.create("coordinator", text.trim());
            setText("");
            setSent(true);
            setTimeout(() => setSent(false), 3000);
            onSent();
        } catch { /* silencioso */ }
        finally { setLoading(false); }
    };

    return (
        <div className="flex items-center gap-2 bg-[#18181b] border border-[#27272a] rounded-xl px-4 py-3">
            <div className="w-7 h-7 rounded-full bg-violet-500/10 border border-violet-500/20 flex items-center justify-center shrink-0">
                <Bot className="w-3.5 h-3.5 text-violet-400" />
            </div>
            <input
                value={text}
                onChange={e => setText(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSend()}
                placeholder="Dile al coordinador qué necesitas… Ej: necesito un empleado de marketing"
                className="flex-1 bg-transparent text-sm text-white placeholder:text-zinc-600 focus:outline-none"
            />
            {sent ? (
                <span className="text-xs text-emerald-400 shrink-0">✓ Enviado</span>
            ) : (
                <button onClick={handleSend} disabled={!text.trim() || loading}
                    className="p-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white transition-colors shrink-0">
                    {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                </button>
            )}
        </div>
    );
}

// ── Página principal ──────────────────────────────────────────────────────────
export default function MiEquipoPage() {
    const [employees, setEmployees]           = useState<AIEmployee[]>([]);
    const [loading, setLoading]               = useState(true);
    const [seeding, setSeeding]               = useState(false);
    const [refreshing, setRefreshing]         = useState(false);
    const [error, setError]                   = useState<string | null>(null);
    const [instructTarget, setInstructTarget] = useState<AIEmployee | null>(null);
    const [showNewModal, setShowNewModal]     = useState(false);
    const [toast, setToast]                   = useState<string | null>(null);

    const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3500); };

    const loadData = useCallback(async () => {
        try { const emps = await api.aiEmployees.list(); setEmployees(emps); setError(null); }
        catch (e: any) { setError(e?.message ?? "Error cargando datos"); }
    }, []);

    useEffect(() => {
        setLoading(true);
        loadData().finally(() => setLoading(false));
        const interval = setInterval(loadData, 15_000);
        return () => clearInterval(interval);
    }, [loadData]);

    const handleSeed = async () => {
        setSeeding(true);
        try { await api.aiEmployees.seed(); await loadData(); }
        finally { setSeeding(false); }
    };

    const handleToggle = async (id: string, current: AIEmployee["status"]) => {
        const next = current === "paused" ? "idle" : "paused";
        setEmployees(prev => prev.map(e => e.id === id ? { ...e, status: next } : e));
        try { await api.aiEmployees.updateStatus(id, next); }
        catch { setEmployees(prev => prev.map(e => e.id === id ? { ...e, status: current } : e)); }
    };

    if (loading) return (
        <div className="flex items-center justify-center h-64">
            <div className="w-7 h-7 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
        </div>
    );

    return (
        <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
            {toast && (
                <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-zinc-900 border border-zinc-700 text-white text-sm px-5 py-2.5 rounded-full shadow-lg">
                    {toast}
                </div>
            )}
            {instructTarget && <InstructModal employee={instructTarget} onClose={() => setInstructTarget(null)}
                onSent={() => { showToast(`Instrucción enviada a ${instructTarget.name}`); loadData(); }} />}
            {showNewModal && <NewEmployeeModal onClose={() => setShowNewModal(false)}
                onCreated={() => { loadData(); showToast("Empleado IA creado"); }} />}

            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-semibold text-white flex items-center gap-2">
                        <Bot className="w-6 h-6 text-violet-400" /> Mi Equipo IA
                    </h1>
                    <p className="text-xs text-zinc-500 mt-1">Empleados virtuales que trabajan en segundo plano</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={() => { setRefreshing(true); loadData().finally(() => setRefreshing(false)); }}
                        className="p-2 rounded-lg border border-[#27272a] hover:bg-zinc-800 text-zinc-500 transition-colors">
                        <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
                    </button>
                    <button onClick={() => setShowNewModal(true)}
                        className="flex items-center gap-2 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-medium transition-colors">
                        <Plus className="w-3.5 h-3.5" /> Nueva IA
                    </button>
                </div>
            </div>

            {/* Barra global coordinador */}
            <CoordinatorBar onSent={loadData} />

            {error && (
                <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
                    <AlertCircle className="w-4 h-4 shrink-0" /> {error}
                </div>
            )}

            {/* Organigrama */}
            {employees.length === 0 ? (
                <div className="text-center py-16 border-2 border-dashed border-[#27272a] rounded-xl">
                    <Users2 className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
                    <p className="text-zinc-400 font-medium text-sm">Sin empleados aún</p>
                    <p className="text-xs text-zinc-600 mt-1">Crea el equipo inicial con Ana, Carlos y Sofía</p>
                    <button onClick={handleSeed} disabled={seeding}
                        className="mt-4 px-5 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium disabled:opacity-60 transition-colors">
                        {seeding ? "Creando…" : "Crear equipo inicial"}
                    </button>
                </div>
            ) : (
                <>
                    <div>
                        <p className="text-xs font-semibold text-zinc-600 uppercase tracking-wider mb-3">
                            Organigrama · {employees.length} empleados
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {employees.map(emp => (
                                <EmployeeCard key={emp.id} employee={emp} onToggle={handleToggle} onInstruct={setInstructTarget} />
                            ))}
                        </div>
                    </div>
                    <div className="flex items-center justify-between pt-2 border-t border-[#27272a]">
                        <p className="text-xs text-zinc-600">Las actividades de tus agentes aparecen en la bandeja</p>
                        <a href="/actividades" className="text-xs text-violet-400 hover:text-violet-300 transition-colors">
                            Ver bandeja de agentes →
                        </a>
                    </div>
                </>
            )}
        </div>
    );
}

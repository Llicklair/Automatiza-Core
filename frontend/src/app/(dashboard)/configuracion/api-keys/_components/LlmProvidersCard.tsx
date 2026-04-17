import { ChevronDown, ChevronUp, Cpu, Eye, EyeOff, ExternalLink } from "lucide-react";
import { LLM_PROVIDERS, type ProviderState } from "../_hooks/useApiKeys";

interface LlmProvidersCardProps {
    providers: Record<string, ProviderState>;
    activeLlm: string;
    setActiveLlm: (v: string) => void;
    updateProvider: (key: string, patch: Partial<ProviderState>) => void;
}

export function LlmProvidersCard({ providers, activeLlm, setActiveLlm, updateProvider }: LlmProvidersCardProps) {
    return (
        <div className="bg-card border border-border rounded-2xl p-6 mb-4">
            <h1 className="text-xl font-bold text-foreground flex items-center gap-2 mb-1">
                <Cpu className="w-5 h-5 text-primary" /> Modelos de lenguaje (LLM)
            </h1>
            <p className="text-xs text-muted-foreground mb-5">
                Activa los proveedores que quieras usar. El <span className="text-primary">proveedor activo</span> es el que usan los agentes.
                Las claves se cifran en base de datos.
            </p>

            <div className="space-y-3">
                {LLM_PROVIDERS.map(p => {
                    const s = providers[p.key];
                    if (!s) return null;
                    const isActive = activeLlm === p.key;

                    return (
                        <div
                            key={p.key}
                            className={`rounded-xl border transition-all ${
                                isActive
                                    ? "border-primary/20 bg-primary/5"
                                    : s.enabled
                                    ? "border-emerald-500/30 bg-emerald-500/5"
                                    : "border-border bg-card"
                            }`}
                        >
                            {/* Header row */}
                            <div className="flex items-center gap-3 p-3">
                                <button
                                    onClick={() => updateProvider(p.key, { enabled: !s.enabled })}
                                    className={`relative w-9 h-5 rounded-full transition-colors flex-shrink-0 ${
                                        s.enabled ? "bg-emerald-500" : "bg-accent"
                                    }`}
                                >
                                    <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all ${s.enabled ? "left-4" : "left-0.5"}`} />
                                </button>

                                <span className={`text-sm font-medium flex-1 ${isActive ? "text-primary" : s.enabled ? "text-foreground" : "text-muted-foreground"}`}>
                                    {p.label}
                                    {s.has_key && !s.api_key && (
                                        <span className="ml-2 text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-full">clave guardada</span>
                                    )}
                                </span>

                                {s.enabled && !isActive && (
                                    <button
                                        onClick={() => setActiveLlm(p.key)}
                                        className="text-[11px] px-2.5 py-1 rounded-lg border border-primary/20 text-primary hover:bg-primary/10 transition"
                                    >
                                        Usar como activo
                                    </button>
                                )}
                                {isActive && (
                                    <span className="text-[10px] font-bold uppercase tracking-wider bg-primary text-foreground px-2 py-0.5 rounded-full">
                                        Activo
                                    </span>
                                )}

                                <button
                                    onClick={() => updateProvider(p.key, { expanded: !s.expanded })}
                                    className="text-muted-foreground hover:text-muted-foreground transition ml-1"
                                >
                                    {s.expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                </button>
                            </div>

                            {/* Expanded: api key + model */}
                            {s.expanded && (
                                <div className="px-3 pb-3 space-y-2 border-t border-border pt-3">
                                            {p.hint && <p className="text-[11px] text-muted-foreground mb-1">{p.hint}</p>}
                                            <div>
                                                <div className="flex items-center justify-between mb-1">
                                                    <label className="text-[11px] text-muted-foreground">API Key</label>
                                                    {p.consoleUrl && (
                                                        <a
                                                            href={p.consoleUrl}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-[11px] text-primary hover:text-primary flex items-center gap-1 transition"
                                                        >
                                                            Obtener API Key <ExternalLink className="w-3 h-3" />
                                                        </a>
                                                    )}
                                                </div>
                                                <div className="relative">
                                                    <input
                                                        type={s.showKey ? "text" : "password"}
                                                        value={s.api_key}
                                                        onChange={e => updateProvider(p.key, { api_key: e.target.value })}
                                                        placeholder={s.has_key ? "••••••••  (dejar vacío para no cambiar)" : p.placeholder}
                                                        className="w-full pr-9 px-3 py-2 rounded-lg bg-muted border border-border text-xs font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/20 transition"
                                                    />
                                                    <button
                                                        type="button"
                                                        onClick={() => updateProvider(p.key, { showKey: !s.showKey })}
                                                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                                    >
                                                        {s.showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                                                    </button>
                                                </div>
                                            </div>
                                            <div>
                                                <label className="text-[11px] text-muted-foreground mb-1 block">Modelo</label>
                                                <select
                                                    value={p.models.includes(s.model) ? s.model : "__custom__"}
                                                    onChange={e => {
                                                        if (e.target.value !== "__custom__") updateProvider(p.key, { model: e.target.value });
                                                    }}
                                                    className="w-full px-3 py-2 rounded-lg bg-muted border border-border text-xs font-mono text-foreground focus:outline-none focus:border-primary/20 transition mb-1"
                                                >
                                                    {p.models.map(m => (
                                                        <option key={m} value={m} className="bg-card">{m}</option>
                                                    ))}
                                                    {!p.models.includes(s.model) && (
                                                        <option value="__custom__" className="bg-card">{s.model} (personalizado)</option>
                                                    )}
                                                </select>
                                            </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import {
    FileText, Users, BarChart3, Plus, Trash2, Star, Eye, Loader2,
    Palette, Type, Layout, AlignLeft, Table2, Check, FileCode2,
    Upload, ExternalLink, Copy, PenLine,
} from "lucide-react";

const ContractTemplateEditor = dynamic(
    () => import("@/components/ContractTemplateEditor"),
    { ssr: false }
);
import { sanitizeHTML } from "@/components/GenerativeUI";
import { templatesApi, DocumentTemplate, PreviewRequest } from "@/lib/api/templates";
import { documents, ContractPreviewHtml, ContractTemplate } from "@/lib/api/documents";
import { erp } from "@/lib/api/erp";
import { hr } from "@/lib/api/hr";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { cn } from "@/lib/utils";

// ── Variables de plantilla .docx ─────────────────────────────────────────────

const CONTRACT_VARIABLES = [
    { key: "{{nombre_cliente}}", desc: "Nombre completo del cliente" },
    { key: "{{nif_cliente}}", desc: "NIF/CIF del cliente" },
    { key: "{{direccion_cliente}}", desc: "Dirección del cliente" },
    { key: "{{nombre_empresa}}", desc: "Nombre de tu empresa" },
    { key: "{{nif_empresa}}", desc: "NIF/CIF de tu empresa" },
    { key: "{{fecha}}", desc: "Fecha actual (dd/mm/aaaa)" },
    { key: "{{fecha_inicio}}", desc: "Fecha de inicio del contrato" },
    { key: "{{fecha_fin}}", desc: "Fecha de fin del contrato" },
    { key: "{{importe}}", desc: "Importe total" },
    { key: "{{numero_contrato}}", desc: "Número de contrato" },
];

// ── Tab de Contratos Word ─────────────────────────────────────────────────────

type EntityOption = { id: string; name: string };
type GeneratePanel = { tplId: string; entityType: "client" | "employee"; entityId: string; entities: EntityOption[]; loadingEntities: boolean; generating: boolean };

function ContratosTab() {
    const { show: showToast } = useToastStore();
    const [templates, setTemplates] = useState<ContractTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [panel, setPanel] = useState<GeneratePanel | null>(null);
    const [previewFor, setPreviewFor] = useState<string | null>(null);
    const [previewData, setPreviewData] = useState<ContractPreviewHtml | null>(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [editorModal, setEditorModal] = useState<{ id: string; fileName: string; html: string } | null>(null);
    const [openingEditorId, setOpeningEditorId] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const load = async () => {
        setLoading(true);
        try {
            const data = await documents.contractTemplates.list();
            setTemplates(data);
        } catch {
            showToast("Error cargando plantillas de contrato", "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const openEditor = async (tpl: ContractTemplate) => {
        if (!tpl.file_name.toLowerCase().endsWith(".docx")) {
            showToast("La edición en el navegador solo está disponible para archivos .docx", "warning");
            return;
        }
        setOpeningEditorId(tpl.id);
        try {
            const data = await documents.contractTemplates.previewHtml(tpl.id);
            setEditorModal({ id: tpl.id, fileName: tpl.file_name, html: data.html_editable });
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "No se pudo cargar la plantilla";
            showToast(msg, "error");
        } finally {
            setOpeningEditorId(null);
        }
    };

    const togglePreview = async (tplId: string) => {
        if (previewFor === tplId) {
            setPreviewFor(null);
            setPreviewData(null);
            return;
        }
        setPreviewFor(tplId);
        setPreviewLoading(true);
        setPreviewData(null);
        try {
            const data = await documents.contractTemplates.previewHtml(tplId);
            setPreviewData(data);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Error en vista previa";
            showToast(msg, "error");
            setPreviewFor(null);
        } finally {
            setPreviewLoading(false);
        }
    };

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        try {
            await documents.contractTemplates.upload(file);
            showToast("Plantilla subida correctamente", "success");
            await load();
        } catch (err: any) {
            showToast(err?.message ?? "Error al subir plantilla", "error");
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    const handleOpen = (tpl: ContractTemplate) => {
        if (typeof window !== "undefined" && (window as any).electronAPI?.openTemplateNative) {
            (window as any).electronAPI.openTemplateNative(tpl.file_path);
        } else {
            showToast("Esta función solo está disponible en la app de escritorio", "warning");
        }
    };

    const handleDelete = async (tpl: ContractTemplate) => {
        const confirmed = await showConfirm({
            title: "Eliminar plantilla",
            message: `¿Eliminar "${tpl.file_name}"?`,
            confirmLabel: "Eliminar",
            confirmVariant: "danger",
        });
        if (!confirmed) return;
        try {
            await documents.contractTemplates.delete(tpl.id);
            showToast("Plantilla eliminada", "success");
            await load();
        } catch {
            showToast("Error eliminando plantilla", "error");
        }
    };

    const openGeneratePanel = async (tplId: string, entityType: "client" | "employee") => {
        setPanel({ tplId, entityType, entityId: "", entities: [], loadingEntities: true, generating: false });
        try {
            let entities: EntityOption[];
            if (entityType === "client") {
                const data = await erp.clients.list({ limit: 100 });
                entities = data.map((c: any) => ({ id: c.id, name: c.name }));
            } else {
                const data = await hr.employees.list();
                entities = data.map((e: any) => ({ id: e.id, name: e.name }));
            }
            setPanel(p => p ? { ...p, entities, loadingEntities: false } : null);
        } catch {
            showToast("Error cargando entidades", "error");
            setPanel(p => p ? { ...p, loadingEntities: false } : null);
        }
    };

    const handleGenerate = async () => {
        if (!panel || !panel.entityId) return;
        setPanel(p => p ? { ...p, generating: true } : null);
        try {
            const blob = await documents.contractTemplates.generate(panel.tplId, panel.entityType, panel.entityId);
            const tpl = templates.find(t => t.id === panel.tplId);
            const baseName = tpl?.file_name.replace(/\.[^.]+$/, "") ?? "contrato";
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${baseName}_BORRADOR.docx`;
            a.click();
            URL.revokeObjectURL(url);
            showToast("Borrador generado y descargado", "success");
            setPanel(null);
        } catch (err: any) {
            showToast(err?.message ?? "Error generando contrato", "error");
        } finally {
            setPanel(p => p ? { ...p, generating: false } : null);
        }
    };

    const copyVariable = (key: string) => {
        navigator.clipboard.writeText(key).catch(() => {});
        showToast(`Copiado: ${key}`, "success");
    };

    return (
        <div className="flex gap-6">
            {editorModal && (
                <ContractTemplateEditor
                    templateId={editorModal.id}
                    fileName={editorModal.fileName}
                    initialHtml={editorModal.html}
                    onClose={() => setEditorModal(null)}
                    onSaved={() => void load()}
                />
            )}
            {/* Lista de plantillas */}
            <div className="flex-1 space-y-3">
                <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-zinc-500">
                        Sube plantillas .docx con variables como <code className="text-indigo-400">{`{{nombre_cliente}}`}</code>. El sistema las rellenará con datos reales al generar contratos.
                    </p>
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                        className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
                    >
                        {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                        Subir .docx
                    </button>
                    <input ref={fileInputRef} type="file" accept=".docx,.doc,.odt" className="hidden" onChange={handleUpload} />
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-5 h-5 animate-spin text-zinc-500" />
                    </div>
                ) : templates.length === 0 ? (
                    <div
                        onClick={() => fileInputRef.current?.click()}
                        className="flex flex-col items-center justify-center py-16 border-2 border-dashed border-[#27272a] rounded-xl cursor-pointer hover:border-zinc-600 transition-colors"
                    >
                        <FileCode2 className="w-10 h-10 text-zinc-600 mb-3" />
                        <p className="text-zinc-500 text-sm font-medium">Sin plantillas aún</p>
                        <p className="text-zinc-600 text-xs mt-1">Haz clic para subir tu primer .docx</p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {templates.map(tpl => (
                            <div key={tpl.id} className="bg-[#18181b] border border-[#27272a] rounded-xl overflow-hidden">
                                {/* Fila principal */}
                                <div className="flex items-center gap-3 p-3 group">
                                    <FileCode2 className="w-8 h-8 text-indigo-400 flex-shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm text-white font-medium truncate">{tpl.file_name}</p>
                                        <p className="text-xs text-zinc-500">{(tpl.file_size / 1024).toFixed(1)} KB</p>
                                    </div>
                                    {/* Generar borrador */}
                                    <div className="flex items-center gap-1">
                                        <button
                                            onClick={() => panel?.tplId === tpl.id ? setPanel(null) : openGeneratePanel(tpl.id, "client")}
                                            className="flex items-center gap-1.5 px-2.5 py-1.5 bg-indigo-600/20 border border-indigo-500/40 text-indigo-300 hover:bg-indigo-600/30 text-xs rounded-lg transition-colors"
                                        >
                                            <FileText className="w-3.5 h-3.5" />
                                            Generar borrador
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => void openEditor(tpl)}
                                            disabled={!!openingEditorId}
                                            className="flex items-center gap-1.5 px-2.5 py-1.5 border border-emerald-600/50 text-emerald-300/90 hover:bg-emerald-950/40 text-xs rounded-lg transition-colors disabled:opacity-50"
                                            title="Editar en el navegador (solo .docx)"
                                        >
                                            {openingEditorId === tpl.id ? (
                                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                            ) : (
                                                <PenLine className="w-3.5 h-3.5" />
                                            )}
                                            Editar
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => void togglePreview(tpl.id)}
                                            disabled={previewLoading && previewFor === tpl.id}
                                            className="flex items-center gap-1.5 px-2.5 py-1.5 border border-zinc-600 text-zinc-300 hover:bg-zinc-800 text-xs rounded-lg transition-colors disabled:opacity-50"
                                            title="Vista previa HTML (solo .docx)"
                                        >
                                            {previewLoading && previewFor === tpl.id ? (
                                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                            ) : (
                                                <Eye className="w-3.5 h-3.5" />
                                            )}
                                            Previsualizar
                                        </button>
                                        <button
                                            onClick={() => handleOpen(tpl)}
                                            className="flex items-center gap-1.5 px-2.5 py-1.5 border border-zinc-700 text-zinc-400 hover:text-white text-xs rounded-lg transition-colors"
                                        >
                                            <ExternalLink className="w-3.5 h-3.5" />
                                        </button>
                                        <button
                                            onClick={() => handleDelete(tpl)}
                                            className="p-1.5 text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all rounded-lg hover:bg-red-500/10"
                                        >
                                            <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>

                                {/* Vista previa mammoth (V1) */}
                                {previewFor === tpl.id && (
                                    <div className="border-t border-[#27272a] p-3 bg-[#09090b] space-y-3">
                                        <p className="text-xs text-zinc-500">
                                            Vista previa de solo lectura (HTML). Las variables{" "}
                                            <code className="text-amber-400/90">{`{{nombre}}`}</code> se resaltan si existen en el texto.
                                        </p>
                                        {previewLoading ? (
                                            <div className="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
                                                <Loader2 className="w-5 h-5 animate-spin" />
                                                Convirtiendo documento…
                                            </div>
                                        ) : previewData ? (
                                            <div className="flex flex-col lg:flex-row gap-4">
                                                <div
                                                    className="flex-1 min-h-[180px] max-h-[min(480px,55vh)] overflow-y-auto rounded-lg border border-[#27272a] bg-[#18181b] p-4 text-sm text-zinc-200 [&_.apx-docx-var]:ring-1 [&_.apx-docx-var]:ring-amber-500/30"
                                                    dangerouslySetInnerHTML={{
                                                        __html: sanitizeHTML(previewData.html),
                                                    }}
                                                />
                                                <div className="w-full lg:w-52 shrink-0 space-y-2">
                                                    <p className="text-[10px] text-zinc-500 uppercase tracking-wide font-medium">
                                                        Variables en el documento
                                                    </p>
                                                    {previewData.warnings.length > 0 && (
                                                        <div className="text-[10px] text-amber-400/90 bg-amber-500/10 rounded-lg p-2 space-y-1">
                                                            {previewData.warnings.slice(0, 6).map((w, i) => (
                                                                <p key={i} className="leading-snug">{w}</p>
                                                            ))}
                                                        </div>
                                                    )}
                                                    <ul className="text-xs space-y-1.5 max-h-48 overflow-y-auto">
                                                        {previewData.variables_detected.length === 0 ? (
                                                            <li className="text-zinc-600">
                                                                No se detectaron <code>{`{{ }}`}</code> en el texto convertido.
                                                            </li>
                                                        ) : (
                                                            previewData.variables_detected.map(v => (
                                                                <li key={v}>
                                                                    <code className="text-amber-400 font-mono text-[11px]">{`{{${v}}}`}</code>
                                                                </li>
                                                            ))
                                                        )}
                                                    </ul>
                                                </div>
                                            </div>
                                        ) : null}
                                    </div>
                                )}

                                {/* Panel de generación inline */}
                                {panel?.tplId === tpl.id && (
                                    <div className="border-t border-[#27272a] p-3 bg-[#09090b] space-y-3">
                                        <p className="text-xs text-zinc-400 font-medium">Generar borrador para:</p>
                                        {/* Selector de tipo */}
                                        <div className="flex gap-2">
                                            {(["client", "employee"] as const).map(type => (
                                                <button
                                                    key={type}
                                                    onClick={() => openGeneratePanel(tpl.id, type)}
                                                    className={cn(
                                                        "flex-1 py-1.5 text-xs rounded-lg border transition-colors",
                                                        panel.entityType === type
                                                            ? "border-indigo-500 bg-indigo-600/10 text-indigo-300"
                                                            : "border-[#27272a] text-zinc-500 hover:border-zinc-600"
                                                    )}
                                                >
                                                    {type === "client" ? "Cliente" : "Empleado"}
                                                </button>
                                            ))}
                                        </div>
                                        {/* Selector de entidad */}
                                        {panel.loadingEntities ? (
                                            <div className="flex items-center gap-2 text-xs text-zinc-500">
                                                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Cargando…
                                            </div>
                                        ) : (
                                            <select
                                                value={panel.entityId}
                                                onChange={e => setPanel(p => p ? { ...p, entityId: e.target.value } : null)}
                                                className="w-full bg-[#18181b] border border-[#27272a] rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                                            >
                                                <option value="">-- Seleccionar {panel.entityType === "client" ? "cliente" : "empleado"} --</option>
                                                {panel.entities.map(e => (
                                                    <option key={e.id} value={e.id}>{e.name}</option>
                                                ))}
                                            </select>
                                        )}
                                        {/* Acciones */}
                                        <div className="flex gap-2">
                                            <button
                                                onClick={handleGenerate}
                                                disabled={!panel.entityId || panel.generating}
                                                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
                                            >
                                                {panel.generating
                                                    ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generando…</>
                                                    : <><FileText className="w-3.5 h-3.5" /> Descargar borrador</>
                                                }
                                            </button>
                                            <button
                                                onClick={() => setPanel(null)}
                                                className="px-3 py-1.5 border border-[#27272a] text-zinc-500 text-xs rounded-lg hover:text-white transition-colors"
                                            >
                                                Cancelar
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Catálogo de variables */}
            <div className="w-64 flex-shrink-0">
                <p className="text-xs text-zinc-400 font-medium mb-3 uppercase tracking-wider">Variables disponibles</p>
                <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-3 space-y-1">
                    {CONTRACT_VARIABLES.map(v => (
                        <button
                            key={v.key}
                            onClick={() => copyVariable(v.key)}
                            className="w-full flex items-start gap-2 p-2 rounded-lg hover:bg-[#27272a] transition-colors text-left group"
                            title="Clic para copiar"
                        >
                            <Copy className="w-3 h-3 text-zinc-600 group-hover:text-indigo-400 mt-0.5 flex-shrink-0 transition-colors" />
                            <div>
                                <code className="text-xs text-indigo-400 font-mono">{v.key}</code>
                                <p className="text-[10px] text-zinc-500 mt-0.5">{v.desc}</p>
                            </div>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}

// ── Constantes de opciones ──────────────────────────────────────────────────

const TEMPLATE_TYPES = [
    { value: "invoice",  label: "Facturas",             icon: FileText  },
    { value: "payroll",  label: "Nóminas",              icon: Users     },
    { value: "excel",    label: "Excel / Exportaciones", icon: BarChart3 },
    { value: "albaran",  label: "Albaranes",            icon: Table2    },
    { value: "contract", label: "Contratos Word",       icon: FileCode2 },
] as const;

const LAYOUT_PRESETS = [
    {
        value: "modern",
        label: "Modern",
        desc: "Banda de color, logo izquierda, tabla con rayas",
        preview: "bg-indigo-500",
    },
    {
        value: "classic",
        label: "Classic",
        desc: "Sin banda, logo centrado, Times, tabla con bordes",
        preview: "bg-gray-700",
    },
    {
        value: "minimal",
        label: "Minimal",
        desc: "Línea fina, logo derecha, tabla limpia",
        preview: "bg-zinc-400",
    },
    {
        value: "bold",
        label: "Bold",
        desc: "Cabecera oscura, tabla con acento, máximo impacto",
        preview: "bg-slate-800",
    },
] as const;

const ACCENT_COLORS = [
    { value: "#6366f1", label: "Índigo"   },
    { value: "#3b82f6", label: "Azul"     },
    { value: "#10b981", label: "Esmeralda"},
    { value: "#f59e0b", label: "Ámbar"    },
    { value: "#ef4444", label: "Rojo"     },
    { value: "#8b5cf6", label: "Violeta"  },
    { value: "#06b6d4", label: "Cyan"     },
    { value: "#1e293b", label: "Slate"    },
];

const FONTS = [
    { value: "helvetica", label: "Helvetica",   desc: "Moderna y limpia" },
    { value: "times",     label: "Times Roman",  desc: "Clásica y formal" },
    { value: "courier",   label: "Courier",      desc: "Monoespaciada"   },
];

const HEADER_STYLES = [
    { value: "color_band", label: "Banda color",  desc: "Cabecera rellena con color de acento" },
    { value: "dark_band",  label: "Banda oscura", desc: "Cabecera negra con acento en texto"   },
    { value: "line_only",  label: "Línea",        desc: "Solo una línea separadora"            },
    { value: "none",       label: "Sin cabecera", desc: "Solo tipografía"                      },
];

const TABLE_STYLES = [
    { value: "striped",       label: "Rayas alternas", desc: "Filas intercaladas gris" },
    { value: "bordered",      label: "Con bordes",     desc: "Cuadrícula completa"     },
    { value: "clean",         label: "Limpia",         desc: "Solo líneas horizontales"},
    { value: "accent_header", label: "Cabecera color", desc: "Header con color acento" },
];

const LOGO_POSITIONS = [
    { value: "left",   label: "Izquierda" },
    { value: "center", label: "Centro"    },
    { value: "right",  label: "Derecha"   },
];

// ── Defaults ─────────────────────────────────────────────────────────────────

const EMPTY_FORM: Omit<DocumentTemplate, "id"> = {
    name: "",
    template_type: "invoice",
    layout_style: "modern",
    accent_color: "#6366f1",
    font_family: "helvetica",
    logo_position: "left",
    header_style: "color_band",
    table_style: "striped",
    footer_text: null,
    is_default: false,
};

// ── Componente principal ─────────────────────────────────────────────────────

export default function PlantillasPage() {
    const { show: showToast } = useToastStore();
    const [activeType, setActiveType]   = useState<"invoice" | "payroll" | "excel" | "albaran" | "contract">("invoice");
    const [templates, setTemplates]     = useState<DocumentTemplate[]>([]);
    const [loading, setLoading]         = useState(true);
    const [showForm, setShowForm]       = useState(false);
    const [editingId, setEditingId]     = useState<string | null>(null);
    const [form, setForm]               = useState({ ...EMPTY_FORM });
    const [saving, setSaving]           = useState(false);
    const [previewUrl, setPreviewUrl]   = useState<string | null>(null);
    const [previewing, setPreviewing]   = useState(false);
    const previewDebounce               = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => { if (activeType !== "contract") load(); }, [activeType]); // eslint-disable-line react-hooks/exhaustive-deps

    // Auto-refresh preview when form changes (only if preview was already opened)
    useEffect(() => {
        if (!showForm || !previewUrl) return;
        if (previewDebounce.current) clearTimeout(previewDebounce.current);
        previewDebounce.current = setTimeout(() => { handlePreview(); }, 1200);
        return () => { if (previewDebounce.current) clearTimeout(previewDebounce.current); };
    }, [form]); // eslint-disable-line react-hooks/exhaustive-deps

    const load = async () => {
        setLoading(true);
        try {
            const data = await templatesApi.list(activeType);
            setTemplates(data);
        } catch {
            showToast("Error cargando plantillas", "error");
        } finally {
            setLoading(false);
        }
    };

    const openNew = () => {
        setEditingId(null);
        const t = activeType === "contract" ? "invoice" : activeType;
        setForm({ ...EMPTY_FORM, template_type: t });
        setPreviewUrl(null);
        setShowForm(true);
    };

    const openEdit = (tpl: DocumentTemplate) => {
        setEditingId(tpl.id);
        setForm({ ...tpl });
        setPreviewUrl(null);
        setShowForm(true);
    };

    const handleSave = async () => {
        if (!form.name.trim()) {
            showToast("El nombre es obligatorio", "warning");
            return;
        }
        setSaving(true);
        try {
            if (editingId) {
                await templatesApi.update(editingId, form);
                await templatesApi.setDefault(editingId);
                showToast("Plantilla guardada y establecida como predeterminada", "success");
            } else {
                const created = await templatesApi.create(form);
                await templatesApi.setDefault(created.id);
                showToast("Plantilla creada y establecida como predeterminada", "success");
            }
            setShowForm(false);
            await load();
        } catch {
            showToast("Error guardando plantilla", "error");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (tpl: DocumentTemplate) => {
        const confirmed = await showConfirm({
            title: "Eliminar plantilla",
            message: `¿Eliminar la plantilla "${tpl.name}"? Esta acción no se puede deshacer.`,
            confirmLabel: "Eliminar",
            confirmVariant: "danger",
        });
        if (!confirmed) return;
        try {
            await templatesApi.delete(tpl.id);
            showToast("Plantilla eliminada", "success");
            await load();
        } catch {
            showToast("Error eliminando plantilla", "error");
        }
    };

    const handleSetDefault = async (tpl: DocumentTemplate) => {
        try {
            await templatesApi.setDefault(tpl.id);
            showToast(`"${tpl.name}" establecida como predeterminada`, "success");
            await load();
        } catch {
            showToast("Error actualizando plantilla", "error");
        }
    };

    const handlePreview = async () => {
        setPreviewing(true);
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        try {
            const url = await templatesApi.preview(form as PreviewRequest);
            setPreviewUrl(url);
        } catch {
            showToast("Error generando vista previa", "error");
        } finally {
            setPreviewing(false);
        }
    };

    const setField = (key: keyof typeof form, value: any) =>
        setForm(f => ({ ...f, [key]: value }));

    return (
        <div className="p-6 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-xl font-semibold text-white">Plantillas de documentos</h1>
                    <p className="text-xs text-zinc-500 mt-0.5">
                        Personaliza el estilo visual de tus facturas y nóminas. La IA usará la plantilla por defecto.
                    </p>
                </div>
                <button
                    onClick={openNew}
                    className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors"
                >
                    <Plus className="w-3.5 h-3.5" />
                    Nueva plantilla
                </button>
            </div>

            {/* Tipo selector */}
            <div className="flex gap-1 mb-6 bg-[#18181b] border border-[#27272a] rounded-xl p-1 w-fit">
                {TEMPLATE_TYPES.map(t => (
                    <button
                        key={t.value}
                        onClick={() => { setActiveType(t.value); setShowForm(false); }}
                        className={cn(
                            "flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-medium transition-colors",
                            activeType === t.value
                                ? "bg-indigo-600 text-white"
                                : "text-zinc-400 hover:text-white"
                        )}
                    >
                        <t.icon className="w-3.5 h-3.5" />
                        {t.label}
                    </button>
                ))}
            </div>

            {activeType === "contract" ? (
                <ContratosTab />
            ) : (
            <div className="flex gap-6">
                {/* Lista de plantillas */}
                <div className="w-72 flex-shrink-0 space-y-2">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="w-5 h-5 animate-spin text-zinc-500" />
                        </div>
                    ) : templates.length === 0 ? (
                        <div className="text-center py-12 space-y-3">
                            <p className="text-zinc-500 text-sm">No hay plantillas de este tipo.</p>
                            <button
                                onClick={async () => {
                                    try {
                                        await templatesApi.seedDefaults(activeType);
                                        showToast("Plantillas preestablecidas creadas", "success");
                                        load();
                                    } catch {
                                        showToast("Error creando preestablecidas", "error");
                                    }
                                }}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors"
                            >
                                <Palette className="w-3.5 h-3.5" />
                                Crear preestablecidas
                            </button>
                        </div>
                    ) : (
                        templates.map(tpl => (
                            <div
                                key={tpl.id}
                                onClick={() => openEdit(tpl)}
                                className={cn(
                                    "group relative p-3 rounded-xl border cursor-pointer transition-all",
                                    editingId === tpl.id
                                        ? "border-indigo-500/50 bg-indigo-600/10"
                                        : "border-[#27272a] bg-[#18181b] hover:border-zinc-600"
                                )}
                            >
                                {/* Color swatch */}
                                <div className="flex items-center gap-2.5 mb-2">
                                    <div
                                        className="w-5 h-5 rounded-md flex-shrink-0"
                                        style={{ background: tpl.accent_color }}
                                    />
                                    <span className="text-sm text-white font-medium truncate">{tpl.name}</span>
                                    {tpl.is_default && (
                                        <Star className="w-3 h-3 text-amber-400 fill-amber-400 flex-shrink-0 ml-auto" />
                                    )}
                                </div>
                                <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 capitalize">
                                        {tpl.layout_style}
                                    </span>
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 capitalize">
                                        {tpl.font_family}
                                    </span>
                                </div>
                                {/* Acciones */}
                                <div className="absolute top-2 right-2 hidden group-hover:flex gap-1">
                                    {!tpl.is_default && (
                                        <button
                                            onClick={e => { e.stopPropagation(); handleSetDefault(tpl); }}
                                            className="flex items-center gap-1 px-2 py-1 rounded-md bg-zinc-800 hover:bg-amber-500/20 text-zinc-400 hover:text-amber-400 transition-colors text-[10px] font-medium"
                                        >
                                            <Star className="w-3 h-3" />
                                            Default
                                        </button>
                                    )}
                                    <button
                                        onClick={e => { e.stopPropagation(); handleDelete(tpl); }}
                                        className="p-1 rounded-md bg-zinc-800 hover:bg-red-500/20 text-zinc-400 hover:text-red-400 transition-colors"
                                    >
                                        <Trash2 className="w-3 h-3" />
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                {/* Editor + Preview */}
                {showForm && (
                    <div className="flex-1 flex gap-4 min-w-0">
                        {/* Editor */}
                        <div className="flex-1 bg-[#18181b] border border-[#27272a] rounded-xl p-5 space-y-5 overflow-y-auto max-h-[calc(100vh-220px)]">
                            {/* Nombre */}
                            <div>
                                <label className="text-xs text-zinc-400 font-medium mb-1.5 block">Nombre de la plantilla</label>
                                <input
                                    value={form.name}
                                    onChange={e => setField("name", e.target.value)}
                                    placeholder="Ej: Factura corporativa azul"
                                    className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500"
                                />
                            </div>

                            {/* Preset de layout */}
                            <div>
                                <label className="text-xs text-zinc-400 font-medium mb-2 flex items-center gap-1.5">
                                    <Layout className="w-3.5 h-3.5" /> Estilo de diseño
                                </label>
                                <div className="grid grid-cols-2 gap-2">
                                    {LAYOUT_PRESETS.map(p => (
                                        <button
                                            key={p.value}
                                            onClick={() => setField("layout_style", p.value)}
                                            className={cn(
                                                "p-3 rounded-xl border text-left transition-all",
                                                form.layout_style === p.value
                                                    ? "border-indigo-500 bg-indigo-600/10"
                                                    : "border-[#27272a] hover:border-zinc-600"
                                            )}
                                        >
                                            <div className="flex items-center gap-2 mb-1">
                                                <div className={cn("w-3 h-3 rounded-sm", p.preview)} />
                                                <span className="text-xs font-medium text-white">{p.label}</span>
                                                {form.layout_style === p.value && (
                                                    <Check className="w-3 h-3 text-indigo-400 ml-auto" />
                                                )}
                                            </div>
                                            <p className="text-[10px] text-zinc-500">{p.desc}</p>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Color de acento */}
                            <div>
                                <label className="text-xs text-zinc-400 font-medium mb-2 flex items-center gap-1.5">
                                    <Palette className="w-3.5 h-3.5" /> Color de acento
                                </label>
                                <div className="flex flex-wrap gap-2">
                                    {ACCENT_COLORS.map(c => (
                                        <button
                                            key={c.value}
                                            onClick={() => setField("accent_color", c.value)}
                                            title={c.label}
                                            className={cn(
                                                "w-7 h-7 rounded-lg transition-all",
                                                form.accent_color === c.value
                                                    ? "ring-2 ring-white ring-offset-2 ring-offset-[#18181b] scale-110"
                                                    : "hover:scale-105"
                                            )}
                                            style={{ background: c.value }}
                                        />
                                    ))}
                                    {/* Color personalizado */}
                                    <div className="relative">
                                        <input
                                            type="color"
                                            value={form.accent_color}
                                            onChange={e => setField("accent_color", e.target.value)}
                                            className="w-7 h-7 rounded-lg cursor-pointer opacity-0 absolute inset-0"
                                        />
                                        <div
                                            className="w-7 h-7 rounded-lg border-2 border-dashed border-zinc-600 flex items-center justify-center"
                                            style={{ background: ACCENT_COLORS.find(c => c.value === form.accent_color) ? "transparent" : form.accent_color }}
                                        >
                                            <Plus className="w-3 h-3 text-zinc-400" />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Fuente */}
                            <div>
                                <label className="text-xs text-zinc-400 font-medium mb-2 flex items-center gap-1.5">
                                    <Type className="w-3.5 h-3.5" /> Tipografía
                                </label>
                                <div className="flex gap-2">
                                    {FONTS.map(f => (
                                        <button
                                            key={f.value}
                                            onClick={() => setField("font_family", f.value)}
                                            className={cn(
                                                "flex-1 p-2.5 rounded-lg border text-center transition-all",
                                                form.font_family === f.value
                                                    ? "border-indigo-500 bg-indigo-600/10"
                                                    : "border-[#27272a] hover:border-zinc-600"
                                            )}
                                        >
                                            <div className="text-xs font-medium text-white">{f.label}</div>
                                            <div className="text-[10px] text-zinc-500 mt-0.5">{f.desc}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Estilo de cabecera */}
                            <div>
                                <label className="text-xs text-zinc-400 font-medium mb-2 flex items-center gap-1.5">
                                    <AlignLeft className="w-3.5 h-3.5" /> Cabecera
                                </label>
                                <div className="grid grid-cols-2 gap-1.5">
                                    {HEADER_STYLES.map(h => (
                                        <button
                                            key={h.value}
                                            onClick={() => setField("header_style", h.value)}
                                            className={cn(
                                                "p-2.5 rounded-lg border text-left transition-all",
                                                form.header_style === h.value
                                                    ? "border-indigo-500 bg-indigo-600/10"
                                                    : "border-[#27272a] hover:border-zinc-600"
                                            )}
                                        >
                                            <div className="text-xs font-medium text-white">{h.label}</div>
                                            <div className="text-[10px] text-zinc-500">{h.desc}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Estilo de tabla */}
                            <div>
                                <label className="text-xs text-zinc-400 font-medium mb-2 flex items-center gap-1.5">
                                    <Table2 className="w-3.5 h-3.5" /> Tabla de líneas
                                </label>
                                <div className="grid grid-cols-2 gap-1.5">
                                    {TABLE_STYLES.map(t => (
                                        <button
                                            key={t.value}
                                            onClick={() => setField("table_style", t.value)}
                                            className={cn(
                                                "p-2.5 rounded-lg border text-left transition-all",
                                                form.table_style === t.value
                                                    ? "border-indigo-500 bg-indigo-600/10"
                                                    : "border-[#27272a] hover:border-zinc-600"
                                            )}
                                        >
                                            <div className="text-xs font-medium text-white">{t.label}</div>
                                            <div className="text-[10px] text-zinc-500">{t.desc}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Posición del logo */}
                            <div>
                                <label className="text-xs text-zinc-400 font-medium mb-2 block">Posición del logo / empresa</label>
                                <div className="flex gap-2">
                                    {LOGO_POSITIONS.map(p => (
                                        <button
                                            key={p.value}
                                            onClick={() => setField("logo_position", p.value)}
                                            className={cn(
                                                "flex-1 py-1.5 rounded-lg border text-xs transition-all",
                                                form.logo_position === p.value
                                                    ? "border-indigo-500 bg-indigo-600/10 text-indigo-300"
                                                    : "border-[#27272a] text-zinc-400 hover:border-zinc-600"
                                            )}
                                        >
                                            {p.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Pie de página */}
                            <div>
                                <label className="text-xs text-zinc-400 font-medium mb-1.5 block">Texto del pie (opcional)</label>
                                <textarea
                                    value={form.footer_text || ""}
                                    onChange={e => setField("footer_text", e.target.value || null)}
                                    placeholder="Ej: Gracias por su confianza · www.miempresa.es · +34 91 000 0000"
                                    rows={2}
                                    className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 resize-none"
                                />
                            </div>

                            {/* Predeterminada */}
                            <label className="flex items-center gap-2.5 cursor-pointer">
                                <div
                                    onClick={() => setField("is_default", !form.is_default)}
                                    className={cn(
                                        "w-8 h-4 rounded-full transition-colors relative flex-shrink-0",
                                        form.is_default ? "bg-indigo-600" : "bg-zinc-700"
                                    )}
                                >
                                    <div className={cn(
                                        "absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform",
                                        form.is_default ? "translate-x-4" : "translate-x-0.5"
                                    )} />
                                </div>
                                <span className="text-xs text-zinc-300">Usar como plantilla por defecto</span>
                                <Star className="w-3 h-3 text-amber-400" />
                            </label>

                            {/* Botones */}
                            <div className="flex gap-2 pt-2">
                                <button
                                    onClick={handlePreview}
                                    disabled={previewing}
                                    className="flex items-center gap-1.5 px-3 py-1.5 border border-[#27272a] text-zinc-300 hover:text-white hover:border-zinc-500 text-xs rounded-lg transition-colors disabled:opacity-50"
                                >
                                    {previewing
                                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                        : <Eye className="w-3.5 h-3.5" />}
                                    Vista previa
                                </button>
                                <button
                                    onClick={() => setShowForm(false)}
                                    className="px-3 py-1.5 border border-[#27272a] text-zinc-400 text-xs rounded-lg hover:text-white transition-colors"
                                >
                                    Cancelar
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={saving}
                                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
                                >
                                    {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                                    {editingId ? "Guardar cambios" : "Crear plantilla"}
                                </button>
                            </div>
                        </div>

                        {/* Vista previa PDF */}
                        {previewUrl && (
                            <div className="w-[480px] flex-shrink-0">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-zinc-400 font-medium">Vista previa</span>
                                    <button
                                        onClick={() => { URL.revokeObjectURL(previewUrl); setPreviewUrl(null); }}
                                        className="text-[10px] text-zinc-500 hover:text-zinc-300"
                                    >
                                        Cerrar
                                    </button>
                                </div>
                                <iframe
                                    src={previewUrl}
                                    className="w-full rounded-xl border border-[#27272a] bg-white"
                                    style={{ height: "calc(100vh - 220px)" }}
                                />
                            </div>
                        )}
                    </div>
                )}
            </div>
            )}
        </div>
    );
}

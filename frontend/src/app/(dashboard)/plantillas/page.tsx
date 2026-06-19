"use client";

import {
    Plus, Loader2, Trash2, Star, Eye,
    Palette, Type, Layout, AlignLeft, Table2, Check,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import ContratosTab from "./_components/ContratosTab";
import {
    buildTemplateTypes, buildLayoutPresets, buildAccentColors,
    buildFonts, buildHeaderStyles, buildTableStyles, buildLogoPositions,
} from "./_components/templateOptions";
import { usePlantillas } from "./_hooks/usePlantillas";
import { PageContainer } from "@/components/shared/PageContainer";

export default function PlantillasPage() {
    const t = useTranslations("plantillas");
    const TEMPLATE_TYPES = buildTemplateTypes(t);
    const LAYOUT_PRESETS = buildLayoutPresets(t);
    const ACCENT_COLORS = buildAccentColors(t);
    const FONTS = buildFonts(t);
    const HEADER_STYLES = buildHeaderStyles(t);
    const TABLE_STYLES = buildTableStyles(t);
    const LOGO_POSITIONS = buildLogoPositions(t);
    const {
        activeType, switchType,
        templates, loading, load,
        showForm, setShowForm,
        editingId, form, setField,
        saving, previewUrl, previewing,
        openNew, openEdit,
        handleSave, handleDelete, handleSetDefault, handlePreview, closePreview,
        handleSeedDefaults,
    } = usePlantillas();

    return (
        <PageContainer width="7xl">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-xl font-semibold text-foreground">{t("header.title")}</h1>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        {t("header.subtitle")}
                    </p>
                </div>
                <button onClick={openNew}
                    className="flex items-center gap-2 px-3 py-1.5 bg-primary hover:bg-primary text-foreground text-xs font-medium rounded-lg transition-colors">
                    <Plus className="w-3.5 h-3.5" /> {t("header.newTemplate")}
                </button>
            </div>

            {/* Tipo selector */}
            <div className="flex gap-1 mb-6 bg-card border border-border rounded-xl p-1 w-fit">
                {TEMPLATE_TYPES.map(tt => (
                    <button key={tt.value} onClick={() => switchType(tt.value)}
                        className={cn("flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-medium transition-colors",
                            activeType === tt.value ? "bg-primary text-foreground" : "text-muted-foreground hover:text-foreground")}>
                        <tt.icon className="w-3.5 h-3.5" />
                        {tt.label}
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
                                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                            </div>
                        ) : templates.length === 0 ? (
                            <div className="text-center py-12 space-y-3">
                                <p className="text-muted-foreground text-sm">{t("list.empty")}</p>
                                <button
                                    onClick={handleSeedDefaults}
                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary text-foreground text-xs font-medium rounded-lg transition-colors">
                                    <Palette className="w-3.5 h-3.5" /> {t("list.createPresets")}
                                </button>
                            </div>
                        ) : (
                            templates.map(tpl => (
                                <div key={tpl.id} onClick={() => openEdit(tpl)}
                                    className={cn("group relative p-3 rounded-xl border cursor-pointer transition-all",
                                        editingId === tpl.id ? "border-primary/20 bg-primary/20" : "border-border bg-card hover:border-border")}>
                                    <div className="flex items-center gap-2.5 mb-2">
                                        <div className="w-5 h-5 rounded-md flex-shrink-0" style={{ background: tpl.accent_color }} />
                                        <span className="text-sm text-foreground font-medium truncate">{tpl.name}</span>
                                        {tpl.is_default && <Star className="w-3 h-3 text-amber-400 fill-amber-400 flex-shrink-0 ml-auto" />}
                                    </div>
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground capitalize">{tpl.layout_style}</span>
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground capitalize">{tpl.font_family}</span>
                                    </div>
                                    <div className="absolute top-2 right-2 hidden group-hover:flex gap-1">
                                        {!tpl.is_default && (
                                            <button onClick={e => { e.stopPropagation(); handleSetDefault(tpl); }}
                                                className="flex items-center gap-1 px-2 py-1 rounded-md bg-muted hover:bg-amber-500/20 text-muted-foreground hover:text-amber-400 transition-colors text-[10px] font-medium">
                                                <Star className="w-3 h-3" /> {t("card.default")}
                                            </button>
                                        )}
                                        <button onClick={e => { e.stopPropagation(); handleDelete(tpl); }}
                                            className="p-1 rounded-md bg-muted hover:bg-red-500/20 text-muted-foreground hover:text-red-400 transition-colors">
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
                            <div className="flex-1 bg-card border border-border rounded-xl p-5 space-y-5 overflow-y-auto max-h-[calc(100vh-220px)]">
                                {/* Nombre */}
                                <div>
                                    <label className="text-xs text-muted-foreground font-medium mb-1.5 block">{t("form.nameLabel")}</label>
                                    <input value={form.name} onChange={e => setField("name", e.target.value)}
                                        placeholder={t("form.namePlaceholder")}
                                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary" />
                                </div>

                                {/* Preset de layout */}
                                <div>
                                    <label className="text-xs text-muted-foreground font-medium mb-2 flex items-center gap-1.5">
                                        <Layout className="w-3.5 h-3.5" /> {t("form.layoutLabel")}
                                    </label>
                                    <div className="grid grid-cols-2 gap-2">
                                        {LAYOUT_PRESETS.map(p => (
                                            <button key={p.value} onClick={() => setField("layout_style", p.value)}
                                                className={cn("p-3 rounded-xl border text-left transition-all",
                                                    form.layout_style === p.value ? "border-primary bg-primary/20" : "border-border hover:border-border")}>
                                                <div className="flex items-center gap-2 mb-1">
                                                    <div className={cn("w-3 h-3 rounded-sm", p.preview)} />
                                                    <span className="text-xs font-medium text-foreground">{p.label}</span>
                                                    {form.layout_style === p.value && <Check className="w-3 h-3 text-primary ml-auto" />}
                                                </div>
                                                <p className="text-[10px] text-muted-foreground">{p.desc}</p>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Color de acento */}
                                <div>
                                    <label className="text-xs text-muted-foreground font-medium mb-2 flex items-center gap-1.5">
                                        <Palette className="w-3.5 h-3.5" /> {t("form.accentLabel")}
                                    </label>
                                    <div className="flex flex-wrap gap-2">
                                        {ACCENT_COLORS.map(c => (
                                            <button key={c.value} onClick={() => setField("accent_color", c.value)} title={c.label}
                                                className={cn("w-7 h-7 rounded-lg transition-all",
                                                    form.accent_color === c.value ? "ring-2 ring-white ring-offset-2 ring-offset-card scale-110" : "hover:scale-105")}
                                                style={{ background: c.value }} />
                                        ))}
                                        <div className="relative">
                                            <input type="color" value={form.accent_color} onChange={e => setField("accent_color", e.target.value)}
                                                className="w-7 h-7 rounded-lg cursor-pointer opacity-0 absolute inset-0" />
                                            <div className="w-7 h-7 rounded-lg border-2 border-dashed border-border flex items-center justify-center"
                                                style={{ background: ACCENT_COLORS.find(c => c.value === form.accent_color) ? "transparent" : form.accent_color }}>
                                                <Plus className="w-3 h-3 text-muted-foreground" />
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Fuente */}
                                <div>
                                    <label className="text-xs text-muted-foreground font-medium mb-2 flex items-center gap-1.5">
                                        <Type className="w-3.5 h-3.5" /> {t("form.fontLabel")}
                                    </label>
                                    <div className="flex gap-2">
                                        {FONTS.map(f => (
                                            <button key={f.value} onClick={() => setField("font_family", f.value)}
                                                className={cn("flex-1 p-2.5 rounded-lg border text-center transition-all",
                                                    form.font_family === f.value ? "border-primary bg-primary/20" : "border-border hover:border-border")}>
                                                <div className="text-xs font-medium text-foreground">{f.label}</div>
                                                <div className="text-[10px] text-muted-foreground mt-0.5">{f.desc}</div>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Estilo de cabecera */}
                                <div>
                                    <label className="text-xs text-muted-foreground font-medium mb-2 flex items-center gap-1.5">
                                        <AlignLeft className="w-3.5 h-3.5" /> {t("form.headerLabel")}
                                    </label>
                                    <div className="grid grid-cols-2 gap-1.5">
                                        {HEADER_STYLES.map(h => (
                                            <button key={h.value} onClick={() => setField("header_style", h.value)}
                                                className={cn("p-2.5 rounded-lg border text-left transition-all",
                                                    form.header_style === h.value ? "border-primary bg-primary/20" : "border-border hover:border-border")}>
                                                <div className="text-xs font-medium text-foreground">{h.label}</div>
                                                <div className="text-[10px] text-muted-foreground">{h.desc}</div>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Estilo de tabla */}
                                <div>
                                    <label className="text-xs text-muted-foreground font-medium mb-2 flex items-center gap-1.5">
                                        <Table2 className="w-3.5 h-3.5" /> {t("form.tableLabel")}
                                    </label>
                                    <div className="grid grid-cols-2 gap-1.5">
                                        {TABLE_STYLES.map(ts => (
                                            <button key={ts.value} onClick={() => setField("table_style", ts.value)}
                                                className={cn("p-2.5 rounded-lg border text-left transition-all",
                                                    form.table_style === ts.value ? "border-primary bg-primary/20" : "border-border hover:border-border")}>
                                                <div className="text-xs font-medium text-foreground">{ts.label}</div>
                                                <div className="text-[10px] text-muted-foreground">{ts.desc}</div>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Posición del logo */}
                                <div>
                                    <label className="text-xs text-muted-foreground font-medium mb-2 block">{t("form.logoLabel")}</label>
                                    <div className="flex gap-2">
                                        {LOGO_POSITIONS.map(p => (
                                            <button key={p.value} onClick={() => setField("logo_position", p.value)}
                                                className={cn("flex-1 py-1.5 rounded-lg border text-xs transition-all",
                                                    form.logo_position === p.value ? "border-primary bg-primary/20 text-primary" : "border-border text-muted-foreground hover:border-border")}>
                                                {p.label}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Pie de página */}
                                <div>
                                    <label className="text-xs text-muted-foreground font-medium mb-1.5 block">{t("form.footerLabel")}</label>
                                    <textarea value={form.footer_text || ""} onChange={e => setField("footer_text", e.target.value || null)}
                                        placeholder={t("form.footerPlaceholder")} rows={2}
                                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary resize-none" />
                                </div>

                                {/* Predeterminada */}
                                <label className="flex items-center gap-2.5 cursor-pointer">
                                    <div onClick={() => setField("is_default", !form.is_default)}
                                        className={cn("w-8 h-4 rounded-full transition-colors relative flex-shrink-0", form.is_default ? "bg-primary" : "bg-accent")}>
                                        <div className={cn("absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform", form.is_default ? "translate-x-4" : "translate-x-0.5")} />
                                    </div>
                                    <span className="text-xs text-foreground">{t("form.useAsDefault")}</span>
                                    <Star className="w-3 h-3 text-amber-400" />
                                </label>

                                {/* Botones */}
                                <div className="flex gap-2 pt-2">
                                    <button onClick={handlePreview} disabled={previewing}
                                        className="flex items-center gap-1.5 px-3 py-1.5 border border-border text-foreground hover:text-foreground hover:border-border text-xs rounded-lg transition-colors disabled:opacity-50">
                                        {previewing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
                                        {t("form.preview")}
                                    </button>
                                    <button onClick={() => setShowForm(false)}
                                        className="px-3 py-1.5 border border-border text-muted-foreground text-xs rounded-lg hover:text-foreground transition-colors">
                                        {t("form.cancel")}
                                    </button>
                                    <button onClick={handleSave} disabled={saving}
                                        className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary text-foreground text-xs font-medium rounded-lg transition-colors disabled:opacity-50">
                                        {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                                        {editingId ? t("form.saveChanges") : t("form.createTemplate")}
                                    </button>
                                </div>
                            </div>

                            {/* Vista previa PDF */}
                            {previewUrl && (
                                <div className="w-[480px] flex-shrink-0">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs text-muted-foreground font-medium">{t("form.preview")}</span>
                                        <button onClick={closePreview} className="text-[10px] text-muted-foreground hover:text-foreground">{t("form.close")}</button>
                                    </div>
                                    <iframe src={previewUrl} className="w-full rounded-xl border border-border bg-white"
                                        style={{ height: "calc(100vh - 220px)" }} />
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </PageContainer>
    );
}

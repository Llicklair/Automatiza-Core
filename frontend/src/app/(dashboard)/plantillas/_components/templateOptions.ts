import { FileText, Users, BarChart3, Table2, FileCode2 } from "lucide-react";
import type { DocumentTemplate } from "@/lib/api/templates";

export const CONTRACT_VARIABLES = [
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

export const TEMPLATE_TYPES = [
    { value: "invoice",  label: "Facturas",              icon: FileText  },
    { value: "payroll",  label: "Nóminas",               icon: Users     },
    { value: "excel",    label: "Excel / Exportaciones", icon: BarChart3 },
    { value: "albaran",  label: "Albaranes",             icon: Table2    },
    { value: "contract", label: "Contratos Word",        icon: FileCode2 },
] as const;

export const LAYOUT_PRESETS = [
    { value: "modern",  label: "Modern",  desc: "Banda de color, logo izquierda, tabla con rayas",  preview: "bg-primary"          },
    { value: "classic", label: "Classic", desc: "Sin banda, logo centrado, Times, tabla con bordes", preview: "bg-gray-700"         },
    { value: "minimal", label: "Minimal", desc: "Línea fina, logo derecha, tabla limpia",            preview: "bg-muted-foreground" },
    { value: "bold",    label: "Bold",    desc: "Cabecera oscura, tabla con acento, máximo impacto", preview: "bg-slate-800"        },
] as const;

export const ACCENT_COLORS = [
    { value: "#6366f1", label: "Índigo"    },
    { value: "#3b82f6", label: "Azul"      },
    { value: "#10b981", label: "Esmeralda" },
    { value: "#f59e0b", label: "Ámbar"     },
    { value: "#ef4444", label: "Rojo"      },
    { value: "#8b5cf6", label: "Violeta"   },
    { value: "#06b6d4", label: "Cyan"      },
    { value: "#1e293b", label: "Slate"     },
];

export const FONTS = [
    { value: "helvetica", label: "Helvetica",  desc: "Moderna y limpia" },
    { value: "times",     label: "Times Roman", desc: "Clásica y formal" },
    { value: "courier",   label: "Courier",     desc: "Monoespaciada"   },
];

export const HEADER_STYLES = [
    { value: "color_band", label: "Banda color",  desc: "Cabecera rellena con color de acento" },
    { value: "dark_band",  label: "Banda oscura", desc: "Cabecera negra con acento en texto"   },
    { value: "line_only",  label: "Línea",        desc: "Solo una línea separadora"            },
    { value: "none",       label: "Sin cabecera", desc: "Solo tipografía"                      },
];

export const TABLE_STYLES = [
    { value: "striped",       label: "Rayas alternas", desc: "Filas intercaladas gris"  },
    { value: "bordered",      label: "Con bordes",     desc: "Cuadrícula completa"      },
    { value: "clean",         label: "Limpia",         desc: "Solo líneas horizontales" },
    { value: "accent_header", label: "Cabecera color", desc: "Header con color acento"  },
];

export const LOGO_POSITIONS = [
    { value: "left",   label: "Izquierda" },
    { value: "center", label: "Centro"    },
    { value: "right",  label: "Derecha"   },
];

export const EMPTY_FORM: Omit<DocumentTemplate, "id"> = {
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

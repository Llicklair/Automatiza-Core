import { FileText, Users, BarChart3, Table2, FileCode2 } from "lucide-react";
import type { useTranslations } from "next-intl";
import type { DocumentTemplate } from "@/lib/api/templates";

type T = ReturnType<typeof useTranslations>;

export const buildContractVariables = (t: T) => [
    { key: "{{nombre_cliente}}", desc: t("variables.nombreCliente") },
    { key: "{{nif_cliente}}", desc: t("variables.nifCliente") },
    { key: "{{direccion_cliente}}", desc: t("variables.direccionCliente") },
    { key: "{{nombre_empresa}}", desc: t("variables.nombreEmpresa") },
    { key: "{{nif_empresa}}", desc: t("variables.nifEmpresa") },
    { key: "{{fecha}}", desc: t("variables.fecha") },
    { key: "{{fecha_inicio}}", desc: t("variables.fechaInicio") },
    { key: "{{fecha_fin}}", desc: t("variables.fechaFin") },
    { key: "{{importe}}", desc: t("variables.importe") },
    { key: "{{numero_contrato}}", desc: t("variables.numeroContrato") },
];

export const buildTemplateTypes = (t: T) => [
    { value: "invoice",  label: t("types.invoice"),  icon: FileText  },
    { value: "payroll",  label: t("types.payroll"),  icon: Users     },
    { value: "excel",    label: t("types.excel"),    icon: BarChart3 },
    { value: "albaran",  label: t("types.albaran"),  icon: Table2    },
    { value: "contract", label: t("types.contract"), icon: FileCode2 },
] as const;

export const buildLayoutPresets = (t: T) => [
    { value: "modern",  label: t("layout.modern.label"),  desc: t("layout.modern.desc"),  preview: "bg-primary"          },
    { value: "classic", label: t("layout.classic.label"), desc: t("layout.classic.desc"), preview: "bg-gray-700"         },
    { value: "minimal", label: t("layout.minimal.label"), desc: t("layout.minimal.desc"), preview: "bg-muted-foreground" },
    { value: "bold",    label: t("layout.bold.label"),    desc: t("layout.bold.desc"),    preview: "bg-slate-800"        },
] as const;

export const buildAccentColors = (t: T) => [
    { value: "#6366f1", label: t("colors.indigo")    },
    { value: "#3b82f6", label: t("colors.blue")      },
    { value: "#10b981", label: t("colors.emerald")   },
    { value: "#f59e0b", label: t("colors.amber")     },
    { value: "#ef4444", label: t("colors.red")       },
    { value: "#8b5cf6", label: t("colors.violet")    },
    { value: "#06b6d4", label: t("colors.cyan")      },
    { value: "#1e293b", label: t("colors.slate")     },
];

export const buildFonts = (t: T) => [
    { value: "helvetica", label: "Helvetica",   desc: t("fonts.helvetica") },
    { value: "times",     label: "Times Roman", desc: t("fonts.times")     },
    { value: "courier",   label: "Courier",     desc: t("fonts.courier")   },
];

export const buildHeaderStyles = (t: T) => [
    { value: "color_band", label: t("headers.colorBand.label"), desc: t("headers.colorBand.desc") },
    { value: "dark_band",  label: t("headers.darkBand.label"),  desc: t("headers.darkBand.desc")  },
    { value: "line_only",  label: t("headers.lineOnly.label"),  desc: t("headers.lineOnly.desc")  },
    { value: "none",       label: t("headers.none.label"),      desc: t("headers.none.desc")      },
];

export const buildTableStyles = (t: T) => [
    { value: "striped",       label: t("tables.striped.label"),      desc: t("tables.striped.desc")      },
    { value: "bordered",      label: t("tables.bordered.label"),     desc: t("tables.bordered.desc")     },
    { value: "clean",         label: t("tables.clean.label"),        desc: t("tables.clean.desc")        },
    { value: "accent_header", label: t("tables.accentHeader.label"), desc: t("tables.accentHeader.desc") },
];

export const buildLogoPositions = (t: T) => [
    { value: "left",   label: t("logoPositions.left")   },
    { value: "center", label: t("logoPositions.center") },
    { value: "right",  label: t("logoPositions.right")  },
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

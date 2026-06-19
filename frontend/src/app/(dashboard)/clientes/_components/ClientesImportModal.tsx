"use client";

import { useTranslations } from "next-intl";
import { ImportCsvModal } from "@/components/shared/ImportCsvModal";
import { api } from "@/lib/api";

interface ClientesImportModalProps {
    open: boolean;
    onClose: () => void;
}

export function ClientesImportModal({ open, onClose }: ClientesImportModalProps) {
    const t = useTranslations("clientes");

    const columns = [
        { header: t("import.colNombre"), field: "nombre", required: true, example: t("import.exNombre") },
        { header: t("import.colNif"), field: "nif", example: t("import.exNif") },
        { header: t("emailColumn"), field: "email", example: t("import.exEmail") },
        { header: t("import.colTelefono"), field: "telefono", example: t("import.exTelefono") },
        { header: t("import.colDireccion"), field: "direccion", example: t("import.exDireccion") },
        { header: t("import.colCiudad"), field: "ciudad", example: t("import.exCiudad") },
        { header: t("import.colCodigoPostal"), field: "codigo_postal", example: t("import.exCodigoPostal") },
        { header: t("typeColumn"), field: "tipo", example: t("import.exTipo") },
    ];

    return (
        <ImportCsvModal
            open={open}
            onClose={onClose}
            entityName="clientes"
            columns={columns}
            onImport={(rows) => api.importBulk.clients(rows)}
            onSuccess={() => window.location.reload()}
        />
    );
}

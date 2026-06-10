"use client";

import { ImportCsvModal } from "@/components/shared/ImportCsvModal";
import { api } from "@/lib/api";

interface ClientesImportModalProps {
    open: boolean;
    onClose: () => void;
}

export function ClientesImportModal({ open, onClose }: ClientesImportModalProps) {
    return (
        <ImportCsvModal
            open={open}
            onClose={onClose}
            entityName="clientes"
            columns={[
                { header: "Nombre", field: "nombre", required: true, example: "Acme S.L." },
                { header: "NIF", field: "nif", example: "B12345678" },
                { header: "Email", field: "email", example: "contacto@acme.com" },
                { header: "Teléfono", field: "telefono", example: "91 234 56 78" },
                { header: "Dirección", field: "direccion", example: "Calle Mayor 1" },
                { header: "Ciudad", field: "ciudad", example: "Madrid" },
                { header: "Código postal", field: "codigo_postal", example: "28001" },
                { header: "Tipo", field: "tipo", example: "customer" },
            ]}
            onImport={(rows) => api.importBulk.clients(rows)}
            onSuccess={() => window.location.reload()}
        />
    );
}

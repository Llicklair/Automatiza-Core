"use client";

import { useState } from "react";
import { Users, Plus, Wallet, ShieldCheck, Upload } from "lucide-react";
import { useEmpleados, STATUS_OPTIONS, currencyFmt } from "./_hooks/useEmpleados";
import { EmployeeDocsModal } from "./_components/EmployeeDocsModal";
import { EmpleadoFormModal } from "./_components/EmpleadoFormModal";
import { PayrollDrawer } from "./_components/PayrollDrawer";

import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { exportToCsv } from "@/lib/utils/export-csv";
import type { Employee } from "@/lib/api";
import { api } from "@/lib/api";
import { ImportCsvModal } from "@/components/shared/ImportCsvModal";

export default function EmployeesPage() {
    const {
        employees, isLoading, columns, departmentOptions, activeCount, totalSalary,
        form, setForm, showModal, setShowModal, editingId, saving, error, openModal, handleSubmit,
        selectedEmp, setSelectedEmp, empPayrolls, loadingPayrolls,
        docsEmp, setDocsEmp,
    } = useEmpleados();

    const [showImport, setShowImport] = useState(false);

    const handleExport = () =>
        exportToCsv<Employee>("empleados", employees, [
            { header: "Nombre", accessor: (e) => e.name },
            { header: "NIF", accessor: (e) => e.nif ?? "" },
            { header: "Email", accessor: (e) => e.email ?? "" },
            { header: "Departamento", accessor: (e) => e.department ?? "" },
            { header: "Rol", accessor: (e) => e.role ?? "" },
            { header: "Salario base", accessor: (e) => e.base_salary ?? "" },
            { header: "Estado", accessor: (e) => e.status },
            { header: "Fecha alta", accessor: (e) => e.join_date ?? "" },
        ]);

    return (
        <div className="space-y-6 p-6">
            {docsEmp && <EmployeeDocsModal employee={docsEmp} onClose={() => setDocsEmp(null)} />}

            <PageHeader
                title="Directorio de Empleados"
                description="Gestiona las altas, roles y salarios. El Agente RRHH usará esta tabla para pre-calcular nóminas."
                icon={Users}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => setShowImport(true)}>
                            <Upload className="mr-2 h-4 w-4" /> Importar CSV
                        </Button>
                        <Button onClick={openModal}>
                            <Plus className="mr-2 h-4 w-4" /> Añadir Empleado
                        </Button>
                    </div>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <KpiCard title="Plantilla Activa" value={activeCount} icon={Users} />
                <KpiCard title="Gasto Salarial (Mensual)" value={currencyFmt.format(totalSalary)} icon={Wallet} />
                <KpiCard
                    title="Status Legal"
                    value="En regla"
                    icon={ShieldCheck}
                    description="Contratos en regla. El sistema generará borradores el día 26."
                />
            </div>

            {/* Table */}
            {employees.length === 0 && !isLoading ? (
                <EmptyState
                    icon={Users}
                    title="No hay empleados registrados"
                    description="Añade tu primer empleado para empezar a gestionar la plantilla."
                    action={{ label: "Añadir el primero", onClick: openModal }}
                />
            ) : (
                <DataTable
                    columns={columns}
                    data={employees}
                    searchKey="name"
                    searchPlaceholder="Buscar por nombre o NIF..."
                    isLoading={isLoading}
                    emptyMessage="No se encontraron empleados."
                    facetedFilters={[
                        { column: "status", title: "Estado", options: STATUS_OPTIONS },
                        { column: "department", title: "Departamento", options: departmentOptions },
                    ]}
                    onExport={handleExport}
                />
            )}

            {/* Employee form modal */}
            <EmpleadoFormModal
                open={showModal}
                onClose={() => setShowModal(false)}
                editingId={editingId}
                form={form}
                setForm={setForm}
                saving={saving}
                error={error}
                onSubmit={handleSubmit}
            />

            {/* Import CSV modal */}
            <ImportCsvModal
                open={showImport}
                onClose={() => setShowImport(false)}
                entityName="empleados"
                columns={[
                    { header: "Nombre", field: "nombre", required: true, example: "Ana García" },
                    { header: "NIF", field: "nif", example: "12345678A" },
                    { header: "Email", field: "email", example: "ana@empresa.com" },
                    { header: "Departamento", field: "departamento", example: "Ventas" },
                    { header: "Rol", field: "rol", example: "Comercial" },
                    { header: "Salario base", field: "salario_base", example: "28000" },
                    { header: "IRPF %", field: "irpf", example: "15" },
                    { header: "Estado", field: "estado", example: "active" },
                ]}
                onImport={(rows) => api.importBulk.employees(rows)}
                onSuccess={() => window.location.reload()}
            />

            {/* Payroll drawer */}
            {selectedEmp && (
                <PayrollDrawer
                    selectedEmp={selectedEmp}
                    onClose={() => setSelectedEmp(null)}
                    empPayrolls={empPayrolls}
                    loadingPayrolls={loadingPayrolls}
                />
            )}
        </div>
    );
}

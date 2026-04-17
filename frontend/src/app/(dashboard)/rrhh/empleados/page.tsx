"use client";

import { Users, Plus, Wallet, ShieldCheck } from "lucide-react";
import { useEmpleados, STATUS_OPTIONS, currencyFmt } from "./_hooks/useEmpleados";
import { EmployeeDocsModal } from "./_components/EmployeeDocsModal";
import { EmpleadoFormModal } from "./_components/EmpleadoFormModal";
import { PayrollDrawer } from "./_components/PayrollDrawer";

import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";

export default function EmployeesPage() {
    const {
        employees, isLoading, columns, departmentOptions, activeCount, totalSalary,
        form, setForm, showModal, setShowModal, editingId, saving, error, openModal, handleSubmit,
        selectedEmp, setSelectedEmp, empPayrolls, loadingPayrolls,
        docsEmp, setDocsEmp,
    } = useEmpleados();

    return (
        <div className="space-y-6 p-6">
            {docsEmp && <EmployeeDocsModal employee={docsEmp} onClose={() => setDocsEmp(null)} />}

            <PageHeader
                title="Directorio de Empleados"
                description="Gestiona las altas, roles y salarios. El Agente RRHH usará esta tabla para pre-calcular nóminas."
                icon={Users}
                actions={
                    <Button onClick={openModal}>
                        <Plus className="mr-2 h-4 w-4" /> Añadir Empleado
                    </Button>
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
                    action={
                        <Button onClick={openModal} size="sm">
                            <Plus className="mr-2 h-4 w-4" /> Añadir el primero
                        </Button>
                    }
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

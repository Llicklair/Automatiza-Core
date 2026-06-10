"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { PortalData, Expense, Employee } from "@/lib/api";
import { useUserRole } from "@/hooks/useUserRole";
import type { Tab } from "../_components/constants";

export interface LeaveFormState {
    leave_type: string;
    start_date: string;
    end_date: string;
    notes: string;
}

export interface ExpenseFormState {
    amount: string;
    category: string;
    description: string;
    date: string;
    notes: string;
}

export function usePortal() {
    const role = useUserRole();
    const isAdmin = role === "admin";

    const [tab, setTab] = useState<Tab>("ficha");
    const [data, setData] = useState<PortalData | null>(null);
    const [loading, setLoading] = useState(true);

    // Admin "view as employee" mode
    const [employeesList, setEmployeesList] = useState<Employee[]>([]);
    const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>("");
    const readOnly = !!data?.read_only;

    // Clock in/out
    const [clockBusy, setClockBusy] = useState(false);
    const [clockError, setClockError] = useState<string | null>(null);

    // Leave request modal
    const [showLeave, setShowLeave] = useState(false);
    const [leaveForm, setLeaveForm] = useState<LeaveFormState>({ leave_type: "vacaciones", start_date: "", end_date: "", notes: "" });
    const [saving, setSaving] = useState(false);
    const [leaveError, setLeaveError] = useState<string | null>(null);

    // Gastos
    const [myExpenses, setMyExpenses] = useState<Expense[]>([]);
    const [showExpense, setShowExpense] = useState(false);
    const [expenseForm, setExpenseForm] = useState<ExpenseFormState>({ amount: "", category: "viaje", description: "", date: new Date().toISOString().slice(0, 10), notes: "" });
    const [expenseSaving, setExpenseSaving] = useState(false);
    const [expenseError, setExpenseError] = useState<string | null>(null);
    const [uploadingReceiptId, setUploadingReceiptId] = useState<string | null>(null);

    const load = async (asEmployeeId?: string) => {
        setLoading(true);
        try {
            const portalData = asEmployeeId
                ? await api.portal.meAs(asEmployeeId)
                : await api.portal.me();
            setData(portalData);
            if (portalData.employee) {
                try {
                    const exps = await api.hr.expenses.list(undefined, portalData.employee.id);
                    setMyExpenses(exps);
                } catch { /* noop */ }
            } else {
                setMyExpenses([]);
            }
        } catch { /* noop */ }
        finally { setLoading(false); }
    };

    useEffect(() => { load(); }, []);

    // Admin: load employees list for the "view as" selector
    useEffect(() => {
        if (!isAdmin) return;
        (async () => {
            try {
                const list = await api.hr.employees.list();
                setEmployeesList(list);
            } catch { /* noop */ }
        })();
    }, [isAdmin]);

    const handleSelectEmployee = (empId: string) => {
        setSelectedEmployeeId(empId);
        load(empId || undefined);
    };

    const handleClockIn = async () => {
        setClockBusy(true);
        setClockError(null);
        try {
            await api.portal.clockIn();
            await load();
        } catch (e) {
            setClockError(e instanceof Error ? e.message : "No se pudo fichar la entrada");
        } finally {
            setClockBusy(false);
        }
    };

    const handleClockOut = async () => {
        setClockBusy(true);
        setClockError(null);
        try {
            await api.portal.clockOut();
            await load();
        } catch (e) {
            setClockError(e instanceof Error ? e.message : "No se pudo fichar la salida");
        } finally {
            setClockBusy(false);
        }
    };

    const emp = data?.employee;

    const handleSubmitExpense = async () => {
        if (!expenseForm.amount || !expenseForm.description || !expenseForm.date) {
            setExpenseError("Completa los campos obligatorios."); return;
        }
        if (!emp) return;
        setExpenseSaving(true); setExpenseError(null);
        try {
            await api.hr.expenses.create({
                employee_id: emp.id,
                amount: parseFloat(expenseForm.amount),
                category: expenseForm.category,
                description: expenseForm.description,
                date: expenseForm.date,
                notes: expenseForm.notes || undefined,
            });
            setShowExpense(false);
            setExpenseForm({ amount: "", category: "viaje", description: "", date: new Date().toISOString().slice(0, 10), notes: "" });
            await load();
        } catch { setExpenseError("Error al enviar el gasto."); }
        finally { setExpenseSaving(false); }
    };

    const handleUploadReceipt = async (expId: string, file: File) => {
        setUploadingReceiptId(expId);
        try {
            await api.hr.expenses.uploadReceipt(expId, file);
            await load();
        } catch { /* noop */ }
        finally { setUploadingReceiptId(null); }
    };

    const handleSubmitLeave = async () => {
        if (!leaveForm.start_date || !leaveForm.end_date) { setLeaveError("Rellena las fechas."); return; }
        setSaving(true); setLeaveError(null);
        try {
            await api.portal.submitLeave(leaveForm);
            setShowLeave(false);
            setLeaveForm({ leave_type: "vacaciones", start_date: "", end_date: "", notes: "" });
            await load();
        } catch { setLeaveError("Error al enviar."); }
        finally { setSaving(false); }
    };

    return {
        isAdmin,
        tab, setTab,
        data, loading,
        employeesList, selectedEmployeeId, readOnly,
        clockBusy, clockError,
        showLeave, setShowLeave, leaveForm, setLeaveForm, saving, leaveError, setLeaveError,
        myExpenses, showExpense, setShowExpense, expenseForm, setExpenseForm, expenseSaving, expenseError, setExpenseError,
        uploadingReceiptId,
        handleSelectEmployee, handleClockIn, handleClockOut,
        handleSubmitExpense, handleUploadReceipt, handleSubmitLeave,
        emp,
    };
}

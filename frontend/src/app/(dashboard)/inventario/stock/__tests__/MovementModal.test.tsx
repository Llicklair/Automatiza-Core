import { useState } from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@/test-utils/render";
import { MovementModal } from "../_components/MovementModal";
import { type MovementForm } from "../_hooks/useStock";
import { type Product } from "@/lib/api";

const product = {
    id: "p1",
    tenant_id: "t1",
    item_type: "product",
    sku: "SKU-1",
    barcode: null,
    name: "Caja de tornillos",
    description: null,
    category: null,
    location: null,
    unit: "ud",
    price: 10,
    cost_price: null,
    tax_percentage: 21,
    stock_quantity: 50,
    stock_boxes: 4,
    stock_min_alert: 0,
    is_active: true,
    supplier_id: null,
    reorder_quantity: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
} as Product;

const baseForm: MovementForm = {
    movement_type: "entrada",
    stock_kind: "unit",
    quantity: 1,
    reference: "",
    reason: "",
    notes: "",
};

// Stateful harness so the controlled MovementForm actually updates,
// mirroring how useStock wires setMovForm in the real page.
function Harness({ initial, onForm }: { initial?: Partial<MovementForm>; onForm?: (f: MovementForm) => void }) {
    const [movForm, setMovForm] = useState<MovementForm>({ ...baseForm, ...initial });
    onForm?.(movForm);
    return (
        <MovementModal
            open
            onOpenChange={vi.fn()}
            selectedProduct={product}
            movForm={movForm}
            setMovForm={(updater) => {
                setMovForm((prev) => {
                    const next = typeof updater === "function" ? updater(prev) : updater;
                    onForm?.(next);
                    return next;
                });
            }}
            onSubmit={vi.fn()}
            saving={false}
        />
    );
}

describe("MovementModal", () => {
    it("shows both unit and box counters in the description", () => {
        render(<Harness />);
        expect(screen.getByText("50")).toBeInTheDocument();
        expect(screen.getByText("4 cajas")).toBeInTheDocument();
    });

    it("renders the stock_kind selector (Unidad / Caja)", () => {
        render(<Harness />);
        expect(screen.getByRole("button", { name: "Unidad" })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Caja" })).toBeInTheDocument();
    });

    it("switches stock_kind to box when Caja is clicked", async () => {
        let latest: MovementForm = baseForm;
        const { user } = render(<Harness onForm={(f) => { latest = f; }} />);
        await user.click(screen.getByRole("button", { name: "Caja" }));
        expect(latest.stock_kind).toBe("box");
    });

    it("does NOT show the reason selector for entrada", () => {
        render(<Harness initial={{ movement_type: "entrada" }} />);
        expect(screen.queryByLabelText("Motivo")).not.toBeInTheDocument();
    });

    it("shows the reason selector with write-off motives for salida", () => {
        render(<Harness initial={{ movement_type: "salida" }} />);
        expect(screen.getByLabelText("Motivo")).toBeInTheDocument();
        expect(screen.getByRole("option", { name: "Rotura" })).toBeInTheDocument();
        expect(screen.getByRole("option", { name: "Merma" })).toBeInTheDocument();
        expect(screen.getByRole("option", { name: "Robo" })).toBeInTheDocument();
        expect(screen.getByRole("option", { name: "Caducado" })).toBeInTheDocument();
    });

    it("updates reason when an option is selected (write-off)", async () => {
        let latest: MovementForm = baseForm;
        const { user } = render(<Harness initial={{ movement_type: "salida" }} onForm={(f) => { latest = f; }} />);
        await user.selectOptions(screen.getByLabelText("Motivo"), "rotura");
        expect(latest.reason).toBe("rotura");
    });

    it("previews new box stock when stock_kind is box", () => {
        render(<Harness initial={{ movement_type: "entrada", stock_kind: "box", quantity: 2 }} />);
        // 4 boxes + 2 = 6
        expect(screen.getByText("6")).toBeInTheDocument();
    });
});

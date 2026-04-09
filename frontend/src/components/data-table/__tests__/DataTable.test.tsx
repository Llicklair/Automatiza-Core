import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@/test-utils/render";
import { DataTable } from "../DataTable";
import { ColumnDef } from "@tanstack/react-table";

// Mock sub-components that have complex dependencies
vi.mock("../DataTablePagination", () => ({
    DataTablePagination: () => <div data-testid="pagination">Pagination</div>,
}));

vi.mock("../DataTableToolbar", () => ({
    DataTableToolbar: () => <div data-testid="toolbar">Toolbar</div>,
}));

vi.mock("../DataTableSkeleton", () => ({
    DataTableSkeleton: () => <div data-testid="skeleton">Loading...</div>,
}));

interface TestRow {
    id: number;
    name: string;
    status: string;
}

const columns: ColumnDef<TestRow, unknown>[] = [
    {
        accessorKey: "id",
        header: "ID",
    },
    {
        accessorKey: "name",
        header: "Nombre",
    },
    {
        accessorKey: "status",
        header: "Estado",
    },
];

const sampleData: TestRow[] = [
    { id: 1, name: "Alice", status: "activo" },
    { id: 2, name: "Bob", status: "inactivo" },
    { id: 3, name: "Charlie", status: "pendiente" },
];

describe("DataTable", () => {
    it("renders column headers", () => {
        render(<DataTable columns={columns} data={sampleData} />);

        expect(screen.getByText("ID")).toBeInTheDocument();
        expect(screen.getByText("Nombre")).toBeInTheDocument();
        expect(screen.getByText("Estado")).toBeInTheDocument();
    });

    it("renders row data", () => {
        render(<DataTable columns={columns} data={sampleData} />);

        expect(screen.getByText("Alice")).toBeInTheDocument();
        expect(screen.getByText("Bob")).toBeInTheDocument();
        expect(screen.getByText("Charlie")).toBeInTheDocument();
    });

    it("renders the correct number of rows", () => {
        render(<DataTable columns={columns} data={sampleData} />);

        // 1 header row + 3 data rows = 4
        const rows = screen.getAllByRole("row");
        expect(rows.length).toBe(4);
    });

    it("shows empty message when data is empty", () => {
        render(<DataTable columns={columns} data={[]} />);

        expect(screen.getByText("Sin resultados.")).toBeInTheDocument();
    });

    it("shows custom empty message", () => {
        render(
            <DataTable
                columns={columns}
                data={[]}
                emptyMessage="No hay datos disponibles"
            />,
        );

        expect(screen.getByText("No hay datos disponibles")).toBeInTheDocument();
    });

    it("renders skeleton when isLoading is true", () => {
        render(<DataTable columns={columns} data={[]} isLoading={true} />);

        expect(screen.getByTestId("skeleton")).toBeInTheDocument();
        // Should NOT render the table headers
        expect(screen.queryByText("ID")).not.toBeInTheDocument();
    });

    it("renders toolbar and pagination", () => {
        render(<DataTable columns={columns} data={sampleData} />);

        expect(screen.getByTestId("toolbar")).toBeInTheDocument();
        expect(screen.getByTestId("pagination")).toBeInTheDocument();
    });

    it("renders cell values correctly", () => {
        render(<DataTable columns={columns} data={sampleData} />);

        expect(screen.getByText("1")).toBeInTheDocument();
        expect(screen.getByText("2")).toBeInTheDocument();
        expect(screen.getByText("3")).toBeInTheDocument();
        expect(screen.getByText("activo")).toBeInTheDocument();
        expect(screen.getByText("inactivo")).toBeInTheDocument();
        expect(screen.getByText("pendiente")).toBeInTheDocument();
    });
});

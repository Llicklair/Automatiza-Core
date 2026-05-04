export interface CsvColumn<T> {
    header: string;
    accessor: (row: T) => string | number | null | undefined;
}

export function exportToCsv<T>(filename: string, rows: T[], columns: CsvColumn<T>[]): void {
    const header = columns.map((c) => `"${c.header}"`).join(",");
    const body = rows
        .map((row) =>
            columns
                .map((c) => {
                    const val = c.accessor(row) ?? "";
                    return `"${String(val).replace(/"/g, '""')}"`;
                })
                .join(",")
        )
        .join("\n");

    const csv = `${header}\n${body}`;
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

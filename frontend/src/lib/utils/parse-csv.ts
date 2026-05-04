/**
 * Parses a CSV string into an array of row arrays.
 * Handles quoted fields with embedded commas and newlines.
 */
export function parseCsvRows(text: string): string[][] {
    const rows: string[][] = [];
    let row: string[] = [];
    let cell = "";
    let inQuotes = false;
    const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

    for (let i = 0; i < normalized.length; i++) {
        const ch = normalized[i];
        if (ch === '"') {
            if (inQuotes && normalized[i + 1] === '"') { cell += '"'; i++; }
            else { inQuotes = !inQuotes; }
        } else if (ch === "," && !inQuotes) {
            row.push(cell.trim()); cell = "";
        } else if (ch === "\n" && !inQuotes) {
            row.push(cell.trim()); cell = "";
            if (row.some((c) => c !== "")) rows.push(row);
            row = [];
        } else {
            cell += ch;
        }
    }
    if (cell || row.length) { row.push(cell.trim()); if (row.some((c) => c !== "")) rows.push(row); }
    return rows;
}

/**
 * Converts CSV text to an array of objects using the first row as keys.
 * Keys are normalized to lowercase with underscores.
 */
export function csvToObjects(text: string): Record<string, string>[] {
    const rows = parseCsvRows(text);
    if (rows.length < 2) return [];
    const headers = rows[0].map((h) => h.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, ""));
    return rows.slice(1).map((row) =>
        Object.fromEntries(headers.map((h, i) => [h, row[i] ?? ""]))
    );
}

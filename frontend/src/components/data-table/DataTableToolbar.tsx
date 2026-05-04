"use client";

import { Table } from "@tanstack/react-table";
import { X, SlidersHorizontal, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    DropdownMenu,
    DropdownMenuCheckboxItem,
    DropdownMenuContent,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { DataTableFacetedFilter } from "./DataTableFacetedFilter";

export interface FacetedFilterConfig {
    column: string;
    title: string;
    options: { label: string; value: string; icon?: React.ComponentType<{ className?: string }> }[];
}

interface DataTableToolbarProps<TData> {
    table: Table<TData>;
    searchKey?: string;
    searchPlaceholder?: string;
    facetedFilters?: FacetedFilterConfig[];
    onExport?: () => void;
}

export function DataTableToolbar<TData>({
    table,
    searchKey,
    searchPlaceholder = "Buscar...",
    facetedFilters,
    onExport,
}: DataTableToolbarProps<TData>) {
    const isFiltered = table.getState().columnFilters.length > 0;

    return (
        <div className="flex items-center justify-between gap-2">
            <div className="flex flex-1 items-center gap-2">
                {searchKey && (
                    <Input
                        placeholder={searchPlaceholder}
                        value={(table.getColumn(searchKey)?.getFilterValue() as string) ?? ""}
                        onChange={(event) => table.getColumn(searchKey)?.setFilterValue(event.target.value)}
                        className="h-8 w-[150px] lg:w-[250px]"
                    />
                )}
                {facetedFilters?.map((filter) => {
                    const column = table.getColumn(filter.column);
                    return column ? (
                        <DataTableFacetedFilter
                            key={filter.column}
                            column={column}
                            title={filter.title}
                            options={filter.options}
                        />
                    ) : null;
                })}
                {isFiltered && (
                    <Button variant="ghost" onClick={() => table.resetColumnFilters()} className="h-8 px-2 lg:px-3">
                        Limpiar
                        <X className="ml-2 h-4 w-4" />
                    </Button>
                )}
            </div>
            {onExport && (
                <Button variant="outline" size="sm" className="h-8 gap-1.5" onClick={onExport}>
                    <Download className="h-3.5 w-3.5" />
                    CSV
                </Button>
            )}
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="ml-auto hidden h-8 lg:flex">
                        <SlidersHorizontal className="mr-2 h-4 w-4" />
                        Columnas
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[180px]">
                    <DropdownMenuLabel>Visibilidad</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    {table.getAllColumns().filter((column) => typeof column.accessorFn !== "undefined" && column.getCanHide()).map((column) => (
                        <DropdownMenuCheckboxItem
                            key={column.id}
                            checked={column.getIsVisible()}
                            onCheckedChange={(value) => column.toggleVisibility(!!value)}
                            className="capitalize"
                        >
                            {column.id}
                        </DropdownMenuCheckboxItem>
                    ))}
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    );
}

"use client";

import { useState } from "react";
import type { Employee } from "@/lib/api";

/** Manages which employee's document modal is open. */
export function useEmpleadosUpload() {
    const [docsEmp, setDocsEmp] = useState<Employee | null>(null);
    return { docsEmp, setDocsEmp };
}

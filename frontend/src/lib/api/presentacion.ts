/**
 * PRES.ASS — cliente de presentación asistida AEAT (Modelos 131 y 200).
 */
import { BASE, getToken, request } from "./client";

export type ModeloAsistido = "131" | "200";

export interface PresentacionInfo {
    modelo: ModeloAsistido;
    descripcion: string;
    sede_url: string;
    asistido: true;
    presentacion_automatica: false;
}

export const presentacion = {
    info: (modelo: ModeloAsistido): Promise<PresentacionInfo> =>
        request<PresentacionInfo>(
            `/api/v1/presentacion/asistida/info/${modelo}`,
        ),

    /** Descarga el XML pre-rellenado como fichero. */
    downloadXml: async (
        modelo: ModeloAsistido,
        params?: { ejercicio?: number; trimestre?: number },
    ): Promise<void> => {
        const token = getToken();
        if (!token) throw new Error("No autenticado");
        const qs = new URLSearchParams();
        if (params?.ejercicio) qs.append("ejercicio", String(params.ejercicio));
        if (params?.trimestre) qs.append("trimestre", String(params.trimestre));
        const url = `${BASE}/api/v1/presentacion/asistida/xml/${modelo}${qs.toString() ? "?" + qs : ""}`;
        const res = await fetch(url, {
            headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Error descargando XML: ${res.status}`);
        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = objectUrl;
        const period = modelo === "131"
            ? `${params?.ejercicio ?? new Date().getFullYear()}-Q${params?.trimestre ?? 1}`
            : `${params?.ejercicio ?? new Date().getFullYear()}`;
        a.download = `modelo${modelo}-prerelleno-${period}.xml`;
        a.click();
        URL.revokeObjectURL(objectUrl);
    },
};

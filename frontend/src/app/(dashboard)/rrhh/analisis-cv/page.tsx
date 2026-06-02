import { redirect } from "next/navigation";

// El análisis de CV se fusionó con Reclutamiento (pestaña «Análisis de CV»).
// Mantenemos esta ruta como redirección para enlaces/marcadores antiguos.
export default function AnalisisCvRedirect() {
    redirect("/rrhh/reclutamiento?tab=cv");
}

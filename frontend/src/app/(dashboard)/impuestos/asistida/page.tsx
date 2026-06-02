import { redirect } from "next/navigation";

// Presentación asistida se fusionó en «Impuestos» (pestaña Presentación asistida).
export default function AsistidaRedirect() {
    redirect("/impuestos?tab=asistida");
}

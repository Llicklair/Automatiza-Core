import { redirect } from "next/navigation";

// Apoderamiento AEAT se fusionó en «Configuración fiscal» (pestaña Apoderamiento).
export default function RegapRedirect() {
    redirect("/configuracion/verifactu?tab=apoderamiento");
}

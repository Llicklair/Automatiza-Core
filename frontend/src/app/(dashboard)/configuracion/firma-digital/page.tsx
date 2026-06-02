import { redirect } from "next/navigation";

// Firma digital se fusionó en «Configuración fiscal» (pestaña Firma digital).
export default function FirmaDigitalRedirect() {
    redirect("/configuracion/verifactu?tab=firma");
}

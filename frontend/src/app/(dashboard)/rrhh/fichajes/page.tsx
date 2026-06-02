import { redirect } from "next/navigation";

// Fichajes se fusionó en «Jornada y ausencias» (pestaña Fichajes).
export default function FichajesRedirect() {
    redirect("/rrhh/jornada?tab=fichajes");
}

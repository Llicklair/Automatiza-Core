import { redirect } from "next/navigation";

// Vacaciones se fusionó en «Jornada y ausencias» (pestaña Vacaciones).
export default function VacacionesRedirect() {
    redirect("/rrhh/jornada?tab=vacaciones");
}

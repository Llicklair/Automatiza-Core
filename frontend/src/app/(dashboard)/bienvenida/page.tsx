import { redirect } from "next/navigation";

// El wizard de bienvenida se retiró; el onboarding único es «Primeros pasos».
// (La simulación /bienvenida/simulacion-303 sigue disponible por su URL.)
export default function BienvenidaRedirect() {
    redirect("/primeros-pasos");
}

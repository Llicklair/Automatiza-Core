import { redirect } from "next/navigation";

// La importación de Excel se fusionó con Escáner (pestaña «Importar Excel»).
// Mantenemos esta ruta como redirección para enlaces/marcadores antiguos.
export default function ExcelRedirect() {
    redirect("/escaner?tab=excel");
}

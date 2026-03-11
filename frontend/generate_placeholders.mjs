import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const routes = [
    '/ventas/presupuestos',
    '/ventas/servicios',
    '/compras/facturas',
    '/crm/embudo-de-ventas',
    '/crm/actividades',
    '/crm/calendario',
    '/crm/reservas',
    '/crm/reuniones',
    '/rrhh/nominas',
    '/proyectos/mis-tareas',
    '/proyectos/proyectos',
    '/tesoreria/cashflow',
    '/tesoreria/pagos-y-cobros',
    '/tesoreria/remesas',
    '/contabilidad/cuadro-de-cuentas',
    '/contabilidad/libro-diario',
    '/contabilidad/activos',
    '/contabilidad/perdidas-y-ganancias',
    '/contabilidad/balance-de-situacion',
    '/contabilidad/asesorias',
    '/impuestos',
    '/analitica'
];

// Project root is C:\Users\Marcos\Desktop\atomatizacion de empresas\frontend
// This script will be run from the frontend directory
const basePath = path.join(process.cwd(), 'src/app/(dashboard)');

routes.forEach(route => {
    const dirPath = path.join(basePath, route);
    fs.mkdirSync(dirPath, { recursive: true });

    const title = route.split('/').pop().replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    const content = `"use client";

import { Construction } from "lucide-react";

export default function PlaceholderPage() {
    return (
        <div className="p-8 max-w-4xl mx-auto h-[80vh] flex flex-col items-center justify-center text-center">
            <div className="w-20 h-20 bg-indigo-500/10 rounded-3xl flex items-center justify-center mb-6 border border-indigo-500/20 shadow-lg shadow-indigo-500/10">
                <Construction className="w-10 h-10 text-indigo-400" />
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">${title}</h1>
            <p className="text-zinc-400 max-w-md">
                Este módulo está actualmente en desarrollo. Muy pronto podrás acceder a todas sus funcionalidades.
            </p>
        </div>
    );
}
`;
    fs.writeFileSync(path.join(dirPath, 'page.tsx'), content);
});
console.log('Placeholders genreados exitosamente.');

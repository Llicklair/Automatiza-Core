# Auditoría de accesibilidad — U.6 / QA.AXE

> **Versión 1.0 — 2026-05-14**
>
> Objetivo: garantizar conformidad **WCAG 2.1 nivel AA** en la UI desktop de
> AutomatizaPyme. Alcance MVP: rutas críticas del flujo fiscal (login,
> dashboard, chat agente, modal de aprobación humana, presentación AEAT).

## §1 Marco normativo aplicable

| Norma | Aplicabilidad |
|---|---|
| WCAG 2.1 nivel AA | Estándar internacional de facto. |
| UNE-EN 301 549 | Transposición europea de WCAG. Obligatoria para Sector Público; recomendada para B2B. |
| RD 1112/2018 | Accesibilidad de sitios web del sector público español. AutomatizaPyme no es sector público, pero al integrarse con clientes-gestoría que sirven al sector público hereda parte del estándar. |
| Reglamento UE 2024/1689 (AI Act) Art. 50 | El banner de transparencia AI debe ser perceptible por todos los usuarios incluyendo aquellos con lector de pantalla. |

## §2 Gate automatizado (axe-core)

### §2.1 Suite local

```bash
cd frontend
npm run test:a11y
```

Ejecuta `vitest run src/test/a11y` — todos los componentes deben devolver
`toHaveNoViolations()` contra el preset `wcag2a + wcag2aa + wcag21a + wcag21aa`.

### §2.2 CI

El job `frontend-a11y` en `.github/workflows/ci.yml` se ejecuta en cada PR
contra `main` y bloquea el merge si hay violaciones. Es dependencia
upstream de `frontend-build`, así que un PR con violaciones no llega a
empaquetarse.

### §2.3 Componentes cubiertos a 2026-05-14

| Componente | Test | Verde |
|---|---|---|
| `AIDisclosureBanner` (AI.BAN) | `AIDisclosureBanner.a11y.test.tsx` | ✓ |
| `AIGenerationFooter` (AI.BAN) | `AIGenerationFooter.a11y.test.tsx` | ✓ |
| `LoginPage` | `login.a11y.test.tsx` | ✓ |

Próximos componentes a cubrir (PR follow-up): ChatSection (`mi-equipo`),
ApprovalCard (`bandeja`), AsientoModal (`contabilidad`), modal de
aprobación fiscal (SEC.APR), wizard onboarding (UI.ONB), wizard REGAP
(PRES.REG).

## §3 Auditoría manual con NVDA — procedimiento para fundador

NVDA es el lector de pantalla open-source de referencia para Windows
(NV Access). La auditoría manual cubre lo que axe-core no puede detectar:
flujos completos, claridad del anuncio por voz, orden de tabulación,
y mensajes de error contextuales.

### §3.1 Instalación (10 min)

1. Descargar de https://www.nvaccess.org/download/ (gratuito).
2. Instalar con permisos estándar (no admin para auditoría).
3. Atajos clave a memorizar:
   - `Insert + Q` — apagar NVDA temporalmente
   - `Insert + Espacio` — modo navegación / modo formulario
   - `H` — siguiente encabezado (h1, h2...)
   - `D` — siguiente landmark (main, nav, banner...)
   - `F` — siguiente campo de formulario
   - `B` — siguiente botón
   - `Tab` — siguiente elemento focusable

### §3.2 Checklist por flujo (2h sesión)

Marcar ✓ o ✗ con nota.

**Login (5 min)**
- [ ] Al cargar la página, NVDA anuncia "AutomatizaPyme - Panel de Control".
- [ ] El skip-link "Saltar al contenido" se anuncia al primer Tab.
- [ ] Los campos email y password se anuncian con su etiqueta (no solo "edit").
- [ ] El botón "Iniciar sesión" anuncia su estado (botón / submit).
- [ ] Si se envía con credenciales incorrectas, NVDA anuncia el error inmediatamente (rol "alert").
- [ ] Tab navega en orden lógico: email → password → botón → "olvidé contraseña" → "regístrate".

**Dashboard (5 min)**
- [ ] `D` lista al menos: banner (header), navigation (sidebar), main (contenido).
- [ ] El botón "Colapsar menú" anuncia su estado `aria-expanded`.
- [ ] Los ítems de menú con submenús anuncian "expandido/colapsado".
- [ ] El indicador de notificaciones se anuncia con el número.

**Chat agente — `mi-equipo` (10 min)**
- [ ] Al primer mensaje, NVDA anuncia el banner Art. 50 ("Estás interactuando con un sistema de IA…").
- [ ] El input del mensaje tiene `aria-label` claro.
- [ ] El botón "Enviar" se anuncia como botón submit.
- [ ] Tras la respuesta, el footer "Generado por…" se lee (no `aria-hidden`).
- [ ] El icono `↳` decorativo NO se lee (debe tener `aria-hidden`).

**Modal de aprobación fiscal — SEC.APR (15 min)**
- [ ] Al abrir, el foco se mueve al modal automáticamente.
- [ ] Tab queda atrapado dentro del modal (no escapa al fondo).
- [ ] El texto canónico a tipear se anuncia íntegro.
- [ ] El campo de tipeo anuncia errores de validación (texto que no coincide).
- [ ] Escape cierra el modal y devuelve el foco al disparador original.

**Verifactu QR público — `/verify/<huella>` (5 min)**
- [ ] La huella se anuncia como código (no como palabra).
- [ ] El estado "Integridad verificada" se anuncia con rol `status`.
- [ ] El logo de AutomatizaPyme tiene alt.

**Banca, CRM, Documentos, Contabilidad (resto de la sesión)**
- [ ] Cada tabla principal se anuncia con número de filas y columnas.
- [ ] Los iconos-solo (lupa, papelera, edit) tienen `aria-label`.
- [ ] Los empty states comunican estado + CTA primario claramente.

### §3.3 Registro de la auditoría

Tras la sesión, registrar en `tasks/lessons.md` con encabezado
`A11Y NVDA — <fecha>` y bullets por flujo. Las violaciones detectadas
abren tickets en backlog con ID `A11Y.<n>`.

## §4 Reglas de regresión

- **Pre-commit**: si el diff toca `src/components/` o `src/app/`, el
  desarrollador debe ejecutar `npm run test:a11y` antes de empujar.
  Actualmente no está atado como hook (futuro: husky + lint-staged).
- **PR template**: las PRs que añaden UI deben marcar en checklist
  "He ejecutado `npm run test:a11y` y pasa".
- **Revisión trimestral**: la auditoría manual NVDA se repite cada
  quarter o tras cambios mayores de diseño (rediseño completo, nueva
  paleta, refactor de Sidebar/Header).

## §5 Excepciones documentadas

- **Canvas decorativo del login** (`NeuralBackground`): `aria-hidden`
  porque es animación ambiental sin información.
- **Spinner SVG en submit**: `aria-hidden` porque el texto "Iniciando
  sesión" ya comunica el estado.
- **Iconos lucide-react sin label**: cuando van junto a texto visible,
  no necesitan label (axe-core lo respeta automáticamente).

## §6 Histórico

| Fecha | Cambio |
|---|---|
| 2026-05-14 | Doc inicial. Suite axe-core con 5 tests verde + gate CI. |

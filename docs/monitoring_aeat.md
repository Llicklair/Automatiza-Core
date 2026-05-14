# Monitorización portal AEAT — CONT.MON

> Fuentes que el equipo de AutomatizaPyme debe vigilar para anticipar cambios normativos o técnicos que afecten a la presentación de modelos y a Verifactu.

## §1 Fuentes oficiales (suscripción obligatoria)

### Portal AEAT — Novedades técnicas

* **URL**: <https://www2.agenciatributaria.gob.es/wlpl/inwinvoc/es.aeat.dit.adu.adws.diseno.servlets.NovedadesServlet>
* **RSS**: <https://sede.agenciatributaria.gob.es/sede/novedades.xml>
* **Periodicidad de revisión**: lunes 09:00 CET por dev senior.
* **Disparador de acción**: cualquier mención a `Verifactu`, `SII`, `WSDL`, `XSD`, `Plataforma Colaboradores Sociales`, `modelo 303/130/347/390/111/190`.

### BOE — Sumario diario

* **URL**: <https://www.boe.es/diario_boe/ultimos.php>
* **RSS sumario**: <https://www.boe.es/rss/canal.php?c=ultimasdisposiciones>
* **Filtros relevantes**:
  - Reglamento Verifactu (`RD 1007/2023`).
  - Reglamento Facturación (`RD 1619/2012`).
  - Ley General Tributaria (modificaciones).
  - Orden HAC/* (modelos AEAT — periódicamente se publican órdenes de campañas).
* **Disparador**: cambio en RD que modifique fechas, formatos o aplicabilidad.

### Documentación Verifactu — versión vigente

* **URL**: <https://sede.agenciatributaria.gob.es/Sede/iva/sistemas-informaticos-facturacion-verifactu.html>
* **Periodicidad**: cada release de AutomatizaPyme verifica que el XSD usado coincide con la última versión publicada.
* **Disparador**: AEAT publica nuevo XSD → ticket P-0 para revisar tests de integración (FAC.TST).

## §2 Procedimiento de respuesta

Cuando se detecta un cambio relevante:

1. **Triaje (mismo día)**: dev senior abre ticket etiquetado `aeat-change` con el enlace al BOE/AEAT y resumen 3 líneas del impacto potencial.
2. **Análisis (T+24h)**: validar si el cambio afecta a:
   - XSD de Facturae/Verifactu → bloquea release siguiente.
   - Plazos de presentación → actualizar `compliance_agent` y calendario UI.
   - Tipos impositivos → actualizar agregaciones `services/reports/modelos_aeat.py`.
3. **PR (T+72h)**: implementar cambios + actualizar tests + nota en `tasks/lessons.md`.
4. **Comunicación cliente** (si afecta a UX o calendario): banner en dashboard + email a tier Gestoría.

## §3 Buffer técnico en sprint

Cada sprint Verifactu/PRES.* del roadmap incluye buffer **3 días** para absorber cambios AEAT sin descuadrar calendario. Si el buffer se consume completo y AEAT publica más cambios, se renegocia el sprint con el fundador.

## §4 Calendario interno

| Recurrente | Acción |
|---|---|
| **Lunes 09:00 CET** | Revisión RSS AEAT + BOE de la semana |
| **T-15d antes de cada vencimiento trimestral fiscal** | Comprobar que XSD/normas siguen vigentes |
| **Anual (enero)** | Revisar tipos impositivos / umbrales / fechas tope de campañas |

## §5 Runbook expreso si AEAT publica un breaking change crítico durante un sprint comprometido

1. **Pausar** trabajo del sprint actual relacionado con presentación.
2. **Calcular** plazo de adaptación que AEAT concede (normalmente 30-90 días).
3. **Comunicar** al fundador con número exacto de días hasta deadline.
4. Si el plazo de AEAT < tiempo de adaptación realista del software: **escalar** públicamente al cliente con plan B (presentación manual vía sede + asistida por AutomatizaPyme).
5. Una vez resuelto: post-mortem técnico en `tasks/lessons.md`.

# Runbook eje 12 — Presentación telemática AEAT (PRES.RB)

> Operativa real del flujo dual **homologación → producción** consensuada en Ronda 27 R.D. Permite que el equipo dev avance contra el entorno de pruebas AEAT mientras el trámite administrativo PRES.0 (alta colaborador social + cert representación) está en curso.

## §1 Las dos fases

### Fase A — Homologación (sin esperar PRES.0)

* **Credencial necesaria**: cert de pruebas FNMT (gratuito, online, ~10 min — solicitar al inicio de sprint 5).
* **Endpoint AEAT**: `https://www7.aeat.es/wlpl/inwinvoc/...` (pre-producción).
* **Datos**: usar fixtures sintéticos del corpus `tests/fixtures/`. Nunca NIFs reales en pruebas.
* **Cobertura técnica**:
  - Generación XML conforme XSD vigente.
  - Firma XAdES con cert pruebas.
  - Envío contra preproducción.
  - Parseo de acuse simulado.
  - Manejo de errores AEAT (XSD inválido, conflicto de huella, etc.).

### Fase B — Producción (después de PRES.0)

* **Credencial necesaria**: cert de representación FNMT de AutomatizaCore S.L. (decisión humana 15, ~50€). El alta como colaborador social (decisión humana 14) debe estar **completada y efectiva** antes.
* **Endpoint AEAT**: `https://www2.agenciatributaria.gob.es/wlpl/inwinvoc/...` (producción).
* **Datos**: facturas reales del tenant tras `MANDATORY_HUMAN_FISCAL` aprobado.
* **Smoke test obligatorio antes del primer cliente**:
  1. Crear factura test interna (tenant de pruebas de AutomatizaCore).
  2. Aprobar con `approve_fiscal` el modelo 303 simulado.
  3. Presentar contra producción AEAT.
  4. Verificar acuse de recibo.
  5. **Solo entonces** habilitar presentación automática en tier Gestoría.

## §2 Conmutación entre fases

Configuración por variable de entorno:

```
# Pre-producción (Fase A)
AEAT_PRESENTATION_MODE=staging
AEAT_PRESENTATION_ENDPOINT=https://www7.aeat.es/...
AEAT_REPRESENTATION_CERT_LABEL=test_fnmt

# Producción (Fase B)
AEAT_PRESENTATION_MODE=production
AEAT_PRESENTATION_ENDPOINT=https://www2.agenciatributaria.gob.es/...
AEAT_REPRESENTATION_CERT_LABEL=production_aeat
```

El cert se carga desde `CertStore` (DIS.IFACE) — nunca está en el .env en plano.

## §3 Checklist pre-launch comercial (1-jul / 22-jul / 9-ago según rama)

- [ ] **PRES.0** alta colaborador social efectiva (correo confirmación de AEAT).
- [ ] **DEC.15** cert representación FNMT producción cargado en `CertStore`.
- [ ] **DEC.16** contrato apoderamiento REGAP listo para enviar al cliente vía wizard PRES.1'.
- [ ] **Smoke test fase B** con tenant interno: 1 factura completa generada, aprobada, presentada y acuse recibido.
- [ ] **Healthcheck** `/api/v1/system/preconditions` devuelve ok=true.
- [ ] **Banner kill-switch** desactivado.
- [ ] **Cert de pruebas FNMT** conservado por si hay incidencia futura que requiera reproducir contra preproducción.

## §4 Procedimiento si AEAT rechaza un envío

1. **Capturar** el código de error AEAT + descripción + huella del registro afectado.
2. Si error de XSD/formato: el bug es nuestro → ticket `aeat-format-bug` P-0.
3. Si error de cadena de huella: investigar — la cadena debería ser íntegra (test `verify_chain_integrity`). Si está rota: ticket `verifactu-chain-break` P-0 + investigación de causa.
4. Si error de credenciales/expiración cert: emergencia → renovar cert AEAT inmediatamente (T+24h). Mientras tanto, pausar presentaciones automáticas.
5. Si error de plazo (vencimiento): comunicar al cliente que la presentación debe hacerse manual desde sede AEAT con asistencia de AutomatizaCore (deep-link PRES.5).

## §5 Mantenimiento del cert producción

* **Renovación**: certs FNMT de representación caducan a 2 años. Recordatorio T-60d antes (`CONT.1` punto 6).
* **Si caduca por accidente**: cae presentación de todos los clientes. Renovación urgente (cita previa FNMT ~3-5d hábiles). Comunicar a tier Gestoría con plazo.
* **Custodia**: `CertStore` (DIS.IFACE) cifrado con `safeStorage`. Acceso solo desde el proceso main de Electron en el equipo del fundador / servidor de presentación si se externaliza.

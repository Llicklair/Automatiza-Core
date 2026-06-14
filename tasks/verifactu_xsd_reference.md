# Referencia XSD oficial AEAT VeriFactu (Suministro de Registros de Facturación)

> RD 1007/2023 + Orden HAC/1177/2024. Referencia EXACTA extraída de los XSD oficiales
> descargados de la AEAT (versión de esquema `IDVersion = 1.0`). Todo lo que sigue está
> verificado contra el texto literal de `SuministroInformacion.xsd` y `SuministroLR.xsd`.

---

## 0. URLs canónicas oficiales (página de desarrolladores AEAT)

Página índice (developers):
`https://www.agenciatributaria.es/AEAT.desarrolladores/Desarrolladores/_menu_/Documentacion/Sistemas_Informaticos_de_Facturacion_y_Sistemas_VERI_FACTU/Esquemas_de_los_servicios_web/Esquemas_de_los_servicios_web.html`

XSD (la página oficial enlaza a `prewww2.aeat.es`; la **réplica de producción sin
certificado** que sí descarga es `www2.agenciatributaria.gob.es`, misma ruta
`tikeV1.0/cont/ws/`):

| Fichero | URL producción (descargable) |
|---|---|
| `SuministroLR.xsd` | `https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SuministroLR.xsd` |
| `SuministroInformacion.xsd` | `.../tikeV1.0/cont/ws/SuministroInformacion.xsd` |
| `RespuestaSuministro.xsd` | `.../tikeV1.0/cont/ws/RespuestaSuministro.xsd` |
| `ConsultaLR.xsd` | `.../tikeV1.0/cont/ws/ConsultaLR.xsd` |
| `RespuestaConsultaLR.xsd` | `.../tikeV1.0/cont/ws/RespuestaConsultaLR.xsd` |
| `EventosSIF.xsd` (solo no-VeriFactu) | `.../tikeV1.0/cont/ws/EventosSIF.xsd` |
| `RespuestaValRegistNoVeriFactu.xsd` | `.../tikeV1.0/cont/ws/RespuestaValRegistNoVeriFactu.xsd` |

La página oficial los enlaza vía `https://prewww2.aeat.es/static_files/.../tikeV1.0/cont/ws/<fichero>` (marcados "Con certificado").

> NO confundir con el SII: el SII vive en `.../G417/FicherosSuministros/V_1_1/` y usa
> otros namespaces (`.../ws/SuministroLR.xsd` del SII NO es el de VeriFactu).

Los 7 XSD están descargados en:
`backend/app/services/aeat/xsd/`

---

## 1. Namespaces y prefijos (CLAVE — versión del path ≠ versión del namespace)

> **Sorpresa #1:** la ruta de descarga es `tikeV1.0/...` pero el **target namespace es
> `tike/...` (SIN `V1.0`)**. Hay que usar EXACTAMENTE el namespace del atributo
> `targetNamespace`, no el de la URL.

| Prefijo | Namespace (targetNamespace literal) |
|---|---|
| `sf:` | `https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd` |
| `sfLR:` | `https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd` |
| `ds:` | `http://www.w3.org/2000/09/xmldsig#` (firma XML opcional) |

`elementFormDefault="qualified"` en ambos → **todos los elementos van cualificados**.

- `RegFactuSistemaFacturacion`, `Cabecera`, `RegistroFactura` → namespace **`sfLR`**.
- `RegistroAlta`, `RegistroAnulacion` y TODOS sus hijos → namespace **`sf`**
  (están definidos en `SuministroInformacion.xsd`, no en `SuministroLR.xsd`).

> **Sorpresa #2:** `RegistroAlta`/`RegistroAnulacion` y su contenido pertenecen a `sf:`
> (SuministroInformacion), aunque el contenedor `RegistroFactura` sea `sfLR:`.

---

## 2. Elemento raíz `RegFactuSistemaFacturacion` (sfLR)

```
RegFactuSistemaFacturacion (sfLR)
├── Cabecera                 sf:CabeceraType        [1]
└── RegistroFactura          sfLR:RegistroFacturaType  [1..1000]   ← maxOccurs=1000
        └── CHOICE: sf:RegistroAlta | sf:RegistroAnulacion
```

`CabeceraType` (orden exacto):
```
ObligadoEmision        sf:PersonaFisicaJuridicaESType   [1]   {NombreRazon, NIF}
Representante          sf:PersonaFisicaJuridicaESType   [0..1]{NombreRazon, NIF}
CHOICE [0..1]:
  RemisionVoluntaria   { FechaFinVeriFactu [0..1], Incidencia [0..1] }
  RemisionRequerimiento{ RefRequerimiento [1], FinRequerimiento [0..1] }
```
`PersonaFisicaJuridicaESType = { NombreRazon (TextMax120), NIF (NIFType, 9 chars) }`.

> Nota: `RemisionVoluntaria` es un elemento **inline** dentro de un CHOICE opcional;
> sus dos hijos (`FechaFinVeriFactu`, `Incidencia`) son ambos opcionales, así que
> `<RemisionVoluntaria/>` vacío es válido. Para VeriFactu real se suele omitir o dejar vacío.

---

## 3. `RegistroAlta` — ORDEN EXACTO (sf:RegistroFacturacionAltaType)

Orden literal del XSD (REQ = obligatorio, OPT = opcional):

| # | Elemento | Tipo | Oblig. |
|---|---|---|---|
| 1 | `IDVersion` | VersionType (enum: `1.0`) | REQ |
| 2 | `IDFactura` | IDFacturaExpedidaType | REQ |
| 3 | `RefExterna` | TextMax60 | OPT |
| 4 | `NombreRazonEmisor` | TextMax120 | REQ |
| 5 | `Subsanacion` | S/N | OPT |
| 6 | `RechazoPrevio` | N/S/X | OPT |
| 7 | `TipoFactura` | ClaveTipoFacturaType | REQ |
| 8 | `TipoRectificativa` | S/I | OPT |
| 9 | `FacturasRectificadas` | { IDFacturaRectificada [1..1000] } | OPT |
| 10 | `FacturasSustituidas` | { IDFacturaSustituida [1..1000] } | OPT |
| 11 | `ImporteRectificacion` | DesgloseRectificacionType | OPT |
| 12 | `FechaOperacion` | fecha (DD-MM-YYYY) | OPT |
| 13 | `DescripcionOperacion` | TextMax500 | REQ |
| 14 | `FacturaSimplificadaArt7273` | S/N | OPT |
| 15 | `FacturaSinIdentifDestinatarioArt61d` | S/N | OPT |
| 16 | `Macrodato` | S/N | OPT |
| 17 | `EmitidaPorTerceroODestinatario` | D/T | OPT |
| 18 | `Tercero` | PersonaFisicaJuridicaType | OPT |
| 19 | `Destinatarios` | { IDDestinatario [1..1000] } | OPT |
| 20 | `Cupon` | S/N | OPT |
| 21 | `Desglose` | DesgloseType | REQ |
| 22 | `CuotaTotal` | ImporteSgn12.2 | REQ |
| 23 | `ImporteTotal` | ImporteSgn12.2 | REQ |
| 24 | `Encadenamiento` | CHOICE PrimerRegistro \| RegistroAnterior | REQ |
| 25 | `SistemaInformatico` | SistemaInformaticoType | REQ |
| 26 | `FechaHoraHusoGenRegistro` | dateTime (ISO-8601 con huso) | REQ |
| 27 | `NumRegistroAcuerdoFacturacion` | TextMax15 | OPT |
| 28 | `IdAcuerdoSistemaInformatico` | TextMax16 | OPT |
| 29 | `TipoHuella` | TipoHuellaType (enum `01`) | REQ |
| 30 | `Huella` | TextMax64 | REQ |
| 31 | `ds:Signature` | xmldsig | OPT |

> **Sorpresa #3 (correcciones al borrador):**
> - NO existe `NombreRazonEmisor` justo tras `IDFactura` sin más — sí existe, pero
>   `RefExterna` puede ir ENTRE `IDFactura` y `NombreRazonEmisor`.
> - `ClaveRegimen`, `CalificacionOperacion`, `TipoImpositivo`, `BaseImponible...`,
>   `CuotaRepercutida` NO son hijos directos de `RegistroAlta`: van dentro de
>   `Desglose → DetalleDesglose`.
> - El `Encadenamiento.RegistroAnterior` NO usa `IDEmisorFactura/NumSerieFactura/...`
>   anidados bajo otro nombre: son `IDEmisorFactura`, `NumSerieFactura`,
>   `FechaExpedicionFactura`, `Huella` (4 campos, ver §5).
> - `SistemaInformatico` usa un **CHOICE NIF | IDOtro**, no siempre `NIF` (ver §6).

### Sub-tipos del Alta

`IDFacturaExpedidaType` (= `IDFactura`):
```
IDEmisorFactura         NIFType        [1]
NumSerieFactura         TextoIDFactura(≤60) [1]
FechaExpedicionFactura  fecha DD-MM-YYYY    [1]
```

`Desglose` → `DesgloseType`:
```
DetalleDesglose  sf:DetalleType   [1..12]   ← máximo 12 líneas de desglose
```

`DetalleType` (orden exacto):
```
Impuesto                       ImpuestoType (01 IVA,02 IPSI,03 IGIC,05 Otros)  [0..1]
ClaveRegimen                   IdOperacionesTrascendenciaTributariaType        [0..1]
CHOICE [1]:
   CalificacionOperacion       S1 | S2 | N1 | N2
   OperacionExenta             E1..E8
TipoImpositivo                 Tipo2.2 (\d{1,3}(\.\d{0,2})?)                    [0..1]
BaseImponibleOimporteNoSujeto  ImporteSgn12.2                                  [1]   ← único REQ
BaseImponibleACoste            ImporteSgn12.2                                  [0..1]
CuotaRepercutida               ImporteSgn12.2                                  [0..1]
TipoRecargoEquivalencia        Tipo2.2                                         [0..1]
CuotaRecargoEquivalencia       ImporteSgn12.2                                  [0..1]
```
> Dentro de un `DetalleDesglose` SÓLO `BaseImponibleOimporteNoSujeto` es obligatorio,
> y hay un CHOICE obligatorio entre `CalificacionOperacion` y `OperacionExenta`.

---

## 4. `RegistroAnulacion` — ORDEN EXACTO (sf:RegistroFacturacionAnulacionType)

| # | Elemento | Tipo | Oblig. |
|---|---|---|---|
| 1 | `IDVersion` | VersionType (`1.0`) | REQ |
| 2 | `IDFactura` | IDFacturaExpedidaBajaType (campos *Anulada*) | REQ |
| 3 | `RefExterna` | TextMax60 | OPT |
| 4 | `SinRegistroPrevio` | S/N | OPT |
| 5 | `RechazoPrevio` | N/S (RechazoPrevioAnulacionType) | OPT |
| 6 | `GeneradoPor` | E/D/T | OPT |
| 7 | `Generador` | PersonaFisicaJuridicaType | OPT |
| 8 | `Encadenamiento` | CHOICE PrimerRegistro \| RegistroAnterior | REQ |
| 9 | `SistemaInformatico` | SistemaInformaticoType | REQ |
| 10 | `FechaHoraHusoGenRegistro` | dateTime | REQ |
| 11 | `TipoHuella` | TipoHuellaType (`01`) | REQ |
| 12 | `Huella` | TextMax64 | REQ |
| 13 | `ds:Signature` | xmldsig | OPT |

`IDFacturaExpedidaBajaType` (= `IDFactura` de la anulación):
```
IDEmisorFacturaAnulada         NIFType        [1]
NumSerieFacturaAnulada         TextoIDFactura [1]
FechaExpedicionFacturaAnulada  fecha          [1]
```
> El `IDFactura` de la anulación NO se llama `IDFacturaAnulada`: el elemento es
> `IDFactura` y sus **hijos** llevan el sufijo `...Anulada`.

---

## 5. `Encadenamiento` (idéntico en Alta y Anulación)

```
CHOICE:
  PrimerRegistro   = "S"                          ← primer registro de la cadena
  RegistroAnterior (EncadenamientoFacturaAnteriorType):
        IDEmisorFactura         NIFType
        NumSerieFactura         TextMax60
        FechaExpedicionFactura  fecha
        Huella                  TextMax64    ← huella del registro inmediatamente anterior
```

---

## 6. `SistemaInformatico` (SistemaInformaticoType) — orden exacto

```
NombreRazon                    TextMax120   [1]
CHOICE [1]:  NIF (NIFType)  |  IDOtro (IDOtroType)
NombreSistemaInformatico       TextMax30    [1]
IdSistemaInformatico           TextMax2     [1]   ← OJO: máx 2 caracteres
Version                        TextMax50    [1]
NumeroInstalacion              TextMax100   [1]
TipoUsoPosibleSoloVerifactu    S/N          [1]
TipoUsoPosibleMultiOT          S/N          [1]
IndicadorMultiplesOT           S/N          [1]
```
> `IdSistemaInformatico` está limitado a **2 caracteres** (`TextMax2Type`).

---

## 7. Enumeraciones clave (valores literales del XSD)

- **IDVersion / VersionType**: `1.0`
- **TipoFactura (ClaveTipoFacturaType)**: `F1` (factura completa), `F2` (simplificada),
  `F3` (sustitución de simplificadas), `R1` (rectificativa art.80.1/80.2 y error fundado),
  `R2` (art.80.3), `R3` (art.80.4), `R4` (resto rectificativas), `R5` (rectificativa de simplificadas).
- **TipoRectificativa**: `S` (sustitutiva), `I` (incremental).
- **TipoHuella**: `01` = SHA-256. (único valor)
- **CalificacionOperacion**: `S1` (sujeta y no exenta, sin inversión SP), `S2` (sujeta y no
  exenta, con inversión SP), `N1` (no sujeta art.7/14/otros), `N2` (no sujeta por localización).
- **OperacionExenta**: `E1, E2, E3, E4, E5, E6, E7, E8` (8 valores — el borrador decía E1-E6).
- **Impuesto**: `01` IVA, `02` IPSI, `03` IGIC, `05` Otros.
- **ClaveRegimen (IdOperacionesTrascendenciaTributariaType)**:
  `01,02,03,04,05,06,07,08,09,10,11,14,15,17,18,19,20,21` (faltan 12,13,16 — no existen).
- **SiNoType**: `S`, `N`. **GeneradoPor**: `E` (expedidor), `D` (destinatario), `T` (tercero).
- **RechazoPrevio (Alta)**: `N`, `S`, `X`. **RechazoPrevio (Anulación)**: `N`, `S`.

### Patrones / longitudes
- `NIFType`: string, longitud exacta 9.
- `fecha`: patrón `\d{2}-\d{2}-\d{4}` → **DD-MM-YYYY** (no ISO).
- `FechaHoraHusoGenRegistro`: `xs:dateTime` ISO-8601 **con huso horario** (p.ej. `+01:00`).
- `TextoIDFacturaType`: máx 60. `TextMax64Type` (Huella): máx 64.
- `ImporteSgn12.2Type`: `(\+|-)?\d{1,12}(\.\d{0,2})?` → punto decimal, hasta 2 decimales, signo opcional.
- `Tipo2.2Type`: `\d{1,3}(\.\d{0,2})?`.

---

## 8. Cálculo de la Huella (SHA-256) — payload canónico

Algoritmo: **SHA-256**, resultado en **hexadecimal de 64 caracteres**. La cadena se
codifica en **UTF-8** antes de hashear. `TipoHuella = 01`.

> Confirmado contra la FAQ oficial de desarrolladores AEAT (VERI*FACTU) y la guía técnica.

### 8.1 Huella de `RegistroAlta`
Concatenación de `clave=valor` separados por `&`, EN ESTE ORDEN EXACTO, sin espacios,
nombres de campo tal cual (case-sensitive):

```
IDEmisorFactura={NIF emisor}&NumSerieFactura={num}&FechaExpedicionFactura={DD-MM-YYYY}&TipoFactura={F1...}&CuotaTotal={importe}&ImporteTotal={importe}&Huella={huella registro anterior}&FechaHoraHusoGenRegistro={ISO-8601 con huso}
```

Ejemplo literal de cadena previa al hash (de la doc AEAT):
```
IDEmisorFactura=89890001K&NumSerieFactura=12345678/G33&FechaExpedicionFactura=01-01-2024&TipoFactura=F1&CuotaTotal=12.35&ImporteTotal=123.45&Huella=&FechaHoraHusoGenRegistro=2024-01-01T19:20:30+01:00
```
Notas:
- En el **primer registro** de la cadena, `Huella=` queda vacío (string vacío, pero la
  clave `Huella=` SÍ aparece).
- Los importes van **tal cual figuran en el XML** (mismo formato/decimales que se envía).
- `FechaHoraHusoGenRegistro` debe ser EXACTAMENTE el mismo valor que va en el XML.
- **La AEAT recomienda la huella en MAYÚSCULAS** (hex). Sé consistente con lo que envíes.

### 8.2 Huella de `RegistroAnulacion`
Mismo método, distinto conjunto de campos y orden:
```
IDEmisorFacturaAnulada={NIF}&NumSerieFacturaAnulada={num}&FechaExpedicionFacturaAnulada={DD-MM-YYYY}&Huella={huella registro anterior}&FechaHoraHusoGenRegistro={ISO-8601 con huso}
```
> La `Huella` que entra aquí es la del **último registro de la cadena** (el inmediatamente
> anterior en el flujo), NO la del registro que se está anulando.

### 8.3 Implementación Python (referencia)
```python
import hashlib

def huella_alta(d: dict) -> str:
    cadena = (
        f"IDEmisorFactura={d['IDEmisorFactura']}"
        f"&NumSerieFactura={d['NumSerieFactura']}"
        f"&FechaExpedicionFactura={d['FechaExpedicionFactura']}"
        f"&TipoFactura={d['TipoFactura']}"
        f"&CuotaTotal={d['CuotaTotal']}"
        f"&ImporteTotal={d['ImporteTotal']}"
        f"&Huella={d.get('HuellaAnterior', '')}"
        f"&FechaHoraHusoGenRegistro={d['FechaHoraHusoGenRegistro']}"
    )
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest().upper()

def huella_anulacion(d: dict) -> str:
    cadena = (
        f"IDEmisorFacturaAnulada={d['IDEmisorFacturaAnulada']}"
        f"&NumSerieFacturaAnulada={d['NumSerieFacturaAnulada']}"
        f"&FechaExpedicionFacturaAnulada={d['FechaExpedicionFacturaAnulada']}"
        f"&Huella={d.get('HuellaAnterior', '')}"
        f"&FechaHoraHusoGenRegistro={d['FechaHoraHusoGenRegistro']}"
    )
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest().upper()
```

---

## 9. Ejemplo XML mínimo VÁLIDO — `RegistroAlta`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sfLR:RegFactuSistemaFacturacion
    xmlns:sfLR="https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd"
    xmlns:sf="https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd">
  <sfLR:Cabecera>
    <sf:ObligadoEmision>
      <sf:NombreRazon>EMPRESA EJEMPLO SL</sf:NombreRazon>
      <sf:NIF>B12345678</sf:NIF>
    </sf:ObligadoEmision>
  </sfLR:Cabecera>
  <sfLR:RegistroFactura>
    <sf:RegistroAlta>
      <sf:IDVersion>1.0</sf:IDVersion>
      <sf:IDFactura>
        <sf:IDEmisorFactura>B12345678</sf:IDEmisorFactura>
        <sf:NumSerieFactura>FA2026/001</sf:NumSerieFactura>
        <sf:FechaExpedicionFactura>14-06-2026</sf:FechaExpedicionFactura>
      </sf:IDFactura>
      <sf:NombreRazonEmisor>EMPRESA EJEMPLO SL</sf:NombreRazonEmisor>
      <sf:TipoFactura>F1</sf:TipoFactura>
      <sf:DescripcionOperacion>Venta de servicios de consultoria</sf:DescripcionOperacion>
      <sf:Desglose>
        <sf:DetalleDesglose>
          <sf:Impuesto>01</sf:Impuesto>
          <sf:ClaveRegimen>01</sf:ClaveRegimen>
          <sf:CalificacionOperacion>S1</sf:CalificacionOperacion>
          <sf:TipoImpositivo>21</sf:TipoImpositivo>
          <sf:BaseImponibleOimporteNoSujeto>100.00</sf:BaseImponibleOimporteNoSujeto>
          <sf:CuotaRepercutida>21.00</sf:CuotaRepercutida>
        </sf:DetalleDesglose>
      </sf:Desglose>
      <sf:CuotaTotal>21.00</sf:CuotaTotal>
      <sf:ImporteTotal>121.00</sf:ImporteTotal>
      <sf:Encadenamiento>
        <sf:PrimerRegistro>S</sf:PrimerRegistro>
      </sf:Encadenamiento>
      <sf:SistemaInformatico>
        <sf:NombreRazon>AUTOMATIZA PYME SL</sf:NombreRazon>
        <sf:NIF>B87654321</sf:NIF>
        <sf:NombreSistemaInformatico>AutomatizaPyme</sf:NombreSistemaInformatico>
        <sf:IdSistemaInformatico>01</sf:IdSistemaInformatico>
        <sf:Version>1.0</sf:Version>
        <sf:NumeroInstalacion>0001</sf:NumeroInstalacion>
        <sf:TipoUsoPosibleSoloVerifactu>S</sf:TipoUsoPosibleSoloVerifactu>
        <sf:TipoUsoPosibleMultiOT>N</sf:TipoUsoPosibleMultiOT>
        <sf:IndicadorMultiplesOT>N</sf:IndicadorMultiplesOT>
      </sf:SistemaInformatico>
      <sf:FechaHoraHusoGenRegistro>2026-06-14T10:30:00+02:00</sf:FechaHoraHusoGenRegistro>
      <sf:TipoHuella>01</sf:TipoHuella>
      <sf:Huella>3C9...HASH_SHA256_64_HEX...A1F</sf:Huella>
    </sf:RegistroAlta>
  </sfLR:RegistroFactura>
</sfLR:RegFactuSistemaFacturacion>
```

---

## 10. Ejemplo XML mínimo VÁLIDO — `RegistroAnulacion`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sfLR:RegFactuSistemaFacturacion
    xmlns:sfLR="https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd"
    xmlns:sf="https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd">
  <sfLR:Cabecera>
    <sf:ObligadoEmision>
      <sf:NombreRazon>EMPRESA EJEMPLO SL</sf:NombreRazon>
      <sf:NIF>B12345678</sf:NIF>
    </sf:ObligadoEmision>
  </sfLR:Cabecera>
  <sfLR:RegistroFactura>
    <sf:RegistroAnulacion>
      <sf:IDVersion>1.0</sf:IDVersion>
      <sf:IDFactura>
        <sf:IDEmisorFacturaAnulada>B12345678</sf:IDEmisorFacturaAnulada>
        <sf:NumSerieFacturaAnulada>FA2026/001</sf:NumSerieFacturaAnulada>
        <sf:FechaExpedicionFacturaAnulada>14-06-2026</sf:FechaExpedicionFacturaAnulada>
      </sf:IDFactura>
      <sf:Encadenamiento>
        <sf:RegistroAnterior>
          <sf:IDEmisorFactura>B12345678</sf:IDEmisorFactura>
          <sf:NumSerieFactura>FA2026/001</sf:NumSerieFactura>
          <sf:FechaExpedicionFactura>14-06-2026</sf:FechaExpedicionFactura>
          <sf:Huella>3C9...HASH_DEL_REGISTRO_ANTERIOR...A1F</sf:Huella>
        </sf:RegistroAnterior>
      </sf:Encadenamiento>
      <sf:SistemaInformatico>
        <sf:NombreRazon>AUTOMATIZA PYME SL</sf:NombreRazon>
        <sf:NIF>B87654321</sf:NIF>
        <sf:NombreSistemaInformatico>AutomatizaPyme</sf:NombreSistemaInformatico>
        <sf:IdSistemaInformatico>01</sf:IdSistemaInformatico>
        <sf:Version>1.0</sf:Version>
        <sf:NumeroInstalacion>0001</sf:NumeroInstalacion>
        <sf:TipoUsoPosibleSoloVerifactu>S</sf:TipoUsoPosibleSoloVerifactu>
        <sf:TipoUsoPosibleMultiOT>N</sf:TipoUsoPosibleMultiOT>
        <sf:IndicadorMultiplesOT>N</sf:IndicadorMultiplesOT>
      </sf:SistemaInformatico>
      <sf:FechaHoraHusoGenRegistro>2026-06-14T11:00:00+02:00</sf:FechaHoraHusoGenRegistro>
      <sf:TipoHuella>01</sf:TipoHuella>
      <sf:Huella>9F2...HASH_SHA256_64_HEX...B7C</sf:Huella>
    </sf:RegistroAnulacion>
  </sfLR:RegistroFactura>
</sfLR:RegFactuSistemaFacturacion>
```

---

## 11. Checklist de validación para Python (lxml)

1. Cargar `SuministroLR.xsd` (importa automáticamente `SuministroInformacion.xsd`
   por `schemaLocation` relativo → mantener ambos en el mismo dir → `backend/app/services/aeat/xsd/`).
2. `SuministroInformacion.xsd` importa `xmldsig-core-schema.xsd` **por URL absoluta**
   (`http://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd`). Si no hay red al validar,
   descargar ese XSD y resolver vía `XMLCatalog` o editar el `schemaLocation` local.
3. Respetar el orden de §3/§4 y los namespaces de §1 (target NS = `tike/...`, sin `V1.0`).
4. Fechas en `DD-MM-YYYY`; `FechaHoraHusoGenRegistro` en `xs:dateTime` con huso.
5. Calcular `Huella` ANTES de serializar el elemento `Huella` (§8) y rellenar
   `Encadenamiento` del registro siguiente con esa huella.

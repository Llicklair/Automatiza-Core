# Cláusula AI Act para EULA — AI.EULA

> Texto plantilla a incluir en el contrato de licencia entre AutomatizaPyme S.L. (proveedor) y el cliente (deployer). **Sujeto a validación por abogado SaaS especializado antes de su uso comercial** (decisión humana 6 del consenso). Esta plantilla no constituye asesoramiento jurídico.

---

## Cláusula X — Sistema de Inteligencia Artificial

### X.1 Naturaleza del sistema

El software **AutomatizaPyme** (en adelante, "el Sistema") incluye agentes basados en inteligencia artificial conforme al **Reglamento (UE) 2024/1689 del Parlamento Europeo y del Consejo, de 13 de junio de 2024** (en adelante, "AI Act"). El proveedor del Sistema es **AutomatizaPyme S.L.** (en adelante, "el Proveedor") y el cliente que lo despliega y lo utiliza en su organización es el **deployer** según definición del artículo 3.4 del AI Act.

### X.2 Distribución de responsabilidades

#### Como Proveedor (Art. 16 AI Act), AutomatizaPyme S.L. asume:

a) **Diseño y desarrollo conforme** del Sistema según los principios del AI Act, según se detalla en `docs/ai_act_scoping.md` y `docs/ai_act_governance.md` del Sistema.

b) **Sistema de gestión de calidad** documentado (Art. 17 AI Act), proporcional al tamaño del Proveedor y a los riesgos del Sistema.

c) **Documentación técnica** según Anexo IV del AI Act, disponible a petición del Cliente, autoridades competentes o usuarios afectados.

d) **Registros automáticos** (Art. 12 AI Act) de cada invocación de los agentes durante al menos 6 meses, conservando: identificación pseudonimizada del cliente, modelo de IA usado, identificador de prompt versionado, métricas de uso (tokens, duración, coste), y hash criptográfico del prompt y del output para verificar integridad sin almacenar contenido en plano.

e) **Transparencia hacia el deployer** (Art. 13 AI Act): instrucciones de uso, limitaciones conocidas, capacidad de supervisión humana implementada (`autonomy_policy`).

f) **Cooperación con autoridades** competentes en materia de IA si fuera requerido.

g) **Notificación al Cliente** de incidentes graves del Sistema en un plazo razonable, conforme Art. 73 AI Act.

#### Como Deployer (Art. 26 AI Act), el Cliente asume:

a) **Uso del Sistema conforme** a las instrucciones de uso entregadas por el Proveedor.

b) **Asignación de supervisión humana** a personal cualificado con autoridad suficiente para revisar y, en su caso, modificar o anular las decisiones del Sistema. Por defecto, el Sistema requiere confirmación humana en operaciones de mayor riesgo (`autonomy_policy=CONFIRM` o `MANUAL`).

c) **Asegurar la representatividad y calidad** de los datos de entrada que aporta al Sistema (facturas, contratos, datos de personal, etc.). El Proveedor no responde por errores derivados de datos incorrectos suministrados por el Cliente.

d) **Monitorización** del funcionamiento del Sistema y conservación de los registros automáticos por un plazo mínimo de 6 meses.

e) **Información a representantes de trabajadores y a los trabajadores afectados** antes del despliegue, conforme Art. 26.7 AI Act, utilizando la plantilla provista por el Proveedor en `docs/ai_act_info_trabajadores.md` o equivalente.

f) **Cooperación con autoridades** competentes si fuera requerido por incidente o investigación.

### X.3 Sistemas de alto riesgo y excepciones

El Proveedor declara, según scoping documentado, que los agentes del Sistema:

* **Quedan fuera del Anexo III** del AI Act en su configuración por defecto (Escenario A), mediante: (i) retirada del cálculo automático de puntuación de candidatos (`score_candidate`), y (ii) reducción de la plantilla de documento de despido a estructura formal vacía sin motivación generada por IA, requiriendo redacción humana por abogado laboralista.

* El Cliente acepta no reactivar funcionalidades retiradas (en particular, scoring automático de candidatos) sin previo acuerdo con el Proveedor que documente el cumplimiento adicional necesario (sistema de gestión de calidad reforzado, evaluación de conformidad, registro en base de datos UE, marcado CE).

### X.4 Limitación de responsabilidad

a) El Sistema produce resultados que **deben ser revisados por el Cliente** antes de su uso oficial, particularmente en lo relativo a actos fiscales (modelos AEAT) y actos laborales (contratos, despidos, nóminas).

b) El Proveedor pone a disposición del Cliente mecanismos de **aprobación humana obligatoria** (`MANDATORY_HUMAN_FISCAL`) para los actos fiscales. La omisión de estos mecanismos por parte del Cliente exime al Proveedor de responsabilidad sobre el resultado del acto.

c) **El Proveedor no responde**: (i) por decisiones que el Cliente adopte basándose en los outputs del Sistema sin la supervisión humana exigida, (ii) por errores derivados de proveedores GPAI subyacentes (Anthropic, OpenAI, Groq, etc.) que el Proveedor utilice, (iii) por interrupciones de servicio causadas por la indisponibilidad de dichos proveedores GPAI.

### X.5 Datos personales (RGPD)

El tratamiento de datos personales por el Sistema se rige adicionalmente por:

* **RGPD** y normativa nacional aplicable (LOPDGDD).
* **Política de Privacidad** del Sistema (URL).
* **Política de telemetría** del Sistema, en `docs/telemetry-data-policy.md`.

Por defecto, AutomatizaPyme S.L. **no centraliza** datos de negocio del Cliente en sus servidores. Los datos viven en el equipo del Cliente. Cualquier envío de datos al Proveedor (telemetría técnica, backup remoto cifrado) es **opcional, opt-in y revocable**.

### X.6 Modificación de la cláusula

Cualquier cambio sustantivo en el alcance de los agentes de IA del Sistema o en la `autonomy_policy` por defecto será comunicado al Cliente con al menos **30 días de antelación**, con derecho del Cliente a rescindir si considera que el cambio afecta sustancialmente a su uso.

---

## Notas internas (no parte del EULA del cliente)

* Esta cláusula sustituye/complementa cualquier cláusula previa sobre IA en el EULA estándar.
* **Validación obligatoria por abogado SaaS** (decisión humana 6) antes de uso comercial.
* La versión final debe incluir referencias cruzadas a: (i) Política de Privacidad, (ii) Política de Cookies, (iii) Términos de uso, (iv) DPA RGPD Art. 28.
* Idioma oficial del EULA: castellano. Traducciones a CA/EU/GA para territorios con cooficialidad (I18N.UI, I18N.PDF) — la versión castellana prevalece en caso de discrepancia salvo que la normativa autonómica obligue a lo contrario.
* Versión plantilla: **1.0** — generada 2026-05-14.

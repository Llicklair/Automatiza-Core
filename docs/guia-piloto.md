# AutomatizaCore — Guía rápida de instalación (piloto)

Bienvenido. En ~15 minutos tendrás el ERP funcionando con tus agentes de IA.

---

## 1. Instalar
1. Ejecuta **`AutomatizaCore Setup.exe`**.
2. Si Windows muestra *"Windows protegió tu PC"* (SmartScreen) → **Más información → Ejecutar de todos modos**. *(Es normal mientras la app no esté firmada; la instala tu proveedor de confianza.)*
3. El **primer arranque tarda unos minutos** y necesita **internet**: la app prepara sola su base de datos y motor interno. Déjala terminar (verás una pantalla de carga). Los siguientes arranques son rápidos.

## 2. Crear tu cuenta
En la pantalla inicial → **Crear cuenta**. Necesitas:
- Tu nombre, email y contraseña.
- **Nombre de la empresa** y **NIF/CIF** (9 caracteres).

## 3. Configurar lo esencial (Primeros pasos)
La app te lleva a **Primeros pasos**. Haz estos dos, que son los importantes:

**a) Empresa** → *Configuración → Empresa*
- Razón social y NIF tal como deben salir en facturas. (Opcional: dirección, teléfono, logo.)

**b) 🔑 Clave de IA** → *Configuración → Claves API*  ← **imprescindible**
- Los agentes de IA usan **tu propia clave** (modelo "trae tu clave"). Sin ella, la IA no funciona y verás un aviso ámbar en el panel.
- Pega una clave de **Anthropic** (recomendado), **OpenAI** o **Groq**, actívala y guarda.
- *¿No tienes clave? La creas en la web del proveedor (p.ej. console.anthropic.com) en 2 minutos; pagas solo tu consumo.*

## 4. (Opcional) Integraciones
- **Gmail / Drive / Calendario** → *Configuración → Mensajería / Integraciones*. ⚠️ Durante el piloto puede pedirte **reconectar cada ~7 días** (limitación temporal de Google).
- **Certificado digital (.p12)** para firmar/e-factura → *Verifactu → Configuración fiscal (AEAT) → Firma digital*.

## 5. Probar (5 minutos)
1. Crea un **cliente** (*Contactos → Clientes*).
2. Crea una **factura** (*Ventas → Facturas*) — o pídeselo a la IA.
3. Habla con la **IA** desde el panel o *Mi equipo*:
   - *"¿Cuánto he facturado este mes?"*
   - *"Crea una factura de 500€ + IVA a [cliente] por consultoría"*
   - *"Muéstrame las facturas vencidas sin cobrar"*

---

## Bueno saber
- **Tus datos** se guardan **en tu propio ordenador** (no en la nube). Hay copias de seguridad automáticas.
- **Actualizaciones**: la app se actualiza sola (*Configuración → Actualizaciones*).
- **¿Algo no funciona?** Anota qué hacías y escríbenos. En el piloto, tu feedback es lo que más vale.

*Gracias por probar AutomatizaCore. Cuéntanos qué te ayuda y qué te estorba.*

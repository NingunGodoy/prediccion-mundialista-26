# ⚽ Predicción Mundialista 26

App para predecir marcadores del mundial con tus amigos.

**Reglas de puntos**
- `0` puntos → fallaste
- `1` punto → acertaste el ganador (o el empate)
- `3` puntos → acertaste el **marcador exacto**

Cada quien predice **antes** de que empiece el partido. Cuando el partido
comienza (hora de México), tu predicción se **bloquea** y se **revelan** las
de todos. Ya no se puede cambiar.

---

## 📁 Qué hay en esta carpeta

| Archivo | Para qué sirve |
|---|---|
| `app.py` | La aplicación (lo que ven tus amigos). |
| `db.py` | Conexión con la base de datos. No lo toques. |
| `schema.sql` | Texto que pegarás en Supabase para crear las tablas. |
| `requirements.txt` | Lista de programas que la app necesita. |
| `partidos_ejemplo.txt` | Los partidos de hoy, listos para pegar. |
| `.streamlit/secrets.toml.example` | Plantilla de claves secretas. |

---

## 🟢 PARTE A — Crear la base de datos (Supabase) · ~5 min

1. Entra a **https://supabase.com** y crea una cuenta gratis (puedes usar tu Google).
2. Clic en **New project**. Ponle un nombre (ej. `mundial26`), elige una contraseña
   para la base de datos (guárdala) y región la más cercana. Clic en **Create new project**
   y espera ~2 minutos a que se prepare.
3. En el menú de la izquierda entra a **SQL Editor** → botón **New query**.
4. Abre el archivo `schema.sql` de esta carpeta, **copia TODO** y pégalo en el editor.
   Clic en **Run** (abajo a la derecha). Debe decir *Success*.
5. Ahora copia tus 2 claves:
   - Menú **Project Settings** (el engranaje) → **API**.
   - Copia el **Project URL** (algo como `https://xxxx.supabase.co`).
   - Copia la clave **`service_role`** (NO la `anon`). Es secreta, no la compartas.

Guarda esos dos valores, los usarás en la Parte B y D.

---

## 🟡 PARTE B — Probar en tu PC (opcional pero recomendado)

> Si prefieres saltarte esto y publicar directo, ve a la PARTE C.

1. Instala **Python** desde https://www.python.org/downloads/ (marca la casilla
   *“Add Python to PATH”* durante la instalación).
2. Abre **PowerShell** y entra a la carpeta del proyecto. Escribe `cd ` (con espacio),
   arrastra la carpeta a la ventana y presiona Enter:
   ```powershell
   cd "C:\Users\nggm5\OneDrive\DISA\05 Varios escritoro\Prediccino mundialista 26"
   ```
3. Instala lo que necesita la app:
   ```powershell
   pip install -r requirements.txt
   ```
4. Crea tu archivo de claves: copia `secrets.toml.example` y renómbralo a
   `secrets.toml` (dentro de la carpeta `.streamlit`). Ábrelo con el Bloc de notas
   y pon tu URL, tu clave `service_role` y una contraseña de admin que tú inventes.
5. Arranca la app:
   ```powershell
   streamlit run app.py
   ```
   Se abrirá sola en tu navegador. Si no, entra a la dirección que muestre
   (normalmente `http://localhost:8501`).

Para cerrarla: en PowerShell presiona `Ctrl + C`.

---

## 🔵 PARTE C — Subir el proyecto a GitHub · ~10 min

Esto es necesario para publicarla online gratis.

1. Crea una cuenta en **https://github.com** (gratis).
2. La forma más fácil sin terminal: instala **GitHub Desktop**
   (https://desktop.github.com).
3. En GitHub Desktop: **File → Add local repository** y elige esta carpeta.
   Te dirá que no es un repo; acepta **create a repository**.
4. Clic en **Publish repository**. **MUY IMPORTANTE**: déjalo marcado como
   **Private** (privado) para que solo tú lo veas.
   - El archivo `secrets.toml` NO se sube (está protegido por `.gitignore`). ✅

Cada vez que yo te haga cambios, en GitHub Desktop verás los cambios →
escribe un texto → **Commit** → **Push**, y la app online se actualiza sola.

---

## 🟣 PARTE D — Publicar online (Streamlit Cloud) · ~5 min

1. Entra a **https://share.streamlit.io** e inicia sesión con tu cuenta de GitHub.
2. Clic en **Create app** → **Deploy a public app from GitHub**.
3. Elige tu repositorio, rama `main`, y en *Main file path* pon: `app.py`.
4. Antes de desplegar, clic en **Advanced settings → Secrets** y pega esto
   (con TUS valores):
   ```toml
   SUPABASE_URL = "https://TU-PROYECTO.supabase.co"
   SUPABASE_KEY = "tu-clave-service_role"
   ADMIN_PASSWORD = "la-contraseña-de-admin-que-inventaste"
   ```
5. Clic en **Deploy**. Espera 2-3 minutos. ¡Listo! Tendrás un enlace tipo
   `https://algo.streamlit.app` que puedes pasarle a tus amigos.

---

## 🎮 Cómo se usa

**Tus amigos:**
1. Abren el enlace → pestaña **Crear usuario** → ponen su nombre y un PIN (4-8 números).
2. En **⚽ Partidos** escriben el marcador que creen y dan *Guardar predicción*.
   Pueden cambiarla cuantas veces quieran **hasta que empiece el partido**.
3. Cuando el partido empieza, ven las predicciones de todos. En **🏆 Posiciones**
   ven la tabla general.

**Tú (admin):**
1. Pestaña **🛠️ Admin** → escribe la contraseña de admin.
2. **Cargar partidos**: pega el texto (como `partidos_ejemplo.txt`) o sube un Excel.
   Puedes cargar un día o el calendario completo cuando quieras; no se duplican.
3. Cuando termine un partido, en **Capturar resultados** pones el marcador final
   y se reparten los puntos automáticamente.

### Formato para cargar partidos
- **Pegando texto:** una línea por partido, separada por tabulaciones:
  `fecha	fecha	equipo1	equipo2	grupo	---	X points`
  (la app ignora todo a partir del grupo).
- **Excel/CSV:** columnas `fecha` (formato `dd/mm/aa HH:MM`), `equipo1`, `equipo2`, `grupo`.

> Los horarios se interpretan en **hora de México**.

---

## ❓ Dudas frecuentes
- **Olvidé mi PIN:** dile al admin; por ahora se resuelve borrando tu usuario en
  Supabase (tabla `users`) y volviéndote a registrar.
- **¿Se pueden ver las predicciones antes?** No. Solo se revelan al iniciar el partido.
- **¿Quiero agregar banderas de otros países?** Se agregan en la lista `FLAGS` de `app.py`.

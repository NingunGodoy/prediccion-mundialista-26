"""
Predicción Mundialista 26  ⚽
App para predecir resultados entre amigos.

Reglas:
  - Cada quien predice el marcador de cada partido ANTES de que empiece.
  - Al iniciar el partido la predicción se bloquea y se revelan las de todos.
  - Puntos:  0 = fallaste | 1 = acertaste el ganador | 3 = marcador exacto.
"""

import re
import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="Predicción Mundialista 26", page_icon="⚽", layout="centered")

# Banderitas opcionales para que se vea bonito (si falta una, no pasa nada).
FLAGS = {
    "Portugal": "🇵🇹", "DR Congo": "🇨🇩", "England": "🏴", "Croatia": "🇭🇷",
    "Ghana": "🇬🇭", "Panama": "🇵🇦", "Uzbekistan": "🇺🇿", "Colombia": "🇨🇴",
    "Mexico": "🇲🇽", "Argentina": "🇦🇷", "Brazil": "🇧🇷", "France": "🇫🇷",
    "Spain": "🇪🇸", "Germany": "🇩🇪", "USA": "🇺🇸", "Canada": "🇨🇦",
}


def flag(team: str) -> str:
    return f"{FLAGS.get(team, '⚽')} {team}"


# ----------------------------------------------------------------------
#  Sesión
# ----------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None


def login_screen():
    st.title("⚽ Predicción Mundialista 26")
    st.caption("Predice los marcadores y compite con tus amigos.")

    tab_login, tab_signup = st.tabs(["Iniciar sesión", "Crear usuario"])

    with tab_login:
        with st.form("login"):
            name = st.text_input("Tu nombre")
            pin = st.text_input("PIN", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                user = db.verify_user(name, pin)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Nombre o PIN incorrecto.")

    with tab_signup:
        st.caption("Elige un nombre y un PIN de 4 a 8 números. ¡No olvides tu PIN!")
        with st.form("signup"):
            name = st.text_input("Nombre nuevo")
            pin = st.text_input("Crea tu PIN (4-8 números)", type="password")
            if st.form_submit_button("Crear usuario", use_container_width=True):
                ok, msg = db.create_user(name, pin)
                if ok:
                    st.session_state.user = db.get_user(name.strip())
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


# ----------------------------------------------------------------------
#  Pantalla de partidos / predicciones
# ----------------------------------------------------------------------
def matches_screen():
    user = st.session_state.user
    matches = db.get_matches(only_active=True)

    if not matches:
        st.info("Todavía no hay partidos en la quiniela. El admin debe seleccionarlos en la pestaña **Admin**.")
        return

    # Agrupar por día (hora de México)
    by_day: dict[str, list] = {}
    for m in matches:
        day = db.to_mx(db.parse_iso(m["kickoff"])).strftime("%A %d/%m/%Y")
        by_day.setdefault(day, []).append(m)

    for day, day_matches in by_day.items():
        st.subheader(f"📅 {day}")
        for m in day_matches:
            render_match(m, user)
        st.divider()


def render_match(m: dict, user: dict):
    status = db.match_status(m)
    ko = db.to_mx(db.parse_iso(m["kickoff"]))
    badge = {"open": "🟢 Abierto", "locked": "🔒 En juego / cerrado", "finished": "🏁 Finalizado"}[status]

    with st.container(border=True):
        top = st.columns([3, 1])
        top[0].markdown(f"**{flag(m['team1'])}  vs  {flag(m['team2'])}**")
        top[1].markdown(f"<div style='text-align:right'>{badge}</div>", unsafe_allow_html=True)
        st.caption(f"{m.get('grupo') or ''} · 🕐 {ko.strftime('%H:%M')} (hora México)")

        if status == "finished":
            st.markdown(f"### Resultado: {m['home_score']} - {m['away_score']}")

        if status == "open":
            _prediction_form(m, user)
        else:
            _reveal_predictions(m)


def _prediction_form(m: dict, user: dict):
    prev = db.get_user_prediction(user["id"], m["id"])
    with st.form(f"pred_{m['id']}"):
        c1, c2, c3 = st.columns([2, 2, 2])
        h = c1.number_input(m["team1"], min_value=0, max_value=30, step=1,
                            value=int(prev["pred_home"]) if prev else 0, key=f"h_{m['id']}")
        a = c2.number_input(m["team2"], min_value=0, max_value=30, step=1,
                            value=int(prev["pred_away"]) if prev else 0, key=f"a_{m['id']}")
        label = "Actualizar predicción" if prev else "Guardar predicción"
        if c3.form_submit_button(label, use_container_width=True):
            # Doble verificación: que no haya empezado justo al enviar.
            if db.match_status(m) != "open":
                st.error("El partido ya empezó, no se puede predecir.")
            else:
                db.save_prediction(user["id"], m["id"], int(h), int(a))
                st.success(f"Tu predicción: {int(h)} - {int(a)}  (puedes cambiarla hasta el inicio)")
    if prev:
        st.caption(f"✅ Predicción guardada: **{prev['pred_home']} - {prev['pred_away']}**")


def _reveal_predictions(m: dict):
    preds = db.get_predictions_for_match(m["id"])
    if not preds:
        st.caption("Nadie predijo este partido.")
        return

    finished = db.match_status(m) == "finished"
    rows = []
    for p in preds:
        name = (p.get("users") or {}).get("name", "?")
        row = {"Jugador": name, "Predicción": f"{p['pred_home']} - {p['pred_away']}"}
        if finished:
            pts = db.points_for(p["pred_home"], p["pred_away"], m["home_score"], m["away_score"])
            row["Puntos"] = pts
        rows.append(row)
    if finished:
        rows.sort(key=lambda r: r["Puntos"], reverse=True)
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


# ----------------------------------------------------------------------
#  Tabla de posiciones
# ----------------------------------------------------------------------
def scoreboard_screen():
    st.subheader("🏆 Tabla de posiciones")
    board = db.scoreboard()
    if not board:
        st.info("Aún no hay puntos. Aparecerán cuando los partidos tengan resultado.")
        return
    df = pd.DataFrame(board)
    df.insert(0, "#", range(1, len(df) + 1))
    st.dataframe(df, hide_index=True, use_container_width=True)
    st.caption("Desempate: más marcadores exactos.")


# ----------------------------------------------------------------------
#  Admin
# ----------------------------------------------------------------------
def parse_pasted(text: str) -> tuple[list[dict], list[str]]:
    """Convierte el texto pegado en partidos. Devuelve (partidos, errores)."""
    rows, errors = [], []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 5:  # por si se pegó con espacios en vez de tabs
            parts = [p.strip() for p in re.split(r"\s{2,}", line)]
        if len(parts) < 5:
            errors.append(f"Línea {i}: no entendí el formato.")
            continue
        try:
            rows.append({
                "kickoff": db.parse_kickoff(parts[0]),
                "team1": parts[2],
                "team2": parts[3],
                "grupo": parts[4],
            })
        except ValueError:
            errors.append(f"Línea {i}: fecha inválida ('{parts[0]}'). Usa dd/mm/aa HH:MM.")
    return rows, errors


def parse_excel(file) -> tuple[list[dict], list[str]]:
    """Lee un Excel/CSV con columnas: fecha, equipo1, equipo2, grupo."""
    if file.name.lower().endswith(".csv"):
        df = pd.read_csv(file, dtype=str)
    else:
        df = pd.read_excel(file, dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]

    def col(*names):
        for n in names:
            if n in df.columns:
                return n
        return None

    c_fecha = col("fecha", "fecha_hora", "fecha y hora", "kickoff", "hora")
    c_t1 = col("equipo1", "local", "team1", "equipo 1")
    c_t2 = col("equipo2", "visitante", "team2", "equipo 2")
    c_grp = col("grupo", "group")
    if not (c_fecha and c_t1 and c_t2):
        return [], ["El Excel necesita al menos las columnas: fecha, equipo1, equipo2."]

    rows, errors = [], []
    for i, r in df.iterrows():
        try:
            rows.append({
                "kickoff": db.parse_kickoff(str(r[c_fecha])),
                "team1": str(r[c_t1]).strip(),
                "team2": str(r[c_t2]).strip(),
                "grupo": str(r[c_grp]).strip() if c_grp else None,
            })
        except (ValueError, TypeError):
            errors.append(f"Fila {i + 2}: fecha inválida ('{r[c_fecha]}'). Usa dd/mm/aa HH:MM.")
    return rows, errors


def admin_screen():
    st.subheader("🛠️ Administración")
    if not st.session_state.get("is_admin"):
        pwd = st.text_input("Contraseña de administrador", type="password")
        if st.button("Entrar como admin"):
            if pwd and pwd == st.secrets.get("ADMIN_PASSWORD"):
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        return

    st.success("Modo administrador activo.")

    # ---- Cargar partidos: pegar texto ----
    st.markdown("#### 1) Cargar partidos pegando texto")
    st.caption("Pega las líneas tal cual (con tabulaciones). La última columna de 'points' se ignora.")
    pasted = st.text_area("Pega aquí los partidos", height=160,
                          placeholder="17/06/26 11:00\t17/06/26 11:00\tPortugal\tDR Congo\tGroup K\t---\t2 - 4 points")
    if st.button("Cargar partidos pegados"):
        rows, errors = parse_pasted(pasted)
        for e in errors:
            st.warning(e)
        if rows:
            added = db.add_matches(rows)
            st.success(f"Se agregaron {added} partidos nuevos (de {len(rows)} leídos).")

    # ---- Cargar partidos: Excel/CSV ----
    st.markdown("#### 2) Cargar partidos desde Excel/CSV")
    st.caption("Columnas necesarias: **fecha** (dd/mm/aa HH:MM), **equipo1**, **equipo2**, **grupo** (opcional).")
    up = st.file_uploader("Sube un .xlsx o .csv", type=["xlsx", "csv"])
    if up and st.button("Cargar archivo"):
        rows, errors = parse_excel(up)
        for e in errors:
            st.warning(e)
        if rows:
            added = db.add_matches(rows)
            st.success(f"Se agregaron {added} partidos nuevos (de {len(rows)} leídos).")

    st.divider()

    # ---- Seleccionar qué partidos entran a la quiniela ----
    st.markdown("#### 3) Elegir partidos de la quiniela")
    st.caption("Marca la casilla de los partidos que tus amigos podrán predecir. "
               "Los que dejes sin marcar no aparecen ni cuentan puntos.")
    all_matches = db.get_matches()
    if not all_matches:
        st.caption("Primero carga partidos arriba.")
    else:
        rows = []
        for m in all_matches:
            ko = db.to_mx(db.parse_iso(m["kickoff"]))
            rows.append({
                "id": m["id"],
                "Fecha": ko.strftime("%d/%m %H:%M"),
                "Partido": f"{m['team1']} vs {m['team2']}",
                "Grupo": m.get("grupo") or "",
                "En quiniela": bool(m.get("activo")),
            })
        df = pd.DataFrame(rows)

        c1, c2 = st.columns(2)
        if c1.button("✅ Marcar todos", use_container_width=True):
            for m in all_matches:
                db.set_active(m["id"], True)
            st.rerun()
        if c2.button("⬜ Quitar todos", use_container_width=True):
            for m in all_matches:
                db.set_active(m["id"], False)
            st.rerun()

        edited = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            disabled=["id", "Fecha", "Partido", "Grupo"],
            column_config={"En quiniela": st.column_config.CheckboxColumn("En quiniela")},
            key="pool_editor",
        )
        if st.button("💾 Guardar selección", type="primary"):
            current = {m["id"]: bool(m.get("activo")) for m in all_matches}
            cambios = 0
            for _, r in edited.iterrows():
                new_val = bool(r["En quiniela"])
                if current.get(int(r["id"])) != new_val:
                    db.set_active(int(r["id"]), new_val)
                    cambios += 1
            st.success(f"Selección guardada ({cambios} cambios).")
            st.rerun()

    st.divider()

    # ---- Capturar resultados ----
    st.markdown("#### 4) Capturar resultados finales")
    st.caption("Solo de los partidos que están en la quiniela.")
    matches = db.get_matches(only_active=True)
    started = [m for m in matches if db.match_status(m) in ("locked", "finished")]
    if not started:
        st.caption("Aún no hay partidos que hayan empezado.")
        return
    for m in started:
        ko = db.to_mx(db.parse_iso(m["kickoff"]))
        with st.container(border=True):
            st.markdown(f"**{m['team1']} vs {m['team2']}** · {ko.strftime('%d/%m %H:%M')}")
            with st.form(f"res_{m['id']}"):
                c1, c2, c3 = st.columns([2, 2, 2])
                h = c1.number_input(m["team1"], min_value=0, max_value=30, step=1,
                                    value=int(m["home_score"]) if m.get("home_score") is not None else 0,
                                    key=f"rh_{m['id']}")
                a = c2.number_input(m["team2"], min_value=0, max_value=30, step=1,
                                    value=int(m["away_score"]) if m.get("away_score") is not None else 0,
                                    key=f"ra_{m['id']}")
                if c3.form_submit_button("Guardar resultado", use_container_width=True):
                    db.set_result(m["id"], int(h), int(a))
                    st.success("Resultado guardado.")
                    st.rerun()


# ----------------------------------------------------------------------
#  Main
# ----------------------------------------------------------------------
def main():
    if st.session_state.user is None:
        login_screen()
        return

    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.user['name']}**")
        if st.button("Cerrar sesión", use_container_width=True):
            st.session_state.user = None
            st.session_state.pop("is_admin", None)
            st.rerun()
        st.button("🔄 Actualizar", use_container_width=True, on_click=st.rerun)

    tab1, tab2, tab3 = st.tabs(["⚽ Partidos", "🏆 Posiciones", "🛠️ Admin"])
    with tab1:
        matches_screen()
    with tab2:
        scoreboard_screen()
    with tab3:
        admin_screen()


main()

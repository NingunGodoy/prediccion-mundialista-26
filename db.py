"""
Capa de datos: todo lo que habla con la base de datos (Supabase) vive aquí.
app.py solo llama a estas funciones y no se preocupa por SQL.
"""

import hashlib
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import streamlit as st
from supabase import create_client, Client

# Hora de México (sin horario de verano desde 2023 => UTC-6 todo el año).
MX_TZ = ZoneInfo("America/Mexico_City")


# ----------------------------------------------------------------------
#  Conexión
# ----------------------------------------------------------------------
@st.cache_resource
def _client() -> Client:
    """Crea (una sola vez) el cliente de Supabase usando las claves secretas."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# ----------------------------------------------------------------------
#  Helpers de fecha / PIN
# ----------------------------------------------------------------------
def hash_pin(name: str, pin: str) -> str:
    """Convierte el PIN en una huella irreversible (no se guarda el PIN real)."""
    return hashlib.sha256(f"{name.lower()}::{pin}".encode("utf-8")).hexdigest()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_mx(dt: datetime) -> datetime:
    """Convierte un datetime (con zona) a hora de México para mostrarlo."""
    return dt.astimezone(MX_TZ)


def parse_kickoff(dt_str: str) -> datetime:
    """Lee 'dd/mm/yy HH:MM' como hora de México y lo devuelve en UTC."""
    local = datetime.strptime(dt_str.strip(), "%d/%m/%y %H:%M").replace(tzinfo=MX_TZ)
    return local.astimezone(timezone.utc)


def parse_iso(s: str) -> datetime:
    """Lee la fecha que devuelve Supabase y garantiza que tenga zona UTC."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ----------------------------------------------------------------------
#  Usuarios
# ----------------------------------------------------------------------
def get_user(name: str):
    res = _client().table("users").select("*").eq("name", name).execute()
    return res.data[0] if res.data else None


def create_user(name: str, pin: str):
    """Crea un usuario nuevo. Devuelve (ok, mensaje)."""
    name = name.strip()
    if not name:
        return False, "Escribe un nombre."
    if not re.fullmatch(r"\d{4,8}", pin):
        return False, "El PIN debe ser de 4 a 8 números."
    if get_user(name):
        return False, "Ese nombre ya existe. Si eres tú, inicia sesión."
    _client().table("users").insert(
        {"name": name, "pin_hash": hash_pin(name, pin)}
    ).execute()
    return True, "Usuario creado."


def verify_user(name: str, pin: str):
    """Comprueba nombre + PIN. Devuelve el usuario o None."""
    user = get_user(name.strip())
    if user and user["pin_hash"] == hash_pin(user["name"], pin):
        return user
    return None


# ----------------------------------------------------------------------
#  Partidos
# ----------------------------------------------------------------------
def add_matches(rows: list[dict]) -> int:
    """
    Inserta partidos evitando duplicados (mismo equipo1, equipo2 y hora).
    rows: lista de dicts con kickoff(datetime UTC), team1, team2, grupo.
    Devuelve cuántos se agregaron como nuevos.
    """
    added = 0
    cli = _client()
    for r in rows:
        payload = {
            "kickoff": r["kickoff"].isoformat(),
            "team1": r["team1"],
            "team2": r["team2"],
            "grupo": r.get("grupo"),
        }
        # ¿ya existe? (mismo par de equipos y misma hora)
        exists = (
            cli.table("matches")
            .select("id")
            .eq("team1", r["team1"])
            .eq("team2", r["team2"])
            .eq("kickoff", payload["kickoff"])
            .execute()
        )
        if not exists.data:
            cli.table("matches").insert(payload).execute()
            added += 1
    return added


def get_matches(only_active: bool = False) -> list[dict]:
    """Lista los partidos. only_active=True => solo los que están en la quiniela."""
    q = _client().table("matches").select("*")
    if only_active:
        q = q.eq("activo", True)
    res = q.order("kickoff").execute()
    return res.data or []


def set_active(match_id: int, value: bool):
    """Marca/desmarca si un partido entra a la quiniela."""
    _client().table("matches").update({"activo": value}).eq("id", match_id).execute()


def set_result(match_id: int, home: int, away: int):
    _client().table("matches").update(
        {"home_score": home, "away_score": away}
    ).eq("id", match_id).execute()


def clear_result(match_id: int):
    _client().table("matches").update(
        {"home_score": None, "away_score": None}
    ).eq("id", match_id).execute()


# ----------------------------------------------------------------------
#  Predicciones
# ----------------------------------------------------------------------
def save_prediction(user_id: int, match_id: int, home: int, away: int):
    """Crea o actualiza la predicción de un usuario para un partido."""
    cli = _client()
    existing = (
        cli.table("predictions")
        .select("id")
        .eq("user_id", user_id)
        .eq("match_id", match_id)
        .execute()
    )
    data = {"pred_home": home, "pred_away": away}
    if existing.data:
        cli.table("predictions").update(data).eq("id", existing.data[0]["id"]).execute()
    else:
        cli.table("predictions").insert(
            {"user_id": user_id, "match_id": match_id, **data}
        ).execute()


def get_user_prediction(user_id: int, match_id: int):
    res = (
        _client()
        .table("predictions")
        .select("*")
        .eq("user_id", user_id)
        .eq("match_id", match_id)
        .execute()
    )
    return res.data[0] if res.data else None


def get_predictions_for_match(match_id: int) -> list[dict]:
    res = (
        _client()
        .table("predictions")
        .select("*, users(name)")
        .eq("match_id", match_id)
        .execute()
    )
    return res.data or []


def get_all_predictions() -> list[dict]:
    res = _client().table("predictions").select("*, users(name)").execute()
    return res.data or []


# ----------------------------------------------------------------------
#  Lógica del juego
# ----------------------------------------------------------------------
def match_status(m: dict) -> str:
    """'open' = se puede predecir | 'locked' = ya empezó | 'finished' = con resultado."""
    if m.get("home_score") is not None and m.get("away_score") is not None:
        return "finished"
    if now_utc() >= parse_iso(m["kickoff"]):
        return "locked"
    return "open"


def points_for(pred_h: int, pred_a: int, act_h, act_a) -> int | None:
    """0 si falla, 1 si acierta el ganador/empate, 3 si acierta el marcador exacto."""
    if act_h is None or act_a is None:
        return None
    if pred_h == act_h and pred_a == act_a:
        return 3
    sign = lambda h, a: (h > a) - (h < a)
    if sign(pred_h, pred_a) == sign(act_h, act_a):
        return 1
    return 0


def scoreboard() -> list[dict]:
    """Tabla de posiciones: puntos, aciertos exactos y aciertos de ganador por usuario."""
    matches = {m["id"]: m for m in get_matches(only_active=True)}
    preds = get_all_predictions()
    table: dict[str, dict] = {}

    for p in preds:
        m = matches.get(p["match_id"])
        if not m:
            continue
        name = (p.get("users") or {}).get("name", "?")
        row = table.setdefault(
            name, {"Jugador": name, "Puntos": 0, "Exactos (3)": 0, "Ganador (1)": 0, "Jugados": 0}
        )
        pts = points_for(p["pred_home"], p["pred_away"], m.get("home_score"), m.get("away_score"))
        if pts is None:
            continue  # partido aún sin resultado
        row["Jugados"] += 1
        row["Puntos"] += pts
        if pts == 3:
            row["Exactos (3)"] += 1
        elif pts == 1:
            row["Ganador (1)"] += 1

    return sorted(
        table.values(),
        key=lambda r: (r["Puntos"], r["Exactos (3)"]),
        reverse=True,
    )

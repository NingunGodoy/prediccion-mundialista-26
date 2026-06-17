-- ============================================================
--  Base de datos para "Predicción Mundialista 26"
--  Copia TODO este texto y pégalo en Supabase:
--    Proyecto  ->  SQL Editor  ->  New query  ->  Run
-- ============================================================

-- Usuarios (tus amigos). El PIN se guarda encriptado, nunca en texto claro.
create table if not exists users (
  id         bigint generated always as identity primary key,
  name       text unique not null,
  pin_hash   text not null,
  created_at timestamptz default now()
);

-- Partidos del mundial.
create table if not exists matches (
  id         bigint generated always as identity primary key,
  kickoff    timestamptz not null,   -- fecha/hora de inicio (guardada en UTC)
  team1      text not null,
  team2      text not null,
  grupo      text,
  home_score int,                    -- resultado real (lo llena el admin al terminar)
  away_score int,
  unique (team1, team2, kickoff)     -- evita partidos duplicados al cargar dos veces
);

-- Predicciones de cada usuario por partido.
create table if not exists predictions (
  id         bigint generated always as identity primary key,
  user_id    bigint references users(id)   on delete cascade,
  match_id   bigint references matches(id) on delete cascade,
  pred_home  int not null,
  pred_away  int not null,
  created_at timestamptz default now(),
  unique (user_id, match_id)         -- una sola predicción por usuario y partido
);

-- Es un juego privado entre amigos: desactivamos la seguridad por filas.
alter table users       disable row level security;
alter table matches     disable row level security;
alter table predictions disable row level security;

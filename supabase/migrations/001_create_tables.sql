create extension if not exists pgcrypto;

create table if not exists public.cargas_csv (
    id uuid primary key default gen_random_uuid(),
    nombre_archivo text not null,
    cantidad_filas integer not null check (cantidad_filas >= 0),
    creado_en timestamptz not null default now()
);

create table if not exists public.registros_academicos (
    id uuid primary key default gen_random_uuid(),
    carga_id uuid references public.cargas_csv(id) on delete set null,
    estudiante_id text not null,
    asistencia_pct double precision,
    promedio_parcial double precision,
    horas_estudio double precision,
    tareas_entregadas_pct double precision,
    participacion_aula text,
    cursos_desaprobados integer,
    actividad_plataforma integer,
    estado_real text check (estado_real is null or estado_real in ('En riesgo', 'Sin riesgo')),
    creado_en timestamptz not null default now(),
    check (asistencia_pct is null or asistencia_pct between 0 and 100),
    check (promedio_parcial is null or promedio_parcial between 0 and 20),
    check (horas_estudio is null or horas_estudio >= 0),
    check (tareas_entregadas_pct is null or tareas_entregadas_pct between 0 and 100),
    check (participacion_aula is null or participacion_aula in ('Baja', 'Media', 'Alta')),
    check (cursos_desaprobados is null or cursos_desaprobados >= 0),
    check (actividad_plataforma is null or actividad_plataforma >= 0)
);

create table if not exists public.clasificaciones (
    id uuid primary key default gen_random_uuid(),
    registro_id uuid not null references public.registros_academicos(id) on delete cascade,
    estado_predicho text not null check (estado_predicho in ('En riesgo', 'Sin riesgo')),
    probabilidad_riesgo double precision not null check (probabilidad_riesgo between 0 and 1),
    version_modelo text not null,
    clasificado_en timestamptz not null default now()
);

create table if not exists public.detalles_clasificacion (
    id uuid primary key default gen_random_uuid(),
    clasificacion_id uuid not null references public.clasificaciones(id) on delete cascade,
    variable text not null,
    valor text,
    cambio_estimado_probabilidad double precision not null,
    interpretacion text not null
);

create table if not exists public.evaluaciones_modelo (
    id uuid primary key default gen_random_uuid(),
    version_modelo text not null,
    algoritmo text not null,
    accuracy double precision not null,
    precision_en_riesgo double precision not null,
    recall_en_riesgo double precision not null,
    f1_en_riesgo double precision not null,
    matriz_confusion jsonb not null,
    evaluado_en timestamptz not null default now()
);

create index if not exists idx_registros_estudiante on public.registros_academicos(estudiante_id);
create index if not exists idx_registros_carga on public.registros_academicos(carga_id);
create index if not exists idx_clasificaciones_registro on public.clasificaciones(registro_id);
create index if not exists idx_detalles_clasificacion on public.detalles_clasificacion(clasificacion_id);

-- El acceso se realiza únicamente a través de FastAPI.
alter table public.cargas_csv enable row level security;
alter table public.registros_academicos enable row level security;
alter table public.clasificaciones enable row level security;
alter table public.detalles_clasificacion enable row level security;
alter table public.evaluaciones_modelo enable row level security;


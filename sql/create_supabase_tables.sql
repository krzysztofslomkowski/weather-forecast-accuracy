create table if not exists forecast_records (
    provider text not null,
    run_date date not null,
    target_date date not null,
    horizon_days integer not null,
    tmax_c double precision not null,
    created_at timestamptz not null default now(),
    primary key (provider, run_date, target_date, horizon_days)
);

create table if not exists actual_records (
    date date primary key,
    tmax_c double precision not null,
    created_at timestamptz not null default now()
);

create table if not exists evaluation_detailed_records (
    provider text not null,
    run_date date not null,
    target_date date not null,
    forecast_tmax_c double precision not null,
    actual_tmax_c double precision not null,
    abs_error_c double precision not null,
    created_at timestamptz not null default now(),
    primary key (provider, run_date, target_date)
);

create table if not exists evaluation_mae_records (
    provider text not null,
    evaluation_run_date date not null,
    mae_c double precision not null,
    observations_count integer not null,
    created_at timestamptz not null default now(),
    primary key (provider, evaluation_run_date)
);

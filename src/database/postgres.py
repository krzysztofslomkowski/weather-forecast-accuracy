"""PostgreSQL/Supabase persistence helpers."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


def load_local_env(path: str = ".env") -> None:
    """Load simple KEY=value pairs from a local .env file."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_database_url() -> str:
    """Return DATABASE_URL from the environment, if configured."""
    load_local_env()
    return (os.getenv("DATABASE_URL") or "").strip()


def get_engine():
    """Create a SQLAlchemy engine for PostgreSQL/Supabase."""
    database_url = get_database_url()
    if not database_url:
        return None
    return create_engine(database_url, pool_pre_ping=True)


def ensure_tables(engine) -> None:
    """Create project tables if they do not exist yet."""
    statements = [
        """
        create table if not exists forecast_records (
            provider text not null,
            run_date date not null,
            target_date date not null,
            horizon_days integer not null,
            tmax_c double precision not null,
            created_at timestamptz not null default now(),
            primary key (provider, run_date, target_date, horizon_days)
        );
        """,
        """
        create table if not exists actual_records (
            date date primary key,
            tmax_c double precision not null,
            created_at timestamptz not null default now()
        );
        """,
        """
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
        """,
        """
        create table if not exists evaluation_mae_records (
            provider text not null,
            evaluation_run_date date not null,
            mae_c double precision not null,
            observations_count integer not null,
            created_at timestamptz not null default now(),
            primary key (provider, evaluation_run_date)
        );
        """,
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def save_forecasts_to_db(df: pd.DataFrame) -> None:
    """Upsert forecast rows to PostgreSQL/Supabase when DATABASE_URL is configured."""
    engine = get_engine()
    if engine is None:
        print("Skipping database save for forecasts (DATABASE_URL not configured).")
        return

    ensure_tables(engine)
    temp_table = "tmp_forecast_records"

    with engine.begin() as connection:
        df.to_sql(temp_table, connection, if_exists="replace", index=False)
        connection.execute(
            text(
                """
                insert into forecast_records (provider, run_date, target_date, horizon_days, tmax_c)
                select provider, run_date, target_date, horizon_days, tmax_c
                from tmp_forecast_records
                on conflict (provider, run_date, target_date, horizon_days)
                do update set tmax_c = excluded.tmax_c;
                drop table tmp_forecast_records;
                """
            )
        )

    print(f"Saved {len(df)} forecast rows to database.")


def save_actuals_to_db(df: pd.DataFrame) -> None:
    """Upsert actual observation rows to PostgreSQL/Supabase when DATABASE_URL is configured."""
    engine = get_engine()
    if engine is None:
        print("Skipping database save for actuals (DATABASE_URL not configured).")
        return

    ensure_tables(engine)
    temp_table = "tmp_actual_records"

    with engine.begin() as connection:
        df.to_sql(temp_table, connection, if_exists="replace", index=False)
        connection.execute(
            text(
                """
                insert into actual_records (date, tmax_c)
                select date, tmax_c
                from tmp_actual_records
                on conflict (date)
                do update set tmax_c = excluded.tmax_c;
                drop table tmp_actual_records;
                """
            )
        )

    print(f"Saved {len(df)} actual rows to database.")


def save_evaluation_to_db(detailed_df: pd.DataFrame, mae_df: pd.DataFrame) -> None:
    """Upsert detailed evaluation and MAE rows to PostgreSQL/Supabase."""
    engine = get_engine()
    if engine is None:
        print("Skipping database save for evaluation (DATABASE_URL not configured).")
        return

    ensure_tables(engine)
    mae_to_save = mae_df.copy()
    mae_to_save["evaluation_run_date"] = pd.Timestamp.utcnow().date()
    counts = detailed_df.groupby("provider").size().reset_index(name="observations_count")
    mae_to_save = mae_to_save.merge(counts, on="provider", how="left")
    mae_to_save["observations_count"] = mae_to_save["observations_count"].fillna(0).astype(int)

    with engine.begin() as connection:
        detailed_df.to_sql("tmp_evaluation_detailed_records", connection, if_exists="replace", index=False)
        mae_to_save.to_sql("tmp_evaluation_mae_records", connection, if_exists="replace", index=False)

        connection.execute(
            text(
                """
                insert into evaluation_detailed_records
                    (provider, run_date, target_date, forecast_tmax_c, actual_tmax_c, abs_error_c)
                select provider, run_date, target_date, forecast_tmax_c, actual_tmax_c, abs_error_c
                from tmp_evaluation_detailed_records
                on conflict (provider, run_date, target_date)
                do update set
                    forecast_tmax_c = excluded.forecast_tmax_c,
                    actual_tmax_c = excluded.actual_tmax_c,
                    abs_error_c = excluded.abs_error_c;

                insert into evaluation_mae_records
                    (provider, evaluation_run_date, mae_c, observations_count)
                select provider, evaluation_run_date, mae_c, observations_count
                from tmp_evaluation_mae_records
                on conflict (provider, evaluation_run_date)
                do update set
                    mae_c = excluded.mae_c,
                    observations_count = excluded.observations_count;

                drop table tmp_evaluation_detailed_records;
                drop table tmp_evaluation_mae_records;
                """
            )
        )

    print(f"Saved {len(detailed_df)} detailed evaluation rows and {len(mae_to_save)} MAE rows to database.")

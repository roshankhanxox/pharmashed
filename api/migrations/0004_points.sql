-- Phase 4: an append-only points ledger and the badges derived from it.
-- Points are never edited. A hidden report is reversed by adding negative rows, so history stays auditable.
create table points_events (
    id         bigserial primary key,
    user_id    text not null,
    report_id  uuid references reports (id) on delete cascade,
    points     integer not null,                 -- 0 rows explain why a report earned nothing
    reason     text not null,
    created_at timestamptz not null default now()
);

-- One row per (report, reason): awarding twice for the same report is impossible, so it is safe to retry.
create unique index points_events_once_idx on points_events (report_id, reason);
create index points_events_user_idx on points_events (user_id, created_at desc);

create table badges_awarded (
    user_id    text not null,
    badge      text not null,
    awarded_at timestamptz not null default now(),
    primary key (user_id, badge)
);

-- Phase 3: one optional photo per report. Files live in the private Neon storage bucket; this row is the record.
create table report_photos (
    id         uuid primary key default gen_random_uuid(),
    user_id    text not null,
    report_id  uuid references reports (id) on delete cascade,   -- null until the report is filed
    object_key text not null,
    width      integer not null,
    height     integer not null,
    bytes      integer not null,
    ai_ok      boolean,                                           -- null = the check could not run
    ai_flags   jsonb not null default '{}',
    created_at timestamptz not null default now()
);

create unique index report_photos_report_idx on report_photos (report_id) where report_id is not null;
create index report_photos_user_idx on report_photos (user_id, created_at desc);

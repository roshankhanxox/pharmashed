-- Phase 5: flags from readers and the moderator's decisions.
create table report_flags (
    id          bigserial primary key,
    report_id   uuid not null references reports (id) on delete cascade,
    flagged_by  text not null,
    reason      text not null check (reason in ('inaccurate', 'personal_info', 'inappropriate', 'not_a_stream', 'spam')),
    created_at  timestamptz not null default now(),
    resolved_at timestamptz,                         -- set when a moderator approves or hides the report
    unique (report_id, flagged_by)                   -- one flag per person per report
);
create index report_flags_open_idx on report_flags (report_id) where resolved_at is null;
create index report_flags_user_idx on report_flags (flagged_by, created_at desc);

create table moderation_actions (
    id            bigserial primary key,
    report_id     uuid not null references reports (id) on delete cascade,
    admin_user_id text not null,
    action        text not null check (action in ('approve', 'hide')),
    note          text not null default '',
    created_at    timestamptz not null default now()
);
create index moderation_actions_report_idx on moderation_actions (report_id, created_at desc);

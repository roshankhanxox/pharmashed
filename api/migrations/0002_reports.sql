-- Phase 2: citizen reports. A report is an observation at a pin on a stream, linked to the nearest of the
-- 105 model sites when one is within range. Reports never feed the model; they are a separate, unverified layer.
create table reports (
    id          uuid primary key default gen_random_uuid(),
    user_id     text not null,                       -- Neon Auth `sub`; the fixed value 'sample' marks seeded samples
    is_sample   boolean not null default false,
    lat         double precision not null check (lat between -90 and 90),
    lon         double precision not null check (lon between -180 and 180),
    site_id     text,                                -- nearest model site within range, else null
    city        text check (city in ('TLS', 'GNT', 'BNV', 'CBR', 'OSL')),
    distance_m  integer check (distance_m >= 0),     -- distance from the pin to site_id
    observed_at timestamptz not null,
    checklist   jsonb not null,
    note_raw    text not null default '',            -- what the person typed
    note_clean  text,                                -- the AI-proofread version they confirmed (phase 3)
    status      text not null default 'approved' check (status in ('pending', 'approved', 'hidden')),
    created_at  timestamptz not null default now()
);

create index reports_created_idx  on reports (created_at desc) where status = 'approved';
create index reports_site_idx     on reports (site_id, observed_at desc) where status = 'approved';
create index reports_user_idx     on reports (user_id, created_at desc);

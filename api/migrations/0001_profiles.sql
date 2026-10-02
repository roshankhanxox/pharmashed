-- Phase 1: one profile per signed-in user. We store no email and no real name; the nickname is the
-- only public identity. user_id is the `sub` of the Neon Auth token.
create table profiles (
    user_id             text primary key,
    nickname            text not null,
    nickname_key        text generated always as (lower(nickname)) stored,
    show_on_leaderboard boolean not null default true,
    home_city           text check (home_city in ('TLS', 'GNT', 'BNV', 'CBR', 'OSL')),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    constraint profiles_nickname_key_unique unique (nickname_key)
);

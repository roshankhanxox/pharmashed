-- Moderators, kept in our own database. A row here makes a person a moderator, no environment setting needed.
-- The grant is tied to the sign-in user id (the token's `sub`), which nobody else can claim, so unlike the
-- ADMIN_EMAILS route it does not need a verified email.
create table moderators (
    user_id  text primary key,
    added_at timestamptz not null default now(),
    note     text not null default ''
);

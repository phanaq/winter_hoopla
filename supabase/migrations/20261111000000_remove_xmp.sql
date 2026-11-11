-- Only MMP and WMP signups are allowed.
alter table public.signups drop constraint if exists signups_gender_match_check;
alter table public.signups
    add constraint signups_gender_match_check check (gender_match in ('mmp', 'wmp'));

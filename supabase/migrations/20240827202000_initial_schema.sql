-- Enable necessary extensions
create extension if not exists "uuid-ossp";

-- Users table (maps to your Flask User model)
create table if not exists users (
    id uuid references auth.users on delete cascade not null primary key,
    email text unique not null,
    username text unique,
    full_name text,
    bio text,
    profile_pic text default 'default.jpg',
    is_admin boolean default false,
    is_approved boolean default false,
    profile_updated boolean default false,
    created_at timestamptz default timezone('utc'::text, now()) not null,
    last_login timestamptz,
    updated_at timestamptz default timezone('utc'::text, now()) not null,
    constraint username_length check (char_length(username) >= 3)
);

-- Campaigns table
create table if not exists campaigns (
    id uuid default uuid_generate_v4() primary key,
    name text not null,
    description text,
    system text not null,
    image text default 'default_campaign.jpg',
    created_at timestamptz default timezone('utc'::text, now()) not null,
    dm_id uuid references users(id) on delete cascade not null
);

-- Player-Campaign many-to-many relationship
create table if not exists player_campaign (
    user_id uuid references users(id) on delete cascade,
    campaign_id uuid references campaigns(id) on delete cascade,
    primary key (user_id, campaign_id)
);

-- Characters table
create table if not exists characters (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references users(id) on delete cascade not null,
    campaign_id uuid references campaigns(id) on delete cascade not null,
    character_name text not null,
    display_name text not null default '',
    character_class text,
    level integer,
    race text,
    description text,
    image text,
    created_at timestamptz default timezone('utc'::text, now()) not null,
    updated_at timestamptz default timezone('utc'::text, now()) not null
);

-- NPCs table
create table if not exists npcs (
    id uuid default uuid_generate_v4() primary key,
    campaign_id uuid references campaigns(id) on delete cascade not null,
    created_by uuid references users(id) on delete cascade not null,
    name text not null,
    race text,
    age integer,
    gender text,
    appearance text,
    personality text,
    background text,
    notes text,
    tags text,
    is_important boolean default false,
    image text default 'default_npc.jpg',
    created_at timestamptz default timezone('utc'::text, now()) not null,
    updated_at timestamptz default timezone('utc'::text, now()) not null
);

-- Quests table
create table if not exists quests (
    id uuid default uuid_generate_v4() primary key,
    campaign_id uuid references campaigns(id) on delete cascade not null,
    created_by uuid references users(id) on delete cascade not null,
    title text not null,
    description text,
    reward text,
    status text default 'open',
    priority text default 'normal',
    is_main boolean default false,
    tags text,
    created_at timestamptz default timezone('utc'::text, now()) not null,
    updated_at timestamptz default timezone('utc'::text, now()) not null
);

-- Sessions table
create table if not exists sessions (
    id uuid default uuid_generate_v4() primary key,
    campaign_id uuid references campaigns(id) on delete cascade not null,
    created_by uuid references users(id) on delete cascade not null,
    title text,
    scheduled_at timestamptz not null,
    location text,
    notes text,
    created_at timestamptz default timezone('utc'::text, now()) not null
);

-- Session responses
create table if not exists session_responses (
    id uuid default uuid_generate_v4() primary key,
    session_id uuid references sessions(id) on delete cascade not null,
    user_id uuid references users(id) on delete cascade not null,
    response text not null,
    created_at timestamptz default timezone('utc'::text, now()) not null,
    updated_at timestamptz default timezone('utc'::text, now()) not null,
    unique(session_id, user_id)
);

-- Session polls
create table if not exists session_polls (
    id uuid default uuid_generate_v4() primary key,
    campaign_id uuid references campaigns(id) on delete cascade not null,
    created_by uuid references users(id) on delete cascade not null,
    title text,
    notes text,
    is_closed boolean default false,
    created_at timestamptz default timezone('utc'::text, now()) not null
);

-- Poll options
create table if not exists session_poll_options (
    id uuid default uuid_generate_v4() primary key,
    poll_id uuid references session_polls(id) on delete cascade not null,
    scheduled_at timestamptz not null,
    location text,
    notes text
);

-- Poll votes
create table if not exists session_poll_votes (
    id uuid default uuid_generate_v4() primary key,
    option_id uuid references session_poll_options(id) on delete cascade not null,
    user_id uuid references users(id) on delete cascade not null,
    response text not null,
    created_at timestamptz default timezone('utc'::text, now()) not null,
    updated_at timestamptz default timezone('utc'::text, now()) not null,
    unique(option_id, user_id)
);

-- Posts table
create table if not exists posts (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references users(id) on delete cascade not null,
    campaign_id uuid references campaigns(id) on delete cascade not null,
    title text not null,
    content text not null,
    created_at timestamptz default timezone('utc'::text, now()) not null
);

-- Messages table
create table if not exists messages (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references users(id) on delete cascade not null,
    campaign_id uuid references campaigns(id) on delete cascade not null,
    character_id uuid references characters(id) on delete set null,
    content text not null,
    created_at timestamptz default timezone('utc'::text, now()) not null
);

-- Create indexes for better performance
create index if not exists idx_messages_campaign_id on messages(campaign_id);
create index if not exists idx_characters_campaign_id on characters(campaign_id);
create index if not exists idx_characters_user_id on characters(user_id);
create index if not exists idx_quests_campaign_id on quests(campaign_id);
create index if not exists idx_npcs_campaign_id on npcs(campaign_id);
create index if not exists idx_sessions_campaign_id on sessions(campaign_id);
create index if not exists idx_session_responses_session_id on session_responses(session_id);
create index if not exists idx_session_polls_campaign_id on session_polls(campaign_id);
create index if not exists idx_session_poll_options_poll_id on session_poll_options(poll_id);
create index if not exists idx_session_poll_votes_option_id on session_poll_votes(option_id);

-- Set up Row Level Security (RLS)
alter table users enable row level security;
alter table campaigns enable row level security;
alter table player_campaign enable row level security;
alter table characters enable row level security;
alter table npcs enable row level security;
alter table quests enable row level security;
alter table sessions enable row level security;
alter table session_responses enable row level security;
alter table session_polls enable row level security;
alter table session_poll_options enable row level security;
alter table session_poll_votes enable row level security;
alter table posts enable row level security;
alter table messages enable row level security;

-- Create a trigger to handle user signups
create or replace function public.handle_new_user() 
returns trigger as $$
begin
  insert into public.users (id, email, username, created_at, updated_at)
  values (
    new.id, 
    new.email, 
    split_part(new.email, '@', 1) || '_' || substr(md5(random()::text), 1, 4),
    timezone('utc'::text, now()),
    timezone('utc'::text, now())
  )
  on conflict (id) do update set
    email = excluded.email,
    updated_at = timezone('utc'::text, now())
  returning id into new.id;
  return new;
end;
$$ language plpgsql security definer;

-- Trigger the function every time a user is created
create or replace trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Create a trigger to update the updated_at column
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = timezone('utc'::text, now());
  return new;
end;
$$ language plpgsql;

-- Add the trigger to all tables with updated_at
create or replace function add_updated_at_trigger(table_name text) returns void as $$
begin
  execute format('create or replace trigger update_%s_updated_at
                 before update on %s
                 for each row execute procedure update_updated_at_column()',
                table_name, table_name);
end;
$$ language plpgsql;

-- Call the function for each table with updated_at
select add_updated_at_trigger('users');
select add_updated_at_trigger('characters');
select add_updated_at_trigger('npcs');
select add_updated_at_trigger('quests');
select add_updated_at_trigger('session_responses');
select add_updated_at_trigger('session_poll_votes');

-- Set up storage for file uploads
insert into storage.buckets (id, name, public)
values ('profile_pics', 'profile_pics', true)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('character_images', 'character_images', true)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('campaign_images', 'campaign_images', true)
on conflict (id) do nothing;

-- Set up storage policies
create policy "Profile pictures are publicly accessible"
on storage.objects for select
using (bucket_id = 'profile_pics');

create policy "Character images are publicly accessible"
on storage.objects for select
using (bucket_id = 'character_images');

create policy "Campaign images are publicly accessible"
on storage.objects for select
using (bucket_id = 'campaign_images');

-- Create a function to generate a unique username
drop function if exists public.generate_username;
create or replace function public.generate_username(email text) 
returns text as $$
declare
  base_username text;
  new_username text;
  counter int := 1;
begin
  base_username := split_part(email, '@', 1);
  new_username := base_username;
  
  while exists (select 1 from auth.users where raw_user_meta_data->>'username' = new_username) loop
    new_username := base_username || counter::text;
    counter := counter + 1;
  end loop;
  
  return new_username;
end;
$$ language plpgsql security definer;

-- Update the handle_new_user function to use the new username generator
create or replace function public.handle_new_user() 
returns trigger as $$
begin
  insert into public.users (id, email, username, created_at, updated_at)
  values (
    new.id, 
    new.email, 
    public.generate_username(new.email),
    timezone('utc'::text, now()),
    timezone('utc'::text, now())
  )
  on conflict (id) do update set
    email = excluded.email,
    updated_at = timezone('utc'::text, now())
  returning id into new.id;
  return new;
end;
$$ language plpgsql security definer;

-- Grant necessary permissions
grant all on all tables in schema public to postgres, anon, authenticated, service_role;
grant all on all sequences in schema public to postgres, anon, authenticated, service_role;
grant all on all functions in schema public to postgres, anon, authenticated, service_role;

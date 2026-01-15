const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: '.env.local' });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
    console.error('Error: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set in .env.local');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseAnonKey);

async function migrate() {
    console.log('Starting migration to Supabase...');

    // 1. Migrate Users
    const usersPath = path.join(__dirname, '../../data/users.json');
    if (fs.existsSync(usersPath)) {
        console.log('Migrating users...');
        const users = JSON.parse(fs.readFileSync(usersPath, 'utf8'));
        const formattedUsers = users.map(u => ({
            username: u.username,
            is_pro: u.isPro ?? u.is_pro ?? false
        }));

        const { error: userError } = await supabase
            .from('users')
            .upsert(formattedUsers, { onConflict: 'username' });

        if (userError) console.error('Error migrating users:', userError);
        else console.log('Users migrated successfully.');
    }

    // 2. Migrate Settings
    const settingsPath = path.join(__dirname, '../../data/admin_settings.json');
    if (fs.existsSync(settingsPath)) {
        console.log('Migrating settings...');
        const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));

        // Migrate wallets
        if (settings.wallets) {
            const { error: settingsError } = await supabase
                .from('settings')
                .upsert({
                    key: 'wallets',
                    value: JSON.stringify(settings.wallets)
                }, { onConflict: 'key' });

            if (settingsError) console.error('Error migrating settings:', settingsError);
            else console.log('Settings migrated successfully.');
        }
    }

    console.log('Migration complete.');
}

migrate();

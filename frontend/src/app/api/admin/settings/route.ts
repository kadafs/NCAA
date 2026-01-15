import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET() {
    try {
        const { data, error } = await supabase
            .from('settings')
            .select('*');

        if (error) throw error;

        // Format the flat key-value pairs into the expected object structure
        const settings = (data || []).reduce((acc: any, curr: any) => {
            acc[curr.key] = curr.value;
            return acc;
        }, {});

        // Ensure 'wallets' key exists and is parsed if it was a string
        if (settings.wallets && typeof settings.wallets === 'string') {
            try { settings.wallets = JSON.parse(settings.wallets); } catch (e) { }
        }

        return NextResponse.json(settings);
    } catch (error) {
        console.error('Supabase error:', error);
        return NextResponse.json({ wallets: [] });
    }
}

export async function POST(request: Request) {
    try {
        const body = await request.json(); // Expected: { wallets: [...] }

        // We stores settings as individual rows for flexibility
        const { error } = await supabase
            .from('settings')
            .upsert({
                key: 'wallets',
                value: JSON.stringify(body.wallets || [])
            }, { onConflict: 'key' });

        if (error) throw error;
        return NextResponse.json({ success: true });
    } catch (error) {
        console.error('Supabase error:', error);
        return NextResponse.json({ success: false, error: String(error) }, { status: 500 });
    }
}

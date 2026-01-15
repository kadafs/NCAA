import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET() {
    try {
        const { data, error } = await supabase
            .from('users')
            .select('*');

        if (error) throw error;
        return NextResponse.json(data || []);
    } catch (error) {
        console.error('Supabase error:', error);
        return NextResponse.json([]);
    }
}

export async function POST(request: Request) {
    try {
        const body = await request.json();

        if (Array.isArray(body)) {
            // Bulk update/upsert
            const { data, error } = await supabase
                .from('users')
                .upsert(body, { onConflict: 'username' });

            if (error) throw error;
            return NextResponse.json({ success: true, users: data });
        } else {
            // Single user update/upsert
            const { data, error } = await supabase
                .from('users')
                .upsert({
                    username: body.username,
                    is_pro: body.is_pro ?? body.isPro ?? false
                }, { onConflict: 'username' })
                .select()
                .single();

            if (error) throw error;
            return NextResponse.json({ success: true, user: data });
        }
    } catch (error) {
        console.error('Supabase error:', error);
        return NextResponse.json({ success: false, error: String(error) }, { status: 500 });
    }
}

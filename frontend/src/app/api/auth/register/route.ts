import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import bcrypt from "bcryptjs";

export async function POST(req: Request) {
    try {
        const { username, password } = await req.json();

        if (!username || !password) {
            return NextResponse.json({ error: "Username and password are required" }, { status: 400 });
        }

        // Check if user already exists
        const { data: existingUser, error: fetchError } = await supabase
            .from('users')
            .select('username')
            .eq('username', username)
            .single();

        if (existingUser) {
            return NextResponse.json({ error: "Username already exists" }, { status: 400 });
        }

        // Hash the password
        const hashedPassword = await bcrypt.hash(password, 10);

        // Create the user
        const { data: newUser, error: createError } = await supabase
            .from('users')
            .insert([{ username, password_hash: hashedPassword, is_pro: false }])
            .select()
            .single();

        if (createError) {
            console.error("Registration Error:", createError);
            return NextResponse.json({ error: "Failed to create user" }, { status: 500 });
        }

        return NextResponse.json({ message: "User created successfully", user: { id: newUser.id, username: newUser.username } });

    } catch (error) {
        console.error("Registration API error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}

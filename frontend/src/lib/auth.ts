import { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { supabase } from "@/lib/supabase";

export const authOptions: NextAuthOptions = {
    providers: [
        CredentialsProvider({
            name: "Credentials",
            credentials: {
                username: { label: "Username", type: "text" },
                password: { label: "Password", type: "password" }
            },
            async authorize(credentials) {
                if (!credentials?.username) return null;

                // For now, we allow login with just username (simple migration)
                // In production, you would verify the password here
                const { data: user, error } = await supabase
                    .from('users')
                    .select('*')
                    .eq('username', credentials.username)
                    .single();

                if (error || !user) {
                    // Create user if not exists (to match existing flow)
                    const { data: newUser, error: createError } = await supabase
                        .from('users')
                        .insert([{ username: credentials.username, is_pro: false }])
                        .select()
                        .single();

                    if (createError) return null;
                    return { id: newUser.id, name: newUser.username, username: newUser.username, isPro: false };
                }

                return {
                    id: user.id,
                    name: user.username,
                    username: user.username,
                    isPro: user.is_pro
                };
            }
        })
    ],
    callbacks: {
        async jwt({ token, user }) {
            if (user) {
                token.id = user.id;
                token.username = (user as any).username;
                token.isPro = (user as any).isPro;
            }
            return token;
        },
        async session({ session, token }) {
            if (session.user) {
                (session.user as any).id = token.id;
                (session.user as any).username = token.username;
                (session.user as any).isPro = token.isPro;
            }
            return session;
        }
    },
    pages: {
        signIn: '/', // We handle login in a modal on the home page for now
    },
    session: {
        strategy: "jwt",
    },
    secret: process.env.NEXTAUTH_SECRET,
};

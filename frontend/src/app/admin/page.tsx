'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    Users,
    Settings,
    Wallet,
    CheckCircle2,
    XCircle,
    Save,
    Plus,
    Trash2,
    Trophy
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

export default function AdminDashboard() {
    const { data: session, status } = useSession();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<'users' | 'settings'>('users');
    const [users, setUsers] = useState<any[]>([]);
    const [wallets, setWallets] = useState<{ type: string; address: string }[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (status === 'unauthenticated' || (session && (session.user as any).username !== 'admin')) {
            router.push('/');
        } else if (status === 'authenticated') {
            fetchData();
        }
    }, [status, session]);

    const fetchData = async () => {
        try {
            const usersRes = await fetch('/api/admin/users');
            const settingsRes = await fetch('/api/admin/settings');
            const usersData = await usersRes.json();
            const settingsData = await settingsRes.json();
            // Normalize users (Supabase is_pro -> frontend isPro)
            const normalizedUsers = usersData.map((u: any) => ({
                ...u,
                isPro: u.is_pro ?? u.isPro ?? false
            }));
            setUsers(normalizedUsers);
            setWallets(settingsData.wallets || []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const togglePro = async (username: string, currentStatus: boolean) => {
        try {
            await fetch('/api/admin/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, is_pro: !currentStatus })
            });
            fetchData();
        } catch (err) {
            console.error(err);
        }
    };

    const addWallet = () => {
        setWallets([...wallets, { type: 'BTC', address: '' }]);
    };

    const removeWallet = (index: number) => {
        setWallets(wallets.filter((_, i) => i !== index));
    };

    const updateWallet = (index: number, field: 'type' | 'address', value: string) => {
        const newWallets = [...wallets];
        newWallets[index][field] = value;
        setWallets(newWallets);
    };

    const saveSettings = async () => {
        try {
            await fetch('/api/admin/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wallets })
            });
            alert('Settings Saved');
        } catch (err) {
            console.error(err);
        }
    };

    if (loading) return <div className="min-h-screen bg-black text-white flex items-center justify-center font-bold">LOADING ADMIN...</div>;

    return (
        <div className="min-h-screen bg-[#050510] text-gray-200 font-sans selection:bg-accent-blue/30">
            {/* Header */}
            <nav className="glass border-b border-white/5 p-6 flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-accent-orange rounded-lg flex items-center justify-center">
                        <Settings className="text-white w-5 h-5" />
                    </div>
                    <h1 className="text-lg font-black tracking-tighter">NCAA <span className="text-accent-orange">ADMIN</span></h1>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setActiveTab('users')}
                        className={cn("px-4 py-2 rounded-lg text-sm font-bold transition-all", activeTab === 'users' ? "bg-white/10 text-white" : "text-gray-500 hover:text-white")}
                    >
                        Users
                    </button>
                    <button
                        onClick={() => setActiveTab('settings')}
                        className={cn("px-4 py-2 rounded-lg text-sm font-bold transition-all", activeTab === 'settings' ? "bg-white/10 text-white" : "text-gray-500 hover:text-white")}
                    >
                        Payment settings
                    </button>
                </div>
            </nav>

            <main className="p-8 max-w-6xl mx-auto">
                {activeTab === 'users' ? (
                    <section className="space-y-6">
                        <h2 className="text-2xl font-bold flex items-center gap-2">
                            <Users className="text-accent-orange" />
                            Manage User Access
                        </h2>
                        <div className="glass overflow-hidden rounded-2xl border border-white/5">
                            <table className="w-full text-left">
                                <thead className="bg-white/5 border-b border-white/5">
                                    <tr>
                                        <th className="p-4 text-xs font-bold text-gray-400 uppercase tracking-widest">Username</th>
                                        <th className="p-4 text-xs font-bold text-gray-400 uppercase tracking-widest">Status</th>
                                        <th className="p-4 text-xs font-bold text-gray-400 uppercase tracking-widest text-right">Action</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {users.map((user) => (
                                        <tr key={user.username} className="hover:bg-white/[0.02] transition-colors">
                                            <td className="p-4 font-bold text-white">{user.username}</td>
                                            <td className="p-4">
                                                {user.isPro ? (
                                                    <span className="flex items-center gap-1.5 text-xs font-bold text-green-400">
                                                        <CheckCircle2 className="w-4 h-4" /> PRO
                                                    </span>
                                                ) : (
                                                    <span className="flex items-center gap-1.5 text-xs font-bold text-gray-500">
                                                        <XCircle className="w-4 h-4" /> BASIC
                                                    </span>
                                                )}
                                            </td>
                                            <td className="p-4 text-right">
                                                <button
                                                    onClick={() => togglePro(user.username, user.isPro)}
                                                    className={cn(
                                                        "px-4 py-1.5 rounded-lg text-xs font-bold transition-all",
                                                        user.isPro ? "bg-red-500/10 text-red-500 hover:bg-red-500/20" : "bg-green-500/10 text-green-500 hover:bg-green-500/20"
                                                    )}
                                                >
                                                    {user.isPro ? "Revoke Pro" : "Grant Pro"}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                    {users.length === 0 && (
                                        <tr>
                                            <td colSpan={3} className="p-12 text-center text-gray-500 font-medium">No users found. Wait for registrations.</td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </section>
                ) : (
                    <section className="space-y-6 max-w-2xl">
                        <div className="flex justify-between items-center">
                            <h2 className="text-2xl font-bold flex items-center gap-2">
                                <Wallet className="text-accent-orange" />
                                Wallet Addresses
                            </h2>
                            <button
                                onClick={addWallet}
                                className="flex items-center gap-2 bg-accent-orange text-white px-4 py-2 rounded-xl text-xs font-bold hover:scale-105 transition-all"
                            >
                                <Plus className="w-4 h-4" /> Add Coin
                            </button>
                        </div>

                        <div className="space-y-4">
                            {wallets.map((wallet, i) => (
                                <div key={i} className="glass p-4 rounded-2xl flex gap-4 items-end border border-white/5">
                                    <div className="flex-1 space-y-2">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase">Coin Name (e.g. USDT TRC20)</label>
                                        <input
                                            className="w-full bg-black/50 border border-white/10 rounded-lg p-2.5 text-white"
                                            value={wallet.type}
                                            onChange={(e) => updateWallet(i, 'type', e.target.value)}
                                        />
                                    </div>
                                    <div className="flex-[2] space-y-2">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase">Wallet Address</label>
                                        <input
                                            className="w-full bg-black/50 border border-white/10 rounded-lg p-2.5 text-white font-mono"
                                            value={wallet.address}
                                            onChange={(e) => updateWallet(i, 'address', e.target.value)}
                                        />
                                    </div>
                                    <button
                                        onClick={() => removeWallet(i)}
                                        className="p-3 text-red-500 hover:bg-red-500/10 rounded-xl transition-colors"
                                    >
                                        <Trash2 className="w-5 h-5" />
                                    </button>
                                </div>
                            ))}

                            <button
                                onClick={saveSettings}
                                className="w-full mt-8 flex items-center justify-center gap-2 bg-white text-black py-4 rounded-2xl font-black hover:scale-[1.02] transition-all"
                            >
                                <Save className="w-5 h-5" /> SAVE PAYMENT SETTINGS
                            </button>
                        </div>
                    </section>
                )}
            </main>
        </div>
    );
}

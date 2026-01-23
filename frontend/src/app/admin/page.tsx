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
    ArrowLeft
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

/**
 * Admin Dashboard - Dark Theme
 * 
 * Provides admin-only access for user management and payment settings
 */

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

    if (loading) {
        return (
            <div className="min-h-screen bg-dash-bg flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                        className="w-12 h-12 border-2 border-gold/20 border-t-gold rounded-full"
                    />
                    <span className="text-[10px] font-bold text-dash-text-muted uppercase tracking-widest">
                        Loading Admin...
                    </span>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-dash-bg text-dash-text-primary">
            {/* Header */}
            <header className="sticky top-0 z-30 bg-dash-bg/80 backdrop-blur-xl border-b border-dash-border">
                <div className="max-w-6xl mx-auto px-4 py-4">
                    <Link
                        href="/dashboard"
                        className="inline-flex items-center gap-2 text-[10px] font-bold text-dash-text-muted uppercase tracking-widest hover:text-white transition-colors mb-4 group"
                    >
                        <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-1 transition-transform" />
                        Back to Dashboard
                    </Link>

                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gold rounded-xl flex items-center justify-center">
                                <Settings className="text-dash-bg w-5 h-5" />
                            </div>
                            <h1 className="text-xl font-black text-white uppercase tracking-tighter">
                                Admin <span className="text-gold italic">Panel</span>
                            </h1>
                        </div>
                        <div className="flex gap-2 bg-dash-card border border-dash-border rounded-xl p-1">
                            <button
                                onClick={() => setActiveTab('users')}
                                className={cn(
                                    "px-4 py-2 rounded-lg text-xs font-bold uppercase transition-all",
                                    activeTab === 'users'
                                        ? "bg-gold text-dash-bg"
                                        : "text-dash-text-muted hover:text-white"
                                )}
                            >
                                Users
                            </button>
                            <button
                                onClick={() => setActiveTab('settings')}
                                className={cn(
                                    "px-4 py-2 rounded-lg text-xs font-bold uppercase transition-all",
                                    activeTab === 'settings'
                                        ? "bg-gold text-dash-bg"
                                        : "text-dash-text-muted hover:text-white"
                                )}
                            >
                                Payments
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            <main className="p-4 md:p-8 max-w-6xl mx-auto">
                {activeTab === 'users' ? (
                    <section className="space-y-6">
                        <h2 className="text-lg font-black text-white uppercase flex items-center gap-2">
                            <Users className="text-gold w-5 h-5" />
                            Manage User Access
                        </h2>
                        <div className="bg-dash-card border border-dash-border rounded-2xl overflow-hidden">
                            <table className="w-full text-left">
                                <thead className="bg-dash-bg border-b border-dash-border">
                                    <tr>
                                        <th className="p-4 text-[10px] font-black text-dash-text-muted uppercase tracking-widest">Username</th>
                                        <th className="p-4 text-[10px] font-black text-dash-text-muted uppercase tracking-widest">Status</th>
                                        <th className="p-4 text-[10px] font-black text-dash-text-muted uppercase tracking-widest text-right">Action</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-dash-border">
                                    {users.map((user) => (
                                        <tr key={user.username} className="hover:bg-dash-bg-secondary transition-colors">
                                            <td className="p-4 font-bold text-white">{user.username}</td>
                                            <td className="p-4">
                                                {user.isPro ? (
                                                    <span className="flex items-center gap-1.5 text-[10px] font-black text-dash-success uppercase">
                                                        <CheckCircle2 className="w-4 h-4" /> PRO
                                                    </span>
                                                ) : (
                                                    <span className="flex items-center gap-1.5 text-[10px] font-black text-dash-text-muted uppercase">
                                                        <XCircle className="w-4 h-4" /> BASIC
                                                    </span>
                                                )}
                                            </td>
                                            <td className="p-4 text-right">
                                                <button
                                                    onClick={() => togglePro(user.username, user.isPro)}
                                                    className={cn(
                                                        "px-4 py-1.5 rounded-lg text-[10px] font-black uppercase transition-all",
                                                        user.isPro
                                                            ? "bg-dash-danger/10 text-dash-danger hover:bg-dash-danger/20"
                                                            : "bg-dash-success/10 text-dash-success hover:bg-dash-success/20"
                                                    )}
                                                >
                                                    {user.isPro ? "Revoke Pro" : "Grant Pro"}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                    {users.length === 0 && (
                                        <tr>
                                            <td colSpan={3} className="p-12 text-center text-dash-text-muted font-medium">
                                                No users found. Wait for registrations.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </section>
                ) : (
                    <section className="space-y-6 max-w-2xl">
                        <div className="flex justify-between items-center">
                            <h2 className="text-lg font-black text-white uppercase flex items-center gap-2">
                                <Wallet className="text-gold w-5 h-5" />
                                Wallet Addresses
                            </h2>
                            <button
                                onClick={addWallet}
                                className="flex items-center gap-2 bg-gold text-dash-bg px-4 py-2 rounded-xl text-[10px] font-black uppercase hover:scale-105 transition-all"
                            >
                                <Plus className="w-4 h-4" /> Add Coin
                            </button>
                        </div>

                        <div className="space-y-4">
                            {wallets.map((wallet, i) => (
                                <div key={i} className="bg-dash-card border border-dash-border p-4 rounded-2xl flex gap-4 items-end">
                                    <div className="flex-1 space-y-2">
                                        <label className="text-[10px] font-bold text-dash-text-muted uppercase">Coin Name</label>
                                        <input
                                            className="w-full bg-dash-bg border border-dash-border rounded-lg p-2.5 text-white text-sm focus:border-gold/50 outline-none transition-colors"
                                            value={wallet.type}
                                            onChange={(e) => updateWallet(i, 'type', e.target.value)}
                                        />
                                    </div>
                                    <div className="flex-[2] space-y-2">
                                        <label className="text-[10px] font-bold text-dash-text-muted uppercase">Wallet Address</label>
                                        <input
                                            className="w-full bg-dash-bg border border-dash-border rounded-lg p-2.5 text-white font-mono text-sm focus:border-gold/50 outline-none transition-colors"
                                            value={wallet.address}
                                            onChange={(e) => updateWallet(i, 'address', e.target.value)}
                                        />
                                    </div>
                                    <button
                                        onClick={() => removeWallet(i)}
                                        className="p-3 text-dash-danger hover:bg-dash-danger/10 rounded-xl transition-colors"
                                    >
                                        <Trash2 className="w-5 h-5" />
                                    </button>
                                </div>
                            ))}

                            <button
                                onClick={saveSettings}
                                className="w-full mt-8 flex items-center justify-center gap-2 bg-gold text-dash-bg py-4 rounded-2xl font-black uppercase hover:scale-[1.02] transition-all"
                            >
                                <Save className="w-5 h-5" /> Save Payment Settings
                            </button>
                        </div>
                    </section>
                )}
            </main>
        </div>
    );
}

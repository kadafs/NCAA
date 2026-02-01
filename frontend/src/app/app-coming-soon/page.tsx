"use client";

import React from "react";
import { motion } from "framer-motion";
import { Smartphone, Apple, Play, ArrowLeft, Bell } from "lucide-react";
import Link from "next/link";

/**
 * App Coming Soon Page
 * 
 * Displays information about upcoming mobile apps for iOS and Android
 * with notification signup for launch announcements
 */

export default function AppComingSoonPage() {
    return (
        <div className="min-h-screen bg-dash-bg text-dash-text-primary flex items-center justify-center px-4">
            {/* Background Effects */}
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute top-20 -right-40 w-96 h-96 bg-gold/5 rounded-full blur-3xl" />
                <div className="absolute -bottom-20 -left-40 w-96 h-96 bg-cyan/5 rounded-full blur-3xl" />
            </div>

            <div className="relative max-w-3xl w-full">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                    className="text-center"
                >
                    {/* Back Button */}
                    <Link
                        href="/"
                        className="inline-flex items-center gap-2 text-dash-text-muted hover:text-white transition-colors mb-8 text-sm font-bold uppercase tracking-widest"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back to Home
                    </Link>

                    {/* Icon */}
                    <motion.div
                        initial={{ scale: 0.8 }}
                        animate={{ scale: 1 }}
                        transition={{ duration: 0.5, delay: 0.2 }}
                        className="w-24 h-24 bg-gold rounded-3xl flex items-center justify-center mx-auto mb-8 shadow-[0_0_40px_rgba(251,191,36,0.3)]"
                    >
                        <Smartphone className="w-12 h-12 text-dash-bg" />
                    </motion.div>

                    {/* Badge */}
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-dash-card border border-dash-border rounded-full mb-6">
                        <Bell className="w-3 h-3 text-gold" />
                        <span className="text-[10px] font-bold text-dash-text-secondary uppercase tracking-widest">
                            Coming Soon
                        </span>
                    </div>

                    {/* Title */}
                    <h1 className="text-4xl md:text-6xl font-black text-white uppercase tracking-tighter mb-4">
                        Mobile Apps
                        <br />
                        <span className="text-gold">In Development</span>
                    </h1>

                    {/* Description */}
                    <p className="text-base md:text-lg text-dash-text-muted max-w-2xl mx-auto mb-12 leading-relaxed">
                        We're building native iOS and Android apps to bring you the world's most advanced basketball prediction engine on the go. Get real-time predictions, live game tracking, and advanced analytics right in your pocket.
                    </p>

                    {/* App Store Badges */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg mx-auto mb-12">
                        {/* iOS App Store */}
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.4 }}
                            className="bg-dash-card border border-dash-border rounded-2xl p-6 hover:border-gold/30 transition-colors"
                        >
                            <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center mb-4 mx-auto">
                                <Apple className="w-6 h-6 text-white" />
                            </div>
                            <h3 className="text-lg font-black text-white uppercase tracking-tight mb-2">
                                iOS App
                            </h3>
                            <p className="text-xs text-dash-text-muted mb-4">
                                Available on the App Store
                            </p>
                            <div className="px-4 py-2 bg-dash-bg-secondary border border-dash-border rounded-lg text-xs font-bold text-dash-text-muted uppercase">
                                Coming Soon
                            </div>
                        </motion.div>

                        {/* Android Play Store */}
                        <motion.div
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.5 }}
                            className="bg-dash-card border border-dash-border rounded-2xl p-6 hover:border-gold/30 transition-colors"
                        >
                            <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center mb-4 mx-auto">
                                <Play className="w-6 h-6 text-white" />
                            </div>
                            <h3 className="text-lg font-black text-white uppercase tracking-tight mb-2">
                                Android App
                            </h3>
                            <p className="text-xs text-dash-text-muted mb-4">
                                Available on Google Play
                            </p>
                            <div className="px-4 py-2 bg-dash-bg-secondary border border-dash-border rounded-lg text-xs font-bold text-dash-text-muted uppercase">
                                Coming Soon
                            </div>
                        </motion.div>
                    </div>

                    {/* Features Preview */}
                    <div className="bg-dash-card border border-dash-border rounded-3xl p-8 mb-8">
                        <h2 className="text-xl font-black text-white uppercase tracking-tight mb-6">
                            What to Expect
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
                            <div>
                                <div className="text-gold font-black text-lg mb-2">📊</div>
                                <h3 className="text-sm font-bold text-white uppercase mb-1">Live Predictions</h3>
                                <p className="text-xs text-dash-text-muted">
                                    Real-time game predictions with instant updates
                                </p>
                            </div>
                            <div>
                                <div className="text-gold font-black text-lg mb-2">🔔</div>
                                <h3 className="text-sm font-bold text-white uppercase mb-1">Push Notifications</h3>
                                <p className="text-xs text-dash-text-muted">
                                    Get alerts for high-value betting opportunities
                                </p>
                            </div>
                            <div>
                                <div className="text-gold font-black text-lg mb-2">📱</div>
                                <h3 className="text-sm font-bold text-white uppercase mb-1">Native Experience</h3>
                                <p className="text-xs text-dash-text-muted">
                                    Optimized performance for mobile devices
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* CTA */}
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link
                            href="/dashboard"
                            className="px-8 py-4 bg-gold text-dash-bg font-black uppercase tracking-widest rounded-2xl hover:scale-105 transition-transform shadow-[0_0_30px_rgba(251,191,36,0.3)]"
                        >
                            Use Web App Now
                        </Link>
                        <Link
                            href="/"
                            className="px-8 py-4 border border-dash-border text-white font-bold uppercase tracking-widest rounded-2xl hover:border-gold/30 transition-colors"
                        >
                            Back to Home
                        </Link>
                    </div>

                    {/* Footer Note */}
                    <p className="text-xs text-dash-text-muted mt-12">
                        Want to be notified when we launch? Follow us on social media or check back here for updates.
                    </p>
                </motion.div>
            </div>
        </div>
    );
}

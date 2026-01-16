"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Trophy,
  Activity,
  Target,
  Zap,
  Wallet,
  BarChart3,
  TrendingUp,
  Users,
  Search,
  ChevronRight,
  ShieldCheck,
  Lock,
  Crown,
  Copy,
  Check,
  LogOut,
  User
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useSession, signIn, signOut } from "next-auth/react";

// Initial fallback data (empty by default to force live fetch)
const GAMES: any[] = [];

const PLATFORM_STATS = [
  { label: "Active Projections", value: "32", icon: Target, color: "text-accent-blue" },
  { label: "Avg Precision", value: "84.2%", icon: Activity, color: "text-green-400" },
  { label: "Prop Accuracy", value: "71.5%", icon: Zap, color: "text-yellow-400" },
];

export default function Dashboard() {
  const { data: session, status } = useSession();
  const user = session?.user as any;
  const [showLogin, setShowLogin] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [showPayments, setShowPayments] = useState(false);
  const [paymentWallets, setPaymentWallets] = useState<{ type: string; address: string }[]>([]);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const [games, setGames] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    fetchWallets();
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");

    if (!loginUsername || !loginPassword) {
      setAuthError("Username and password are required");
      return;
    }

    if (isSignUp) {
      try {
        const res = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: loginUsername, password: loginPassword })
        });
        const data = await res.json();
        if (!res.ok) {
          setAuthError(data.error || "Registration failed");
          return;
        }
        await signIn("credentials", {
          username: loginUsername,
          password: loginPassword,
          redirect: false
        });
        setShowLogin(false);
      } catch (err) {
        setAuthError("An error occurred during registration");
      }
    } else {
      const result = await signIn("credentials", {
        username: loginUsername,
        password: loginPassword,
        redirect: false
      });

      if (result?.error) {
        setAuthError("Invalid username or password");
      } else {
        setShowLogin(false);
      }
    }
  };

  const handleLogout = () => {
    signOut();
  };

  const fetchWallets = async () => {
    try {
      const res = await fetch("/api/admin/settings");
      const data = await res.json();
      setPaymentWallets(data.wallets || []);
    } catch (err) { console.error(err); }
  };

  const fetchData = async () => {
    try {
      const res = await fetch("/api/predictions");
      const data = await res.json();
      if (data.games) setGames(data.games);
    } catch (err) {
      console.error("Fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  const copyAddress = (address: string, index: number) => {
    navigator.clipboard.writeText(address);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#050510] text-gray-200">
      {/* Navigation Bar */}
      <nav className="border-b border-white/5 bg-black/40 backdrop-blur-md sticky top-0 z-[50]">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="bg-accent-blue p-2 rounded-xl shadow-lg shadow-accent-blue/20 group-hover:scale-110 transition-all">
                <Trophy className="w-6 h-6 text-white" />
              </div>
              <span className="font-black text-xl tracking-tighter uppercase italic">NCAA<span className="text-accent-blue not-italic">HUB</span></span>
            </Link>

            <div className="h-6 w-px bg-white/10 hidden md:block" />

            <div className="hidden md:flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/5">
              <Link href="/" className="px-4 py-1.5 rounded-lg text-sm font-bold bg-accent-blue text-white shadow-lg shadow-accent-blue/20">Dashboard</Link>
              <Link href="/scoreboard" className="px-4 py-1.5 rounded-lg text-sm font-bold text-gray-500 hover:text-white transition-all">Scoreboard</Link>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {!user ? (
              <button
                onClick={() => setShowLogin(true)}
                className="px-6 py-2 bg-white text-black rounded-xl text-sm font-black hover:scale-105 transition-all shadow-lg"
              >
                SIGN IN
              </button>
            ) : (
              <div className="flex items-center gap-4">
                {user.isPro && (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-accent-blue/10 border border-accent-blue/20 rounded-full">
                    <Zap className="w-3.5 h-3.5 text-accent-blue fill-accent-blue" />
                    <span className="text-[10px] font-black uppercase text-accent-blue tracking-wider">PRO Member</span>
                  </div>
                )}
                <div className="flex items-center gap-3 pl-4 border-l border-white/10">
                  <Link href="/admin" className="p-2 text-accent-orange hover:bg-accent-orange/10 rounded-lg transition-all" title="Admin">
                    <Activity className="w-5 h-5" />
                  </Link>
                  <div className="text-right hidden sm:block">
                    <div className="text-[10px] font-black text-gray-500 uppercase tracking-widest leading-none">Logged In</div>
                    <div className="text-xs font-bold">{user.username}</div>
                  </div>
                  <button onClick={handleLogout} className="p-2 text-gray-500 hover:text-white transition-colors">
                    <LogOut className="w-5 h-5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Login Modal */}
      <AnimatePresence>
        {showLogin && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setShowLogin(false)}
              className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="relative glass w-full max-w-md p-8 rounded-3xl border border-white/5 space-y-6"
            >
              <div className="text-center space-y-2">
                <h3 className="text-2xl font-black">{isSignUp ? "Join the Elite" : "Welcome Back"}</h3>
                <p className="text-sm text-gray-500">{isSignUp ? "Create an account to access advanced metrics" : "Enter your credentials to access your dashboard"}</p>
              </div>

              {authError && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 text-xs font-bold text-center">
                  {authError}
                </div>
              )}

              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-bold text-gray-500 uppercase tracking-widest pl-1">Username</label>
                  <input
                    autoFocus
                    className="w-full bg-black/50 border border-white/10 rounded-2xl p-4 text-white placeholder:text-gray-700 focus:border-accent-blue/50 outline-none transition-all"
                    placeholder="Enter username..."
                    value={loginUsername}
                    onChange={(e) => setLoginUsername(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-bold text-gray-500 uppercase tracking-widest pl-1">Password</label>
                  <input
                    type="password"
                    className="w-full bg-black/50 border border-white/10 rounded-2xl p-4 text-white placeholder:text-gray-700 focus:border-accent-blue/50 outline-none transition-all"
                    placeholder="Enter password..."
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                  />
                </div>
                <button className="w-full bg-accent-blue text-white py-4 rounded-2xl font-black shadow-xl shadow-accent-blue/20 hover:scale-[1.02] active:scale-[0.98] transition-all uppercase">
                  {isSignUp ? "Sign Up" : "Continue"}
                </button>
              </form>

              <div className="text-center pt-2">
                <button
                  onClick={() => {
                    setIsSignUp(!isSignUp);
                    setAuthError("");
                  }}
                  className="text-xs font-bold text-gray-500 hover:text-white transition-colors uppercase tracking-widest"
                >
                  {isSignUp ? "Already have an account? Sign In" : "Don't have an account? Sign Up"}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Payment Modal */}
      <AnimatePresence>
        {showPayments && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setShowPayments(false)}
              className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.9, y: 20, opacity: 0 }} animate={{ scale: 1, y: 0, opacity: 1 }} exit={{ scale: 0.9, y: 20, opacity: 0 }}
              className="relative glass w-full max-w-lg overflow-hidden rounded-3xl border border-accent-orange/20"
            >
              <div className="p-8 space-y-6">
                <div className="flex justify-between items-start">
                  <div className="space-y-1">
                    <h3 className="text-2xl font-black text-accent-orange">Upgrade to Pro</h3>
                    <p className="text-xs font-bold text-gray-400">Manual verification required</p>
                  </div>
                  <div className="bg-accent-orange/10 p-3 rounded-2xl">
                    <Zap className="w-6 h-6 text-accent-orange" />
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="text-sm text-gray-300 leading-relaxed">
                    Send payment to any of the addresses below. After payment, the admin will manually upgrade your account <span className="text-accent-orange font-bold">({user?.username})</span>.
                  </div>

                  <div className="space-y-3">
                    {paymentWallets.length > 0 ? paymentWallets.map((wallet, i) => (
                      <div key={i} className="bg-black/40 border border-white/5 p-4 rounded-2xl space-y-2 group">
                        <div className="flex justify-between items-center">
                          <span className="text-[10px] font-black uppercase text-accent-orange tracking-widest">{wallet.type}</span>
                          <button
                            onClick={() => copyAddress(wallet.address, i)}
                            className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                          >
                            {copiedIndex === i ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-gray-500" />}
                          </button>
                        </div>
                        <div className="font-mono text-sm break-all text-white/90 selection:bg-accent-orange/30">{wallet.address}</div>
                      </div>
                    )) : (
                      <div className="p-8 text-center text-gray-500 font-bold border-2 border-dashed border-white/5 rounded-2xl">
                        No payment addresses set by admin.
                      </div>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => setShowPayments(false)}
                  className="w-full bg-white text-black py-4 rounded-2xl font-black hover:scale-[1.02] transition-all"
                >
                  I'VE MADE THE PAYMENT
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="flex-1 p-6 md:p-8 space-y-8 max-w-7xl mx-auto w-full">
        {/* Welcome Section */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-1 space-y-2">
            <h2 className="text-3xl font-bold tracking-tight">Command Center</h2>
            <p className="text-gray-400 text-sm">Advanced NCAA Basketball Intelligence</p>
          </div>
          <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-3 gap-4">
            {PLATFORM_STATS.map((stat, i) => (
              <div key={stat.label} className="glass p-4 rounded-2xl flex items-center gap-4 border border-white/5">
                <div className={cn("p-2.5 rounded-lg bg-gray-900/50", stat.color)}><stat.icon className="w-5 h-5" /></div>
                <div>
                  <div className="text-xs text-gray-500 font-medium">{stat.label}</div>
                  <div className="text-lg font-bold">
                    {stat.label === "Active Projections" ? (games.length > 0 ? games.length : stat.value) : stat.value}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Scoreboard */}
          <section className="lg:col-span-5 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-accent-blue" />
                Daily Slate
              </h3>
              <Link href="/scoreboard" className="text-xs font-bold text-accent-blue bg-accent-blue/10 px-3 py-1.5 rounded-xl hover:bg-accent-blue/20 transition-all flex items-center gap-1">
                FULL SCOREBOARD <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="space-y-4">
              {games.length > 0 ? games.map((game, i) => (
                <motion.div
                  key={game.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + (i * 0.1) }}
                  className="glass group p-5 rounded-2xl border border-white/5 transition-all hover:bg-white/[0.05] hover:border-accent-blue/30 cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-4">
                    <span className={cn(
                      "text-[10px] font-black px-2 py-0.5 rounded border",
                      game.status === "LIVE"
                        ? "bg-red-500/20 text-red-400 border-red-500/30 animate-pulse"
                        : "bg-gray-800 text-gray-400 border-gray-700"
                    )}>
                      {game.status}
                    </span>
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">Advanced Model v2.4</div>
                  </div>

                  <div className="flex justify-between items-center">
                    <div className="flex-1">
                      <div className="text-xl font-bold">{game.away}</div>
                      <div className="text-sm text-gray-500 font-medium">@ {game.home}</div>
                    </div>

                    <div className="flex items-center gap-4 text-right">
                      <div className="space-y-1">
                        <div className="text-xs text-gray-500 font-medium">PROJ SCORE</div>
                        <div className="text-lg font-mono font-black text-accent-blue">
                          {game.predictions?.advanced?.scoreA || 0} - {game.predictions?.advanced?.scoreH || 0}
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-accent-blue group-hover:translate-x-1 transition-all" />
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-white/5 grid grid-cols-2 gap-4">
                    <div className="text-center bg-gray-900/20 p-2 rounded-xl">
                      <div className="text-[10px] text-gray-500 font-bold uppercase">Spread</div>
                      <div className="text-sm font-bold">{game.predictions?.advanced?.spread > 0 ? `+${game.predictions?.advanced?.spread}` : game.predictions?.advanced?.spread || 0}</div>
                    </div>
                    <div className="text-center bg-gray-900/20 p-2 rounded-xl">
                      <div className="text-[10px] text-gray-500 font-bold uppercase">Total</div>
                      <div className="text-sm font-bold">{game.predictions?.advanced?.total || 0}</div>
                    </div>
                  </div>
                </motion.div>
              )) : (
                <div className="p-12 text-center text-gray-500 font-bold glass rounded-2xl border border-white/5">
                  {loading ? "FETCHING LIVE INTEL..." : "NO GAMES SCHEDULED FOR TODAY"}
                </div>
              )}
            </div>
          </section>

          {/* Right Column: Advanced Analytics */}
          <section className="lg:col-span-7 space-y-8">
            <div className="glass p-8 rounded-3xl min-h-[400px] flex flex-col relative overflow-hidden group">
              <div className="flex items-center justify-between mb-8">
                <div><h3 className="text-xl font-bold">Efficiency Landscape</h3><p className="text-gray-400 text-sm">Adjusted Offense vs. Defense PPP</p></div>
                <div className="p-3 bg-accent-blue/20 rounded-2xl"><TrendingUp className="text-accent-blue w-6 h-6" /></div>
              </div>
              <div className="flex-1 border-l-2 border-b-2 border-white/10 relative m-8">
                {[...Array(8)].map((_, i) => (
                  <div key={i} className="absolute w-4 h-4 rounded-full border-2 border-accent-blue bg-accent-blue/20 shadow-lg" style={{ left: `${20 + Math.random() * 70}%`, bottom: `${10 + Math.random() * 80}%` }} />
                ))}
              </div>

              {!user?.isPro && (
                <div className="absolute inset-0 bg-gray-900/60 backdrop-blur-sm flex flex-col items-center justify-center p-8 text-center z-10">
                  <div className="w-16 h-16 bg-accent-orange/20 rounded-full flex items-center justify-center mb-4 border border-accent-orange/30">
                    <Lock className="text-accent-orange w-8 h-8" />
                  </div>
                  <h4 className="text-xl font-bold mb-2">{!user ? "Identity Protected" : "Premium Content Restricted"}</h4>
                  <p className="text-sm text-gray-300 max-w-xs mb-6">
                    {!user ? "Sign in with your username to begin" : "Unlock real-time efficiency metrics and deep-level team intelligence."}
                  </p>
                  <button
                    onClick={() => !user ? setShowLogin(true) : setShowPayments(true)}
                    className="px-8 py-3 bg-accent-orange text-white rounded-xl font-bold shadow-lg shadow-accent-orange/30 hover:scale-105 transition-all"
                  >
                    {!user ? "Sign In to Access" : "Upgrade to Pro"}
                  </button>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="glass p-6 rounded-2xl space-y-4">
                <h4 className="font-bold flex items-center gap-2 text-gray-300"><Users className="w-4 h-4 text-accent-blue" />Top Player Value</h4>
                <div className="space-y-4">
                  {games.slice(0, 4).some(g => g.props?.away?.length || g.props?.home?.length) ? (
                    games.slice(0, 4).flatMap(g => [
                      ...(g.props?.away || []).map((p: any) => ({ ...p, team: g.away })),
                      ...(g.props?.home || []).map((p: any) => ({ ...p, team: g.home }))
                    ]).sort((a, b) => b.pts - a.pts).slice(0, 4).map((p, idx) => (
                      <motion.div
                        key={`${p.name}-${idx}`}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.5 + (idx * 0.1) }}
                        className="flex items-center justify-between p-3 bg-white/5 rounded-xl border border-white/5"
                      >
                        <div>
                          <div className="font-bold text-sm">{p.name}</div>
                          <div className="text-[10px] text-gray-500">{p.team}</div>
                        </div>
                        <div className="text-right font-bold text-accent-blue">
                          {p.pts} <span className="text-[10px] text-green-400 block">PROJ PTS</span>
                        </div>
                      </motion.div>
                    ))
                  ) : (
                    <div className="p-4 text-center text-xs text-gray-600 font-bold border border-white/5 rounded-xl border-dashed">
                      NO PLAYER INTEL FOR SELECTED GAMES
                    </div>
                  )}
                </div>
              </div>
              <div className="glass p-6 rounded-2xl flex flex-col items-center justify-center text-center space-y-3 relative overflow-hidden">
                <ShieldCheck className="w-10 h-10 text-accent-blue/50" />
                <h4 className="font-bold text-sm">Manual Verification</h4>
                <p className="text-[11px] text-gray-500">Payments are manually processed by admins to ensure maximum security and privacy.</p>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

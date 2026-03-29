import React, { useState, useMemo } from 'react';
import { flagFor } from '../utils';

export default function TeamTracker({ teamLeaderboard }) {
  const [minGames, setMinGames] = useState(3);
  const [sortBy, setSortBy] = useState('hitRate'); // 'hitRate' | 'mae' | 'games'

  const filteredTeams = useMemo(() => {
    if (!teamLeaderboard || teamLeaderboard.length === 0) return [];
    
    // Filter out teams that don't meet the minimum games threshold
    const filtered = teamLeaderboard.filter(t => (t.graded_totals || 0) >= minGames);
    
    // Sort logic
    filtered.sort((a, b) => {
      const gA = a.graded_totals || 0;
      const gB = b.graded_totals || 0;
      
      if (sortBy === 'games') {
        return gB - gA;
      }
      
      if (sortBy === 'mae') {
        const mA = a.mae != null ? a.mae : 999;
        const mB = b.mae != null ? b.mae : 999;
        if (mA !== mB) return mA - mB; // Ascending (lower error is better)
        return (b.outcome_hit_rate || 0) - (a.outcome_hit_rate || 0);
      }
      
      if (sortBy === 'volatility') {
        const vA = a.volatility_index != null ? a.volatility_index : 999;
        const vB = b.volatility_index != null ? b.volatility_index : 999;
        if (vA !== vB) return vA - vB; // Ascending (lower standard deviation is safer)
        return (b.outcome_hit_rate || 0) - (a.outcome_hit_rate || 0);
      }
      
      // Default: hitRate
      const hrA = a.outcome_hit_rate || 0;
      const hrB = b.outcome_hit_rate || 0;
      if (hrB !== hrA) return hrB - hrA; // Descending (higher hit rate better)
      return (a.mae ?? 999) - (b.mae ?? 999);
    });
    
    return filtered;
  }, [teamLeaderboard, minGames, sortBy]);

  if (!teamLeaderboard || teamLeaderboard.length === 0) {
    return <div className="empty-state"><div className="icon">📭</div><p>No team tracking data available for the current epoch.</p></div>;
  }

  return (
    <div className="team-tracker-container" style={{ padding: '0 16px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
      
      {/* Controls */}
      <div style={{ display: 'flex', gap: '16px', margin: '20px 0', alignItems: 'center', background: '#fff', padding: '12px 20px', borderRadius: 8, border: '1px solid #e2e8f0', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#475569' }}>Min Games:</span>
          <select 
            value={minGames} 
            onChange={e => setMinGames(Number(e.target.value))}
            style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13, fontWeight: 600, background: '#f8fafc', color: '#1e293b', outline: 'none' }}
          >
            <option value="1">1+ Games</option>
            <option value="3">3+ Games</option>
            <option value="5">5+ Games</option>
            <option value="10">10+ Games</option>
          </select>
        </div>
        
        <div style={{ width: '1px', height: '24px', background: '#e2e8f0' }}></div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#475569' }}>Sort Priority:</span>
          <select 
            value={sortBy} 
            onChange={e => setSortBy(e.target.value)}
            style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13, fontWeight: 600, background: '#f8fafc', color: '#1e293b', outline: 'none' }}
          >
            <option value="hitRate">1. Model Hit Rate (%)</option>
            <option value="mae">1. Lowest Point Error (MAE)</option>
            <option value="volatility">1. Lowest Volatility (Most Consistent)</option>
            <option value="games">1. Highest Sample Size</option>
          </select>
        </div>
        
        <div style={{ marginLeft: 'auto', fontSize: 13, color: '#64748b', fontWeight: 500 }}>
          Tracking <strong>{filteredTeams.length}</strong> Qualified Teams
        </div>
      </div>

      {/* Table */}
      <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, overflow: 'hidden', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 1.5fr) 1fr 1fr 1fr 1fr 1fr 1fr 1fr', background: '#f8fafc', padding: '14px 20px', borderBottom: '1px solid #e2e8f0', fontSize: 12, fontWeight: 800, color: '#64748b', letterSpacing: '0.5px' }}>
          <div>TEAM</div>
          <div style={{ textAlign: 'center' }}>RECORD</div>
          <div style={{ textAlign: 'center' }}>HIT RATE</div>
          <div style={{ textAlign: 'center' }}>AVG MAE</div>
          <div style={{ textAlign: 'center' }}>± BIAS</div>
          <div style={{ textAlign: 'center' }}>VOLATILITY σ</div>
          <div style={{ textAlign: 'center' }}>🎯 BULLSEYE</div>
          <div style={{ textAlign: 'center' }}>🔴 BUST</div>
        </div>
        
        {filteredTeams.length === 0 ? (
          <div style={{ padding: '60px 20px', textAlign: 'center', color: '#94a3b8', fontSize: 15, fontWeight: 500 }}>
            No teams meet the minimum game requirement.
          </div>
        ) : (
          filteredTeams.map((t, idx) => {
            const hr = t.outcome_hit_rate || 0;
            const isCashCow = hr >= 70 && (t.mae || 999) <= 12 && (t.graded_totals || 0) >= 2;
            const isProblem = (t.mae || 0) >= 16 || Math.abs(t.avg_signed_delta || 0) >= 10;
            
            return (
              <div key={`${t.name}-${idx}`} style={{ 
                display: 'grid', 
                gridTemplateColumns: 'minmax(200px, 1.5fr) 1fr 1fr 1fr 1fr 1fr 1fr 1fr', 
                padding: '16px 20px', 
                borderBottom: '1px solid #f1f5f9',
                background: isCashCow ? '#f0fdf4' : isProblem ? '#fef2f2' : '#ffffff',
                alignItems: 'center',
                transition: 'background 0.2s ease'
              }}>
                {/* Team Info */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 15, fontWeight: 700, color: isCashCow ? '#166534' : isProblem ? '#991b1b' : '#1e293b' }}>
                    {isCashCow && <span title="Cash Cow: High Hit Rate / Low Volatility" style={{ fontSize: 14 }}>⭐</span>}
                    {isProblem && <span title="Red Flag: High MAE or Extreme Bias" style={{ fontSize: 14 }}>⚠️</span>}
                    {t.name}
                  </div>
                  <div style={{ fontSize: 11, color: isCashCow ? '#15803d' : isProblem ? '#b91c1c' : '#94a3b8', fontWeight: 600 }}>
                    {t.league} <span style={{ opacity: 0.6, fontWeight: 400 }}>({t.graded_totals || 0} games tracked)</span>
                  </div>
                </div>

                {/* Record */}
                <div style={{ textAlign: 'center', fontSize: 14, fontWeight: 700, color: '#334155' }}>
                  <span style={{ color: '#16a34a' }}>{t.outcome_w || 0}W</span> - <span style={{ color: '#dc2626' }}>{t.outcome_l || 0}L</span>
                </div>

                {/* Hit Rate */}
                <div style={{ textAlign: 'center' }}>
                  <span style={{ 
                    display: 'inline-block',
                    padding: '4px 10px',
                    background: hr >= 60 ? '#16a34a' : hr >= 45 ? '#d97706' : '#dc2626',
                    color: '#fff',
                    borderRadius: 12,
                    fontSize: 13,
                    fontWeight: 700
                  }}>
                    {hr.toFixed(1)}%
                  </span>
                </div>

                {/* MAE */}
                <div style={{ textAlign: 'center', fontSize: 14, fontWeight: 700, color: (t.mae || 999) <= 10 ? '#16a34a' : (t.mae || 0) >= 16 ? '#dc2626' : '#64748b' }}>
                  {t.mae != null ? t.mae.toFixed(1) : '—'}
                </div>

                {/* Signed Bias */}
                <div style={{ textAlign: 'center', fontSize: 14, fontWeight: 700, color: (t.avg_signed_delta || 0) > 4 ? '#b91c1c' : (t.avg_signed_delta || 0) < -4 ? '#15803d' : '#64748b' }} title={(t.avg_signed_delta || 0) > 0 ? "Consistently goes OVER" : "Consistently goes UNDER"}>
                  {t.avg_signed_delta != null ? `${t.avg_signed_delta > 0 ? '+' : ''}${t.avg_signed_delta.toFixed(1)}` : '—'}
                </div>

                {/* Volatility */}
                <div style={{ textAlign: 'center', fontSize: 15, fontWeight: 800, color: (t.volatility_index || 999) > 14.0 ? '#ef4444' : (t.volatility_index || 999) < 9.0 ? '#16a34a' : '#64748b' }} title="Standard Deviation of localized errors">
                  {t.volatility_index != null ? t.volatility_index.toFixed(2) : '—'}
                </div>

                {/* Bullseyes */}
                <div style={{ textAlign: 'center', fontSize: 14, fontWeight: 700, color: '#d946ef' }}>
                  {(t.bullseyes || 0) > 0 ? `🎯 ×${t.bullseyes}` : '-'}
                </div>

                {/* Busts */}
                <div style={{ textAlign: 'center', fontSize: 14, fontWeight: 700, color: '#dc2626' }}>
                  {(t.busts || 0) > 0 ? `🔴 ×${t.busts}` : '-'}
                </div>

              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

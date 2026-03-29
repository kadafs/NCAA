import { flagFor } from '../utils'
import MatchRow from './MatchRow'
import BasketballRow from './BasketballRow'

export default function LeagueGroup({ group, sport }) {
  const { league, country, games, stats } = group
  const isFootball = sport === 'football'
  // Does any game today in this league have an ADV prediction?
  const leagueHasAdv = !isFootball && games.some(g => g.predictions?.adv)

  return (
    <div>
      {/* League header */}
      <div className={`league-header ${sport}`}>
        <div className="league-name" style={{ gridColumn: '1 / 3', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span>{flagFor(country)}</span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            {(country || '').toUpperCase()} — {(league || '').toUpperCase()}
            {!isFootball && games && games.length > 0 && games[0].mbet_threshold && (
              <span style={{ fontSize: 10, color: '#94a3b8', fontWeight: 800, padding: '2px 6px', background: '#f1f5f9', borderRadius: 4 }}>
                MBET {games[0].mbet_threshold}
              </span>
            )}
          </span>
          {isFootball && stats && (stats.btts_plays > 0) && (
            <span style={{ 
              fontSize: 11, 
              padding: '2px 8px', 
              background: stats.btts_roi > 0 ? '#f0fdf4' : '#fef2f2', 
              color: stats.btts_roi > 0 ? '#15803d' : '#b91c1c',
              borderRadius: 4, 
              whiteSpace: 'nowrap',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              border: `1px solid ${stats.btts_roi > 0 ? '#bbf7d0' : '#fecaca'}`
            }}>
              BTTS: {stats.btts_roi > 0 ? '+' : ''}{stats.btts_roi} U ({stats.btts_hit_rate}%)
            </span>
          )}
          {isFootball && stats && (stats.graded_totals > 0) && (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '2px 6px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 4 }}>
              <span style={{ fontSize: 10, fontWeight: 800, color: '#1d4ed8' }}>xG</span>
              {stats.mae !== null && (
                <span style={{ fontSize: 11, fontWeight: 700, color: '#0369a1', whiteSpace: 'nowrap', cursor: 'default' }}>
                  MAE {stats.mae.toFixed(2)} <span style={{ fontWeight: 400, fontSize: 10, color: '#94a3b8' }}>({stats.graded_totals}g)</span>
                </span>
              )}
              {stats.avg_signed_delta !== null && (
                <span title={stats.avg_signed_delta > 0 ? "Model undershoots, games go OVER" : "Model overshoots, games go UNDER"} style={{ fontSize: 11, fontWeight: 600, color: stats.avg_signed_delta > 0 ? '#b91c1c' : stats.avg_signed_delta < 0 ? '#15803d' : '#475569', whiteSpace: 'nowrap', borderLeft: '1px solid #bae6fd', paddingLeft: 6, cursor: 'help' }}>
                  ±Δ {stats.avg_signed_delta > 0 ? '+' : ''}{stats.avg_signed_delta.toFixed(2)}
                </span>
              )}
            </div>
          )}
          {!isFootball && stats && (() => {
            const renderStats = (modelName, mStats) => {
              if (!mStats || mStats.graded_totals === 0) return null
              const mape = mStats.mape ?? 0
              const mae  = mStats.mae ?? null
              const signed = mStats.avg_signed_delta ?? null
              const isAdv    = modelName === 'ADV'
              const bg       = isAdv ? '#eff6ff' : '#f0f9ff'
              const color    = isAdv ? '#1d4ed8' : '#0369a1'
              const border   = isAdv ? '#bfdbfe' : '#bae6fd'
              const mapeColor = mape <= 6.5 ? '#15803d' : mape <= 10.0 ? '#d97706' : '#b91c1c'
              
              const tierTooltip = [
                mStats.bullseyes  > 0 ? `🎯×${mStats.bullseyes}`  : null,
                mStats.excellents > 0 ? `🟢×${mStats.excellents}` : null,
                mStats.solids     > 0 ? `🟡×${mStats.solids}`     : null,
                mStats.misses     > 0 ? `🟠×${mStats.misses}`     : null,
                mStats.busts      > 0 ? `🔴×${mStats.busts}`      : null,
              ].filter(Boolean).join('  ')

              return (
                <div key={modelName} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '2px 6px', background: bg, border: `1px solid ${border}`, borderRadius: 4 }}>
                  <span style={{ fontSize: 10, fontWeight: 800, color: color }}>{modelName}</span>
                  <span title={tierTooltip || undefined} style={{ fontSize: 11, fontWeight: 700, color: mapeColor, whiteSpace: 'nowrap', cursor: 'default' }}>
                    MAPE {mape.toFixed(1)}% <span style={{ fontWeight: 400, fontSize: 10, color: '#94a3b8' }}>({mStats.graded_totals}g)</span>
                  </span>
                  {mae !== null && (
                    <span style={{ fontSize: 11, fontWeight: 600, color: '#475569', whiteSpace: 'nowrap', borderLeft: `1px solid ${border}`, paddingLeft: 6 }}>
                      MAE {mae.toFixed(1)}
                    </span>
                  )}
                  {signed !== null && (
                    <span title={signed > 0 ? "Model undershoots, game goes OVER" : "Model overshoots, game goes UNDER"} style={{ fontSize: 11, fontWeight: 600, color: signed > 0 ? '#b91c1c' : signed < 0 ? '#15803d' : '#475569', whiteSpace: 'nowrap', borderLeft: `1px solid ${border}`, paddingLeft: 6, cursor: 'help' }}>
                      ±Δ {signed > 0 ? '+' : ''}{signed.toFixed(1)}
                    </span>
                  )}
                  {mStats.volatility_index !== null && mStats.volatility_index !== undefined && (
                    <span title="Volatility (Standard Deviation). <9.0 is highly consistent!" style={{ fontSize: 11, fontWeight: 800, color: mStats.volatility_index > 14.0 ? '#ef4444' : mStats.volatility_index < 9.0 ? '#16a34a' : '#64748b', whiteSpace: 'nowrap', borderLeft: `1px solid ${border}`, paddingLeft: 6, cursor: 'help' }}>
                      σ {mStats.volatility_index.toFixed(1)}
                    </span>
                  )}
                </div>
              )
            }

            return (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {stats.adv && stats.adv.graded_totals > 0
                  ? renderStats('ADV', stats.adv)
                  : (stats.srs && renderStats('SRS', stats.srs))
                }
              </div>
            )
          })()}

        </div>
        
        {isFootball ? (
          <>
            <div className="col-label" style={{ textAlign: 'center' }}>TIP</div>
            <div className="chevron-spacer" /> {/* chevron spacer */}
            <div className="col-label" style={{ textAlign: 'center' }}>1X2</div>
            <div className="col-label" style={{ textAlign: 'center' }}>BTTS</div>
            <div className="col-label match-xg" style={{ textAlign: 'center' }}>xG</div>
            <div className="col-label" style={{ textAlign: 'center' }}>BTTS PLAY</div>
          </>
        ) : (
          <>
            <div className="col-label" style={{ textAlign: 'center' }}>TIP</div>
            <div className="chevron-spacer" /> {/* chevron spacer */}
            <div className="col-label" style={{ textAlign: 'center' }}>12</div>
            <div className="col-label" style={{ textAlign: 'center' }}>MODEL</div>
            <div className="col-label match-xpts" style={{ textAlign: 'center' }}>xPTS</div>
          </>
        )}
      </div>

      {/* Match rows */}
      {games.map((g, i) => (
        isFootball 
          ? <MatchRow key={`${g.home_team}-${g.away_team}-${i}`} game={g} />
          : <BasketballRow key={`${g.home_team}-${g.away_team}-${i}`} game={g} leagueHasAdv={leagueHasAdv} />
      ))}
    </div>
  )
}


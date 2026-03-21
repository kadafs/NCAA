import { flagFor } from '../utils'
import MatchRow from './MatchRow'
import BasketballRow from './BasketballRow'

export default function LeagueGroup({ group, sport }) {
  const { league, country, games, stats } = group
  const isFootball = sport === 'football'

  return (
    <div>
      {/* League header — 8-col grid for football, custom for basketball */}
      <div 
        className={`league-header ${!isFootball ? 'bball-grid' : ''}`}
        style={!isFootball ? { gridTemplateColumns: '72px 1fr 44px 22px 116px 80px 100px' } : undefined}
      >
        <div className="league-name" style={{ gridColumn: '1 / 3', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span>{flagFor(country)}</span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            {(country || '').toUpperCase()} — {(league || '').toUpperCase()}
            {!isFootball && games && games.length > 0 && games[0].mbet_threshold && (
              <span style={{ fontSize: 10, color: '#94a3b8', fontWeight: 800, padding: '2px 6px', background: '#f1f5f9', borderRadius: 4 }}>
                MBET {games[0].mbet_threshold}
              </span>
            )}
            {!isFootball && games && games.length > 0 && games[0].model_architecture && (
              <span style={{ fontSize: 10, color: '#94a3b8', fontWeight: 800, padding: '2px 6px', background: '#f1f5f9', border: '1px solid #e2e8f0', borderRadius: 4 }}>
                {games[0].model_architecture.replace(/\[|\]/g, '').trim()}
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
          {!isFootball && stats && stats.graded_totals > 0 && (() => {
            const mape = stats.mape ?? 0
            const mapeColor  = mape <= 6.5 ? '#15803d' : mape <= 10.0 ? '#d97706' : '#b91c1c'
            const mapeBg     = mape <= 6.5 ? '#f0fdf4' : mape <= 10.0 ? '#fffbeb' : '#fef2f2'
            const mapeBorder = mape <= 6.5 ? '#bbf7d0' : mape <= 10.0 ? '#fde68a' : '#fecaca'
            const tierTooltip = [
              stats.bullseyes  > 0 ? `🎯×${stats.bullseyes}`  : null,
              stats.excellents > 0 ? `🟢×${stats.excellents}` : null,
              stats.solids     > 0 ? `🟡×${stats.solids}`     : null,
              stats.misses     > 0 ? `🟠×${stats.misses}`     : null,
              stats.busts      > 0 ? `🔴×${stats.busts}`      : null,
            ].filter(Boolean).join('  ')
            return (
              <span title={tierTooltip || undefined} style={{
                fontSize: 11, padding: '2px 8px', background: mapeBg, color: mapeColor,
                borderRadius: 4, whiteSpace: 'nowrap', fontWeight: 700,
                display: 'inline-flex', alignItems: 'center', gap: 4,
                border: `1px solid ${mapeBorder}`, cursor: 'default',
              }}>
                MAPE {mape.toFixed(1)}%
                <span style={{ fontWeight: 400, fontSize: 10, color: '#94a3b8' }}>({stats.graded_totals}g)</span>
              </span>
            )
          })()}
          {stats && (stats.outcome_w + stats.outcome_l > 0) && (
            <span style={{ 
              fontSize: 11, 
              padding: '2px 8px', 
              background: '#eef2ff', 
              color: '#4338ca',
              borderRadius: 4, 
              whiteSpace: 'nowrap',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              border: '1px solid #e0e7ff'
            }}>
              1X2: {stats.outcome_w}W-{stats.outcome_l}L ({stats.outcome_hit_rate}%)
            </span>
          )}
        </div>
        
        {isFootball ? (
          <>
            <div className="col-label" style={{ textAlign: 'center' }}>TIP</div>
            <div /> {/* chevron spacer */}
            <div className="col-label" style={{ textAlign: 'center' }}>1X2</div>
            <div className="col-label" style={{ textAlign: 'center' }}>BTTS</div>
            <div className="col-label" style={{ textAlign: 'center' }}>xG</div>
            <div className="col-label" style={{ textAlign: 'center' }}>BTTS PLAY</div>
          </>
        ) : (
          <>
            <div className="col-label" style={{ textAlign: 'center' }}>TIP</div>
            <div /> {/* chevron spacer */}
            <div className="col-label" style={{ textAlign: 'center' }}>12</div>
            <div className="col-label" style={{ textAlign: 'center' }}>MODEL</div>
            <div className="col-label" style={{ textAlign: 'center' }}>xPTS</div>
          </>
        )}
      </div>

      {/* Match rows */}
      {games.map((g, i) => (
        isFootball 
          ? <MatchRow key={`${g.home_team}-${g.away_team}-${i}`} game={g} />
          : <BasketballRow key={`${g.home_team}-${g.away_team}-${i}`} game={g} />
      ))}
    </div>
  )
}

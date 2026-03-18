import { flagFor } from '../utils'
import MatchRow from './MatchRow'

export default function LeagueGroup({ group }) {
  const { league, country, games, stats } = group
  return (
    <div>
      {/* League header — 8-col grid: time | teams | tip | chev | 1x2 | btts | xg | decision */}
      <div className="league-header">
        <div className="league-name" style={{ gridColumn: '1 / 3', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span>{flagFor(country)}</span>
          <span>{country.toUpperCase()} — {league.toUpperCase()}</span>
          {stats && (stats.btts_plays > 0) && (
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
        <div className="col-label" style={{ textAlign: 'center' }}>TIP</div>
        <div /> {/* chevron spacer */}
        <div className="col-label" style={{ textAlign: 'center' }}>1X2</div>
        <div className="col-label" style={{ textAlign: 'center' }}>BTTS</div>
        <div className="col-label" style={{ textAlign: 'center' }}>xG</div>
        <div className="col-label" style={{ textAlign: 'center' }}>BTTS PLAY</div>
      </div>

      {/* Match rows */}
      {games.map((g, i) => (
        <MatchRow key={`${g.home_team}-${g.away_team}-${i}`} game={g} />
      ))}
    </div>
  )
}

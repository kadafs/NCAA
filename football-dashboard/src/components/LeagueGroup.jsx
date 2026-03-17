import { flagFor } from '../utils'
import MatchRow from './MatchRow'

export default function LeagueGroup({ group }) {
  const { league, country, games } = group
  return (
    <div>
      {/* League header — 8-col grid: time | teams | tip | chev | 1x2 | btts | xg | decision */}
      <div className="league-header">
        <div className="league-name" style={{ gridColumn: '1 / 3' }}>
          <span>{flagFor(country)}</span>
          <span>{country.toUpperCase()} — {league.toUpperCase()}</span>
        </div>
        <div className="col-label" style={{ textAlign: 'center' }}>TIP</div>
        <div /> {/* chevron spacer */}
        <div className="col-label" style={{ textAlign: 'center' }}>1X2</div>
        <div className="col-label" style={{ textAlign: 'center' }}>BTTS</div>
        <div className="col-label" style={{ textAlign: 'center' }}>xG</div>
        <div className="col-label" style={{ textAlign: 'center' }}>DECISION</div>
      </div>

      {/* Match rows */}
      {games.map((g, i) => (
        <MatchRow key={`${g.home_team}-${g.away_team}-${i}`} game={g} />
      ))}
    </div>
  )
}

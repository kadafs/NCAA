import { flagFor } from '../utils'
import MatchRow from './MatchRow'

export default function LeagueGroup({ group }) {
  const { league, country, games } = group
  return (
    <div>
      {/* League header */}
      <div className="league-header">
        <div className="league-name" style={{ gridColumn: '1 / 4' }}>
          <span>{flagFor(country)}</span>
          <span>{country.toUpperCase()} — {league.toUpperCase()}</span>
        </div>
        <div className="col-label">TIP</div>
        <div className="col-label" style={{ gridColumn: '5' }}>1X2</div>
        <div className="col-label">BTTS</div>
        <div className="col-label">xG</div>
        <div className="col-label">Decision</div>
      </div>

      {/* Match rows */}
      {games.map((g, i) => (
        <MatchRow key={`${g.home_team}-${g.away_team}-${i}`} game={g} />
      ))}
    </div>
  )
}

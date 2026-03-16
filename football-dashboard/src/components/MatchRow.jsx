import { useState } from 'react'

function tipFor(predicted_result) {
  if (predicted_result === 'HOME') return { label: '1', cls: 'home' }
  if (predicted_result === 'DRAW') return { label: 'X', cls: 'draw' }
  if (predicted_result === 'AWAY') return { label: '2', cls: 'away' }
  return { label: '?', cls: '' }
}

function decisionClass(decision) {
  if (decision === 'PLAY YES') return 'yes'
  if (decision === 'PLAY NO')  return 'no'
  return 'pass'
}

function fmt(v, digits = 0) {
  if (v == null) return '—'
  return typeof v === 'number' ? v.toFixed(digits) : v
}

function kickoffTime(game) {
  // timestamp is ISO string from ET; parse to local
  if (!game.timestamp) return '—'
  try {
    const d = new Date(game.timestamp)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch { return '—' }
}

export default function MatchRow({ game }) {
  const [open, setOpen] = useState(false)
  const tip = tipFor(game.predicted_result)
  const dClass = decisionClass(game.btts_decision)

  return (
    <>
      <div
        className={`match-row ${open ? 'expanded' : ''}`}
        onClick={() => setOpen(o => !o)}
      >
        {/* Time */}
        <div className="match-time">{kickoffTime(game)}</div>

        {/* Teams — home vs away */}
        <div className="teams-cell">
          <span className="team-name home" title={game.home_team}>
            {game.home_team}
          </span>
          <span className="vs-sep">vs</span>
          <span className="team-name away" title={game.away_team}>
            {game.away_team}
          </span>
        </div>

        {/* TIP badge */}
        <div>
          <div className={`tip-badge ${tip.cls}`}>{tip.label}</div>
        </div>

        {/* Chevron expand */}
        <div style={{ textAlign: 'center', color: '#9ca3af', fontSize: 11 }}>
          {open ? '▲' : '▼'}
        </div>

        {/* 1X2 boxes */}
        <div className="stat-group">
          <div className="stat-box home-win">
            {fmt(game.home_win_prob)}<sub>%</sub>
          </div>
          <div className="stat-box draw-box">
            {fmt(game.draw_prob_1x2)}<sub>%</sub>
          </div>
          <div className="stat-box away-win">
            {fmt(game.away_win_prob)}<sub>%</sub>
          </div>
        </div>

        {/* BTTS box */}
        <div>
          <div className="btts-box">
            {fmt(game.btts_prob)}<sub>%</sub>
          </div>
        </div>

        {/* xG box */}
        <div>
          <div className="xg-box">
            {fmt(game.xg_home, 1)} – {fmt(game.xg_away, 1)}<sub> xG</sub>
          </div>
        </div>

        {/* Decision badge */}
        <div>
          <span className={`decision-badge ${dClass}`}>
            {game.btts_decision || 'PASS'}
          </span>
        </div>
      </div>

      {/* Expanded detail panel */}
      {open && (
        <div className="match-detail">
          <div className="detail-item">
            <span className="detail-label">Home win odds</span>
            <span className="detail-value">{fmt(game.home_win_odds, 2)}x</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Draw odds</span>
            <span className="detail-value">{fmt(game.draw_odds, 2)}x</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Away win odds</span>
            <span className="detail-value">{fmt(game.away_win_odds, 2)}x</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">BTTS edge</span>
            <span className="detail-value"
              style={{ color: game.btts_edge >= 0 ? '#16a34a' : '#dc2626' }}>
              {game.btts_edge != null ? (game.btts_edge >= 0 ? '+' : '') + fmt(game.btts_edge, 1) + '%' : '—'}
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Draw prob (Poisson)</span>
            <span className="detail-value">{fmt(game.draw_prob, 1)}%</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Draw fair odds</span>
            <span className="detail-value">{fmt(game.draw_fair_odds, 2)}x</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">xG total</span>
            <span className="detail-value">{fmt(game.xg_total, 2)}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">BTTS confidence</span>
            <span className="detail-value">{game.btts_confidence || '—'}</span>
          </div>
          {game.actual_result && (
            <div className="detail-item">
              <span className="detail-label">Actual result</span>
              <span className="detail-value"
                style={{ color: game.actual_result === game.predicted_result ? '#16a34a' : '#dc2626' }}>
                {game.actual_result}
                {game.actual_result === game.predicted_result ? ' ✓' : ' ✗'}
              </span>
            </div>
          )}
          {game.actual_home_goals != null && (
            <div className="detail-item">
              <span className="detail-label">Final score</span>
              <span className="detail-value">
                {game.home_team} {game.actual_home_goals} – {game.actual_away_goals} {game.away_team}
              </span>
            </div>
          )}
        </div>
      )}
    </>
  )
}

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
  if (decision === '[STRONG] PLAY NO') return 'strong-no'
  return 'pass'
}

function fmt(v, digits = 0) {
  if (v == null) return '—'
  return typeof v === 'number' ? v.toFixed(digits) : v
}

function kickoffTime(game) {
  if (!game.timestamp) return '—'
  try { return new Date(game.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
  catch { return '—' }
}

// ─── Grade logic ─────────────────────────────────────────────
function outcomeGrade(game) {
  if (!game.actual_result) return null           // not graded yet
  return game.predicted_result === game.actual_result ? 'WIN' : 'LOSS'
}

function bttsGrade(game) {
  if (game.actual_btts == null) return null
  if (game.btts_decision === 'PLAY YES') return game.actual_btts ? 'WIN' : 'LOSS'
  if (game.btts_decision === 'PLAY NO' || game.btts_decision === '[STRONG] PLAY NO')  return game.actual_btts ? 'LOSS' : 'WIN'
  return null // PASS
}

function GradeIcon({ grade }) {
  if (grade === null)   return <span className="grade-pending" title="Pending">⏳</span>
  if (grade === 'WIN')  return <span className="grade-win"     title="Correct">✅</span>
  if (grade === 'LOSS') return <span className="grade-loss"    title="Wrong">❌</span>
  return null
}


export default function MatchRow({ game }) {
  const [open, setOpen] = useState(false)
  const tip    = tipFor(game.predicted_result)
  const dClass = decisionClass(game.btts_decision)
  const oGrade = outcomeGrade(game)
  const bGrade = bttsGrade(game)
  const isGraded = game.actual_result != null

  return (
    <>
      <div
        className={`match-row ${open ? 'expanded' : ''} ${isGraded ? 'graded' : ''}`}
        onClick={() => setOpen(o => !o)}
      >
        {/* Time */}
        <div className="match-time">{kickoffTime(game)}</div>

        {/* Teams */}
        <div className="teams-cell">
          <span className="team-name home" title={game.home_team}>{game.home_team}</span>
          {isGraded
            ? <span className="actual-score">{game.actual_home_goals} – {game.actual_away_goals}</span>
            : <span className="vs-sep">vs</span>
          }
          <span className="team-name away" title={game.away_team}>{game.away_team}</span>
        </div>

        {/* TIP + grade */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <div className={`tip-badge ${tip.cls}`}>{tip.label}</div>
          <GradeIcon grade={oGrade} />
        </div>

        {/* Expand chevron */}
        <div style={{ textAlign: 'center', color: '#9ca3af', fontSize: 11 }}>{open ? '▲' : '▼'}</div>

        {/* 1X2 boxes */}
        <div className="stat-group">
          <div className="stat-box home-win">{fmt(game.home_win_prob)}<sub>%</sub></div>
          <div className="stat-box draw-box">{fmt(game.draw_prob_1x2)}<sub>%</sub></div>
          <div className="stat-box away-win">{fmt(game.away_win_prob)}<sub>%</sub></div>
        </div>

        {/* BTTS box + grade */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <div className="btts-box">{fmt(game.btts_prob)}<sub>%</sub></div>
          <GradeIcon grade={bGrade} />
        </div>

        {/* xG box */}
        <div>
          <div className="xg-box">{fmt(game.xg_home, 1)} – {fmt(game.xg_away, 1)}<sub> xG</sub></div>
        </div>

        {/* Decision badge */}
        <div>
          <span className={`decision-badge ${dClass}`}>{game.btts_decision || 'PASS'}</span>
        </div>
      </div>

      {/* Expanded detail */}
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
            <span className="detail-value" style={{ color: game.btts_edge >= 0 ? '#16a34a' : '#dc2626' }}>
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
          {isGraded && (
            <>
              <div className="detail-item">
                <span className="detail-label">Final score</span>
                <span className="detail-value" style={{ fontWeight: 700 }}>
                  {game.home_team} {game.actual_home_goals} – {game.actual_away_goals} {game.away_team}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">1X2 result</span>
                <span className="detail-value" style={{ color: oGrade === 'WIN' ? '#16a34a' : '#dc2626' }}>
                  {game.actual_result}  {oGrade === 'WIN' ? '✅' : '❌'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">BTTS result</span>
                <span className="detail-value" style={{ color: bGrade === 'WIN' ? '#16a34a' : bGrade === 'LOSS' ? '#dc2626' : '#6b7280' }}>
                  {game.actual_btts ? 'Yes' : 'No'}  {bGrade === 'WIN' ? '✅' : bGrade === 'LOSS' ? '❌' : '➖'}
                </span>
              </div>
            </>
          )}
        </div>
      )}
    </>
  )
}

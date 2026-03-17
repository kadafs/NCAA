export default function Navigator({ dates, selected, onSelect }) {
  if (!dates.length) return null

  // dates is now an array of { date, total, graded, graded_count, grade_summary }
  const selectedIdx = dates.findIndex(d => d.date === selected)
  const start   = Math.max(0, selectedIdx - 3)
  const visible = dates.slice(start, start + 7)

  const todayStr = new Date().toISOString().slice(0, 10)

  return (
    <div className="navigator">
      <div className="navigator-label">Select date</div>
      <div className="date-tabs">
        {visible.map(d => {
          const isToday   = d.date === todayStr
          const isActive  = d.date === selected
          return (
            <button
              key={d.date}
              className={`date-tab ${isActive ? 'active' : ''}`}
              onClick={() => onSelect(d.date)}
              title={d.graded ? `Graded: ${d.graded_count}/${d.total} games` : 'Pending results'}
            >
              {isToday ? 'Today' : d.date}
              {d.graded && <span className="tab-graded">✓</span>}
            </button>
          )
        })}
      </div>
    </div>
  )
}

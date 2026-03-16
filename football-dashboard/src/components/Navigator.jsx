export default function Navigator({ dates, selected, onSelect }) {
  if (!dates.length) return null

  // Show a rolling window of ~7 dates centred on selected
  const idx = dates.indexOf(selected)
  const start = Math.max(0, idx - 3)
  const visible = dates.slice(start, start + 7)

  return (
    <div className="navigator">
      <div className="navigator-label">Select date</div>
      <div className="date-tabs">
        {visible.map(d => {
          const isToday = d === new Date().toISOString().slice(0, 10)
          return (
            <button
              key={d}
              className={`date-tab ${d === selected ? 'active' : ''}`}
              onClick={() => onSelect(d)}
            >
              {isToday ? 'Today' : d}
            </button>
          )
        })}
      </div>
    </div>
  )
}

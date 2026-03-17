export default function Header() {
  return (
    <header className="site-header">
      <div className="logo">
        <span className="logo-icon">⚽</span>
        <span className="logo-text">blow<span className="accent">rout</span></span>
        <span className="logo-divider">|</span>
        <span className="logo-tagline">Advanced Football Prediction</span>
      </div>
      <div className="header-right">
        <span className="header-badge">BTTS</span>
        <span className="header-badge">1X2</span>
        <span className="header-badge">xG</span>
      </div>
    </header>
  )
}

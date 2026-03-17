import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null } }
  static getDerivedStateFromError(e) { return { error: e } }
  render() {
    if (this.state.error) return (
      <div style={{ padding: 32, fontFamily: 'monospace', background: '#fff1f2', color: '#991b1b', borderRadius: 8, margin: 24 }}>
        <strong>⚠️ Dashboard crashed:</strong>
        <pre style={{ marginTop: 8, whiteSpace: 'pre-wrap', fontSize: 12 }}>{String(this.state.error)}</pre>
      </div>
    )
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
)

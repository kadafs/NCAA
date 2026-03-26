import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null, info: null } }
  static getDerivedStateFromError(e) { return { error: e } }
  componentDidCatch(error, info) { this.setState({ info }) }
  render() {
    if (this.state.error) return (
      <div style={{ padding: 32, fontFamily: 'monospace', background: '#fff1f2', color: '#991b1b', borderRadius: 8, margin: 24 }}>
        <strong>⚠️ Dashboard crashed:</strong>
        <pre style={{ marginTop: 8, whiteSpace: 'pre-wrap', fontSize: 12 }}>{String(this.state.error)}</pre>
        <pre style={{ marginTop: 16, fontSize: 11, color: '#dc2626' }}>{this.state.info && this.state.info.componentStack}</pre>
        <p style={{ marginTop: 20 }}>Please show this screen to the developer.</p>
      </div>
    )
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)

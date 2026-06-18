import React from 'react';

const CrawlerStatusWidget = ({ status, statusMessage, alerts }) => {
  return (
    <div className="card shadow-lg h-100 position-relative overflow-hidden" style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95))',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '20px',
        backdropFilter: 'blur(10px)'
    }}>
      <div className="card-body p-4 text-white">
        <h5 className="fw-bold mb-4 d-flex align-items-center">
          <div className="d-flex align-items-center justify-content-center me-3" style={{
              width: '36px', height: '36px',
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              borderRadius: '10px',
              boxShadow: '0 4px 12px rgba(16, 185, 129, 0.4)'
          }}>
              <i className="fas fa-robot text-white"></i>
          </div>
          <span style={{ fontSize: '1.1rem', letterSpacing: '0.02em' }}>Hardened AI Crawler</span>
        </h5>
        
        {/* Status Indicator */}
        <div className="mb-4 p-3 rounded-4" style={{
            background: 'rgba(0, 0, 0, 0.2)',
            border: '1px solid rgba(255,255,255,0.05)'
        }}>
            <div className="d-flex align-items-center mb-2">
                <span className="me-2 text-white-50 fw-semibold" style={{ fontSize: '0.9rem' }}>Status:</span>
                <span className={`badge px-3 py-2 rounded-pill`} style={{
                    background: status === 'running' ? 'rgba(16, 185, 129, 0.2)' : status === 'error' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                    color: status === 'running' ? '#34d399' : status === 'error' ? '#f87171' : '#cbd5e1',
                    border: `1px solid ${status === 'running' ? 'rgba(16, 185, 129, 0.5)' : status === 'error' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(148, 163, 184, 0.5)'}`
                }}>
                    <i className={`fas ${status === 'running' ? 'fa-bolt' : status === 'error' ? 'fa-exclamation-triangle' : 'fa-moon'} me-2`}></i>
                    {status === 'running' ? 'ACTIVE' : status === 'error' ? 'BLOCKED' : 'IDLE'}
                </span>
                {status === 'running' && (
                    <div className="spinner-grow spinner-grow-sm ms-3 text-success" role="status" style={{ animationDuration: '1.5s' }}>
                        <span className="visually-hidden">Loading...</span>
                    </div>
                )}
            </div>
            <div className="small text-white-50 mt-2" style={{ fontFamily: 'monospace' }}>
                <i className="fas fa-terminal me-2"></i>{statusMessage || "Waiting for initialization..."}
            </div>
        </div>

        {/* Alerts Box */}
        <h6 className="fw-bold mb-3 d-flex align-items-center" style={{ color: '#f87171' }}>
            <i className="fas fa-bell me-2"></i> Real-time Alerts
        </h6>
        <div className="overflow-auto custom-scrollbar" style={{ maxHeight: '180px' }}>
            {alerts.length === 0 ? (
                <div className="text-center p-4 rounded-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px dashed rgba(255,255,255,0.1)' }}>
                    <i className="fas fa-check-circle text-success mb-2 fs-4 opacity-50"></i>
                    <p className="text-white-50 small mb-0">No significant price anomalies detected.</p>
                </div>
            ) : (
                alerts.map((alert, idx) => (
                    <div key={idx} className="alert py-2 px-3 mb-2 small d-flex gap-3 align-items-center" style={{ 
                        background: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid rgba(239, 68, 68, 0.2)',
                        color: '#fca5a5',
                        borderRadius: '12px'
                    }}>
                        <i className="fas fa-exclamation-circle"></i>
                        <span>{alert}</span>
                    </div>
                ))
            )}
        </div>

        {/* HITL Intervention */}
        {(status === 'error' || statusMessage?.includes('Anti-bot') || statusMessage?.includes('Cloudflare')) && (
            <button className="btn w-100 mt-4 fw-bold d-flex align-items-center justify-content-center gap-2" style={{
                background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                color: 'white',
                borderRadius: '12px',
                padding: '12px',
                boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)',
                border: 'none',
                transition: 'all 0.2s'
            }}>
                <i className="fas fa-user-shield"></i> Open HITL Dashboard (Unlock)
            </button>
        )}
      </div>
    </div>
  );
};

export default CrawlerStatusWidget;

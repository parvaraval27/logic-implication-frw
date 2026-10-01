import { useState } from 'react';

interface PropertiesPanelProps {
  metrics: any;
  selectedNode: any | null;
  isPostFRW: boolean;
  edges?: any[];
  onSelectNodeById?: (id: string) => void;
}

export default function PropertiesPanel({ 
  metrics, 
  selectedNode, 
  isPostFRW,
  edges,
  onSelectNodeById 
}: PropertiesPanelProps) {
  const currentMetrics = isPostFRW ? metrics?.post_frw : metrics?.baseline;
  const [frwExpanded, setFrwExpanded] = useState(false);
  const frwEdges = (edges || []).filter((e: any) => e.is_frw);

  return (
    <aside className="properties-panel">
      <div className="panel-section global-metrics">
        <h3>Circuit Summary</h3>
        {currentMetrics ? (
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-label">Gates</span>
              <span className="metric-value">{currentMetrics.gate_count}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Inputs (PI)</span>
              <span className="metric-value">{currentMetrics.pi_count}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Outputs (PO)</span>
              <span className="metric-value">{currentMetrics.po_count}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Transistors</span>
              <span className="metric-value">
                {currentMetrics.transistors != null 
                  ? currentMetrics.transistors 
                  : `${Math.round(currentMetrics.area / 450)} (est.)`}
              </span>
            </div>
            <div className="metric-card highlight">
              <span className="metric-label">Silicon Area</span>
              <span className="metric-value" title={`${currentMetrics.area?.toLocaleString()} nm (PTM 130nm)`}>
                {currentMetrics.area ? `${(currentMetrics.area / 1000).toFixed(1)}k nm` : '-'}
              </span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Failure Rate (FR)</span>
              <span className="metric-value">{(currentMetrics.avg_pdet * 100).toFixed(1)}%</span>
            </div>
            <div className="metric-card highlight">
              <span className="metric-label">Reliability (1-FR)</span>
              <span className="metric-value">{((1 - currentMetrics.avg_pdet) * 100).toFixed(1)}%</span>
            </div>
            {isPostFRW && (
              <>
                <div className="metric-card highlight">
                  <span className="metric-label">FRWs Added</span>
                  <span className="metric-value">{currentMetrics.frw_added}</span>
                </div>
                <div className="metric-card highlight">
                  <span className="metric-label">FR Reduction</span>
                  <span className="metric-value" style={{ color: '#10b981' }}>
                    {currentMetrics.fr_reduction != null 
                      ? `${currentMetrics.fr_reduction.toFixed(1)}%` 
                      : `${(((metrics.baseline.avg_pdet - currentMetrics.avg_pdet) / (metrics.baseline.avg_pdet || 1)) * 100).toFixed(1)}%`}
                  </span>
                </div>
                <div className="metric-card highlight">
                  <span className="metric-label">Area Overhead</span>
                  <span className="metric-value" style={{ color: currentMetrics.area_overhead > 0 ? '#ef4444' : '#10b981' }}>
                    {currentMetrics.area_overhead > 0 ? '+' : ''}{currentMetrics.area_overhead.toFixed(2)}%
                  </span>
                </div>
              </>
            )}
          </div>
        ) : (
          <p className="no-data">Loading metrics...</p>
        )}
      </div>

      {isPostFRW && frwEdges.length > 0 && (
        <div className="panel-section frw-explorer">
          <div 
            className="collapsible-header"
            onClick={() => setFrwExpanded(!frwExpanded)}
          >
            <div className="collapsible-title">
              <h3>Added FRWs ({frwEdges.length})</h3>
            </div>
            <span className={`chevron ${frwExpanded ? 'open' : ''}`}>
              {frwExpanded ? '▾' : '▸'}
            </span>
          </div>

          {frwExpanded && (
            <div className="frw-list">
              <p className="frw-help-text">Click any wire to inspect its target gate:</p>
              <div className="frw-items-scroll">
                {frwEdges.map((e: any, index: number) => (
                  <div 
                    key={e.id || index}
                    className="frw-item"
                    onClick={() => onSelectNodeById && onSelectNodeById(e.target)}
                    title={`Inspect target gate ${e.target}`}
                  >
                    <span className="frw-badge">#{index + 1}</span>
                    <div className="frw-wire-path">
                      <span className="wire-source">{e.source}</span>
                      <span className="wire-arrow">&rarr;</span>
                      <span className="wire-target">{e.target}</span>
                    </div>
                    {e.source.startsWith('INV_') && (
                      <span className="inverter-badge">Inverted</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="panel-section node-details">
        <h3>Gate Inspector</h3>
        {selectedNode ? (
          <div className="node-stats">
            <div className="node-header">
              <span className="node-id">{selectedNode.id}</span>
              <span className="node-type">{selectedNode.type}</span>
            </div>
            
            <div className="stat-row">
              <span>Role</span>
              <strong>{selectedNode.role}</strong>
            </div>

            {(() => {
              const state = isPostFRW ? selectedNode.post_frw : selectedNode.baseline;
              if (!state) return <div className="no-data">No probability data</div>;
              return (
                <div className="prob-table">
                  <div className="prob-row">
                    <span>P(det_sa0)</span>
                    <strong className={state.Pdet_sa0 < 0.1 ? 'safe' : 'danger'}>
                      {state.Pdet_sa0.toFixed(4)}
                    </strong>
                  </div>
                  <div className="prob-row">
                    <span>P(det_sa1)</span>
                    <strong className={state.Pdet_sa1 < 0.1 ? 'safe' : 'danger'}>
                      {state.Pdet_sa1.toFixed(4)}
                    </strong>
                  </div>
                  <div className="prob-row">
                    <span>P(0)</span>
                    <strong>{state.P0.toFixed(4)}</strong>
                  </div>
                  <div className="prob-row">
                    <span>P(1)</span>
                    <strong>{state.P1.toFixed(4)}</strong>
                  </div>
                </div>
              );
            })()}
          </div>
        ) : (
          <div className="empty-state">
            <p>Select a logic gate in the canvas to view vulnerability metrics.</p>
          </div>
        )}
      </div>
    </aside>
  );
}

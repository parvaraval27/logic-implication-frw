import React from 'react';

interface PropertiesPanelProps {
  metrics: any;
  selectedNode: any | null;
  isPostFRW: boolean;
}

export default function PropertiesPanel({ metrics, selectedNode, isPostFRW }: PropertiesPanelProps) {
  const currentMetrics = isPostFRW ? metrics?.post_frw : metrics?.baseline;

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

            {isPostFRW && (
              <>
                <div className="metric-card highlight">
                  <span className="metric-label">FRWs Added</span>
                  <span className="metric-value">{currentMetrics.frw_added}</span>
                </div>
              </>
            )}
          </div>
        ) : (
          <p className="no-data">Loading metrics...</p>
        )}
      </div>

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
                    <strong className={state.Pdet_sa0 < 0.1 ? 'danger' : 'safe'}>
                      {state.Pdet_sa0.toFixed(4)}
                    </strong>
                  </div>
                  <div className="prob-row">
                    <span>P(det_sa1)</span>
                    <strong className={state.Pdet_sa1 < 0.1 ? 'danger' : 'safe'}>
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

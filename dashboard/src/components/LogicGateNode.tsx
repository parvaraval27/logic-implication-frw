import { Handle, Position } from '@xyflow/react';
import React from 'react';
import './LogicGateNode.css';

export default function LogicGateNode({ data, isConnectable }) {
  const isPostFRW = data.isPostFRW || false;

  // Choose probability state to display based on toggle
  const state = isPostFRW && data.post_frw ? data.post_frw : data.baseline;

  // Vulnerability heatmap (Red = bad, Green = good)
  // We use Pdet_sa0 and Pdet_sa1. High Pdet is GOOD. Low Pdet is BAD (vulnerable).
  // Calculate average or min Pdet.
  const pdet = state ? Math.min(state.Pdet_sa0, state.Pdet_sa1) : 0;

  // Color scale: pdet=0 -> red (#ff4d4d), pdet=1 -> green (#4dff4d)
  // Let's use HSL for an easy transition.
  // Hue: 0 (Red) to 120 (Green)
  const hue = Math.max(0, Math.min(120, pdet * 120));
  const backgroundColor = `hsl(${hue}, 80%, 60%)`;

  return (
    <div
      className={`logic-gate-node gate-${data.type.toLowerCase()}`}
      style={{ backgroundColor }}
    >
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
      <div className="gate-content">
        <div className="gate-name">{data.id}</div>
        <div className="gate-type">{data.type}</div>
        {state && (
          <div className="gate-stats">
            <div title="Min Detection Prob">Pdet: {pdet.toFixed(3)}</div>
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Right} isConnectable={isConnectable} />
    </div>
  );
}

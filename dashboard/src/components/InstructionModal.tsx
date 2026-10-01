
interface InstructionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function InstructionModal({ isOpen, onClose }: InstructionModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-header-text">
            <h2>User Guide & Dashboard Instructions</h2>
            <p>How to view, interact with, and inspect benchmark circuits and FRW fault tolerance</p>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close guide">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="modal-body">
          {/* Guide Section 1 */}
          <div className="guide-card">
            <div className="guide-card-header">
              <h3>1. Dashboard Layout & Navigation</h3>
            </div>
            <p>
              The dashboard is organized into three intuitive panes designed for circuit exploration:
            </p>
            <ul>
              <li><strong>Left Sidebar:</strong> Select any benchmark circuit or illustrative example from the list.</li>
              <li><strong>Center Canvas:</strong> Interactive schematic graph rendered with React Flow.</li>
              <li><strong>Right Panel:</strong> Live circuit-level summary metrics, Gate Inspector, and FRW Explorer.</li>
            </ul>
          </div>

          {/* Guide Section 2 */}
          <div className="guide-card">
            <div className="guide-card-header">
              <h3>2. Baseline vs. Post-FRW Mode</h3>
            </div>
            <p>
              Use the toggle switch at the top of the canvas to switch between circuit states:
            </p>
            <ul>
              <li><strong>Baseline:</strong> Displays the original circuit topology without any redundant masking connections.</li>
              <li><strong>Post-FRW:</strong> Displays the hardened circuit with added <em>Functionally Redundant Wires (FRWs)</em> shown as <strong>animated dashed blue lines</strong>, along with any necessary inserted inverters.</li>
            </ul>
          </div>

          {/* Guide Section 3 */}
          <div className="guide-card">
            <div className="guide-card-header">
              <h3>3. Canvas Interactions</h3>
            </div>
            <ul>
              <li><strong>Pan & Zoom:</strong> Click and drag anywhere on the canvas background to pan. Use your mouse wheel or trackpad to zoom in and out.</li>
              <li><strong>Controls & MiniMap:</strong> Use the controls in the bottom-left to reset zoom or fit the view. The MiniMap in the bottom-right gives an aerial view of larger circuits.</li>
              <li><strong>Select Gates:</strong> Click on any logic gate node to inspect its exact stuck-at fault probabilities in the right sidebar.</li>
            </ul>
          </div>

          {/* Guide Section 4 */}
          <div className="guide-card">
            <div className="guide-card-header">
              <h3>4. Key Metrics Explained</h3>
            </div>
            <ul>
              <li><strong>Area (Transistors):</strong> Sized silicon area based on PTM 130nm transistor drain widths.</li>
              <li><strong>Failure Rate (FR):</strong> Average probability that a single stuck-at fault propagates to at least one primary output.</li>
              <li><strong>Reliability (1 - FR):</strong> Overall resilience of the circuit against particle-induced soft errors (higher is better).</li>
              <li><strong>FR Reduction (% Red):</strong> Percentage drop in the circuit's failure rate achieved through logical masking.</li>
              <li><strong>Area Overhead:</strong> The percentage increase in silicon area incurred by adding the redundant wires.</li>
            </ul>
          </div>

          {/* Guide Section 5 */}
          <div className="guide-card">
            <div className="guide-card-header">
              <h3>5. Gate Inspector & Collapsible FRW List</h3>
            </div>
            <ul>
              <li><strong>Gate Inspector:</strong> Displays P(det_sa0), P(det_sa1), P(0), and P(1) for the selected gate. Numbers colored in <span style={{ color: '#10b981', fontWeight: 600 }}>green</span> indicate that the fault is well-masked, while <span style={{ color: '#ef4444', fontWeight: 600 }}>red</span> marks sensitive unmasked gates.</li>
              <li><strong>Collapsible FRW List:</strong> In the right sidebar, expand the <em>"Added FRWs"</em> section to see the full list of redundant wires. Click any FRW in the list to automatically jump to and inspect its destination gate.</li>
            </ul>
          </div>
        </div>

        <div className="modal-footer">
          <button className="modal-done-btn" onClick={onClose}>
            Got it, Let's Explore
          </button>
        </div>
      </div>
    </div>
  );
}

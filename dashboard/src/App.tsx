import { useState, useEffect } from 'react';
import GraphView from './components/GraphView';
import Sidebar from './components/Sidebar';
import PropertiesPanel from './components/PropertiesPanel';
import InstructionModal from './components/InstructionModal';
import './App.css';

function App() {
  const [benchmarks, setBenchmarks] = useState<string[]>([]);
  const [selectedBenchmark, setSelectedBenchmark] = useState<string>('');
  
  const [graphData, setGraphData] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [isPostFRW, setIsPostFRW] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isGuideOpen, setIsGuideOpen] = useState(false);

  // Fetch available benchmarks on mount
  useEffect(() => {
    fetch('/benchmarks/index.json')
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load benchmarks list");
        return res.json();
      })
      .then((data: string[]) => {
        setBenchmarks(data);
        if (data.length > 0) setSelectedBenchmark(data[0]);
        else setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  // Fetch graph data when selectedBenchmark changes
  useEffect(() => {
    if (!selectedBenchmark) return;
    
    setLoading(true);
    setSelectedNode(null); // Reset selection
    
    fetch(`/benchmarks/${selectedBenchmark}.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${selectedBenchmark}.json`);
        return res.json();
      })
      .then((data) => {
        setGraphData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setGraphData(null);
        setLoading(false);
      });
  }, [selectedBenchmark]);

  // Unselect node if it only exists in post-FRW and user switches to baseline
  useEffect(() => {
    if (!isPostFRW && selectedNode && selectedNode.baseline === null) {
      setSelectedNode(null);
    }
  }, [isPostFRW, selectedNode]);

  const handleSelectNodeById = (nodeId: string) => {
    if (!graphData || !graphData.nodes) return;
    const found = graphData.nodes.find((n: any) => n.id === nodeId);
    if (found) {
      setSelectedNode(found);
    }
  };

  return (
    <div className="dashboard-layout">
      {/* LEFT: Sidebar */}
      <Sidebar 
        benchmarks={benchmarks} 
        selectedBenchmark={selectedBenchmark} 
        onSelect={setSelectedBenchmark} 
      />

      {/* CENTER: Graph View */}
      <main className="center-pane">
        <header className="center-header">
          <div className="header-title">
            <h1>{selectedBenchmark || 'FRW Circuit Dashboard'}</h1>
          </div>
          
          <div className="header-actions">
            <button 
              className="guide-button" 
              onClick={() => setIsGuideOpen(true)}
              title="Documentation & Benchmarks"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </svg>
              <span>Documentation</span>
            </button>

            <div className="toggle-container">
              <span className={!isPostFRW ? 'active' : ''}>Baseline</span>
              <label className="switch">
                <input 
                  type="checkbox" 
                  checked={isPostFRW} 
                  onChange={() => setIsPostFRW(!isPostFRW)} 
                />
                <span className="slider round"></span>
              </label>
              <span className={isPostFRW ? 'active' : ''}>Post-FRW</span>
            </div>
          </div>
        </header>
        
        <div className="graph-container">
          {loading ? (
            <div className="loading">Loading {selectedBenchmark}...</div>
          ) : graphData ? (
            <GraphView 
              graphData={graphData} 
              isPostFRW={isPostFRW} 
              onNodeClick={(node) => setSelectedNode(node)} 
            />
          ) : (
            <div className="error">Failed to load graph data or no benchmarks found.</div>
          )}
        </div>
      </main>

      {/* RIGHT: Properties Panel */}
      <PropertiesPanel 
        metrics={graphData?.metrics} 
        selectedNode={selectedNode} 
        isPostFRW={isPostFRW}
        edges={graphData?.edges}
        onSelectNodeById={handleSelectNodeById}
      />

      {/* Instruction Guide Modal */}
      <InstructionModal 
        isOpen={isGuideOpen} 
        onClose={() => setIsGuideOpen(false)} 
      />
    </div>
  );
}

export default App;

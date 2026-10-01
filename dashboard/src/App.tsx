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
              title="Open Dashboard Instructions & Guide"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>User Guide</span>
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

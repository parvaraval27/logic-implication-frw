import { useState, useEffect } from 'react';
import GraphView from './components/GraphView';
import Sidebar from './components/Sidebar';
import PropertiesPanel from './components/PropertiesPanel';
import './App.css';

function App() {
  const [benchmarks, setBenchmarks] = useState<string[]>([]);
  const [selectedBenchmark, setSelectedBenchmark] = useState<string>('');

  const [graphData, setGraphData] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [isPostFRW, setIsPostFRW] = useState(false);
  const [loading, setLoading] = useState(true);

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
      />
    </div>
  );
}

export default App;

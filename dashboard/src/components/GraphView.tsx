import { useEffect, useRef } from 'react';
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import LogicGateNode from './LogicGateNode';
import { getLayoutedElements } from '../utils/layout';

const nodeTypes = {
  logicGate: LogicGateNode,
};

interface GraphViewProps {
  graphData: any;
  isPostFRW: boolean;
  onNodeClick: (node: any) => void;
}

export default function GraphView({ graphData, isPostFRW, onNodeClick }: GraphViewProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const layoutedNodesRef = useRef<Node[]>([]);

  // 1. Run layout ONLY when graphData changes (not when toggling baseline/postFRW)
  useEffect(() => {
    if (!graphData || !graphData.nodes || !graphData.edges) return;

    const initialNodes = graphData.nodes.map((n: any) => ({
      id: n.id,
      type: 'logicGate',
      position: { x: 0, y: 0 },
      data: { ...n, isPostFRW },
    }));

    // Generate all edges for layout
    const allEdges = graphData.edges.map((e: any) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      is_frw: e.is_frw,
      is_removed: e.is_removed,
    }));

    const { nodes: layoutedNodes } = getLayoutedElements(
      initialNodes,
      allEdges as any,
      'LR'
    );

    layoutedNodesRef.current = layoutedNodes;

    // Filter nodes: in pre-FRW (baseline), vanish inverters/gates that were added only post-FRW
    const visibleNodes = layoutedNodes
      .filter((n: any) => isPostFRW || n.data.baseline !== null)
      .map((n: any) => ({
        ...n,
        data: { ...n.data, isPostFRW },
      }));

    setNodes(visibleNodes as any);
  }, [graphData, setNodes]);

  // 2. Fast edge filter and node visibility update when isPostFRW toggles
  useEffect(() => {
    if (!graphData || !graphData.edges) return;

    if (layoutedNodesRef.current && layoutedNodesRef.current.length > 0) {
      // In baseline, vanish gates that only exist post-FRW
      const visibleNodes = layoutedNodesRef.current
        .filter((n: any) => isPostFRW || n.data.baseline !== null)
        .map((n: any) => ({
          ...n,
          data: { ...n.data, isPostFRW },
        }));

      setNodes(visibleNodes as any);
    }

    const activeEdges = graphData.edges
      .filter((e: any) => {
        if (!isPostFRW && e.is_frw) return false;
        if (isPostFRW && e.is_removed) return false;
        return true;
      })
      .map((e: any) => {
        const isFrwEdge = e.is_frw;
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          type: 'straight',
          animated: isFrwEdge,
          style: isFrwEdge 
            ? { stroke: '#2196f3', strokeWidth: 2.5, strokeDasharray: '5,5' }
            : { stroke: '#94a3b8', strokeWidth: 1.5 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isFrwEdge ? '#2196f3' : '#94a3b8',
            width: 15,
            height: 15,
          },
        };
      });

    setEdges(activeEdges);
  }, [isPostFRW, graphData, setNodes, setEdges]);

  const showMiniMap = nodes.length <= 400;

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node: any) => onNodeClick(node.data)}
        nodeTypes={nodeTypes}
        fitView
        onlyRenderVisibleElements={true}
        attributionPosition="top-right"
        minZoom={0.05}
        maxZoom={2}
      >
        <Background color="#cbd5e1" gap={20} size={1} />
        <Controls />
        {showMiniMap && <MiniMap zoomable pannable nodeStrokeWidth={2} />}
      </ReactFlow>
    </div>
  );
}

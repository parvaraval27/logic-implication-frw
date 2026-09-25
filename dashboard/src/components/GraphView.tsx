import React, { useEffect, useState, useMemo } from 'react';
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  MiniMap,
  MarkerType,
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
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!graphData || !graphData.nodes || !graphData.edges) return;

    // Map JSON nodes to React Flow nodes
    const initialNodes = graphData.nodes.map((n: any) => ({
      id: n.id,
      type: 'logicGate',
      position: { x: 0, y: 0 },
      data: { ...n, isPostFRW },
    }));

    // Map JSON edges to React Flow edges
    const initialEdges = graphData.edges
      .filter((e: any) => {
        // If we are in baseline, hide FRW edges
        if (!isPostFRW && e.is_frw) return false;
        // If we are in post_frw, hide removed edges
        if (isPostFRW && e.is_removed) return false;
        return true;
      })
      .map((e: any) => {
        const isFrwEdge = e.is_frw;
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          animated: isFrwEdge,
          style: isFrwEdge
            ? { stroke: '#2196f3', strokeWidth: 3, strokeDasharray: '5,5' }
            : { stroke: '#999', strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isFrwEdge ? '#2196f3' : '#999',
          },
        };
      });

    // Apply layout
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      initialNodes,
      initialEdges,
      'LR'
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [graphData, isPostFRW, setNodes, setEdges]);

  // When isPostFRW changes, we just need to update the data inside the nodes 
  // so the LogicGateNode component rerenders its colors, and re-filter edges.
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: { ...n.data, isPostFRW },
      }))
    );
  }, [isPostFRW, setNodes]);

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => onNodeClick(node.data)}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="top-right"
      >

        <Background color="#ccc" gap={16} />
        <Controls />
        <MiniMap zoomable pannable />
      </ReactFlow>
    </div>
  );
}

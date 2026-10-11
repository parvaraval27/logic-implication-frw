import dagre from 'dagre';
import { Position, type Node, type Edge } from '@xyflow/react';

const nodeWidth = 120;
const nodeHeight = 60;

export const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'LR') => {
  const isHorizontal = direction === 'LR';

  // For very large circuits (> 300 nodes), full Dagre JS layout blocks the browser main thread.
  // Use ultra-fast topological column placement (runs in < 5ms).
  if (nodes.length > 300) {
    const inDegree: Record<string, number> = {};
    const adj: Record<string, string[]> = {};
    nodes.forEach((n) => {
      inDegree[n.id] = 0;
      adj[n.id] = [];
    });

    edges.forEach((e) => {
      if (inDegree[e.target] !== undefined) inDegree[e.target]++;
      if (adj[e.source] !== undefined) adj[e.source].push(e.target);
    });

    const rank: Record<string, number> = {};
    const queue: string[] = [];

    nodes.forEach((n) => {
      if (inDegree[n.id] === 0) {
        rank[n.id] = 0;
        queue.push(n.id);
      }
    });

    let head = 0;
    while (head < queue.length) {
      const u = queue[head++];
      const currentRank = rank[u] || 0;
      for (const v of adj[u] || []) {
        const nextRank = currentRank + 1;
        if (rank[v] === undefined || nextRank > rank[v]) {
          rank[v] = nextRank;
        }
        inDegree[v]--;
        if (inDegree[v] === 0) {
          queue.push(v);
        }
      }
    }

    // Fallback for any disconnected/cycle nodes
    nodes.forEach((n) => {
      if (rank[n.id] === undefined) rank[n.id] = 0;
    });

    // Group nodes by rank
    const columns: Record<number, Node[]> = {};
    nodes.forEach((n) => {
      const r = rank[n.id];
      if (!columns[r]) columns[r] = [];
      columns[r].push(n);
    });

    const layoutedNodes = nodes.map((node) => {
      const col = rank[node.id];
      const colNodes = columns[col];
      const idx = colNodes.indexOf(node);

      return {
        ...node,
        targetPosition: isHorizontal ? Position.Left : Position.Top,
        sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
        position: {
          x: col * (nodeWidth + 90),
          y: idx * (nodeHeight + 35),
        },
      };
    });

    return { nodes: layoutedNodes, edges };
  }

  // For small/medium circuits (<= 300 nodes), use fresh Dagre layout
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 30, ranksep: 50 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id) || { x: 0, y: 0 };
    return {
      ...node,
      targetPosition: isHorizontal ? Position.Left : Position.Top,
      sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: newNodes, edges };
};


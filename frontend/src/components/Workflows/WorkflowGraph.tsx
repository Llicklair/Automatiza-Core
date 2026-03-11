"use client";

import { useMemo, useCallback, useState } from 'react';
import ReactFlow, {
    Background,
    Controls,
    Node,
    Edge,
    MarkerType,
    Connection,
    NodeChange,
    EdgeChange,
    applyNodeChanges,
    applyEdgeChanges,
    addEdge,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { customNodeTypes } from './CustomNodes';
import WorkflowToolbar from './WorkflowToolbar';
import NodeConfigPanel from './NodeConfigPanel';

interface NodeState {
    status: string;
    output?: any;
    started_at?: string;
    completed_at?: string;
}

interface WorkflowGraphProps {
    nodes: Node[];
    edges: Edge[];
    nodeStates?: Record<string, NodeState>;
    currentNodeId?: string | null;
    editable?: boolean;
    onNodesChange?: (nodes: Node[]) => void;
    onEdgesChange?: (edges: Edge[]) => void;
}

// Status → border glow color
const STATUS_BORDER: Record<string, string> = {
    completed: "#10b981",  // emerald
    running: "#3b82f6",    // blue
    failed: "#ef4444",     // red
    waiting: "#3b82f6",    // blue
    paused: "#f97316",     // orange
    skipped: "#3f3f46",    // zinc-700
};

const DEFAULT_NODE_DATA: Record<string, any> = {
    skill: { label: "Agente IA", domain: "billing", description: "" },
    conditional: { label: "Condicional", condition: { field: "" } },
    delay: { label: "Espera", delay_seconds: 60 },
    approval_gate: { label: "Aprobación", description: "" },
};

export default function WorkflowGraph({
    nodes,
    edges,
    nodeStates,
    currentNodeId,
    editable = false,
    onNodesChange: onNodesProp,
    onEdgesChange: onEdgesProp,
}: WorkflowGraphProps) {
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

    const styledNodes = useMemo(() => {
        return nodes.map(n => {
            const ns = nodeStates?.[n.id];
            const isActive = currentNodeId === n.id;
            const statusColor = ns ? STATUS_BORDER[ns.status] : undefined;

            return {
                ...n,
                type: n.type && n.type in customNodeTypes ? n.type : (n.type || 'default'),
                style: n.type && n.type in customNodeTypes ? {
                    ...(statusColor ? { filter: `drop-shadow(0 0 8px ${statusColor}40)` } : {}),
                    ...(isActive ? { filter: `drop-shadow(0 0 12px #3b82f680)` } : {}),
                    opacity: ns?.status === 'skipped' ? 0.4 : 1,
                } : {
                    background: '#18181b',
                    color: '#fff',
                    border: `2px solid ${statusColor || (n.type === 'trigger' ? '#6366f1' : '#10b981')}`,
                    borderRadius: '12px',
                    padding: '12px',
                    fontSize: '12px',
                    width: 180,
                    opacity: ns?.status === 'skipped' ? 0.4 : 1,
                    ...(isActive ? { boxShadow: '0 0 16px rgba(59,130,246,0.4)' } : {}),
                },
            };
        });
    }, [nodes, nodeStates, currentNodeId]);

    const styledEdges = useMemo(() => {
        return edges.map(e => {
            const branchLabel = e.data?.branch;
            const sourceState = nodeStates?.[e.source];
            const isActive = sourceState?.status === 'completed';

            return {
                ...e,
                animated: isActive || !nodeStates,
                type: 'smoothstep',
                style: {
                    stroke: isActive ? '#10b981' : '#52525b',
                    strokeWidth: isActive ? 2 : 1,
                },
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: isActive ? '#10b981' : '#52525b',
                },
                label: branchLabel === 'true' ? 'Sí' : branchLabel === 'false' ? 'No' : undefined,
                labelStyle: {
                    fill: branchLabel === 'true' ? '#10b981' : branchLabel === 'false' ? '#ef4444' : '#a1a1aa',
                    fontSize: 10,
                    fontWeight: 600,
                },
                labelBgStyle: {
                    fill: '#18181b',
                    fillOpacity: 0.9,
                },
            };
        });
    }, [edges, nodeStates]);

    const handleNodesChange = useCallback((changes: NodeChange[]) => {
        if (!editable || !onNodesProp) return;
        const updated = applyNodeChanges(changes, nodes);
        onNodesProp(updated);
    }, [editable, nodes, onNodesProp]);

    const handleEdgesChange = useCallback((changes: EdgeChange[]) => {
        if (!editable || !onEdgesProp) return;
        const updated = applyEdgeChanges(changes, edges);
        onEdgesProp(updated);
    }, [editable, edges, onEdgesProp]);

    const handleConnect = useCallback((connection: Connection) => {
        if (!editable || !onEdgesProp) return;
        const newEdge: Edge = {
            id: `e-${connection.source}-${connection.target}-${Date.now()}`,
            source: connection.source!,
            target: connection.target!,
            sourceHandle: connection.sourceHandle || undefined,
            targetHandle: connection.targetHandle || undefined,
        };
        onEdgesProp([...edges, newEdge]);
    }, [editable, edges, onEdgesProp]);

    const handleAddNode = useCallback((type: "skill" | "conditional" | "delay" | "approval_gate") => {
        if (!onNodesProp) return;
        const id = `${type}_${Date.now()}`;
        // Place new node below the last node
        const maxY = nodes.reduce((max, n) => Math.max(max, n.position?.y ?? 0), 0);
        const centerX = nodes.length > 0
            ? nodes.reduce((sum, n) => sum + (n.position?.x ?? 0), 0) / nodes.length
            : 250;
        const newNode: Node = {
            id,
            type,
            position: { x: centerX, y: maxY + 130 },
            data: { ...DEFAULT_NODE_DATA[type] },
        };
        onNodesProp([...nodes, newNode]);
    }, [nodes, onNodesProp]);

    const handleNodeClick = useCallback((_: any, node: Node) => {
        if (!editable) return;
        if (node.type === "trigger") return; // trigger not configurable
        setSelectedNodeId(node.id);
    }, [editable]);

    const handleNodeDataUpdate = useCallback((id: string, data: Record<string, any>) => {
        if (!onNodesProp) return;
        onNodesProp(nodes.map(n => n.id === id ? { ...n, data } : n));
    }, [nodes, onNodesProp]);

    const handleNodeDelete = useCallback((id: string) => {
        if (!onNodesProp || !onEdgesProp) return;
        onNodesProp(nodes.filter(n => n.id !== id));
        onEdgesProp(edges.filter(e => e.source !== id && e.target !== id));
        setSelectedNodeId(null);
    }, [nodes, edges, onNodesProp, onEdgesProp]);

    const selectedNode = selectedNodeId ? nodes.find(n => n.id === selectedNodeId) : null;

    if (!nodes || nodes.length === 0) {
        return (
            <div className="flex justify-center items-center h-full w-full bg-zinc-900/50 rounded-xl border border-dashed border-zinc-800">
                <p className="text-zinc-500 text-sm">
                    {editable ? "Usa la barra de herramientas para añadir nodos." : "Este workflow no tiene vista de plano generada."}
                </p>
            </div>
        );
    }

    return (
        <div className="w-full h-full rounded-xl overflow-hidden border border-zinc-800 relative bg-[#09090b]">
            {editable && (
                <div className="absolute top-3 left-3 z-10">
                    <WorkflowToolbar onAddNode={handleAddNode} />
                </div>
            )}
            <ReactFlow
                nodes={styledNodes}
                edges={styledEdges}
                nodeTypes={customNodeTypes}
                fitView
                attributionPosition="bottom-right"
                nodesDraggable={editable}
                nodesConnectable={editable}
                elementsSelectable={true}
                deleteKeyCode={editable ? "Backspace" : null}
                onNodesChange={editable ? handleNodesChange : undefined}
                onEdgesChange={editable ? handleEdgesChange : undefined}
                onConnect={editable ? handleConnect : undefined}
                onNodeClick={handleNodeClick}
                onPaneClick={() => setSelectedNodeId(null)}
            >
                <Background gap={16} size={1} color="#27272a" />
                <Controls showInteractive={false} className="bg-zinc-900 border-zinc-800 fill-zinc-400" />
            </ReactFlow>
            {editable && selectedNode && (
                <div className="absolute top-3 right-3 z-10">
                    <NodeConfigPanel
                        node={selectedNode}
                        onUpdate={handleNodeDataUpdate}
                        onDelete={handleNodeDelete}
                        onClose={() => setSelectedNodeId(null)}
                    />
                </div>
            )}
        </div>
    );
}

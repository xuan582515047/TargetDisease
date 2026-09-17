"use client";

import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import { Maximize, Minimize, ZoomIn, ZoomOut, RotateCcw, Scan } from "lucide-react";
import { EDGE_COLOR, NODE_COLOR, NODE_SHAPE, NODE_SIZE, type NetworkElements } from "@/lib/target-network";

type Props = {
  elements: NetworkElements;
  onSelect: (id: string, kind: "node" | "edge") => void;
  onReady?: (cy: cytoscape.Core | null) => void;
};

export default function NetworkCanvas({ elements, onSelect, onReady }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [fullscreen, setFullscreen] = useFullscreenState();

  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements: [...elements.nodes, ...elements.edges] as cytoscape.ElementDefinition[],
      style: [
        {
          selector: "node",
          style: {
            "background-color": (ele: cytoscape.NodeSingular) => NODE_COLOR[ele.data("type")] ?? NODE_COLOR.background,
            shape: (ele: cytoscape.NodeSingular) =>
              (NODE_SHAPE[ele.data("type")] ?? "ellipse") as cytoscape.Css.NodeShape,
            width: (ele: cytoscape.NodeSingular) => NODE_SIZE[ele.data("type")] ?? NODE_SIZE.background,
            height: (ele: cytoscape.NodeSingular) => NODE_SIZE[ele.data("type")] ?? NODE_SIZE.background,
            label: "data(label)",
            color: "#334155",
            "font-size": 10,
            "text-valign": "bottom",
            "text-margin-y": 6,
            "text-wrap": "ellipsis",
            "text-max-width": "90px",
          },
        },
        {
          selector: 'node[type="background"]',
          style: { display: "element", opacity: 0.7 },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": (ele: cytoscape.EdgeSingular) => EDGE_COLOR[ele.data("type")] ?? EDGE_COLOR.association,
            "curve-style": "bezier",
            opacity: 0.6,
          },
        },
        {
          selector: ":selected",
          style: { "border-width": 3, "border-color": "#2563EB", width: 3 },
        },
      ],
      layout: {
        name: "preset",
        positions: buildPresetPositions(elements.nodes),
      },
      minZoom: 0.1,
      maxZoom: 6,
      wheelSensitivity: 0.2,
    });

    cyRef.current = cy;
    onReady?.(cy);
    cy.on("tap", "node", (e) => onSelect(e.target.id(), "node"));
    cy.on("tap", "edge", (e) => onSelect(e.target.id(), "edge"));

    return () => {
      cy.destroy();
      cyRef.current = null;
      onReady?.(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elements]);

  function cy() {
    return cyRef.current;
  }

  return (
    <div className="relative h-full min-h-[600px] w-full">
      <div className="absolute right-3 top-3 z-10 flex flex-col gap-1 rounded-lg border border-border bg-background/90 p-1 shadow-sm">
        <ToolButton label="放大" onClick={() => cy()?.zoom(cy()!.zoom() * 1.2)}><ZoomIn size={15} /></ToolButton>
        <ToolButton label="缩小" onClick={() => cy()?.zoom(cy()!.zoom() / 1.2)}><ZoomOut size={15} /></ToolButton>
        <ToolButton label="适应视图" onClick={() => cy()?.fit(undefined, 40)}><Scan size={15} /></ToolButton>
        <ToolButton label="重置布局" onClick={() => cy()?.layout({ name: "preset", positions: buildPresetPositions(elements.nodes) }).run()}><RotateCcw size={15} /></ToolButton>
        <ToolButton label={fullscreen ? "退出全屏" : "全屏"} onClick={() => setFullscreen(!fullscreen)}>
          {fullscreen ? <Minimize size={15} /> : <Maximize size={15} />}
        </ToolButton>
      </div>
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}

function ToolButton({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="grid size-8 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
    >
      {children}
    </button>
  );
}

function useFullscreenState() {
  const [fullscreen, setFullscreen] = useState(false);
  return [fullscreen, setFullscreen] as const;
}

function buildPresetPositions(nodes: { data: Record<string, unknown> }[]) {
  const positions: Record<string, { x: number; y: number }> = {};
  const seeds: string[] = [];
  const extended: string[] = [];
  const disease: string[] = [];
  const background: string[] = [];
  for (const n of nodes) {
    const type = n.data.type as string;
    if (type === "disease") disease.push(n.data.id as string);
    else if (type === "seed") seeds.push(n.data.id as string);
    else if (type === "extended") extended.push(n.data.id as string);
    else background.push(n.data.id as string);
  }
  // 疾病居中，种子内圈，扩展候选外圈，背景更外圈
  for (const id of disease) positions[id] = { x: 0, y: 0 };
  const radiusFor = (i: number, total: number, radius: number) => {
    const angle = (2 * Math.PI * i) / Math.max(total, 1) - Math.PI / 2;
    return { x: radius * Math.cos(angle), y: radius * Math.sin(angle) };
  };
  seeds.forEach((id, i) => (positions[id] = radiusFor(i, seeds.length, 150)));
  extended.forEach((id, i) => (positions[id] = radiusFor(i, extended.length, 300)));
  background.forEach((id, i) => (positions[id] = radiusFor(i, background.length, 460)));
  return positions;
}

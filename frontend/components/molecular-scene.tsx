const nodes = Array.from({ length: 22 }, (_, index) => {
  const angle = index * 0.72;
  return { x: 72 + index * 22, y: 195 + Math.sin(angle) * 76, r: 5 + (Math.cos(angle) + 1) * 3 };
});

export default function MolecularScene() {
  return (
    <div className="molecular-scene" aria-hidden="true">
      <div className="molecule-orbit orbit-one" /><div className="molecule-orbit orbit-two" />
      <svg className="peptide-chain" viewBox="0 0 620 400" fill="none">
        <defs><linearGradient id="chain-color" x1="0" y1="0" x2="620" y2="400" gradientUnits="userSpaceOnUse"><stop stopColor="#c6f6a5" /><stop offset="0.5" stopColor="#66ca97" /><stop offset="1" stopColor="#25765d" /></linearGradient></defs>
        <g stroke="url(#chain-color)" strokeWidth="1.2">
          {nodes.slice(1).map((node, index) => <g key={index}><line x1={nodes[index].x} y1={nodes[index].y} x2={node.x} y2={node.y} /><line x1={nodes[index].x} y1={390 - nodes[index].y} x2={node.x} y2={390 - node.y} />{index % 2 === 0 && <line x1={node.x} y1={node.y} x2={node.x} y2={390 - node.y} opacity=".35" />}</g>)}
        </g>
        {nodes.map((node, index) => <g key={index}><circle cx={node.x} cy={node.y} r={node.r + 5} fill="#a9edb2" opacity=".05" /><circle cx={node.x} cy={node.y} r={node.r} fill="url(#chain-color)" /><circle cx={node.x} cy={390 - node.y} r={12 - node.r} fill="#8bd5a7" opacity=".5" /></g>)}
      </svg>
      <span className="molecule-label label-one">MOLECULAR EXPLORATION</span><span className="molecule-label label-two">STRUCTURE · CONNECTION · DISCOVERY</span>
      <span className="molecule-spark spark-one" /><span className="molecule-spark spark-two" /><span className="molecule-spark spark-three" />
    </div>
  );
}

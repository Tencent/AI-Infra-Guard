import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const ParticleNetwork: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!containerRef.current || !svgRef.current) return;

    const container = containerRef.current;
    const svgEl = svgRef.current;
    const svg = d3.select(svgEl);

    // Initial setup
    let width = container.clientWidth;
    let height = container.clientHeight;
    
    svg.attr('viewBox', `0 0 ${width} ${height}`);

    const nodeCount = 60;
    const nodes = Array.from({ length: nodeCount }, (_, i) => ({
      index: i,
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      radius: Math.random() * 2 + 1,
    }));

    // Clear previous content
    svg.selectAll('*').remove();

    // Create groups
    const linesGroup = svg.append('g');
    const nodesGroup = svg.append('g');

    // Drawing nodes
    const nodeElements = nodesGroup.selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d) => d.radius)
      .attr('fill', '#60a5fa') // Blue 400
      .attr('filter', 'drop-shadow(0 0 4px #60a5fa)');

    let animationId: number;

    const update = () => {
      // Update positions
      nodes.forEach((node) => {
        node.x += node.vx;
        node.y += node.vy;

        // Wrap around logic
        if (node.x < 0) node.x = width;
        if (node.x > width) node.x = 0;
        if (node.y < 0) node.y = height;
        if (node.y > height) node.y = 0;
      });

      // Find links based on proximity
      const links = [];
      const threshold = 120;
      for (let i = 0; i < nodeCount; i++) {
        for (let j = i + 1; j < nodeCount; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < threshold) {
            links.push({
              source: nodes[i],
              target: nodes[j],
              opacity: 1 - (dist / threshold),
            });
          }
        }
      }

      // Render lines
      linesGroup.selectAll('line')
        .data(links, (d: any) => `${d.source.index}-${d.target.index}`)
        .join(
          (enter) => enter.append('line')
            .attr('stroke', '#60a5fa') // Blue 400
            .attr('stroke-width', 0.8),
          (update) => update,
          (exit) => exit.remove()
        )
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y)
        .attr('stroke-opacity', (d: any) => d.opacity * 0.5);

      // Update nodes
      nodeElements
        .attr('cx', (d) => d.x)
        .attr('cy', (d) => d.y);

      animationId = requestAnimationFrame(update);
    };

    update();

    const handleResize = () => {
      width = container.clientWidth;
      height = container.clientHeight;
      svg.attr('viewBox', `0 0 ${width} ${height}`);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationId);
      svg.selectAll('*').remove();
    };
  }, []);

  return (
    <div ref={containerRef} className="w-full h-full relative overflow-hidden rounded-2xl">
      <svg ref={svgRef} className="w-full h-full block" />
      {/* Decorative Glow */}
      <div className="absolute inset-0 bg-blue-500/10 blur-[100px] rounded-full pointer-events-none" />
    </div>
  );
};

export default ParticleNetwork;

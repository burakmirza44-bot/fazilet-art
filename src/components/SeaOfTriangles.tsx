import { useEffect, useRef } from 'react';

export default function SeaOfTriangles() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;

    const resize = () => {
      const parent = canvas.parentElement;
      if (parent) {
        canvas.width = parent.clientWidth;
        canvas.height = parent.clientHeight;
      }
    };

    window.addEventListener('resize', resize);
    resize();

    // Grid settings
    const cols = 40;
    const rows = 20;
    const spacingX = canvas.width / cols;
    const spacingY = canvas.height / rows;

    const draw = () => {
      time += 0.02;
      
      // Update spacing in case of resize
      const currentSpacingX = canvas.width / cols;
      const currentSpacingY = canvas.height / rows;

      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
      ctx.lineWidth = 1;

      const points: { x: number, y: number }[][] = [];

      // Calculate points
      for (let y = 0; y <= rows; y++) {
        const row: { x: number, y: number }[] = [];
        for (let x = 0; x <= cols; x++) {
          const px = x * currentSpacingX;
          // Base y position
          const pyBase = y * currentSpacingY;
          
          // Add wave effect using sine waves
          const wave1 = Math.sin(x * 0.2 + time) * 20;
          const wave2 = Math.cos(y * 0.3 + time * 0.8) * 15;
          const wave3 = Math.sin((x + y) * 0.1 + time * 1.2) * 10;
          
          // Perspective effect: waves are smaller at the top (distant) and larger at the bottom (near)
          const depthFactor = y / rows;
          const py = pyBase + (wave1 + wave2 + wave3) * depthFactor;

          row.push({ x: px, y: py });
        }
        points.push(row);
      }

      // Draw triangles
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const p1 = points[y][x];
          const p2 = points[y][x + 1];
          const p3 = points[y + 1][x];
          const p4 = points[y + 1][x + 1];

          // Triangle 1 (top-left)
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.lineTo(p3.x, p3.y);
          ctx.closePath();
          ctx.stroke();

          // Triangle 2 (bottom-right)
          ctx.beginPath();
          ctx.moveTo(p2.x, p2.y);
          ctx.lineTo(p4.x, p4.y);
          ctx.lineTo(p3.x, p3.y);
          ctx.closePath();
          ctx.stroke();
        }
      }

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full block"
      style={{ background: '#000' }}
    />
  );
}

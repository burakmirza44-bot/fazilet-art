import { useEffect, useRef } from 'react';

// ─── D2Q9 Lattice Boltzmann — Ebru (Turkish marbling) style ───────────────
const GW = 200, GH = 112;   // simulation grid (16:9)
const Q  = 9;

const EX = [ 0, 1, 0,-1, 0, 1,-1,-1, 1];
const EY = [ 0, 0, 1, 0,-1, 1, 1,-1,-1];
const W9 = [4/9, 1/9, 1/9, 1/9, 1/9, 1/36, 1/36, 1/36, 1/36];

// Higher TAU = more viscous = more ebru-like (carrageenan water)
const TAU = 0.78;

// Paint pigment colors on dark background (R, G, B in 0-1)
const PAINT: [number, number, number][] = [
  [0.97, 0.93, 0.82],   // 0 — warm cream / white
  [0.88, 0.65, 0.16],   // 1 — gold / amber
  [0.20, 0.74, 0.82],   // 2 — teal
  [0.80, 0.30, 0.50],   // 3 — rose / magenta
  [0.38, 0.55, 0.90],   // 4 — soft indigo
];
const NC = PAINT.length;

// ─── Props (kept for API compatibility, not used) ──────────────────────────
export default function InteractiveLines({
  color = '', density = 0, speed = 0,
  wobble = 0, interact = 0, lineWidth = 0, glow = 0,
}: {
  color?: string; density?: number; speed?: number;
  wobble?: number; interact?: number; lineWidth?: number; glow?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;

    // ─── Allocate LBM arrays ───────────────────────────────────────────────
    const N   = GW * GH;
    const f   = new Float32Array(N * Q);
    const ft  = new Float32Array(N * Q);
    const rho = new Float32Array(N);
    const VX  = new Float32Array(N);
    const VY  = new Float32Array(N);

    // One dye channel per paint color
    const dye : Float32Array[] = Array.from({ length: NC }, () => new Float32Array(N));
    const dyeT: Float32Array[] = Array.from({ length: NC }, () => new Float32Array(N));

    // ─── Init LBM at equilibrium ───────────────────────────────────────────
    for (let i = 0; i < N; i++) {
      rho[i] = 1.0;
      for (let q = 0; q < Q; q++) f[i * Q + q] = W9[q];
    }

    // ─── Helpers ──────────────────────────────────────────────────────────
    const gi = (x: number, y: number) => y * GW + x;

    const feq = (q: number, r: number, u: number, v: number) => {
      const cu = EX[q] * u + EY[q] * v;
      return W9[q] * r * (1 + 3*cu + 4.5*cu*cu - 1.5*(u*u + v*v));
    };

    // Paint drop: injects a gaussian blob of color c
    const addDrop = (
      cx: number, cy: number, r: number,
      c: number, strength: number
    ) => {
      const r2 = r * r;
      for (let dy2 = -Math.ceil(r); dy2 <= Math.ceil(r); dy2++) {
        for (let dx2 = -Math.ceil(r); dx2 <= Math.ceil(r); dx2++) {
          const x = Math.round(cx + dx2), y = Math.round(cy + dy2);
          if (x < 0 || x >= GW || y < 0 || y >= GH) continue;
          const d2 = dx2*dx2 + dy2*dy2;
          if (d2 > r2) continue;
          const w = Math.exp(-d2 / (r2 * 0.45)) * strength;
          const i = gi(x, y);
          dye[c][i] = Math.min(1, dye[c][i] + w);
        }
      }
    };

    // ─── Initial ebru drop pattern — "taş ebrisi" (stone marbling) ────────
    // Classic rows of alternating color drops
    const dropGrid = [
      // [cx%, cy%, radius, colorIdx, strength]
      [0.18, 0.25, 11, 0, 0.95],
      [0.42, 0.25, 10, 1, 0.90],
      [0.65, 0.25,  9, 2, 0.88],
      [0.85, 0.28,  8, 3, 0.85],

      [0.10, 0.50, 10, 2, 0.88],
      [0.32, 0.52, 12, 0, 0.95],
      [0.55, 0.50,  9, 4, 0.82],
      [0.76, 0.50, 10, 1, 0.88],
      [0.92, 0.52,  8, 3, 0.80],

      [0.20, 0.76, 10, 3, 0.85],
      [0.45, 0.74,  9, 0, 0.90],
      [0.68, 0.76, 11, 2, 0.88],
      [0.88, 0.74,  8, 4, 0.82],

      // Accent drops in gaps
      [0.28, 0.38,  5, 4, 0.70],
      [0.52, 0.38,  5, 3, 0.65],
      [0.72, 0.38,  5, 0, 0.70],
      [0.15, 0.63,  4, 1, 0.65],
      [0.38, 0.63,  5, 2, 0.68],
      [0.60, 0.63,  4, 1, 0.65],
      [0.82, 0.63,  5, 0, 0.70],
    ];
    dropGrid.forEach(([cx, cy, r, c, s]) =>
      addDrop(cx * GW, cy * GH, r as number, c as number, s as number)
    );

    // ─── Mouse / touch ─────────────────────────────────────────────────────
    const mouse = { gx: GW * 0.5, gy: GH * 0.5, vx: 0, vy: 0, on: false };
    let pmx = -1, pmy = -1;
    let mouseColor = 0;

    const onMove = (e: MouseEvent | TouchEvent) => {
      const rect = canvas.getBoundingClientRect();
      const cx = e instanceof MouseEvent
        ? e.clientX : (e as TouchEvent).touches[0].clientX;
      const cy = e instanceof MouseEvent
        ? e.clientY : (e as TouchEvent).touches[0].clientY;
      const nx = ((cx - rect.left) / rect.width)  * GW;
      const ny = ((cy - rect.top)  / rect.height) * GH;
      if (pmx >= 0) { mouse.vx = nx - pmx; mouse.vy = ny - pmy; }
      mouse.gx = nx; mouse.gy = ny; mouse.on = true;
      pmx = nx; pmy = ny;
    };
    const onOut = () => { mouse.on = false; pmx = pmy = -1; };
    const onDown = () => { mouseColor = (mouseColor + 1) % NC; };

    canvas.addEventListener('mousemove',  onMove);
    canvas.addEventListener('touchmove',  onMove, { passive: true });
    canvas.addEventListener('mouseleave', onOut);
    canvas.addEventListener('touchend',   onOut);
    canvas.addEventListener('mousedown',  onDown);

    // ─── Simulation step ───────────────────────────────────────────────────
    let t = 0;
    let lastDropTime = 0;

    const step = () => {
      t += 0.005;

      // 1. BGK Collision
      const inv = 1 / TAU;
      for (let y = 0; y < GH; y++) {
        for (let x = 0; x < GW; x++) {
          const i = gi(x, y);
          const base = i * Q;
          let r = 0, u = 0, v = 0;
          for (let q = 0; q < Q; q++) {
            const fq = f[base + q];
            r += fq; u += EX[q] * fq; v += EY[q] * fq;
          }
          if (r > 1e-8) { u /= r; v /= r; } else { u = v = 0; }
          const spd = Math.sqrt(u*u + v*v);
          if (spd > 0.12) { const s = 0.12 / spd; u *= s; v *= s; }
          rho[i] = r; VX[i] = u; VY[i] = v;
          for (let q = 0; q < Q; q++) {
            f[base + q] += (feq(q, r, u, v) - f[base + q]) * inv;
          }
        }
      }

      // 2. Ebru-style combing forces — sinusoidal waves create the
      //    characteristic stretched-filament patterns of traditional ebru
      {
        const comb1 = t * 0.22;   // slow horizontal comb
        const comb2 = t * 0.17;   // slow vertical comb
        const cStr  = 0.000022;

        for (let y = 0; y < GH; y++) {
          for (let x = 0; x < GW; x++) {
            const i    = gi(x, y);
            const base = i * Q;
            const xn   = x / GW, yn = y / GH;

            // Layered sinusoidal combing (simulates comb teeth dragging paint)
            const fx = cStr * (
              Math.sin(yn * Math.PI * 5 + comb1) * 1.2 +
              Math.sin(yn * Math.PI * 2 - comb1 * 0.6) * 0.5 +
              Math.cos(xn * Math.PI * 3 + comb2) * 0.4
            );
            const fy = cStr * (
              Math.cos(xn * Math.PI * 4 + comb2) * 0.8 +
              Math.sin(xn * Math.PI * 2 - comb2 * 0.8) * 0.4 +
              Math.sin(yn * Math.PI * 6 + comb1 * 0.5) * 0.3
            );

            for (let q = 0; q < Q; q++) {
              f[base + q] += W9[q] * 3 * (EX[q] * fx + EY[q] * fy);
            }
          }
        }
      }

      // 3. Mouse: force + paint injection
      if (mouse.on) {
        const R = 5, R2 = R * R;
        const spd = Math.sqrt(mouse.vx*mouse.vx + mouse.vy*mouse.vy);
        for (let dy2 = -R; dy2 <= R; dy2++) {
          for (let dx2 = -R; dx2 <= R; dx2++) {
            const nx = Math.round(mouse.gx + dx2);
            const ny = Math.round(mouse.gy + dy2);
            if (nx < 1 || nx >= GW - 1 || ny < 1 || ny >= GH - 1) continue;
            const d2 = dx2*dx2 + dy2*dy2;
            if (d2 > R2) continue;
            const w    = Math.exp(-d2 / (R2 * 0.4));
            const i    = gi(nx, ny);
            const base = i * Q;
            const fv   = 0.0003 * w;
            for (let q = 0; q < Q; q++) {
              f[base + q] += W9[q] * 3 * (EX[q] * mouse.vx * fv + EY[q] * mouse.vy * fv);
            }
            // Inject paint of current color when moving fast enough
            if (spd > 0.5) {
              dye[mouseColor][i] = Math.min(1, dye[mouseColor][i] + 0.2 * w);
            }
          }
        }
        mouse.vx *= 0.80; mouse.vy *= 0.80;
      }

      // 4. Periodic auto-drops (artist adding paint to the bath)
      if (t - lastDropTime > 0.6 + Math.sin(t) * 0.2) {
        lastDropTime = t;
        const cx = GW * (0.15 + Math.random() * 0.70);
        const cy = GH * (0.15 + Math.random() * 0.70);
        const c  = Math.floor(Math.random() * NC);
        const r  = 3 + Math.random() * 5;
        addDrop(cx, cy, r, c, 0.55 + Math.random() * 0.35);
      }

      // 5. Streaming — pull scheme
      for (let y = 0; y < GH; y++) {
        for (let x = 0; x < GW; x++) {
          const dest = gi(x, y) * Q;
          for (let q = 0; q < Q; q++) {
            const sx = (x - EX[q] + GW) % GW;
            const sy = (y - EY[q] + GH) % GH;
            ft[dest + q] = f[gi(sx, sy) * Q + q];
          }
        }
      }
      f.set(ft);

      // 6. Dye advection for each color channel (semi-Lagrangian)
      const DT = 1.5;
      for (let c = 0; c < NC; c++) {
        const dc = dye[c], dcT = dyeT[c];
        for (let y = 0; y < GH; y++) {
          for (let x = 0; x < GW; x++) {
            const i  = gi(x, y);
            const px = ((x - VX[i] * DT) % GW + GW) % GW;
            const py = ((y - VY[i] * DT) % GH + GH) % GH;
            const x0 = Math.floor(px), y0 = Math.floor(py);
            const x1 = (x0 + 1) % GW,  y1 = (y0 + 1) % GH;
            const fx2 = px - x0,        fy2 = py - y0;
            dcT[i] = (
              dc[gi(x0, y0)] * (1 - fx2) * (1 - fy2) +
              dc[gi(x1, y0)] * fx2       * (1 - fy2) +
              dc[gi(x0, y1)] * (1 - fx2) * fy2       +
              dc[gi(x1, y1)] * fx2       * fy2
            ) * 0.9975; // very slow dissipation — preserve paint
          }
        }
        dye[c].set(dcT);
      }
    };

    // ─── Offscreen canvas (sim resolution) ────────────────────────────────
    const off  = document.createElement('canvas');
    off.width  = GW; off.height = GH;
    const octx = off.getContext('2d')!;
    const img  = octx.createImageData(GW, GH);
    const pix  = img.data;

    // Background color components
    const BG_R = 10, BG_G = 10, BG_B = 10; // #0a0a0a

    const draw = () => {
      for (let y = 0; y < GH; y++) {
        for (let x = 0; x < GW; x++) {
          const i = gi(x, y);

          // Sum dye concentrations and weighted color
          let totalDye = 0;
          let cr = 0, cg = 0, cb = 0;
          for (let c = 0; c < NC; c++) {
            const d = dye[c][i];
            if (d < 0.001) continue;
            totalDye += d;
            cr += d * PAINT[c][0];
            cg += d * PAINT[c][1];
            cb += d * PAINT[c][2];
          }

          let pr: number, pg: number, pb: number;
          if (totalDye < 0.001) {
            pr = BG_R; pg = BG_G; pb = BG_B;
          } else {
            // Normalize to get weighted average paint color
            const inv2 = 1 / totalDye;
            cr *= inv2; cg *= inv2; cb *= inv2;

            // Alpha: how opaque the paint is (ebru paint is quite opaque)
            const alpha = Math.min(1, totalDye * 1.6);
            const inv3  = 1 - alpha;
            pr = Math.round(BG_R * inv3 + cr * alpha * 255);
            pg = Math.round(BG_G * inv3 + cg * alpha * 255);
            pb = Math.round(BG_B * inv3 + cb * alpha * 255);
          }

          // Subtle brightness boost at high velocity (fluid shimmer)
          const spd = Math.sqrt(VX[i]*VX[i] + VY[i]*VY[i]);
          const shimmer = spd * 120;
          const p = i * 4;
          pix[p]     = Math.min(255, pr + shimmer);
          pix[p + 1] = Math.min(255, pg + shimmer);
          pix[p + 2] = Math.min(255, pb + shimmer);
          pix[p + 3] = 255;
        }
      }
      octx.putImageData(img, 0, 0);

      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(off, 0, 0, canvas.width, canvas.height);
    };

    // ─── Animation loop ────────────────────────────────────────────────────
    let animId: number;
    let running = true;

    const loop = () => {
      if (!running) return;
      const cw = canvas.offsetWidth, ch = canvas.offsetHeight;
      if (canvas.width !== cw || canvas.height !== ch) {
        canvas.width = cw; canvas.height = ch;
      }
      step(); step();
      draw();
      animId = requestAnimationFrame(loop);
    };

    animId = requestAnimationFrame(loop);

    return () => {
      running = false;
      cancelAnimationFrame(animId);
      canvas.removeEventListener('mousemove',  onMove);
      canvas.removeEventListener('touchmove',  onMove);
      canvas.removeEventListener('mouseleave', onOut);
      canvas.removeEventListener('touchend',   onOut);
      canvas.removeEventListener('mousedown',  onDown);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute', inset: 0,
        width: '100%', height: '100%',
        display: 'block',
      }}
    />
  );
}

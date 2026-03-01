/**
 * IslamicGeometric.tsx
 * Canvas tabanlı İslami geometrik desen arka planı.
 * 8-kollu yıldız (Sekiz Köşeli Yıldız) motifi + bağlantı şeritleri.
 * Fare pozisyonuna göre altın parıltı efekti.
 */
import { useEffect, useRef } from 'react';

// Altın renk (warm gold)
const GOLD: [number, number, number] = [210, 172, 80];

// 8-kollu yıldızın iç yarıçapı oranı = tan(π/8) ≈ 0.4142
const TAN_PI8 = Math.tan(Math.PI / 8); // ≈ 0.4142

export default function IslamicGeometric() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouse = useRef({ x: -1, y: -1, active: false });

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx    = canvas.getContext('2d')!;
    let raf: number;
    let W = 0, H = 0;

    // ── Boyut ayarı ───────────────────────────────────────
    const resize = () => {
      W = canvas.width  = window.innerWidth;
      H = canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // ── Fare takibi ───────────────────────────────────────
    const onMove = (e: MouseEvent) => {
      mouse.current = { x: e.clientX, y: e.clientY, active: true };
    };
    const onLeave = () => { mouse.current.active = false; };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseleave', onLeave);

    // ── 8-kollu yıldız çizimi ─────────────────────────────
    // cx, cy: merkez  |  R: dış yarıçap  |  rot: başlangıç açısı
    const drawStar8 = (cx: number, cy: number, R: number, rot = 0) => {
      const ri = R * TAN_PI8;
      ctx.beginPath();
      for (let k = 0; k < 16; k++) {
        const a = rot + k * Math.PI / 8 - Math.PI / 2;
        const r = k % 2 === 0 ? R : ri;
        k === 0
          ? ctx.moveTo(cx + r * Math.cos(a), cy + r * Math.sin(a))
          : ctx.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
      }
      ctx.closePath();
    };

    // ── İç sekizgen (yıldızın göbek sekizgeni) ────────────
    const drawOctagon = (cx: number, cy: number, r: number) => {
      ctx.beginPath();
      for (let k = 0; k < 8; k++) {
        const a = k * Math.PI / 4 + Math.PI / 8 - Math.PI / 2;
        k === 0
          ? ctx.moveTo(cx + r * Math.cos(a), cy + r * Math.sin(a))
          : ctx.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
      }
      ctx.closePath();
    };

    // ── Yatay / dikey şerit (bağlantı bandı) ─────────────
    // İki nokta arasında iki paralel çizgi çizer (şerit efekti)
    const drawStrap = (
      x1: number, y1: number,
      x2: number, y2: number,
      hw: number,   // şerit yarı-genişliği
      color: string,
    ) => {
      const dx = x2 - x1, dy = y2 - y1;
      const len = Math.sqrt(dx * dx + dy * dy);
      if (len < 1) return;
      const nx = (-dy / len) * hw;
      const ny = ( dx / len) * hw;
      ctx.strokeStyle = color;
      // Şerit çizgisi 1
      ctx.beginPath();
      ctx.moveTo(x1 + nx, y1 + ny);
      ctx.lineTo(x2 + nx, y2 + ny);
      ctx.stroke();
      // Şerit çizgisi 2
      ctx.beginPath();
      ctx.moveTo(x1 - nx, y1 - ny);
      ctx.lineTo(x2 - nx, y2 - ny);
      ctx.stroke();
    };

    // ── Ana çizim döngüsü ─────────────────────────────────
    const frame = (t: number) => {
      ctx.clearRect(0, 0, W, H);

      // Arka plan
      ctx.fillStyle = '#0a0a0a';
      ctx.fillRect(0, 0, W, H);

      // Tile boyutu — ekran boyutuna göre ölçeklenir (80–130 px arası)
      const T  = Math.max(80, Math.min(130, Math.min(W, H) / 8.5));
      const R  = T * 0.37;          // yıldız dış yarıçapı
      const ri = R * TAN_PI8;       // yıldız iç yarıçapı
      // Şerit genişliği: yıldız ucundaki komşu iç köşe açıklığı
      const strapHW = ri * Math.sin(Math.PI / 8) * 0.9;

      const [gr, gg, gb] = GOLD;
      const glowR = Math.min(W, H) * 0.5;
      const { x: mx, y: my, active } = mouse.current;

      // Hafif nefes animasyonu
      const breathe = 1 + 0.04 * Math.sin(t * 0.00035);

      const cols = Math.ceil(W / T) + 2;
      const rows = Math.ceil(H / T) + 2;

      // ── Döşeme ────────────────────────────────────────────
      for (let j = -1; j <= rows; j++) {
        for (let i = -1; i <= cols; i++) {

          const cx = (i + 0.5) * T;
          const cy = (j + 0.5) * T;

          // Farenin bu yıldıza uzaklığına göre parlaklık
          let alpha = 0.14;
          if (active) {
            const d = Math.sqrt((cx - mx) ** 2 + (cy - my) ** 2);
            alpha = 0.08 + 0.52 * Math.max(0, 1 - d / glowR);
          }
          alpha *= breathe;

          const aStr  = alpha.toFixed(3);
          const aHalf = (alpha * 0.55).toFixed(3);
          const aLow  = (alpha * 0.35).toFixed(3);

          const col  = `rgba(${gr},${gg},${gb},${aStr})`;
          const colH = `rgba(${gr},${gg},${gb},${aHalf})`;
          const colL = `rgba(${gr},${gg},${gb},${aLow})`;

          // ── 1. Yıldız dolgu (çok ince) ────────────────────
          drawStar8(cx, cy, R);
          ctx.fillStyle = `rgba(${gr},${gg},${gb},${(alpha * 0.07).toFixed(3)})`;
          ctx.fill();

          // ── 2. Yıldız konturu ──────────────────────────────
          ctx.strokeStyle = col;
          ctx.lineWidth = 1.15;
          drawStar8(cx, cy, R);
          ctx.stroke();

          // ── 3. İç sekizgen ─────────────────────────────────
          ctx.strokeStyle = colH;
          ctx.lineWidth = 0.65;
          drawOctagon(cx, cy, ri);
          ctx.stroke();

          // ── 4. Merkez küçük daire ──────────────────────────
          ctx.strokeStyle = colL;
          ctx.lineWidth = 0.5;
          ctx.beginPath();
          ctx.arc(cx, cy, ri * 0.38, 0, Math.PI * 2);
          ctx.stroke();

          // ── 5. Yatay şerit → sağ komşuya ──────────────────
          // Sağ yıldızın merkezi: cx + T
          // Mevcut yıldızın sağ ucu: cx + R
          // Sağ yıldızın sol ucu: (cx + T) - R
          ctx.lineWidth = 0.85;
          drawStrap(
            cx + R,     cy,
            cx + T - R, cy,
            strapHW, colH,
          );

          // ── 6. Dikey şerit → alt komşuya ──────────────────
          drawStrap(
            cx, cy + R,
            cx, cy + T - R,
            strapHW, colH,
          );

          // ── 7. Çapraz şerit → sağ-alt komşuya (45°) ──────
          // 45° yönündeki yıldız ucunun yansıması = R / √2
          const d45 = R / Math.SQRT2;
          // 45°: NE-SE diagonal — right-down neighbor
          drawStrap(
            cx + d45, cy + d45,
            cx + T - d45, cy + T - d45,
            strapHW * 0.75, colL,
          );

          // ── 8. Çapraz şerit → sol-alt komşuya (135°) ─────
          drawStrap(
            cx - d45, cy + d45,
            cx - T + d45, cy + T - d45,
            strapHW * 0.75, colL,
          );

          // ── 9. Köşe baklava (şerit kesişim noktası) ───────
          // Yıldızlar arasındaki boşluk ortasında küçük karo
          const mx2 = cx + T / 2;
          const my2 = cy + T / 2;
          const kR  = strapHW * 1.1;
          ctx.strokeStyle = colL;
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          ctx.moveTo(mx2,       my2 - kR);
          ctx.lineTo(mx2 + kR, my2);
          ctx.lineTo(mx2,       my2 + kR);
          ctx.lineTo(mx2 - kR, my2);
          ctx.closePath();
          ctx.stroke();
        }
      }

      // ── Fare altın parıltı ─────────────────────────────────
      if (active) {
        const grd = ctx.createRadialGradient(mx, my, 0, mx, my, glowR * 0.9);
        grd.addColorStop(0,   `rgba(${gr},${gg},${gb},0.07)`);
        grd.addColorStop(0.5, `rgba(${gr},${gg},${gb},0.02)`);
        grd.addColorStop(1,   'rgba(0,0,0,0)');
        ctx.fillStyle = grd;
        ctx.fillRect(0, 0, W, H);
      }

      raf = requestAnimationFrame(frame);
    };

    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseleave', onLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: 0,
        width:  '100%',
        height: '100%',
        display: 'block',
      }}
    />
  );
}

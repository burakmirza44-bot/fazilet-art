/**
 * NotFound.tsx — 404 sayfası
 */
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';

const F = "'proxima-nova','Nunito Sans','Gill Sans MT',sans-serif";

export default function NotFound() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: F, padding: '40px 24px', textAlign: 'center', background: 'var(--c-bg, #fff)', color: 'var(--c-ink, #111)' }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24 }}
      >
        <p style={{ fontSize: 9, letterSpacing: '0.55em', textTransform: 'uppercase', color: '#ccc', margin: 0, fontWeight: 400 }}>
          404
        </p>

        <h1 style={{ fontSize: 'clamp(28px, 4vw, 48px)', fontWeight: 200, margin: 0, letterSpacing: '0.08em', textTransform: 'uppercase', lineHeight: 1.1 }}>
          Page Not Found
        </h1>

        <div style={{ width: 32, height: 1, background: '#e0e0e0', margin: '4px 0' }} />

        <p style={{ fontSize: 13, fontWeight: 300, color: '#888', margin: 0, maxWidth: '36ch', lineHeight: 1.8 }}>
          The page you're looking for doesn't exist or has been moved.
        </p>

        <Link
          to="/"
          style={{
            marginTop: 8,
            fontFamily: F, fontSize: 9, letterSpacing: '0.42em', textTransform: 'uppercase',
            fontWeight: 400, color: '#111', textDecoration: 'none',
            padding: '11px 28px', border: '1px solid rgba(0,0,0,0.16)',
            transition: 'all 0.25s',
            display: 'inline-block',
          }}
          onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.background = '#111'; el.style.color = '#fff'; }}
          onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.background = 'transparent'; el.style.color = '#111'; }}
        >
          Return Home
        </Link>
      </motion.div>
    </div>
  );
}

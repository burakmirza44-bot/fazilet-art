/**
 * PrivatePortfolio.tsx
 *
 * Route: /portfolio/:token
 * ─ Sanatçının gizli portföy sayfası
 * ─ is_public kontrolü YOK — link sahibi her zaman görebilir
 * ─ Eserler büyük grid'de, lightbox ile açılır
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams }                         from 'react-router-dom';
import { motion, AnimatePresence }           from 'motion/react';

const PX  = "'proxima-nova','Nunito Sans','Gill Sans MT',sans-serif";
const SER = "'Cormorant Garamond','Didot','Georgia',serif";

// ─── Types ────────────────────────────────────────────────
interface Artwork {
  id: number;
  title: string;
  year: string;
  medium: string;
  dimensions: string;
  status: string;
  image_url: string;
}
interface ArtistData {
  id: string;
  name: string;
  bio: string;
  medium: string;
  image_url: string | null;
  artworks: Artwork[];
}

// ─── Lightbox ─────────────────────────────────────────────
function Lightbox({ artworks, index, onClose, onNav }: {
  artworks: Artwork[]; index: number;
  onClose: () => void; onNav: (i: number) => void;
}) {
  const aw = artworks[index];

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowRight' && index < artworks.length - 1) onNav(index + 1);
      if (e.key === 'ArrowLeft'  && index > 0) onNav(index - 1);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [index, artworks.length]);

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 2000,
        background: 'rgba(0,0,0,0.94)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      {/* Image + info */}
      <motion.div
        key={aw.id}
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        onClick={e => e.stopPropagation()}
        style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          maxWidth: '85vw', maxHeight: '92vh',
        }}
      >
        <img src={aw.image_url} alt={aw.title}
          style={{ maxWidth: '100%', maxHeight: '76vh', objectFit: 'contain', display: 'block' }} />

        <div style={{ marginTop: 20, textAlign: 'center' }}>
          <p style={{ fontFamily: SER, fontSize: 20, fontWeight: 300,
            color: '#fff', letterSpacing: '0.04em', margin: '0 0 6px' }}>
            {aw.title}
          </p>
          <p style={{ fontFamily: PX, fontSize: 10, fontWeight: 300,
            letterSpacing: '0.28em', color: 'rgba(255,255,255,0.4)',
            textTransform: 'uppercase', margin: 0 }}>
            {[aw.year, aw.medium, aw.dimensions].filter(Boolean).join('  ·  ')}
          </p>
        </div>

        {/* Counter */}
        <p style={{ fontFamily: PX, fontSize: 9, letterSpacing: '0.3em',
          color: 'rgba(255,255,255,0.25)', textTransform: 'uppercase', marginTop: 14 }}>
          {index + 1} / {artworks.length}
        </p>
      </motion.div>

      {/* Nav arrows */}
      {index > 0 && (
        <button onClick={e => { e.stopPropagation(); onNav(index - 1); }}
          style={{
            position: 'fixed', left: 24, top: '50%', transform: 'translateY(-50%)',
            background: 'none', border: '1px solid rgba(255,255,255,0.2)',
            color: '#fff', cursor: 'pointer', width: 48, height: 48,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 20, transition: 'border-color 0.2s',
          }}
          onMouseEnter={e => (e.currentTarget.style.borderColor = '#fff')}
          onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)')}
        >
          ←
        </button>
      )}
      {index < artworks.length - 1 && (
        <button onClick={e => { e.stopPropagation(); onNav(index + 1); }}
          style={{
            position: 'fixed', right: 24, top: '50%', transform: 'translateY(-50%)',
            background: 'none', border: '1px solid rgba(255,255,255,0.2)',
            color: '#fff', cursor: 'pointer', width: 48, height: 48,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 20, transition: 'border-color 0.2s',
          }}
          onMouseEnter={e => (e.currentTarget.style.borderColor = '#fff')}
          onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)')}
        >
          →
        </button>
      )}

      {/* Close */}
      <button onClick={onClose}
        style={{
          position: 'fixed', top: 20, right: 24,
          background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)',
          cursor: 'pointer', fontSize: 28, lineHeight: 1,
          transition: 'color 0.2s',
        }}
        onMouseEnter={e => (e.currentTarget.style.color = '#fff')}
        onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.5)')}
      >
        ×
      </button>
    </motion.div>
  );
}

// ─── Main ─────────────────────────────────────────────────
export default function PrivatePortfolio() {
  const { token } = useParams<{ token: string }>();
  const [data, setData]     = useState<ArtistData | null>(null);
  const [notFound, setNF]   = useState(false);
  const [loading, setLoad]  = useState(true);
  const [lbIndex, setLbIdx] = useState<number | null>(null);

  useEffect(() => {
    fetch(`/api/artists/private/${token}`)
      .then(r => {
        if (r.status === 404) { setNF(true); return null; }
        return r.json();
      })
      .then(json => {
        if (json) setData(json);
        setLoad(false);
      })
      .catch(() => { setNF(true); setLoad(false); });
  }, [token]);

  const publicArtworks = data?.artworks.filter(a => a.status === 'Public') ?? [];

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: '#fff', fontFamily: PX,
      fontSize: 9, letterSpacing: '0.4em', color: '#ccc',
      textTransform: 'uppercase' }}>
      Loading…
    </div>
  );

  if (notFound || !data) return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', background: '#fff',
      fontFamily: PX, textAlign: 'center', padding: 32 }}>
      <p style={{ fontSize: 9, letterSpacing: '0.4em', color: '#ccc',
        textTransform: 'uppercase', margin: '0 0 16px' }}>
        404 — Page Not Found
      </p>
      <p style={{ fontFamily: SER, fontSize: 24, fontWeight: 300, color: '#111',
        margin: 0 }}>
        This portfolio link is invalid or has expired.
      </p>
    </div>
  );

  return (
    <div style={{ background: '#fff', minHeight: '100vh', fontFamily: PX }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,300;6..12,400&family=Cormorant+Garamond:wght@300;400&display=swap');
        .aw-thumb:hover img { transform: scale(1.04); }
        .aw-thumb:hover .aw-over { background: rgba(0,0,0,0.22) !important; }
      `}</style>

      {/* ── Header ── */}
      <header style={{
        background: '#0a0a0a',
        padding: '48px 64px 40px',
        display: 'flex', alignItems: 'flex-end',
        gap: 40, flexWrap: 'wrap',
      }}>
        {/* Artist photo */}
        {data.image_url && (
          <div style={{ width: 80, height: 96, overflow: 'hidden',
            border: '1px solid rgba(255,255,255,0.1)', flexShrink: 0 }}>
            <img src={data.image_url} alt={data.name}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
        )}

        <div style={{ flex: 1 }}>
          <p style={{ fontFamily: PX, fontSize: 9, fontWeight: 300,
            letterSpacing: '0.38em', color: 'rgba(255,255,255,0.3)',
            textTransform: 'uppercase', margin: '0 0 10px' }}>
            Private Portfolio · Fazilet Secgin Art Project Consultancy
          </p>
          <h1 style={{ fontFamily: SER, fontSize: 'clamp(24px, 4vw, 48px)',
            fontWeight: 300, color: '#fff', letterSpacing: '0.06em',
            margin: '0 0 10px' }}>
            {data.name}
          </h1>
          {data.medium && (
            <p style={{ fontFamily: PX, fontSize: 10, fontWeight: 300,
              letterSpacing: '0.28em', color: 'rgba(255,255,255,0.35)',
              textTransform: 'uppercase', margin: '0 0 14px' }}>
              {data.medium}
            </p>
          )}
          {data.bio && (
            <p style={{ fontFamily: PX, fontSize: 12, fontWeight: 300,
              color: 'rgba(255,255,255,0.45)', lineHeight: 1.8,
              letterSpacing: '0.02em', margin: 0, maxWidth: 560 }}>
              {data.bio}
            </p>
          )}
        </div>

        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <p style={{ fontFamily: PX, fontSize: 9, fontWeight: 300,
            letterSpacing: '0.28em', color: 'rgba(255,255,255,0.2)',
            textTransform: 'uppercase', margin: 0 }}>
            {publicArtworks.length} work{publicArtworks.length !== 1 ? 's' : ''}
          </p>
        </div>
      </header>

      {/* ── Artworks grid ── */}
      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '64px 48px 100px' }}>

        {publicArtworks.length === 0 ? (
          <p style={{ fontFamily: PX, fontSize: 10, letterSpacing: '0.3em',
            color: '#ccc', textTransform: 'uppercase', textAlign: 'center',
            padding: '80px 0' }}>
            No artworks available yet
          </p>
        ) : (
          <div style={{
            columns: 'auto 300px', columnGap: 20,
          }}>
            {publicArtworks.map((aw, i) => (
              <motion.div
                key={aw.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ duration: 0.5, delay: (i % 4) * 0.07 }}
                className="aw-thumb"
                onClick={() => setLbIdx(i)}
                style={{
                  breakInside: 'avoid', marginBottom: 20,
                  cursor: 'pointer', position: 'relative', overflow: 'hidden',
                  display: 'block',
                }}
              >
                <img src={aw.image_url} alt={aw.title}
                  style={{ width: '100%', display: 'block',
                    transition: 'transform 0.7s cubic-bezier(0.25,0.46,0.45,0.94)' }} />

                {/* Hover overlay */}
                <div className="aw-over" style={{
                  position: 'absolute', inset: 0,
                  background: 'rgba(0,0,0,0)',
                  transition: 'background 0.4s',
                  display: 'flex', alignItems: 'flex-end',
                }}>
                  <div style={{
                    width: '100%', padding: '14px 16px',
                    background: 'linear-gradient(transparent, rgba(0,0,0,0.55))',
                  }}>
                    <p style={{ fontFamily: PX, fontSize: 11, fontWeight: 400,
                      color: '#fff', margin: '0 0 2px', letterSpacing: '0.06em' }}>
                      {aw.title}
                    </p>
                    <p style={{ fontFamily: PX, fontSize: 9, fontWeight: 300,
                      color: 'rgba(255,255,255,0.55)', margin: 0,
                      letterSpacing: '0.2em', textTransform: 'uppercase' }}>
                      {[aw.year, aw.medium].filter(Boolean).join(' · ')}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer style={{
        borderTop: '1px solid #f0f0f0', padding: '20px 48px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span style={{ fontFamily: PX, fontSize: 9, letterSpacing: '0.3em',
          color: '#ccc', textTransform: 'uppercase' }}>
          Fazilet Secgin Art Project Consultancy
        </span>
        <span style={{ fontFamily: PX, fontSize: 9, letterSpacing: '0.3em',
          color: '#ddd', textTransform: 'uppercase' }}>
          Private — Confidential
        </span>
      </footer>

      {/* ── Lightbox ── */}
      <AnimatePresence>
        {lbIndex !== null && (
          <Lightbox
            artworks={publicArtworks}
            index={lbIndex}
            onClose={() => setLbIdx(null)}
            onNav={setLbIdx}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
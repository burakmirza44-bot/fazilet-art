/**
 * PrivateArtistView.tsx
 * Gizli sanatçı portfolyo sayfası.
 * Tüm fontlar: Proxima Nova ailesi (logo hariç).
 * Navigasyon: ok tuşları, klavye, swipe.
 * Tema: beyaz / siyah arka plan toggle (ziyaretçi seçer).
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronLeft, ChevronRight, X, Mail } from 'lucide-react';

// ── Tek font ailesi — Proxima Nova / Nunito Sans ───────────────────────────
const F = "'proxima-nova','Nunito Sans','Gill Sans MT','Helvetica Neue',Arial,sans-serif";

// ── Renk temaları ─────────────────────────────────────────────────────────
const LIGHT = {
  bg:          '#ffffff',
  hdrBg:       'rgba(255,255,255,0.95)',
  hdrBorder:   'rgba(0,0,0,0.05)',
  text:        '#111111',
  textSub:     '#555555',
  textMuted:   '#999999',
  textFaint:   '#cccccc',
  divider:     'rgba(0,0,0,0.05)',
  dividerHr:   '#f0f0f0',
  cardBg:      '#f5f5f5',
  btnColor:    '#111111',
  btnBorder:   'rgba(0,0,0,0.16)',
  btnHoverBg:  '#111111',
  btnHoverClr: '#ffffff',
  logoFilter:  'none',
  toggleFill:  '#111111',
  toggleRing:  'rgba(0,0,0,0.15)',
  // Viewer (full-screen)
  vBg:         '#f8f8f8',
  vPanel:      '#f0f0f0',
  vPanelBorder:'rgba(0,0,0,0.07)',
  vText:       '#111',
  vTextMuted:  '#666',
  vTextFaint:  '#aaa',
  vLabel:      '#bbb',
  vIcon:       'rgba(0,0,0,0.3)',
  vIconHover:  '#111',
  vDot:        'rgba(0,0,0,0.18)',
  vDotActive:  'rgba(0,0,0,0.7)',
  vBtnBorder:  'rgba(0,0,0,0.18)',
  vBtnColor:   '#111',
  vBtnHoverBg: '#111',
  vBtnHoverClr:'#fff',
};

const DARK = {
  bg:          '#0c0c0c',
  hdrBg:       'rgba(12,12,12,0.95)',
  hdrBorder:   'rgba(255,255,255,0.05)',
  text:        '#e0e0e0',
  textSub:     '#888888',
  textMuted:   '#555555',
  textFaint:   '#333333',
  divider:     'rgba(255,255,255,0.05)',
  dividerHr:   '#1e1e1e',
  cardBg:      '#161616',
  btnColor:    '#e0e0e0',
  btnBorder:   'rgba(255,255,255,0.16)',
  btnHoverBg:  '#ffffff',
  btnHoverClr: '#111111',
  logoFilter:  'brightness(0) invert(1)',
  toggleFill:  '#e0e0e0',
  toggleRing:  'rgba(255,255,255,0.15)',
  // Viewer (full-screen)
  vBg:         '#0c0c0c',
  vPanel:      '#111111',
  vPanelBorder:'rgba(255,255,255,0.06)',
  vText:       '#f0f0f0',
  vTextMuted:  '#999',
  vTextFaint:  '#555',
  vLabel:      '#444',
  vIcon:       'rgba(255,255,255,0.28)',
  vIconHover:  '#fff',
  vDot:        'rgba(255,255,255,0.15)',
  vDotActive:  'rgba(255,255,255,0.7)',
  vBtnBorder:  'rgba(255,255,255,0.18)',
  vBtnColor:   '#fff',
  vBtnHoverBg: '#fff',
  vBtnHoverClr:'#111',
};

// ── Tipler ────────────────────────────────────────────────────────────────
interface Artwork {
  id: number;
  title: string;
  year: string;
  medium: string;
  dimensions: string;
  description: string;
  image_url: string;
  video_url?: string;
}

interface Artist {
  id: string;
  name: string;
  bio: string;
  medium: string;
  image_url: string | null;
  artworks: Artwork[];
}

// ── Tema toggle ikonu (yarım çember SVG) ──────────────────────────────────
function ThemeToggle({ dark, onToggle }: { dark: boolean; onToggle: () => void }) {
  const C = dark ? DARK : LIGHT;
  return (
    <button
      onClick={onToggle}
      title={dark ? 'Switch to light background' : 'Switch to dark background'}
      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6, display: 'flex', alignItems: 'center', borderRadius: '50%' }}
    >
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        {/* Dış halka */}
        <circle cx="9" cy="9" r="7.5" stroke={C.toggleFill} strokeWidth="1" strokeOpacity="0.4" />
        {/* Sol yarı dolu */}
        <path d="M9 1.5 A7.5 7.5 0 0 0 9 16.5 Z" fill={C.toggleFill} fillOpacity="0.75" />
        {/* Orta dikey çizgi */}
        <line x1="9" y1="1.5" x2="9" y2="16.5" stroke={C.toggleFill} strokeWidth="0.75" strokeOpacity="0.3" />
      </svg>
    </button>
  );
}

// ── Full-screen görüntüleyici ─────────────────────────────────────────────
function ArtworkViewer({
  artworks, index, artistName, dark, onClose, onPrev, onNext,
}: {
  artworks: Artwork[]; index: number; artistName: string; dark: boolean;
  onClose: () => void; onPrev: () => void; onNext: () => void;
}) {
  const aw      = artworks[index];
  const hasPrev = index > 0;
  const hasNext = index < artworks.length - 1;
  const C       = dark ? DARK : LIGHT;

  // Touch swipe ─────────────────────────────────────────
  const touchX = useRef<number | null>(null);
  const onTouchStart = (e: { touches: { clientX: number }[] }) => { touchX.current = (e.touches[0] as Touch).clientX; };
  const onTouchEnd   = (e: { changedTouches: { clientX: number }[] }) => {
    if (touchX.current === null) return;
    const dx = e.changedTouches[0].clientX - touchX.current;
    if (dx < -60 && hasNext) onNext();
    if (dx >  60 && hasPrev) onPrev();
    touchX.current = null;
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.28 }}
      className="pav-viewer"
      style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', background: C.vBg, fontFamily: F, transition: 'background 0.35s ease' }}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      {/* Kapat */}
      <button onClick={onClose}
        style={{ position: 'absolute', top: 24, right: 28, zIndex: 10, background: 'none', border: 'none', cursor: 'pointer', color: C.vIcon, transition: 'color .2s', padding: 4 }}
        onMouseEnter={e => (e.currentTarget.style.color = C.vIconHover)}
        onMouseLeave={e => (e.currentTarget.style.color = C.vIcon)}
      >
        <X size={20} strokeWidth={1.2} />
      </button>

      {/* Sol ok */}
      <button onClick={onPrev} disabled={!hasPrev}
        style={{ position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)', zIndex: 10, background: 'none', border: 'none', cursor: hasPrev ? 'pointer' : 'default', color: C.vIcon, opacity: hasPrev ? 1 : 0, transition: 'all .2s', padding: 8 }}
        onMouseEnter={e => { if (hasPrev) e.currentTarget.style.color = C.vIconHover; }}
        onMouseLeave={e => (e.currentTarget.style.color = C.vIcon)}
      >
        <ChevronLeft size={40} strokeWidth={1} />
      </button>

      {/* Sağ ok */}
      <button onClick={onNext} disabled={!hasNext}
        style={{ position: 'absolute', right: 16, top: '50%', transform: 'translateY(-50%)', zIndex: 10, background: 'none', border: 'none', cursor: hasNext ? 'pointer' : 'default', color: C.vIcon, opacity: hasNext ? 1 : 0, transition: 'all .2s', padding: 8 }}
        onMouseEnter={e => { if (hasNext) e.currentTarget.style.color = C.vIconHover; }}
        onMouseLeave={e => (e.currentTarget.style.color = C.vIcon)}
      >
        <ChevronRight size={40} strokeWidth={1} />
      </button>

      {/* ── Görsel / Video alanı ── */}
      <div className="pav-viewer-img" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '56px 64px', overflow: 'hidden' }}>
        <AnimatePresence mode="wait" initial={false}>
          {aw.video_url ? (
            <motion.video
              key={aw.id}
              src={aw.video_url}
              controls
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.32 }}
              style={{ maxWidth: '100%', maxHeight: 'calc(100vh - 112px)' }}
            />
          ) : (
            <motion.img
              key={aw.id}
              src={aw.image_url}
              alt={aw.title}
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.02 }}
              transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
              style={{ maxWidth: '100%', maxHeight: 'calc(100vh - 112px)', objectFit: 'contain' }}
            />
          )}
        </AnimatePresence>
      </div>

      {/* ── Sağ detay paneli ── */}
      <div className="pav-viewer-panel" style={{
        width: 320, flexShrink: 0,
        background: C.vPanel,
        borderLeft: `1px solid ${C.vPanelBorder}`,
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        padding: '56px 36px 36px',
        fontFamily: F,
        transition: 'background 0.35s ease, border-color 0.35s ease',
      }}>
        {/* Detay içerik */}
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={aw.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.28 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 24 }}
          >
            {/* Başlık */}
            <div>
              <p style={{ margin: '0 0 8px', fontSize: 9, letterSpacing: '0.42em', textTransform: 'uppercase', color: C.vLabel, fontWeight: 400 }}>
                Work
              </p>
              <h2 style={{ margin: '0 0 6px', fontSize: 22, fontWeight: 300, color: C.vText, letterSpacing: '0.02em', lineHeight: 1.25 }}>
                {aw.title}
              </h2>
              {aw.year && (
                <p style={{ margin: 0, fontSize: 10, letterSpacing: '0.28em', color: C.vTextFaint, textTransform: 'uppercase', fontWeight: 400 }}>
                  {aw.year}
                </p>
              )}
            </div>

            {/* Meta */}
            <div style={{ borderTop: `1px solid ${C.vPanelBorder}`, paddingTop: 22, display: 'flex', flexDirection: 'column', gap: 16 }}>
              {[
                { label: 'Artist',     value: artistName },
                { label: 'Medium',     value: aw.medium },
                { label: 'Dimensions', value: aw.dimensions },
              ].filter(r => r.value).map(r => (
                <div key={r.label}>
                  <p style={{ margin: '0 0 3px', fontSize: 8, letterSpacing: '0.42em', textTransform: 'uppercase', color: C.vLabel, fontWeight: 400 }}>{r.label}</p>
                  <p style={{ margin: 0, fontSize: 12, color: C.vTextMuted, fontWeight: 300, lineHeight: 1.5 }}>{r.value}</p>
                </div>
              ))}
              {aw.description && (
                <div>
                  <p style={{ margin: '0 0 5px', fontSize: 8, letterSpacing: '0.42em', textTransform: 'uppercase', color: C.vLabel, fontWeight: 400 }}>Note</p>
                  <p style={{ margin: 0, fontSize: 12, color: C.vTextFaint, fontWeight: 300, lineHeight: 1.75 }}>{aw.description}</p>
                </div>
              )}
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Alt: dots + inquire */}
        <div>
          {/* Dot navigasyon */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 24, flexWrap: 'wrap' }}>
            {artworks.map((_, i) => (
              <button
                key={i}
                onClick={() => {
                  const diff = i - index;
                  if (diff > 0) for (let j = 0; j < diff; j++) onNext();
                  if (diff < 0) for (let j = 0; j < -diff; j++) onPrev();
                }}
                style={{
                  width: i === index ? 20 : 5, height: 5, borderRadius: 3,
                  background: i === index ? C.vDotActive : C.vDot,
                  border: 'none', cursor: 'pointer', padding: 0,
                  transition: 'all 0.3s ease', flexShrink: 0,
                }}
              />
            ))}
            <span style={{ fontSize: 9, color: C.vTextFaint, letterSpacing: '0.22em', marginLeft: 6, fontWeight: 400 }}>
              {index + 1} / {artworks.length}
            </span>
          </div>

          {/* Inquire */}
          <a
            href={`mailto:info@faziletsecgin.com?subject=Inquiry: ${aw.title} by ${artistName}`}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              fontFamily: F, fontSize: 9, fontWeight: 400,
              letterSpacing: '0.42em', textTransform: 'uppercase',
              color: C.vBtnColor, textDecoration: 'none',
              border: `1px solid ${C.vBtnBorder}`,
              padding: '13px 16px', width: '100%',
              transition: 'all 0.25s',
            }}
            onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.background = C.vBtnHoverBg; el.style.color = C.vBtnHoverClr; }}
            onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.background = 'transparent'; el.style.color = C.vBtnColor; }}
          >
            <Mail size={11} strokeWidth={1.5} />
            Inquire about this work
          </a>
        </div>
      </div>
    </motion.div>
  );
}

// ── Ana sayfa ─────────────────────────────────────────────────────────────
export default function PrivateArtistView() {
  const { id }   = useParams<{ id: string }>();
  const [artist, setArtist]       = useState<Artist | null>(null);
  const [loading, setLoading]     = useState(true);
  const [viewerIdx, setViewerIdx] = useState<number | null>(null);
  const [bgDark, setBgDark]       = useState(false);   // ← beyaz/siyah toggle

  const C = bgDark ? DARK : LIGHT;

  // Klavye navigasyonu
  const handleKey = useCallback((e: KeyboardEvent) => {
    if (viewerIdx === null || !artist) return;
    const n = artist.artworks.length;
    if (e.key === 'ArrowRight') setViewerIdx(i => i !== null ? Math.min(i + 1, n - 1) : null);
    if (e.key === 'ArrowLeft')  setViewerIdx(i => i !== null ? Math.max(i - 1, 0) : null);
    if (e.key === 'Escape')     setViewerIdx(null);
  }, [viewerIdx, artist]);

  useEffect(() => {
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [handleKey]);

  // Veri çekme — önce token ile, bulamazsa ID ile dene (geriye dönük uyumluluk)
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetch(`/api/artists/private/${id}`)
      .then(async r => {
        if (r.ok) return r.json();
        const r2 = await fetch(`/api/artists/${id}`);
        if (r2.ok) return r2.json();
        return null;
      })
      .then(data => setArtist(data))
      .catch(() => setArtist(null))
      .finally(() => setLoading(false));
  }, [id]);

  // ── Yükleniyor ──
  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa', fontFamily: F }}>
        <motion.p
          initial={{ opacity: 0 }} animate={{ opacity: [0, 1, 0] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
          style={{ fontSize: 10, letterSpacing: '0.5em', textTransform: 'uppercase', color: '#ccc', fontWeight: 400 }}
        >
          Loading portfolio
        </motion.p>
      </div>
    );
  }

  // ── Bulunamadı ──
  if (!artist) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#fafafa', fontFamily: F, gap: 16, textAlign: 'center', padding: 40 }}>
        <p style={{ fontSize: 10, letterSpacing: '0.5em', textTransform: 'uppercase', color: '#ccc', margin: '0 0 12px', fontWeight: 400 }}>404</p>
        <p style={{ fontSize: 22, fontWeight: 300, color: '#333', margin: '0 0 8px', letterSpacing: '0.04em' }}>Portfolio not found</p>
        <p style={{ fontSize: 11, letterSpacing: '0.25em', textTransform: 'uppercase', color: '#bbb', margin: 0, fontWeight: 400 }}>This link may have expired or is invalid.</p>
        <p style={{ fontSize: 11, color: '#ddd', margin: '20px 0 0', fontWeight: 300 }}>Please request a new link from the gallery.</p>
      </div>
    );
  }

  const artworks = artist.artworks ?? [];

  return (
    <div style={{ minHeight: '100vh', background: C.bg, fontFamily: F, color: C.text, transition: 'background 0.35s ease, color 0.35s ease' }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,200;6..12,300;6..12,400;6..12,600&display=swap');
        *, *::before, *::after { box-sizing: border-box; }
        .aw-card-img { transition: transform 0.65s cubic-bezier(0.22,1,0.36,1); }
        .aw-card:hover .aw-card-img { transform: scale(1.05); }
        .aw-card { transition: opacity 0.25s; cursor: pointer; }
        .aw-card:hover { opacity: 0.88; }

        /* ── Mobile ── */
        @media (max-width: 768px) {
          .pav-header       { padding: 14px 20px !important; }
          .pav-confidential { display: none !important; }
          .pav-profile      { padding: 40px 20px 36px !important; }
          .pav-profile-grid { grid-template-columns: 1fr !important; gap: 0 !important; }
          .pav-photo        { max-width: 220px; margin: 0 auto 32px; position: static !important; }
          .pav-works        { padding: 0 20px 64px !important; }
          .pav-grid         { grid-template-columns: repeat(2, 1fr) !important; gap: 28px 16px !important; }
          .pav-footer       { padding: 20px !important; flex-direction: column !important; align-items: flex-start !important; }
          .pav-viewer       { flex-direction: column !important; }
          .pav-viewer-img   { flex: 1 !important; padding: 48px 16px 8px !important; }
          .pav-viewer-panel { width: 100% !important; max-height: 38vh !important; border-left: none !important; border-top: 1px solid rgba(128,128,128,0.15) !important; padding: 20px !important; overflow-y: auto !important; flex-shrink: 0 !important; }
          .pav-inquire      { display: none !important; }
        }
        @media (max-width: 400px) {
          .pav-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>

      {/* ── HEADER ── */}
      <header className="pav-header" style={{
        position: 'sticky', top: 0, zIndex: 20,
        background: C.hdrBg,
        backdropFilter: 'blur(12px)',
        borderBottom: `1px solid ${C.hdrBorder}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 48px',
        transition: 'background 0.35s ease, border-color 0.35s ease',
      }}>
        {/* Logo — ana sayfaya link */}
        <a href="/" style={{ display: 'inline-block', lineHeight: 0 }}>
          <img
            src="/logo.png"
            alt="Fazilet Secgin"
            style={{ height: 18, objectFit: 'contain', opacity: 0.85, cursor: 'pointer', filter: C.logoFilter, transition: 'filter 0.35s ease' }}
          />
        </a>

        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          {/* Gizli etiket */}
          <span className="pav-confidential" style={{ fontSize: 8, letterSpacing: '0.5em', textTransform: 'uppercase', color: C.textFaint, fontWeight: 400 }}>
            Confidential Viewing
          </span>

          {/* Beyaz/Siyah toggle */}
          <ThemeToggle dark={bgDark} onToggle={() => setBgDark(d => !d)} />

          {/* Inquire butonu */}
          <a
            href="mailto:info@faziletsecgin.com"
            className="pav-inquire"
            style={{
              fontFamily: F, fontSize: 9, letterSpacing: '0.38em', textTransform: 'uppercase',
              fontWeight: 400, color: C.btnColor, textDecoration: 'none',
              padding: '9px 22px', border: `1px solid ${C.btnBorder}`,
              transition: 'all 0.25s',
            }}
            onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.background = C.btnHoverBg; el.style.color = C.btnHoverClr; }}
            onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.background = 'transparent'; el.style.color = C.btnColor; }}
          >
            Inquire
          </a>
        </div>
      </header>

      {/* ── SANATÇI PROFİL ── */}
      <section className="pav-profile" style={{ maxWidth: 1320, margin: '0 auto', padding: '80px 48px 72px' }}>
        <div className="pav-profile-grid" style={{
          display: 'grid',
          gridTemplateColumns: artist.image_url ? '300px 1fr' : '1fr',
          gap: '0 80px',
          alignItems: 'start',
        }}>

          {/* Fotoğraf */}
          {artist.image_url && (
            <motion.div
              className="pav-photo"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8 }}
              style={{ position: 'sticky', top: 80 }}
            >
              <div style={{ width: '100%', aspectRatio: '3/4', overflow: 'hidden', background: C.cardBg, transition: 'background 0.35s ease' }}>
                <img
                  src={artist.image_url}
                  alt={artist.name}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                />
              </div>
            </motion.div>
          )}

          {/* İsim ve biyografi */}
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.75, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
          >
            <p style={{ margin: '0 0 22px', fontSize: 8, letterSpacing: '0.55em', textTransform: 'uppercase', color: C.textFaint, fontWeight: 400 }}>
              Artist Portfolio
            </p>

            <h1 style={{
              margin: '0 0 14px',
              fontFamily: F,
              fontSize: 'clamp(40px, 5.5vw, 72px)',
              fontWeight: 200,
              color: C.text,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              lineHeight: 1.08,
            }}>
              {artist.name}
            </h1>

            {artist.medium && (
              <p style={{ margin: '0 0 40px', fontSize: 10, letterSpacing: '0.32em', textTransform: 'uppercase', color: C.textMuted, fontWeight: 400 }}>
                {artist.medium}
              </p>
            )}

            <div style={{ width: 40, height: 1, background: C.dividerHr, margin: '0 0 36px', transition: 'background 0.35s ease' }} />

            {artist.bio && (
              <p style={{
                margin: '0 0 48px',
                fontFamily: F,
                fontSize: 'clamp(14px, 1.2vw, 16px)',
                fontWeight: 300,
                color: C.textSub,
                lineHeight: 1.9,
                maxWidth: '58ch',
                letterSpacing: '0.01em',
              }}>
                {artist.bio}
              </p>
            )}

            {artworks.length > 0 && (
              <p style={{ fontSize: 8, letterSpacing: '0.42em', textTransform: 'uppercase', color: C.textFaint, margin: 0, fontWeight: 400 }}>
                {artworks.length} {artworks.length === 1 ? 'work' : 'works'} selected for viewing
              </p>
            )}
          </motion.div>
        </div>
      </section>

      {/* ── ESERLER ── */}
      {artworks.length > 0 && (
        <section className="pav-works" style={{ maxWidth: 1320, margin: '0 auto', padding: '0 48px 120px' }}>

          {/* Bölüm ayırıcı */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 52 }}>
            <div style={{ flex: 1, height: 1, background: C.dividerHr, transition: 'background 0.35s ease' }} />
            <p style={{ margin: 0, fontSize: 8, letterSpacing: '0.55em', textTransform: 'uppercase', color: C.textFaint, fontWeight: 400, flexShrink: 0 }}>
              Works
            </p>
            <div style={{ flex: 1, height: 1, background: C.dividerHr, transition: 'background 0.35s ease' }} />
          </div>

          {/* Grid */}
          <div className="pav-grid" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
            gap: '56px 32px',
          }}>
            {artworks.map((aw, i) => (
              <motion.div
                key={aw.id}
                className="aw-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.55, delay: 0.04 + i * 0.055, ease: [0.22, 1, 0.36, 1] }}
                onClick={() => setViewerIdx(i)}
              >
                {/* Görsel / Video */}
                <div style={{ width: '100%', aspectRatio: '4/5', overflow: 'hidden', background: C.cardBg, marginBottom: 16, transition: 'background 0.35s ease', position: 'relative' }}>
                  {aw.video_url ? (
                    <>
                      <video
                        src={aw.video_url}
                        muted playsInline preload="metadata"
                        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                      />
                      <div style={{
                        position: 'absolute', inset: 0, display: 'flex',
                        alignItems: 'center', justifyContent: 'center',
                        background: 'rgba(0,0,0,0.18)',
                      }}>
                        <span style={{ fontSize: 32, color: '#fff', opacity: 0.85 }}>▶</span>
                      </div>
                    </>
                  ) : (
                    <img
                      className="aw-card-img"
                      src={aw.image_url}
                      alt={aw.title}
                      style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                    />
                  )}
                </div>

                {/* Bilgiler */}
                <div style={{ padding: '0 2px' }}>
                  <h3 style={{
                    margin: '0 0 5px', fontFamily: F,
                    fontSize: 14, fontWeight: 400,
                    color: C.text, letterSpacing: '0.02em', lineHeight: 1.3,
                  }}>
                    {aw.title}
                  </h3>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    {aw.year && (
                      <span style={{ fontSize: 10, color: C.textMuted, letterSpacing: '0.18em', fontWeight: 400 }}>{aw.year}</span>
                    )}
                    {aw.year && aw.medium && (
                      <span style={{ fontSize: 9, color: C.dividerHr }}>·</span>
                    )}
                    {aw.medium && (
                      <span style={{ fontSize: 10, color: C.textMuted, letterSpacing: '0.1em', fontWeight: 300 }}>{aw.medium}</span>
                    )}
                  </div>
                  {aw.dimensions && (
                    <p style={{ margin: '4px 0 0', fontSize: 9, color: C.textFaint, letterSpacing: '0.15em', textTransform: 'uppercase', fontWeight: 400 }}>
                      {aw.dimensions}
                    </p>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* ── FOOTER ── */}
      <footer className="pav-footer" style={{
        borderTop: `1px solid ${C.hdrBorder}`,
        padding: '28px 48px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12,
        transition: 'border-color 0.35s ease',
      }}>
        <img src="/logo.png" alt="Fazilet Secgin" style={{ height: 14, opacity: 0.3, filter: C.logoFilter, transition: 'filter 0.35s ease' }} />
        <p style={{ margin: 0, fontSize: 8, letterSpacing: '0.42em', textTransform: 'uppercase', color: C.textFaint, fontWeight: 400 }}>
          Confidential — For private viewing only
        </p>
      </footer>

      {/* ── FULL-SCREEN VIEWER ── */}
      <AnimatePresence>
        {viewerIdx !== null && (
          <ArtworkViewer
            artworks={artworks}
            index={viewerIdx}
            artistName={artist.name}
            dark={bgDark}
            onClose={() => setViewerIdx(null)}
            onPrev={() => setViewerIdx(i => i !== null ? Math.max(i - 1, 0) : null)}
            onNext={() => setViewerIdx(i => i !== null ? Math.min(i + 1, artworks.length - 1) : null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

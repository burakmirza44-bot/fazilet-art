import { apiFetch } from '../../utils/api';
import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Link } from 'react-router-dom';
import { ImageIcon, Users, Star, Eye, Plus, ArrowRight, CalendarDays } from 'lucide-react';

// ─── Mini donut chart ──────────────────────────────────────
function DonutChart({ public: pub, private: priv, label }: { public: number; private: number; label: string }) {
  const total = pub + priv || 1;
  const pubPct = pub / total;
  const r = 28, cx = 36, cy = 36, stroke = 8;
  const circ = 2 * Math.PI * r;
  const pubArc = circ * pubPct;
  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={72} height={72} viewBox="0 0 72 72">
        {/* Track */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f0f0f0" strokeWidth={stroke} />
        {/* Public arc */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#111" strokeWidth={stroke}
          strokeDasharray={`${pubArc} ${circ}`}
          strokeLinecap="butt"
          style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%', transition: 'stroke-dasharray 0.8s ease' }}
        />
        <text x={cx} y={cy + 5} textAnchor="middle" fontSize={11} fontFamily="serif" fill="#111">
          {pub}
        </text>
      </svg>
      <p className="text-[9px] tracking-[0.22em] uppercase text-ink/40 text-center">{label}</p>
      <div className="flex gap-3 text-[9px] text-ink/50">
        <span className="flex items-center gap-1"><span className="w-2 h-2 bg-ink rounded-sm inline-block"/>Public</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 bg-ink/10 rounded-sm inline-block"/>Private</span>
      </div>
    </div>
  );
}

// ─── Mini bar chart ────────────────────────────────────────
function BarChart({ data }: { data: { label: string; value: number; color?: string }[] }) {
  const max = Math.max(...data.map(d => d.value), 1);
  return (
    <div className="flex items-end gap-2 h-16">
      {data.map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1 group">
          <span className="text-[9px] text-ink/50 opacity-0 group-hover:opacity-100 transition-opacity">
            {d.value}
          </span>
          <motion.div
            initial={{ height: 0 }} animate={{ height: `${(d.value / max) * 52}px` }}
            transition={{ duration: 0.6, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] }}
            style={{ background: d.color || '#111', width: '100%', minHeight: d.value > 0 ? 4 : 0 }}
          />
          <span className="text-[8px] text-ink/40 truncate w-full text-center">{d.label}</span>
        </div>
      ))}
    </div>
  );
}

interface StatsData {
  totalArtworks: number;
  publicArtworks: number;
  privateArtworks: number;
  totalArtists: number;
  publicArtists: number;
  featuredArtists: number;
  recentActivity: { id: number; action: string; item: string; time: string }[];
}

interface RecentArtwork {
  id: number;
  title: string;
  artist: string;
  image_url: string | null;
  status: string;
}

export default function AdminDashboard() {
  const [stats,   setStats]   = useState<StatsData | null>(null);
  const [recent,  setRecent]  = useState<RecentArtwork[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiFetch('/api/stats').then(r => r.ok ? r.json() : null),
      apiFetch('/api/artworks').then(r => r.ok ? r.json() : []),
    ]).then(([s, aw]) => {
      if (s) setStats(s);
      const list = Array.isArray(aw) ? aw : (aw.data ?? []);
      setRecent(list.slice(0, 6));
    }).catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const statCards = [
    { label: 'Total Artists',  value: stats?.totalArtists ?? 0,   sub: `${stats?.publicArtists ?? 0} public`,   icon: Users,      to: '/admin/artists',       color: '#111'    },
    { label: 'Total Artworks', value: stats?.totalArtworks ?? 0,  sub: `${stats?.publicArtworks ?? 0} public`,  icon: ImageIcon,  to: '/admin/artworks',      color: '#111'    },
    { label: 'Featured',       value: stats?.featuredArtists ?? 0,sub: 'on home page',                          icon: Star,       to: '/admin/artists',       color: '#b5860d' },
    { label: 'Public Works',   value: stats?.publicArtworks ?? 0, sub: 'visible on site',                       icon: Eye,        to: '/admin/viewing-rooms', color: '#2d7a2d' },
  ];

  const quickActions = [
    { label: 'Add Artist',    to: '/admin/artists',       icon: Users,       desc: 'Upload artworks & profile' },
    { label: 'Artworks',      to: '/admin/artworks',      icon: ImageIcon,   desc: 'Manage all works'          },
    { label: 'Exhibitions',   to: '/admin/exhibitions',   icon: CalendarDays,desc: 'Upcoming & past shows'     },
    { label: 'Viewing Room',  to: '/admin/viewing-rooms', icon: Eye,         desc: 'Curate online exhibition'  },
  ];

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
      className="space-y-10">

      {/* Header */}
      <header className="flex justify-between items-end pb-6 border-b border-ink/5">
        <div>
          <h1 className="text-3xl font-serif tracking-tight">Dashboard</h1>
          <p className="text-ink/50 text-sm mt-1">
            {new Date().toLocaleDateString('en-GB', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <Link to="/admin/artists"
          className="flex items-center gap-2 bg-ink text-white text-xs tracking-[0.2em] uppercase px-5 py-2.5 hover:bg-ink/90 transition-colors">
          <Plus size={14} /> Add Artist
        </Link>
      </header>

      {/* Stats */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {statCards.map((card, i) => {
          const Icon = card.icon;
          return (
            <motion.div key={card.label} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.06 }}>
              <Link to={card.to}
                className="block bg-white border border-ink/5 p-5 hover:border-ink/15 transition-colors group">
                <div className="flex items-start justify-between mb-4">
                  <div className="p-2 bg-ink/5 group-hover:bg-ink/8 transition-colors">
                    <Icon size={18} strokeWidth={1.5} style={{ color: card.color }} />
                  </div>
                  <ArrowRight size={14} className="text-ink/20 group-hover:text-ink/50 transition-colors mt-0.5" />
                </div>
                <p className="text-2xl font-serif tracking-tight" style={{ color: card.color }}>
                  {loading ? '—' : card.value}
                </p>
                <p className="text-xs text-ink/50 tracking-widest uppercase mt-1">{card.label}</p>
                <p className="text-[10px] text-ink/30 mt-0.5 tracking-wide">{loading ? '…' : card.sub}</p>
              </Link>
            </motion.div>
          );
        })}
      </div>

      {/* ── Collection Overview charts ── */}
      {!loading && stats && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }}>
          <h2 className="text-xs tracking-[0.3em] uppercase text-ink/40 mb-3">Collection Overview</h2>
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">

            {/* Donut — Artists */}
            <div className="bg-white border border-ink/5 p-6 flex items-center gap-6">
              <DonutChart public={stats.publicArtists ?? 0} private={(stats.totalArtists ?? 0) - (stats.publicArtists ?? 0)} label="Artists" />
              <div className="flex-1 space-y-3">
                <div>
                  <div className="flex justify-between text-[10px] text-ink/50 mb-1">
                    <span>Public</span><span className="font-medium text-ink">{stats.publicArtists ?? 0}</span>
                  </div>
                  <div className="h-1 bg-ink/5 rounded-full overflow-hidden">
                    <motion.div initial={{ width: 0 }} animate={{ width: `${stats.totalArtists ? (stats.publicArtists / stats.totalArtists) * 100 : 0}%` }}
                      transition={{ duration: 0.8, ease: [0.22,1,0.36,1] }} className="h-full bg-ink rounded-full" />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-[10px] text-ink/50 mb-1">
                    <span>Featured</span><span className="font-medium text-amber-600">{stats.featuredArtists ?? 0}</span>
                  </div>
                  <div className="h-1 bg-ink/5 rounded-full overflow-hidden">
                    <motion.div initial={{ width: 0 }} animate={{ width: `${stats.totalArtists ? (stats.featuredArtists / stats.totalArtists) * 100 : 0}%` }}
                      transition={{ duration: 0.8, delay: 0.1, ease: [0.22,1,0.36,1] }} className="h-full bg-amber-500 rounded-full" />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-[10px] text-ink/50 mb-1">
                    <span>Private</span><span className="font-medium text-ink/50">{(stats.totalArtists ?? 0) - (stats.publicArtists ?? 0)}</span>
                  </div>
                  <div className="h-1 bg-ink/5 rounded-full overflow-hidden">
                    <motion.div initial={{ width: 0 }} animate={{ width: `${stats.totalArtists ? ((stats.totalArtists - stats.publicArtists) / stats.totalArtists) * 100 : 0}%` }}
                      transition={{ duration: 0.8, delay: 0.2, ease: [0.22,1,0.36,1] }} className="h-full bg-ink/20 rounded-full" />
                  </div>
                </div>
              </div>
            </div>

            {/* Donut — Artworks */}
            <div className="bg-white border border-ink/5 p-6 flex items-center gap-6">
              <DonutChart public={stats.publicArtworks ?? 0} private={(stats.totalArtworks ?? 0) - (stats.publicArtworks ?? 0)} label="Artworks" />
              <div className="flex-1 space-y-3">
                <div>
                  <div className="flex justify-between text-[10px] text-ink/50 mb-1">
                    <span>Public</span><span className="font-medium text-green-700">{stats.publicArtworks ?? 0}</span>
                  </div>
                  <div className="h-1 bg-ink/5 rounded-full overflow-hidden">
                    <motion.div initial={{ width: 0 }} animate={{ width: `${stats.totalArtworks ? (stats.publicArtworks / stats.totalArtworks) * 100 : 0}%` }}
                      transition={{ duration: 0.8, ease: [0.22,1,0.36,1] }} className="h-full bg-green-500 rounded-full" />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-[10px] text-ink/50 mb-1">
                    <span>Private</span><span className="font-medium text-ink/50">{(stats.totalArtworks ?? 0) - (stats.publicArtworks ?? 0)}</span>
                  </div>
                  <div className="h-1 bg-ink/5 rounded-full overflow-hidden">
                    <motion.div initial={{ width: 0 }} animate={{ width: `${stats.totalArtworks ? ((stats.totalArtworks - stats.publicArtworks) / stats.totalArtworks) * 100 : 0}%` }}
                      transition={{ duration: 0.8, delay: 0.1, ease: [0.22,1,0.36,1] }} className="h-full bg-ink/20 rounded-full" />
                  </div>
                </div>
                <div className="pt-1 border-t border-ink/5">
                  <p className="text-[10px] text-ink/40">Total works in collection</p>
                  <p className="text-lg font-serif text-ink">{stats.totalArtworks ?? 0}</p>
                </div>
              </div>
            </div>

            {/* Bar chart — breakdown */}
            <div className="bg-white border border-ink/5 p-6">
              <p className="text-[10px] tracking-[0.25em] uppercase text-ink/40 mb-4">Collection Breakdown</p>
              <BarChart data={[
                { label: 'Artists',   value: stats.totalArtists   ?? 0, color: '#111' },
                { label: 'Public',    value: stats.publicArtworks ?? 0, color: '#2d7a2d' },
                { label: 'Private',   value: (stats.totalArtworks ?? 0) - (stats.publicArtworks ?? 0), color: '#bbb' },
                { label: 'Featured',  value: stats.featuredArtists ?? 0, color: '#b5860d' },
              ]} />
              <div className="mt-4 pt-3 border-t border-ink/5 grid grid-cols-2 gap-2">
                {[
                  { label: 'Total Artists',  val: stats.totalArtists   ?? 0, dot: '#111' },
                  { label: 'Total Works',    val: stats.totalArtworks  ?? 0, dot: '#444' },
                  { label: 'Public Works',   val: stats.publicArtworks ?? 0, dot: '#2d7a2d' },
                  { label: 'Featured',       val: stats.featuredArtists ?? 0, dot: '#b5860d' },
                ].map(item => (
                  <div key={item.label} className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-sm flex-shrink-0" style={{ background: item.dot }} />
                    <span className="text-[9px] text-ink/50 flex-1 truncate">{item.label}</span>
                    <span className="text-[10px] font-medium text-ink">{item.val}</span>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </motion.div>
      )}

      {/* Quick Actions */}
      <div>
        <h2 className="text-xs tracking-[0.3em] uppercase text-ink/40 mb-3">Quick Actions</h2>
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
          {quickActions.map(a => {
            const Icon = a.icon;
            return (
              <Link key={a.label} to={a.to}
                className="flex items-center gap-3 bg-white border border-ink/5 px-4 py-3 hover:border-ink/20 hover:bg-ink/[0.02] transition-colors group">
                <Icon size={16} strokeWidth={1.5} className="text-ink/40 group-hover:text-ink/70 transition-colors flex-shrink-0" />
                <div>
                  <p className="text-xs font-medium tracking-wide text-ink/80">{a.label}</p>
                  <p className="text-[10px] text-ink/35 tracking-wide">{a.desc}</p>
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Recent Artworks */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs tracking-[0.3em] uppercase text-ink/40">Recent Artworks</h2>
          <Link to="/admin/artworks" className="text-[10px] tracking-[0.2em] uppercase text-ink/35 hover:text-ink/70 transition-colors">
            View all →
          </Link>
        </div>

        {loading ? (
          <div className="bg-white border border-ink/5 p-10 text-center text-xs text-ink/30 tracking-widest uppercase">Loading…</div>
        ) : recent.length === 0 ? (
          <div className="bg-white border border-ink/5 p-10 text-center">
            <p className="text-xs text-ink/30 tracking-widest uppercase mb-4">No artworks yet</p>
            <Link to="/admin/artists" className="text-xs tracking-[0.2em] uppercase border border-ink/15 px-4 py-2 hover:bg-ink hover:text-white transition-colors">
              Add First Artist
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-3 xl:grid-cols-6 gap-3">
            {recent.map((aw, i) => (
              <motion.div key={aw.id} initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3, delay: i * 0.04 }}
                className="group relative bg-ink/5 overflow-hidden" style={{ aspectRatio: '3/4' }}>
                {aw.image_url ? (
                  <img src={aw.image_url} alt={aw.title}
                    className="w-full h-full object-cover group-hover:scale-[1.04] transition-transform duration-500" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <ImageIcon size={20} className="text-ink/20" />
                  </div>
                )}
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-2 translate-y-full group-hover:translate-y-0 transition-transform duration-300">
                  <p className="text-[10px] text-white/90 truncate">{aw.title}</p>
                  <p className="text-[9px] text-white/50 tracking-wide uppercase truncate">{aw.artist || '—'}</p>
                </div>
                <div className={`absolute top-2 right-2 w-1.5 h-1.5 rounded-full ${aw.status === 'Public' ? 'bg-green-400' : 'bg-ink/20'}`} />
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Activity */}
      {stats && stats.recentActivity.length > 0 && (
        <div>
          <h2 className="text-xs tracking-[0.3em] uppercase text-ink/40 mb-3">Recent Activity</h2>
          <div className="bg-white border border-ink/5">
            {stats.recentActivity.slice(0, 5).map(a => (
              <div key={a.id} className="px-5 py-3 flex justify-between items-center border-b border-ink/5 last:border-0 hover:bg-ink/[0.02] transition-colors">
                <div>
                  <p className="text-xs font-medium tracking-wide text-ink/80">{a.action}</p>
                  <p className="text-[10px] text-ink/40 mt-0.5">{a.item}</p>
                </div>
                <span className="text-[10px] text-ink/30 flex-shrink-0 ml-4">{a.time}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

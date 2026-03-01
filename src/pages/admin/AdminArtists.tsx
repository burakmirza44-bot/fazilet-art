import { apiFetch } from '../../utils/api';
import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Plus, Search, Link as LinkIcon, Check, X, UploadCloud,
  Trash2, Image as ImageIcon, RefreshCw, Eye, EyeOff,
  Star, Copy, ExternalLink, ChevronRight, Shield,
} from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────
interface Artist {
  id: string;
  name: string;
  bio: string;
  medium?: string;
  is_public?: number;
  is_featured?: number;
  artworksCount: number;
  status: string;
  image_url: string;
  private_token?: string;
}

interface ArtworkForm {
  id?: string | number;
  title: string;
  year: string;
  medium: string;
  dimensions: string;
  image_url?: string;
  file?: File;
  preview?: string;
  status: string;
  isDeleted?: boolean;
}

// ─── Private Link Modal ───────────────────────────────────────────────────────
function PrivateLinkModal({ artist, onClose }: { artist: Artist; onClose: () => void }) {
  const [copied, setCopied]           = useState<'link' | 'token' | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [token, setToken]             = useState(artist.private_token ?? '');
  // URL'de private_token kullan — ID değil
  const url = `${window.location.origin}/shared/artist/${token}`;

  const copy = (text: string, type: 'link' | 'token') => {
    navigator.clipboard.writeText(text);
    setCopied(type);
    setTimeout(() => setCopied(null), 2200);
  };

  const regenerate = async () => {
    if (!confirm('Regenerate token? The old link will stop working.')) return;
    setRegenerating(true);
    const res = await fetch(`/api/artists/${artist.id}/regenerate-token`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      setToken(data.private_token ?? token);
    }
    setRegenerating(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)' }}
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 8 }}
        transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        className="bg-white w-full max-w-lg shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-7 py-5 border-b border-ink/5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {artist.image_url ? (
              <img src={artist.image_url} alt={artist.name}
                className="w-9 h-9 rounded-full object-cover border border-ink/10" />
            ) : (
              <div className="w-9 h-9 rounded-full bg-ink/8 flex items-center justify-center">
                <span className="text-xs font-serif text-ink/50">{artist.name[0]}</span>
              </div>
            )}
            <div>
              <p className="text-sm font-medium">{artist.name}</p>
              <p className="text-[10px] text-ink/40 tracking-wide">Private Portfolio Link</p>
            </div>
          </div>
          <button onClick={onClose}
            className="p-1.5 text-ink/40 hover:text-ink hover:bg-ink/5 rounded transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="px-7 py-6 space-y-5">
          {/* Security badge */}
          <div className="flex items-center gap-2.5 bg-green-50 border border-green-200 px-4 py-2.5 rounded">
            <Shield size={14} className="text-green-600 flex-shrink-0" />
            <p className="text-[11px] text-green-700">
              This link works regardless of public visibility. Share only with clients.
            </p>
          </div>

          {/* URL */}
          <div>
            <label className="block text-[10px] tracking-[0.25em] uppercase text-ink/40 mb-2">Share URL</label>
            <div className="flex items-stretch border border-ink/10 overflow-hidden">
              <div className="flex-1 px-3 py-2.5 bg-[#F9F9F9] text-xs text-ink/60 font-mono truncate flex items-center">
                {url}
              </div>
              <button onClick={() => copy(url, 'link')}
                className={`px-4 flex items-center gap-1.5 text-xs transition-colors flex-shrink-0 border-l border-ink/10 ${
                  copied === 'link' ? 'bg-green-50 text-green-700' : 'bg-white hover:bg-ink/5 text-ink/60 hover:text-ink'
                }`}>
                {copied === 'link' ? <><Check size={13} />Copied!</> : <><Copy size={13} />Copy</>}
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="grid grid-cols-2 gap-3">
            <a href={url} target="_blank" rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 border border-ink/10 px-4 py-2.5 text-xs text-ink/70 hover:bg-ink/5 hover:text-ink transition-colors">
              <ExternalLink size={13} /> Preview Link
            </a>
            <button onClick={regenerate} disabled={regenerating}
              className="flex items-center justify-center gap-2 border border-amber-200 px-4 py-2.5 text-xs text-amber-700 hover:bg-amber-50 transition-colors disabled:opacity-50">
              <RefreshCw size={13} className={regenerating ? 'animate-spin' : ''} />
              {regenerating ? 'Regenerating…' : 'New Token'}
            </button>
          </div>

          {/* Token */}
          <div>
            <label className="block text-[10px] tracking-[0.25em] uppercase text-ink/40 mb-2">Access Token</label>
            <div className="flex items-stretch border border-ink/10 overflow-hidden">
              <div className="flex-1 px-3 py-2 bg-[#F9F9F9] text-[10px] text-ink/40 font-mono truncate flex items-center">
                {token || '—'}
              </div>
              <button onClick={() => copy(token, 'token')}
                className={`px-4 flex items-center gap-1.5 text-xs transition-colors flex-shrink-0 border-l border-ink/10 ${
                  copied === 'token' ? 'bg-green-50 text-green-700' : 'bg-white hover:bg-ink/5 text-ink/60 hover:text-ink'
                }`}>
                {copied === 'token' ? <Check size={13} /> : <Copy size={13} />}
              </button>
            </div>
            <p className="text-[10px] text-ink/30 mt-1.5">
              Token is embedded in the URL. Use "New Token" to revoke existing access.
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function AdminArtists() {
  const [artists,      setArtists]      = useState<Artist[]>([]);
  const [view,         setView]         = useState<'list' | 'add'>('list');
  const [editId,       setEditId]       = useState<string | null>(null);
  const [search,       setSearch]       = useState('');
  const [loading,      setLoading]      = useState(true);
  const [linkArtist,   setLinkArtist]   = useState<Artist | null>(null);

  // Form state
  const [name,         setName]         = useState('');
  const [bio,          setBio]          = useState('');
  const [medium,       setMedium]       = useState('');
  const [isPublic,     setIsPublic]     = useState(false);
  const [isFeatured,   setIsFeatured]   = useState(false);
  const [imageFile,    setImageFile]    = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [artworks,     setArtworks]     = useState<ArtworkForm[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [step,         setStep]         = useState<1 | 2>(1);

  const fileInputRef    = useRef<HTMLInputElement>(null);
  const artworkInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { fetchArtists(); }, []);

  const fetchArtists = async () => {
    try {
      const res = await apiFetch('/api/artists');
      if (res.ok) {
        const data = await res.json();
        setArtists(Array.isArray(data) ? data : (data.data ?? []));
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const filtered = artists.filter(a =>
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    (a.medium ?? '').toLowerCase().includes(search.toLowerCase())
  );

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    const r = new FileReader();
    r.onloadend = () => setImagePreview(r.result as string);
    r.readAsDataURL(file);
  };

  const handleArtworkImages = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const newAws = Array.from(e.target.files).map(file => ({
      id: `tmp-${Date.now()}-${Math.random()}`,
      title: file.name.replace(/\.[^.]+$/, ''),
      year: new Date().getFullYear().toString(),
      medium: '', dimensions: '',
      file, preview: URL.createObjectURL(file),
      status: 'Private',
    }));
    setArtworks(prev => [...prev, ...newAws]);
    if (artworkInputRef.current) artworkInputRef.current.value = '';
  };

  const updateArtwork = (id: string | number, field: keyof ArtworkForm, val: any) =>
    setArtworks(prev => prev.map(aw => aw.id === id ? { ...aw, [field]: val } : aw));

  const removeArtwork = (id: string | number) =>
    setArtworks(prev => prev.map(aw => aw.id === id ? { ...aw, isDeleted: true } : aw));

  const handleEdit = async (artist: Artist) => {
    setEditId(artist.id);
    setName(artist.name); setBio(artist.bio || ''); setMedium(artist.medium || '');
    setIsPublic(artist.is_public === 1); setIsFeatured(artist.is_featured === 1);
    setImagePreview(artist.image_url || null); setImageFile(null);
    try {
      const res = await fetch(`/api/artists/${artist.id}`);
      if (res.ok) {
        const data = await res.json();
        setArtworks(data.artworks.map((aw: any) => ({ ...aw, preview: aw.image_url })));
      }
    } catch (e) { console.error(e); }
    setStep(1); setView('add');
  };

  const resetForm = () => {
    setEditId(null); setName(''); setBio(''); setMedium('');
    setIsPublic(false); setIsFeatured(false);
    setImagePreview(null); setImageFile(null); setArtworks([]); setStep(1);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) return;
    setIsSubmitting(true);
    try {
      const fd = new FormData();
      if (editId) fd.append('id', editId);
      fd.append('name', name); fd.append('bio', bio); fd.append('medium', medium);
      fd.append('is_public', isPublic ? 'true' : 'false');
      fd.append('is_featured', isFeatured ? 'true' : 'false');
      if (imageFile) fd.append('artist_image', imageFile);

      const active  = artworks.filter(aw => !aw.isDeleted);
      const deleted = artworks.filter(aw => aw.isDeleted && typeof aw.id === 'number').map(aw => aw.id);
      active.forEach((aw, i) => { if (aw.file) fd.append(`artwork_image_${i}`, aw.file); });
      fd.append('artworks', JSON.stringify(active.map((aw, i) => ({
        id: String(aw.id).startsWith('tmp-') ? undefined : aw.id,
        title: aw.title, year: aw.year, medium: aw.medium,
        dimensions: aw.dimensions, status: aw.status, image_url: aw.image_url,
      }))));
      fd.append('deletedArtworks', JSON.stringify(deleted));

      const res = await apiFetch('/api/artists/full', { method: 'POST', body: fd });
      if (res.ok) { resetForm(); await fetchArtists(); setView('list'); }
      else alert('Failed to save artist');
    } catch (e) { console.error(e); alert('An error occurred'); }
    finally { setIsSubmitting(false); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this artist and all their artworks?')) return;
    const res = await fetch(`/api/artists/${id}`, { method: 'DELETE' });
    if (res.ok) setArtists(prev => prev.filter(a => a.id !== id));
  };

  // ── Shared label/input ──────────────────────────────────────────────────────
  const Label = ({ children }: { children: React.ReactNode }) => (
    <label className="block text-[10px] tracking-[0.25em] uppercase text-ink/50 mb-1.5">{children}</label>
  );
  const Input = (props: React.InputHTMLAttributes<HTMLInputElement>) => (
    <input {...props}
      className={`w-full px-3 py-2.5 bg-[#F9F9F9] border border-transparent rounded text-sm
        focus:outline-none focus:border-ink/20 focus:bg-white transition-colors ${props.className ?? ''}`} />
  );

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
      className="space-y-8">

      {/* ── Header ── */}
      <header className="flex justify-between items-end pb-6 border-b border-ink/5">
        <div>
          <h1 className="text-3xl font-serif tracking-tight">Artists & Links</h1>
          <p className="text-ink/50 text-sm mt-1">Manage private portfolios and generate sharing links.</p>
        </div>
        {view === 'list' ? (
          <button onClick={() => { resetForm(); setView('add'); }}
            className="flex items-center gap-2 bg-ink text-white text-xs tracking-[0.2em] uppercase px-5 py-2.5 hover:bg-ink/90 transition-colors">
            <Plus size={14} /> Add Artist
          </button>
        ) : (
          <button onClick={() => setView('list')}
            className="flex items-center gap-2 border border-ink/15 text-sm px-5 py-2.5 hover:bg-ink/5 transition-colors">
            <X size={14} /> Cancel
          </button>
        )}
      </header>

      <AnimatePresence mode="wait">

        {/* ══════════ LIST VIEW ══════════ */}
        {view === 'list' && (
          <motion.div key="list" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="space-y-5">

            {/* Search */}
            <div className="relative max-w-sm">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink/35" />
              <input value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search artists…"
                className="w-full pl-9 pr-4 py-2.5 bg-white border border-ink/10 text-sm focus:outline-none focus:border-ink/25 transition-colors rounded" />
            </div>

            {/* Table */}
            <div className="bg-white border border-ink/5 overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-ink/5">
                    {['Photo', 'Artist', 'Works', 'Visibility', 'Private Link', ''].map(h => (
                      <th key={h} className="px-5 py-3.5 text-[9px] tracking-[0.25em] uppercase text-ink/40 font-normal">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink/[0.04]">
                  {loading && (
                    <tr><td colSpan={6} className="px-5 py-10 text-center text-xs text-ink/40">Loading…</td></tr>
                  )}
                  {!loading && filtered.length === 0 && (
                    <tr><td colSpan={6} className="px-5 py-12 text-center text-xs text-ink/35">
                      {search ? 'No artists match your search.' : 'No artists yet — click "Add Artist" to begin.'}
                    </td></tr>
                  )}
                  {!loading && filtered.map(artist => (
                    <tr key={artist.id} className="hover:bg-[#FAFAFA] transition-colors group">

                      {/* Photo */}
                      <td className="px-5 py-3">
                        {artist.image_url ? (
                          <img src={artist.image_url} alt={artist.name}
                            className="w-11 h-11 rounded-full object-cover border border-ink/8" />
                        ) : (
                          <div className="w-11 h-11 rounded-full bg-ink/6 flex items-center justify-center">
                            <span className="text-sm font-serif text-ink/40">{artist.name[0]}</span>
                          </div>
                        )}
                      </td>

                      {/* Name + medium */}
                      <td className="px-5 py-3">
                        <p className="font-serif text-base leading-tight">{artist.name}</p>
                        {artist.medium && <p className="text-[10px] text-ink/40 tracking-wide mt-0.5">{artist.medium}</p>}
                      </td>

                      {/* Works count */}
                      <td className="px-5 py-3 text-sm text-ink/55">{artist.artworksCount || 0}</td>

                      {/* Visibility badges */}
                      <td className="px-5 py-3">
                        <div className="flex flex-col gap-1">
                          {artist.is_public === 1 && (
                            <span className="inline-flex items-center gap-1 text-[9px] tracking-wider text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 w-fit">
                              <Eye size={9} /> Public
                            </span>
                          )}
                          {artist.is_featured === 1 && (
                            <span className="inline-flex items-center gap-1 text-[9px] tracking-wider text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 w-fit">
                              <Star size={9} /> Featured
                            </span>
                          )}
                          {!artist.is_public && !artist.is_featured && (
                            <span className="text-[9px] tracking-wider text-ink/30 bg-ink/5 border border-ink/10 px-2 py-0.5 w-fit">
                              Draft
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Private link button */}
                      <td className="px-5 py-3">
                        <button onClick={() => setLinkArtist(artist)}
                          className="inline-flex items-center gap-1.5 text-[10px] tracking-wider text-ink/60 border border-ink/10 px-3 py-1.5 hover:bg-ink hover:text-white hover:border-ink transition-all">
                          <LinkIcon size={11} /> View Link
                        </button>
                      </td>

                      {/* Edit / Delete */}
                      <td className="px-5 py-3 text-right">
                        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => handleEdit(artist)}
                            className="px-3 py-1.5 text-xs text-blue-600 hover:bg-blue-50 rounded transition-colors">
                            Edit
                          </button>
                          <button onClick={() => handleDelete(artist.id)}
                            className="p-1.5 text-red-400 hover:bg-red-50 rounded transition-colors">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {/* ══════════ ADD / EDIT VIEW ══════════ */}
        {view === 'add' && (
          <motion.div key="add" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="space-y-6">

            {/* Step indicator */}
            <div className="flex items-center gap-0">
              {(['Artist Details', 'Artworks'] as const).map((label, i) => {
                const s = (i + 1) as 1 | 2;
                const active = step === s;
                const done   = step > s;
                return (
                  <button key={label} onClick={() => setStep(s)}
                    className={`flex items-center gap-2.5 px-5 py-2.5 text-xs tracking-[0.18em] uppercase transition-colors border-b-2 ${
                      active ? 'border-ink text-ink font-medium'
                             : done  ? 'border-ink/30 text-ink/50 hover:text-ink/70'
                                     : 'border-transparent text-ink/35 hover:text-ink/55'
                    }`}>
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] transition-colors ${
                      active ? 'bg-ink text-white' : done ? 'bg-ink/20 text-ink/60' : 'bg-ink/8 text-ink/40'
                    }`}>{done ? <Check size={11} /> : s}</span>
                    {label}
                    {i < 1 && <ChevronRight size={12} className="text-ink/20 ml-1" />}
                  </button>
                );
              })}
            </div>

            <form id="artist-form" onSubmit={handleSubmit}>
              <AnimatePresence mode="wait">

                {/* ── Step 1: Artist Details ── */}
                {step === 1 && (
                  <motion.div key="step1" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }} transition={{ duration: 0.25 }}
                    className="bg-white border border-ink/5 rounded-xl overflow-hidden">

                    <div className="px-8 py-6 border-b border-ink/5">
                      <h2 className="font-serif text-xl">Artist Details</h2>
                      <p className="text-ink/45 text-xs mt-1">Basic information and profile photo</p>
                    </div>

                    <div className="p-8 grid grid-cols-1 lg:grid-cols-3 gap-10">

                      {/* Photo upload */}
                      <div>
                        <Label>Artist Photo</Label>
                        <div onClick={() => fileInputRef.current?.click()}
                          className="border-2 border-dashed border-ink/10 rounded-xl flex flex-col items-center justify-center text-center cursor-pointer hover:border-ink/25 hover:bg-ink/[0.02] transition-all relative overflow-hidden group"
                          style={{ aspectRatio: '3/4' }}>
                          {imagePreview ? (
                            <>
                              <img src={imagePreview} className="absolute inset-0 w-full h-full object-cover" alt="" />
                              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                <p className="text-white text-xs tracking-wide">Change Photo</p>
                              </div>
                            </>
                          ) : (
                            <div className="p-8 flex flex-col items-center">
                              <div className="w-14 h-14 rounded-full bg-ink/6 flex items-center justify-center mb-3 group-hover:bg-ink/10 transition-colors">
                                <UploadCloud size={22} className="text-ink/35" />
                              </div>
                              <p className="text-sm text-ink/60 font-medium">Upload Photo</p>
                              <p className="text-[10px] text-ink/35 mt-1">JPG, PNG — max 50MB</p>
                            </div>
                          )}
                        </div>
                        <input ref={fileInputRef} type="file" className="hidden" accept="image/*" onChange={handleImageChange} />
                      </div>

                      {/* Fields */}
                      <div className="lg:col-span-2 space-y-5">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                          <div>
                            <Label>Full Name *</Label>
                            <Input required value={name} onChange={e => setName(e.target.value)} placeholder="Artist full name" />
                          </div>
                          <div>
                            <Label>Medium / Discipline</Label>
                            <Input value={medium} onChange={e => setMedium(e.target.value)} placeholder="e.g. Oil on Canvas" />
                          </div>
                        </div>

                        <div>
                          <Label>Biography</Label>
                          <textarea rows={7} value={bio} onChange={e => setBio(e.target.value)}
                            placeholder="Artist biography…"
                            className="w-full px-3 py-2.5 bg-[#F9F9F9] border border-transparent rounded text-sm focus:outline-none focus:border-ink/20 focus:bg-white transition-colors resize-none" />
                        </div>

                        {/* Toggles */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-ink/5">
                          {[
                            { label: 'Publish to Website', sub: 'Visible on public Artists page', val: isPublic,   set: setIsPublic,   icon: Eye },
                            { label: 'Feature on Homepage', sub: 'Show in Featured Artists section', val: isFeatured, set: setIsFeatured, icon: Star },
                          ].map(({ label, sub, val, set, icon: Icon }) => (
                            <label key={label} className="flex items-center gap-3 cursor-pointer group p-3 border border-ink/8 rounded-lg hover:border-ink/20 transition-colors">
                              <div className={`w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 transition-colors ${val ? 'bg-ink border-ink' : 'border-ink/20 group-hover:border-ink/40'}`}>
                                {val && <Check size={13} className="text-white" />}
                              </div>
                              <input type="checkbox" checked={val} onChange={e => set(e.target.checked)} className="hidden" />
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5">
                                  <Icon size={12} className="text-ink/40" />
                                  <p className="text-sm font-medium">{label}</p>
                                </div>
                                <p className="text-[10px] text-ink/40 mt-0.5">{sub}</p>
                              </div>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="px-8 py-5 border-t border-ink/5 bg-ink/[0.01] flex justify-end">
                      <button type="button" onClick={() => setStep(2)}
                        className="flex items-center gap-2 bg-ink text-white text-xs tracking-[0.18em] uppercase px-6 py-2.5 hover:bg-ink/90 transition-colors">
                        Next: Artworks <ChevronRight size={14} />
                      </button>
                    </div>
                  </motion.div>
                )}

                {/* ── Step 2: Artworks ── */}
                {step === 2 && (
                  <motion.div key="step2" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.25 }}
                    className="bg-white border border-ink/5 rounded-xl overflow-hidden">

                    <div className="px-8 py-6 border-b border-ink/5 flex items-center justify-between">
                      <div>
                        <h2 className="font-serif text-xl">Artworks Portfolio</h2>
                        <p className="text-ink/45 text-xs mt-1">
                          {artworks.filter(a => !a.isDeleted).length} work{artworks.filter(a => !a.isDeleted).length !== 1 ? 's' : ''} added
                        </p>
                      </div>
                      <button type="button" onClick={() => artworkInputRef.current?.click()}
                        className="flex items-center gap-2 border border-ink/15 text-sm px-4 py-2 hover:bg-ink/5 transition-colors">
                        <Plus size={14} /> Add Images
                      </button>
                      <input ref={artworkInputRef} type="file" className="hidden" accept="image/*" multiple onChange={handleArtworkImages} />
                    </div>

                    <div className="p-8">
                      {artworks.filter(a => !a.isDeleted).length === 0 ? (
                        <div onClick={() => artworkInputRef.current?.click()}
                          className="border-2 border-dashed border-ink/10 rounded-xl p-14 text-center hover:bg-ink/[0.02] hover:border-ink/20 transition-all cursor-pointer">
                          <UploadCloud size={28} className="mx-auto text-ink/25 mb-3" />
                          <p className="text-sm text-ink/50 font-medium">Upload artwork images</p>
                          <p className="text-[10px] text-ink/35 mt-1">Click or drag & drop — multiple files supported</p>
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                          {artworks.filter(a => !a.isDeleted).map(aw => (
                            <div key={String(aw.id)}
                              className="border border-ink/8 rounded-xl overflow-hidden bg-[#FAFAFA] relative group">
                              <button type="button" onClick={() => removeArtwork(aw.id!)}
                                className="absolute top-2.5 right-2.5 z-10 p-1.5 bg-white shadow-sm text-red-400 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-50 rounded">
                                <Trash2 size={13} />
                              </button>

                              <div className="flex gap-0">
                                {/* Artwork thumbnail */}
                                <div className="w-28 flex-shrink-0 bg-ink/5 overflow-hidden" style={{ minHeight: 112 }}>
                                  {aw.preview && (
                                    <img src={aw.preview} alt="" className="w-full h-full object-cover" />
                                  )}
                                </div>

                                {/* Fields */}
                                <div className="flex-1 p-4 space-y-2.5">
                                  <input value={aw.title}
                                    onChange={e => updateArtwork(aw.id!, 'title', e.target.value)}
                                    placeholder="Title"
                                    className="w-full px-2.5 py-1.5 bg-white border border-ink/10 rounded text-sm focus:outline-none focus:border-ink/25 transition-colors" />

                                  <div className="grid grid-cols-2 gap-2">
                                    <input value={aw.year}
                                      onChange={e => updateArtwork(aw.id!, 'year', e.target.value)}
                                      placeholder="Year"
                                      className="w-full px-2.5 py-1.5 bg-white border border-ink/10 rounded text-xs focus:outline-none focus:border-ink/25 transition-colors" />
                                    <input value={aw.dimensions}
                                      onChange={e => updateArtwork(aw.id!, 'dimensions', e.target.value)}
                                      placeholder="Dimensions"
                                      className="w-full px-2.5 py-1.5 bg-white border border-ink/10 rounded text-xs focus:outline-none focus:border-ink/25 transition-colors" />
                                  </div>

                                  <div className="grid grid-cols-2 gap-2">
                                    <input value={aw.medium}
                                      onChange={e => updateArtwork(aw.id!, 'medium', e.target.value)}
                                      placeholder="Medium"
                                      className="w-full px-2.5 py-1.5 bg-white border border-ink/10 rounded text-xs focus:outline-none focus:border-ink/25 transition-colors" />
                                    <select value={aw.status}
                                      onChange={e => updateArtwork(aw.id!, 'status', e.target.value)}
                                      className={`w-full px-2.5 py-1.5 border rounded text-xs focus:outline-none transition-colors ${
                                        aw.status === 'Public'
                                          ? 'bg-green-50 border-green-200 text-green-700'
                                          : 'bg-white border-ink/10 text-ink/60'
                                      }`}>
                                      <option value="Private">Private</option>
                                      <option value="Public">Public</option>
                                    </select>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="px-8 py-5 border-t border-ink/5 bg-ink/[0.01] flex items-center justify-between">
                      <button type="button" onClick={() => setStep(1)}
                        className="text-sm text-ink/50 hover:text-ink transition-colors">
                        ← Back
                      </button>
                      <div className="flex gap-3">
                        <button type="button" onClick={() => setView('list')}
                          className="px-5 py-2.5 text-sm text-ink/50 hover:text-ink transition-colors">
                          Cancel
                        </button>
                        <button type="submit" form="artist-form" disabled={isSubmitting || !name}
                          className="flex items-center gap-2 bg-ink text-white text-xs tracking-[0.18em] uppercase px-7 py-2.5 hover:bg-ink/90 disabled:opacity-50 transition-colors">
                          <Check size={14} />
                          {isSubmitting ? 'Saving…' : editId ? 'Update Artist' : 'Save Artist'}
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Private Link Modal ── */}
      <AnimatePresence>
        {linkArtist && (
          <PrivateLinkModal artist={linkArtist} onClose={() => setLinkArtist(null)} />
        )}
      </AnimatePresence>
    </motion.div>
  );
}

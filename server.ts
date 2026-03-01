/**
 * server.ts — Fazilet Secgin Art Project Consultancy
 *
 * Tüm endpoint'ler:
 *
 * ARTISTS
 *  GET    /api/artists               — admin: tüm liste (sayfalama, arama)
 *  GET    /api/artists/public        — public: is_public=1 olanlar
 *  GET    /api/artists/private/:tok  — gizli link (is_public kontrolü YOK)
 *  GET    /api/artists/:id           — tek sanatçı + eserleri
 *  POST   /api/artists/full          — add/edit sanatçı + çoklu eser (transaction)
 *  PUT    /api/artists/:id/publish   — is_public / is_featured toggle
 *  POST   /api/artists/:id/regenerate-token
 *  DELETE /api/artists/:id
 *
 * ARTWORKS
 *  GET    /api/artworks              — tüm liste
 *  POST   /api/artworks             — tek eser ekle
 *  PUT    /api/artworks/:id         — güncelle
 *  PUT    /api/artworks/:id/publish — status toggle
 *  DELETE /api/artworks/:id
 *
 * STATS
 *  GET    /api/stats
 */

import express, { Request, Response, NextFunction } from 'express';
import { createServer as createViteServer }          from 'vite';
import Database                                       from 'better-sqlite3';
import multer                                         from 'multer';
import path                                           from 'path';
import fs                                             from 'fs';
import crypto                                         from 'crypto';
import { fileURLToPath }                              from 'url';

// ─── Setup ────────────────────────────────────────────────
const __filename  = fileURLToPath(import.meta.url);
const __dirname   = path.dirname(__filename);
const PORT        = Number(process.env.PORT) || 3000;
// Kalıcı depolama — Railway/Render'da /data volume'una bağlanır
const DATA_DIR    = process.env.DATA_DIR    || path.join(__dirname, 'data');
const UPLOADS_DIR = process.env.UPLOADS_DIR || path.join(DATA_DIR, 'uploads');
const DB_PATH     = process.env.DB_PATH     || path.join(DATA_DIR, 'gallery.db');

const ALLOWED_MIME      = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/gif',
  'video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo']);
const ALLOWED_MIME_PUB  = new Set([...['image/jpeg', 'image/png', 'image/webp', 'image/gif'], 'application/pdf']);

if (!fs.existsSync(DATA_DIR))    fs.mkdirSync(DATA_DIR,    { recursive: true });
if (!fs.existsSync(UPLOADS_DIR)) fs.mkdirSync(UPLOADS_DIR, { recursive: true });

// ─── Helpers ─────────────────────────────────────────────
const genToken = () => crypto.randomBytes(20).toString('hex');

const slugify = (s: string) =>
  s.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

const safeUnlink = (relUrl: string | null | undefined) => {
  if (!relUrl) return;
  // relUrl hem /uploads/... hem de /data/uploads/... formatında gelebilir
  let abs: string;
  if (path.isAbsolute(relUrl)) {
    abs = path.resolve(relUrl);
  } else {
    abs = path.resolve(path.join(__dirname, relUrl));
  }
  if (!abs.startsWith(UPLOADS_DIR)) return; // path traversal guard
  try { if (fs.existsSync(abs)) fs.unlinkSync(abs); } catch { /* noop */ }
};

// ─── Database ─────────────────────────────────────────────
const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
  CREATE TABLE IF NOT EXISTS artists (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    bio           TEXT DEFAULT '',
    medium        TEXT DEFAULT '',
    image_url     TEXT,
    is_public     INTEGER NOT NULL DEFAULT 0,
    is_featured   INTEGER NOT NULL DEFAULT 0,
    is_private    INTEGER NOT NULL DEFAULT 1,
    private_token TEXT NOT NULL UNIQUE DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'Active',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS artworks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL DEFAULT 'Untitled',
    artist_id     TEXT REFERENCES artists(id) ON DELETE CASCADE,
    artist        TEXT NOT NULL DEFAULT '',
    year          TEXT DEFAULT '',
    medium        TEXT DEFAULT '',
    dimensions    TEXT DEFAULT '',
    description   TEXT DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'Private',
    sort_order    INTEGER NOT NULL DEFAULT 0,
    viewing_room  INTEGER NOT NULL DEFAULT 0,
    image_url     TEXT,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS publications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    type        TEXT NOT NULL DEFAULT 'catalog',
    year        TEXT DEFAULT '',
    cover_url   TEXT,
    file_url    TEXT,
    is_public   INTEGER NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS exhibitions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    subtitle    TEXT DEFAULT '',
    artists     TEXT DEFAULT '',
    location    TEXT DEFAULT '',
    venue       TEXT DEFAULT '',
    start_date  TEXT DEFAULT '',
    end_date    TEXT DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'upcoming',
    cover_url   TEXT,
    description TEXT DEFAULT '',
    is_public   INTEGER NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    role          TEXT NOT NULL DEFAULT 'viewer',
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  );
`);

// Şifre hash yardımcısı (pbkdf2 — Node.js built-in, bcrypt gerekmez)
const hashPw = (pw: string, salt: string) =>
  crypto.pbkdf2Sync(pw, salt, 100_000, 64, 'sha512').toString('hex');

// Varsayılan admin kullanıcı oluştur (ilk çalışmada)
const existingAdmin = db.prepare(`SELECT id FROM users WHERE role='admin' LIMIT 1`).get();
if (!existingAdmin) {
  const defaultSalt = crypto.randomBytes(16).toString('hex');
  db.prepare(`
    INSERT INTO users (name, email, role, password_hash, salt)
    VALUES (?, ?, 'admin', ?, ?)
  `).run('Admin', 'admin@faziletart.com', hashPw('admin123', defaultSalt), defaultSalt);
  console.log('✦ Default admin created: admin@faziletart.com / admin123');
}

// Migration — add any missing columns silently
const safeMigrate = (sql: string) => { try { db.exec(sql); } catch { /* already exists */ } };
[
  `ALTER TABLE artists ADD COLUMN bio TEXT DEFAULT ''`,
  `ALTER TABLE artists ADD COLUMN medium TEXT DEFAULT ''`,
  `ALTER TABLE artists ADD COLUMN is_public INTEGER NOT NULL DEFAULT 0`,
  `ALTER TABLE artists ADD COLUMN is_featured INTEGER NOT NULL DEFAULT 0`,
  `ALTER TABLE artists ADD COLUMN is_private INTEGER NOT NULL DEFAULT 1`,
  `ALTER TABLE artists ADD COLUMN private_token TEXT NOT NULL DEFAULT ''`,
  `ALTER TABLE artists ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`,
  `ALTER TABLE artworks ADD COLUMN artist_id TEXT`,
  `ALTER TABLE artworks ADD COLUMN description TEXT DEFAULT ''`,
  `ALTER TABLE artworks ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0`,
  `ALTER TABLE artworks ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`,
  `ALTER TABLE artworks ADD COLUMN viewing_room INTEGER NOT NULL DEFAULT 0`,
  `ALTER TABLE artworks ADD COLUMN video_url TEXT`,
].forEach(safeMigrate);

// Ensure all artists have a token
const missingTokens = db
  .prepare(`SELECT id FROM artists WHERE private_token = '' OR private_token IS NULL`)
  .all() as { id: string }[];
const _setToken = db.prepare(`UPDATE artists SET private_token = ? WHERE id = ?`);
for (const { id } of missingTokens) _setToken.run(genToken(), id);

// ─── Multer ───────────────────────────────────────────────
const storage = multer.diskStorage({
  destination: (_, __, cb) => cb(null, UPLOADS_DIR),
  filename: (_, file, cb) => {
    const ext  = path.extname(file.originalname).toLowerCase() || '.jpg';
    const name = file.fieldname + '-' + Date.now() + '-' + crypto.randomBytes(4).toString('hex') + ext;
    cb(null, name);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 200 * 1024 * 1024 },
  fileFilter: (_, file, cb) =>
    ALLOWED_MIME.has(file.mimetype)
      ? cb(null, true)
      : cb(new Error(`Unsupported file type: ${file.mimetype}`)),
});

// Accept: artist_image (1) + artwork_image_0..N + artwork_video_0..N (many)
const uploadFull = upload.fields([
  { name: 'artist_image', maxCount: 1 },
  ...Array.from({ length: 50 }, (_, i) => ({ name: `artwork_image_${i}`, maxCount: 1 })),
  ...Array.from({ length: 50 }, (_, i) => ({ name: `artwork_video_${i}`, maxCount: 1 })),
]);

// Publications uploader (images + PDFs)
const uploadPub = multer({
  storage,
  limits: { fileSize: 100 * 1024 * 1024 },
  fileFilter: (_, file, cb) =>
    ALLOWED_MIME_PUB.has(file.mimetype)
      ? cb(null, true)
      : cb(new Error(`Unsupported file type: ${file.mimetype}`)),
}).fields([
  { name: 'cover',   maxCount: 1 },
  { name: 'file',    maxCount: 1 },
]);

// ─── Auth (session token — no extra packages) ─────────────
const JWT_SECRET  = process.env.JWT_SECRET  || crypto.randomBytes(32).toString('hex');
const SESSION_TTL = 24 * 60 * 60 * 1000; // 24 saat

// { token → { userId, email, role, expiresAt } }
const sessions = new Map<string, { userId: number; email: string; role: string; expiresAt: number }>();

const createSession = (userId: number, email: string, role: string) => {
  const token = crypto.randomBytes(32).toString('hex');
  sessions.set(token, { userId, email, role, expiresAt: Date.now() + SESSION_TTL });
  return token;
};

// Süresi dolmuş oturumları temizle (5 dakikada bir)
setInterval(() => {
  const now = Date.now();
  for (const [k, v] of sessions) if (v.expiresAt < now) sessions.delete(k);
}, 5 * 60 * 1000);

// requireAuth middleware
const requireAuth = (req: Request, res: Response, next: NextFunction) => {
  const header = req.headers.authorization ?? '';
  const token  = header.startsWith('Bearer ') ? header.slice(7) : '';
  const sess   = sessions.get(token);
  if (!sess || sess.expiresAt < Date.now()) {
    sessions.delete(token);
    return res.status(401).json({ error: 'Unauthorized' });
  }
  (req as any).user = sess;
  next();
};

// requireAdmin middleware (role=admin şart)
const requireAdmin = (req: Request, res: Response, next: NextFunction) => {
  requireAuth(req, res, () => {
    if ((req as any).user?.role !== 'admin') return res.status(403).json({ error: 'Forbidden' });
    next();
  });
};

// ─── Rate Limiting (in-memory, paket gerekmez) ────────────
const rateLimitMap = new Map<string, { count: number; reset: number }>();
const rateLimit = (maxReqs: number, windowMs: number) =>
  (req: Request, res: Response, next: NextFunction) => {
    const key = req.ip ?? 'unknown';
    const now = Date.now();
    const entry = rateLimitMap.get(key) ?? { count: 0, reset: now + windowMs };
    if (now > entry.reset) { entry.count = 0; entry.reset = now + windowMs; }
    entry.count++;
    rateLimitMap.set(key, entry);
    if (entry.count > maxReqs) return res.status(429).json({ error: 'Too many requests' });
    next();
  };

// ─── Express ─────────────────────────────────────────────
const app = express();
app.use(express.json({ limit: '10mb' }));
// /uploads: önce DATA_DIR/uploads, bulamazsa proje kökündeki eski uploads/ klasörü
const LEGACY_UPLOADS = path.join(__dirname, 'uploads');
app.use('/uploads', express.static(UPLOADS_DIR));
app.use('/uploads', express.static(LEGACY_UPLOADS));   // eski yüklenen dosyalar için
// Geriye dönük uyumluluk: /data/uploads da aynı klasörü sunar
app.use('/data/uploads', express.static(UPLOADS_DIR));
app.use('/data/uploads', express.static(LEGACY_UPLOADS));

// CORS — production'da gerçek domain'e kısıt
const ALLOWED_ORIGIN = process.env.ALLOWED_ORIGIN || '*';
app.use((_req, res, next) => {
  const origin = _req.headers.origin ?? '';
  const allow  = ALLOWED_ORIGIN === '*' ? '*' : (origin === ALLOWED_ORIGIN ? origin : '');
  res.setHeader('Access-Control-Allow-Origin',  allow || ALLOWED_ORIGIN);
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (_req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

// Logger
app.use((req, _res, next) => {
  process.stdout.write(`[${new Date().toISOString()}] ${req.method} ${req.path}\n`);
  next();
});

// ─── AUTH ─────────────────────────────────────────────────

// POST /api/auth/login
app.post('/api/auth/login', rateLimit(10, 60_000), (req: Request, res: Response, next: NextFunction) => {
  try {
    const { email, password } = req.body;
    if (!email || !password) return res.status(400).json({ error: 'Email ve şifre gerekli' });

    const user = db.prepare(`SELECT * FROM users WHERE email=? AND active=1`).get(email.toLowerCase()) as any;
    if (!user) return res.status(401).json({ error: 'Geçersiz kimlik bilgileri' });

    const hash = hashPw(password, user.salt);
    if (hash !== user.password_hash) return res.status(401).json({ error: 'Geçersiz kimlik bilgileri' });

    const token = createSession(user.id, user.email, user.role);
    res.json({ token, user: { id: user.id, name: user.name, email: user.email, role: user.role } });
  } catch (e) { next(e); }
});

// GET /api/auth/me
app.get('/api/auth/me', requireAuth, (req: Request, res: Response) => {
  const sess = (req as any).user;
  const user = db.prepare(`SELECT id,name,email,role FROM users WHERE id=?`).get(sess.userId) as any;
  if (!user) return res.status(404).json({ error: 'User not found' });
  res.json(user);
});

// POST /api/auth/logout
app.post('/api/auth/logout', (req: Request, res: Response) => {
  const header = req.headers.authorization ?? '';
  const token  = header.startsWith('Bearer ') ? header.slice(7) : '';
  sessions.delete(token);
  res.json({ message: 'Logged out' });
});

// ── Tüm admin API rotaları için blanket koruma ────────────
// Bu middleware auth endpoint'lerinden SONRA, diğer tüm route'lardan ÖNCE tanımlanır.
// app.use('/api', fn) içinde req.path, /api prefix'i olmadan gelir:
//   /api/stats     → /stats
//   /api/artists/public → /artists/public
const PUBLIC_PATHS: { method: string; re: RegExp }[] = [
  { method: 'GET',  re: /^\/stats$/ },
  { method: 'GET',  re: /^\/artists\/public/ },
  { method: 'GET',  re: /^\/artists\/private\// },
  { method: 'GET',  re: /^\/exhibitions\/public/ },
];

app.use('/api', (req: Request, res: Response, next: NextFunction) => {
  const isPublic = PUBLIC_PATHS.some(p => p.method === req.method && p.re.test(req.path));
  if (isPublic) return next();
  return requireAuth(req, res, next);
});

// ─── STATS ───────────────────────────────────────────────
app.get('/api/stats', (_req, res, next) => {
  try {
    const q = (sql: string, ...p: any[]) => (db.prepare(sql).get(...p) as any);
    res.json({
      totalArtworks:   q(`SELECT COUNT(*) c FROM artworks`).c,
      publicArtworks:  q(`SELECT COUNT(*) c FROM artworks WHERE status='Public'`).c,
      privateArtworks: q(`SELECT COUNT(*) c FROM artworks WHERE status='Private'`).c,
      totalArtists:    q(`SELECT COUNT(*) c FROM artists`).c,
      publicArtists:   q(`SELECT COUNT(*) c FROM artists WHERE is_public=1`).c,
      featuredArtists: q(`SELECT COUNT(*) c FROM artists WHERE is_featured=1`).c,
      recentActivity:  (db.prepare(
        `SELECT id,title,artist,created_at FROM artworks ORDER BY created_at DESC LIMIT 8`
      ).all() as any[]).map(i => ({
        id: i.id,
        action: 'Artwork added',
        item: `"${i.title}" — ${i.artist}`,
        time: new Date(i.created_at).toLocaleString('tr-TR'),
      })),
    });
  } catch (e) { next(e); }
});

// ─── ARTISTS ─────────────────────────────────────────────

// GET /api/artists/public — yalnızca yayınlananlar (home + artists page)
app.get('/api/artists/public', (req, res, next) => {
  try {
    const { featured } = req.query;
    let sql = `
      SELECT a.*, COUNT(aw.id) as artworks_count
      FROM artists a
      LEFT JOIN artworks aw ON aw.artist_id = a.id AND aw.status = 'Public'
      WHERE a.is_public = 1
    `;
    if (featured === 'true') sql += ` AND a.is_featured = 1`;
    sql += ` GROUP BY a.id ORDER BY a.name ASC`;
    res.json(db.prepare(sql).all());
  } catch (e) { next(e); }
});

// GET /api/artists/private/:token — gizli link (public kontrolü YOK)
app.get('/api/artists/private/:token', (req, res, next) => {
  try {
    const artist = db.prepare(`
      SELECT * FROM artists WHERE private_token = ?
    `).get(req.params.token) as any;

    if (!artist) return res.status(404).json({ error: 'Invalid or expired link.' });

    const artworks = db.prepare(`
      SELECT * FROM artworks
      WHERE artist_id = ? AND status = 'Public'
      ORDER BY sort_order ASC, created_at DESC
    `).all(artist.id);

    // Strip private_token from response — visitors don't need it
    const { private_token: _tok, ...safeArtist } = artist;
    res.json({ ...safeArtist, artworks });
  } catch (e) { next(e); }
});

// GET /api/artists — admin: tüm liste
app.get('/api/artists', (req, res, next) => {
  try {
    const { q, featured, sort = 'name' } = req.query as Record<string, string>;
    const page  = Math.max(1, parseInt(req.query.page as string) || 1);
    const limit = Math.min(200, parseInt(req.query.limit as string) || 100);
    const offset = (page - 1) * limit;

    const conds: string[] = [];
    const params: any[]   = [];
    if (q)        { conds.push(`(a.name LIKE ? OR a.medium LIKE ?)`); params.push(`%${q}%`, `%${q}%`); }
    if (featured) { conds.push(`a.is_featured = ?`); params.push(featured === 'true' ? 1 : 0); }

    const where   = conds.length ? `WHERE ${conds.join(' AND ')}` : '';
    const orderBy = sort === 'created_at' ? 'a.created_at DESC' : 'a.name ASC';
    const total   = (db.prepare(`SELECT COUNT(*) c FROM artists a ${where}`).get(...params) as any).c;

    const rows = db.prepare(`
      SELECT a.*, COUNT(aw.id) as artworks_count
      FROM artists a
      LEFT JOIN artworks aw ON aw.artist_id = a.id
      ${where}
      GROUP BY a.id
      ORDER BY ${orderBy}
      LIMIT ? OFFSET ?
    `).all(...params, limit, offset);

    res.json({ data: rows, total, page, limit, totalPages: Math.ceil(total / limit) });
  } catch (e) { next(e); }
});

// GET /api/artists/:id — tek sanatçı + tüm eserleri (admin edit için)
app.get('/api/artists/:id', (req, res, next) => {
  try {
    const artist = db.prepare(`SELECT * FROM artists WHERE id = ?`).get(req.params.id) as any;
    if (!artist) return res.status(404).json({ error: 'Artist not found' });
    const artworks = db.prepare(
      `SELECT * FROM artworks WHERE artist_id = ? ORDER BY sort_order ASC, created_at DESC`
    ).all(req.params.id);
    res.json({ ...artist, artworks });
  } catch (e) { next(e); }
});

// POST /api/artists/full — add/update sanatçı + çoklu eser (tek transaction)
app.post('/api/artists/full', uploadFull, (req, res, next) => {
  try {
    const {
      id: reqId, name, bio, medium, is_public, is_featured,
      deletedArtworks: _deleted,
    } = req.body;

    if (!name?.trim()) throw new Error('Artist name is required.');

    const files = req.files as Record<string, Express.Multer.File[]> || {};
    const artworksMeta: any[] = JSON.parse(req.body.artworks || '[]');
    const deletedIds: number[] = JSON.parse(_deleted || '[]');

    const isEdit = !!reqId;
    const id = isEdit ? reqId : slugify(name.trim()) + '-' + Date.now().toString(36);

    // Artist photo
    const artistImageFile = files['artist_image']?.[0];
    let artistImageUrl: string | null = null;
    if (artistImageFile) {
      if (isEdit) {
        const old = db.prepare(`SELECT image_url FROM artists WHERE id=?`).get(id) as any;
        safeUnlink(old?.image_url);
      }
      artistImageUrl = `/uploads/${artistImageFile.filename}`;
    }

    const doAll = db.transaction(() => {
      if (isEdit) {
        // Update artist
        if (artistImageUrl) {
          db.prepare(`
            UPDATE artists SET name=?,bio=?,medium=?,is_public=?,is_featured=?,
            image_url=?,updated_at=CURRENT_TIMESTAMP WHERE id=?
          `).run(name.trim(), bio || '', medium || '',
            is_public === 'true' || is_public === '1' ? 1 : 0,
            is_featured === 'true' || is_featured === '1' ? 1 : 0,
            artistImageUrl, id);
        } else {
          db.prepare(`
            UPDATE artists SET name=?,bio=?,medium=?,is_public=?,is_featured=?,
            updated_at=CURRENT_TIMESTAMP WHERE id=?
          `).run(name.trim(), bio || '', medium || '',
            is_public === 'true' || is_public === '1' ? 1 : 0,
            is_featured === 'true' || is_featured === '1' ? 1 : 0,
            id);
        }
      } else {
        // Insert artist
        db.prepare(`
          INSERT INTO artists (id,name,bio,medium,is_public,is_featured,private_token,image_url)
          VALUES (?,?,?,?,?,?,?,?)
        `).run(
          id, name.trim(), bio || '', medium || '',
          is_public === 'true' ? 1 : 0,
          is_featured === 'true' ? 1 : 0,
          genToken(),
          artistImageUrl,
        );
      }

      // Delete removed artworks
      for (const awId of deletedIds) {
        const aw = db.prepare(`SELECT image_url, video_url FROM artworks WHERE id=?`).get(awId) as any;
        safeUnlink(aw?.image_url);
        safeUnlink(aw?.video_url);
        db.prepare(`DELETE FROM artworks WHERE id=?`).run(awId);
      }

      // Upsert artworks
      for (let i = 0; i < artworksMeta.length; i++) {
        const meta      = artworksMeta[i];
        const imgFile   = files[`artwork_image_${i}`]?.[0];
        const vidFile   = files[`artwork_video_${i}`]?.[0];
        const imgUrl    = imgFile ? `/uploads/${imgFile.filename}` : null;
        const videoUrl  = vidFile ? `/uploads/${vidFile.filename}` : null;
        const hasNew    = imgUrl || videoUrl;

        if (meta.id) {
          // Update existing
          if (hasNew) {
            const old = db.prepare(`SELECT image_url, video_url FROM artworks WHERE id=?`).get(meta.id) as any;
            if (imgUrl)   safeUnlink(old?.image_url);
            if (videoUrl) safeUnlink(old?.video_url);
          }
          const sets: string[] = ['title=?','year=?','medium=?','dimensions=?','status=?'];
          const vals: any[]    = [meta.title||'Untitled',meta.year||'',meta.medium||'',meta.dimensions||'',meta.status||'Private'];
          if (imgUrl)   { sets.push('image_url=?');  vals.push(imgUrl); }
          if (videoUrl) { sets.push('video_url=?');  vals.push(videoUrl); }
          vals.push(meta.id);
          db.prepare(`UPDATE artworks SET ${sets.join(',')}, updated_at=CURRENT_TIMESTAMP WHERE id=?`).run(...vals);
        } else {
          // Insert new (only if has a file)
          if (hasNew) {
            db.prepare(`
              INSERT INTO artworks (title,artist_id,artist,year,medium,dimensions,status,sort_order,image_url,video_url)
              VALUES (?,?,?,?,?,?,?,?,?,?)
            `).run(
              meta.title || 'Untitled', id, name.trim(),
              meta.year || '', meta.medium || '', meta.dimensions || '',
              meta.status || 'Private', i,
              imgUrl, videoUrl,
            );
          }
        }
      }
    });

    doAll();
    res.status(200).json({ id, message: 'Saved successfully' });
  } catch (e) { next(e); }
});

// PUT /api/artists/:id/publish — toggle is_public / is_featured
app.put('/api/artists/:id/publish', (req, res, next) => {
  try {
    const { id }              = req.params;
    const { is_public, is_featured } = req.body;
    const info = db.prepare(`
      UPDATE artists SET is_public=?,is_featured=?,updated_at=CURRENT_TIMESTAMP WHERE id=?
    `).run(is_public ? 1 : 0, is_featured ? 1 : 0, id);
    if (!info.changes) return res.status(404).json({ error: 'Artist not found' });
    res.json({ message: 'Updated' });
  } catch (e) { next(e); }
});

// POST /api/artists/:id/regenerate-token
app.post('/api/artists/:id/regenerate-token', (req, res, next) => {
  try {
    const token = genToken();
    const info  = db.prepare(
      `UPDATE artists SET private_token=?,updated_at=CURRENT_TIMESTAMP WHERE id=?`
    ).run(token, req.params.id);
    if (!info.changes) return res.status(404).json({ error: 'Artist not found' });
    res.json({ private_token: token, message: 'Token regenerated' });
  } catch (e) { next(e); }
});

// DELETE /api/artists/:id
app.delete('/api/artists/:id', (req, res, next) => {
  try {
    const artist = db.prepare(`SELECT image_url FROM artists WHERE id=?`).get(req.params.id) as any;
    if (!artist) return res.status(404).json({ error: 'Not found' });

    // Delete all artwork images
    const artworks = db.prepare(`SELECT image_url FROM artworks WHERE artist_id=?`).all(req.params.id) as any[];
    for (const aw of artworks) safeUnlink(aw.image_url);

    safeUnlink(artist.image_url);
    db.prepare(`DELETE FROM artists WHERE id=?`).run(req.params.id);
    res.json({ message: 'Deleted' });
  } catch (e) { next(e); }
});

// ─── ARTWORKS ─────────────────────────────────────────────

app.get('/api/artworks', (req, res, next) => {
  try {
    const { q, artist_id, status } = req.query as Record<string, string>;
    const conds: string[] = [];
    const params: any[]   = [];
    if (q)         { conds.push(`(title LIKE ? OR artist LIKE ?)`); params.push(`%${q}%`, `%${q}%`); }
    if (artist_id) { conds.push(`artist_id = ?`); params.push(artist_id); }
    if (status)    { conds.push(`status = ?`);    params.push(status); }
    const where = conds.length ? `WHERE ${conds.join(' AND ')}` : '';
    res.json(db.prepare(`SELECT * FROM artworks ${where} ORDER BY sort_order ASC, created_at DESC`).all(...params));
  } catch (e) { next(e); }
});

app.post('/api/artworks', upload.single('image'), (req, res, next) => {
  try {
    const { title, artist_id, artist, year, medium, dimensions, status } = req.body;
    const imageUrl = req.file ? `/uploads/${req.file.filename}` : null;
    const info = db.prepare(`
      INSERT INTO artworks (title,artist_id,artist,year,medium,dimensions,status,image_url)
      VALUES (?,?,?,?,?,?,?,?)
    `).run(title||'Untitled', artist_id||null, artist||'', year||'', medium||'', dimensions||'', status||'Private', imageUrl);
    res.status(201).json({ id: info.lastInsertRowid });
  } catch (e) { next(e); }
});

app.put('/api/artworks/:id', upload.single('image'), (req, res, next) => {
  try {
    const { id } = req.params;
    const { title, year, medium, dimensions, status } = req.body;
    let imageUrl: string | undefined;
    if (req.file) {
      const old = db.prepare(`SELECT image_url FROM artworks WHERE id=?`).get(id) as any;
      safeUnlink(old?.image_url);
      imageUrl = `/uploads/${req.file.filename}`;
    }
    const sql = req.file
      ? `UPDATE artworks SET title=?,year=?,medium=?,dimensions=?,status=?,image_url=?,updated_at=CURRENT_TIMESTAMP WHERE id=?`
      : `UPDATE artworks SET title=?,year=?,medium=?,dimensions=?,status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?`;
    const p = req.file
      ? [title,year,medium,dimensions,status||'Private',imageUrl,id]
      : [title,year,medium,dimensions,status||'Private',id];
    db.prepare(sql).run(...p);
    res.json({ message: 'Updated' });
  } catch (e) { next(e); }
});

app.put('/api/artworks/:id/publish', (req, res, next) => {
  try {
    const { status } = req.body;
    db.prepare(`UPDATE artworks SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?`)
      .run(status, req.params.id);
    res.json({ message: 'Updated' });
  } catch (e) { next(e); }
});

app.delete('/api/artworks/:id', (req, res, next) => {
  try {
    const aw = db.prepare(`SELECT image_url FROM artworks WHERE id=?`).get(req.params.id) as any;
    if (!aw) return res.status(404).json({ error: 'Not found' });
    safeUnlink(aw.image_url);
    db.prepare(`DELETE FROM artworks WHERE id=?`).run(req.params.id);
    res.json({ message: 'Deleted' });
  } catch (e) { next(e); }
});

// ─── PUBLICATIONS ─────────────────────────────────────────

app.get('/api/publications', (req, res, next) => {
  try {
    const { public: pub } = req.query;
    const where = pub === 'true' ? 'WHERE is_public=1' : '';
    res.json(db.prepare(`SELECT * FROM publications ${where} ORDER BY year DESC, created_at DESC`).all());
  } catch (e) { next(e); }
});

app.post('/api/publications', uploadPub, (req, res, next) => {
  try {
    const files = req.files as Record<string, Express.Multer.File[]> || {};
    const { title, description, type, year, is_public } = req.body;
    if (!title?.trim()) throw new Error('Title is required');
    const coverUrl = files['cover']?.[0] ? `/uploads/${files['cover'][0].filename}` : null;
    const fileUrl  = files['file']?.[0]  ? `/uploads/${files['file'][0].filename}`  : (req.body.file_url || null);
    const info = db.prepare(`
      INSERT INTO publications (title,description,type,year,cover_url,file_url,is_public)
      VALUES (?,?,?,?,?,?,?)
    `).run(title.trim(), description||'', type||'catalog', year||'', coverUrl, fileUrl, is_public==='1'||is_public===true?1:0);
    res.status(201).json({ id: info.lastInsertRowid });
  } catch (e) { next(e); }
});

app.put('/api/publications/:id', uploadPub, (req, res, next) => {
  try {
    const files = req.files as Record<string, Express.Multer.File[]> || {};
    const { title, description, type, year, is_public } = req.body;
    const existing = db.prepare(`SELECT * FROM publications WHERE id=?`).get(req.params.id) as any;
    if (!existing) return res.status(404).json({ error: 'Not found' });
    let coverUrl = existing.cover_url;
    let fileUrl  = req.body.file_url || existing.file_url;
    if (files['cover']?.[0]) { safeUnlink(existing.cover_url); coverUrl = `/uploads/${files['cover'][0].filename}`; }
    if (files['file']?.[0])  { safeUnlink(existing.file_url);  fileUrl  = `/uploads/${files['file'][0].filename}`; }
    db.prepare(`
      UPDATE publications SET title=?,description=?,type=?,year=?,cover_url=?,file_url=?,is_public=?,updated_at=CURRENT_TIMESTAMP WHERE id=?
    `).run(title?.trim()||existing.title, description??existing.description, type||existing.type, year??existing.year, coverUrl, fileUrl, is_public==='1'?1:0, req.params.id);
    res.json({ message: 'Updated' });
  } catch (e) { next(e); }
});

app.delete('/api/publications/:id', (req, res, next) => {
  try {
    const pub = db.prepare(`SELECT * FROM publications WHERE id=?`).get(req.params.id) as any;
    if (!pub) return res.status(404).json({ error: 'Not found' });
    safeUnlink(pub.cover_url);
    if (pub.file_url?.startsWith('/uploads/')) safeUnlink(pub.file_url);
    db.prepare(`DELETE FROM publications WHERE id=?`).run(req.params.id);
    res.json({ message: 'Deleted' });
  } catch (e) { next(e); }
});

// ─── VIEWING ROOM toggle on artworks ──────────────────────

// GET /api/viewing-room — artworks flagged for viewing room
app.get('/api/viewing-room', (_req, res, next) => {
  try {
    res.json(db.prepare(`
      SELECT aw.*, a.name as artist_name
      FROM artworks aw
      LEFT JOIN artists a ON a.id = aw.artist_id
      WHERE aw.viewing_room = 1
      ORDER BY aw.sort_order ASC, aw.created_at DESC
    `).all());
  } catch (e) { next(e); }
});

// ─── EXHIBITIONS ─────────────────────────────────────────
app.get('/api/exhibitions', (_req, res, next) => {
  try {
    const rows = db.prepare(`SELECT * FROM exhibitions ORDER BY start_date DESC, created_at DESC`).all();
    res.json(rows);
  } catch (e) { next(e); }
});

app.get('/api/exhibitions/public', (_req, res, next) => {
  try {
    const rows = db.prepare(`SELECT * FROM exhibitions WHERE is_public=1 ORDER BY start_date DESC`).all();
    res.json(rows);
  } catch (e) { next(e); }
});

app.post('/api/exhibitions', upload.single('cover'), (req, res, next) => {
  try {
    const { title, subtitle, artists, location, venue, start_date, end_date, status, description, is_public } = req.body;
    const cover_url = req.file ? `/uploads/${req.file.filename}` : null;
    const id = db.prepare(`
      INSERT INTO exhibitions (title,subtitle,artists,location,venue,start_date,end_date,status,cover_url,description,is_public)
      VALUES (?,?,?,?,?,?,?,?,?,?,?)
    `).run(title, subtitle||'', artists||'', location||'', venue||'', start_date||'', end_date||'',
           status||'upcoming', cover_url, description||'', is_public==='true'?1:0).lastInsertRowid;
    res.json({ id });
  } catch (e) { next(e); }
});

app.put('/api/exhibitions/:id', upload.single('cover'), (req, res, next) => {
  try {
    const { title, subtitle, artists, location, venue, start_date, end_date, status, description, is_public } = req.body;
    const current = db.prepare(`SELECT cover_url FROM exhibitions WHERE id=?`).get(req.params.id) as any;
    let cover_url = current?.cover_url ?? null;
    if (req.file) {
      safeUnlink(cover_url);
      cover_url = `/uploads/${req.file.filename}`;
    }
    db.prepare(`
      UPDATE exhibitions SET title=?,subtitle=?,artists=?,location=?,venue=?,start_date=?,end_date=?,
      status=?,cover_url=?,description=?,is_public=?,updated_at=CURRENT_TIMESTAMP WHERE id=?
    `).run(title, subtitle||'', artists||'', location||'', venue||'', start_date||'', end_date||'',
           status||'upcoming', cover_url, description||'', is_public==='true'?1:0, req.params.id);
    res.json({ message: 'Updated' });
  } catch (e) { next(e); }
});

app.delete('/api/exhibitions/:id', (req, res, next) => {
  try {
    const row = db.prepare(`SELECT cover_url FROM exhibitions WHERE id=?`).get(req.params.id) as any;
    if (row?.cover_url) safeUnlink(row.cover_url);
    db.prepare(`DELETE FROM exhibitions WHERE id=?`).run(req.params.id);
    res.json({ message: 'Deleted' });
  } catch (e) { next(e); }
});

// ─── USERS ───────────────────────────────────────────────

// GET /api/users — tüm kullanıcılar (şifre bilgisi hariç)
app.get('/api/users', (_req, res, next) => {
  try {
    const users = db.prepare(
      `SELECT id,name,email,role,active,created_at,updated_at FROM users ORDER BY created_at DESC`
    ).all();
    res.json(users);
  } catch (e) { next(e); }
});

// POST /api/users — yeni kullanıcı
app.post('/api/users', (req, res, next) => {
  try {
    const { name, email, role, password } = req.body;
    if (!name?.trim())     throw new Error('Name is required.');
    if (!email?.trim())    throw new Error('Email is required.');
    if (!password?.trim()) throw new Error('Password is required.');

    const salt = crypto.randomBytes(16).toString('hex');
    const info = db.prepare(`
      INSERT INTO users (name, email, role, password_hash, salt)
      VALUES (?, ?, ?, ?, ?)
    `).run(name.trim(), email.trim().toLowerCase(), role || 'viewer', hashPw(password, salt), salt);
    res.status(201).json({ id: info.lastInsertRowid });
  } catch (e: any) {
    if (e.message?.includes('UNIQUE')) return res.status(409).json({ error: 'Bu e-posta zaten kullanımda.' });
    next(e);
  }
});

// PUT /api/users/:id — kullanıcı güncelle (şifre hariç)
app.put('/api/users/:id', (req, res, next) => {
  try {
    const { name, email, role, active } = req.body;
    const info = db.prepare(`
      UPDATE users SET name=?,email=?,role=?,active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?
    `).run(name?.trim(), email?.trim().toLowerCase(), role, active ? 1 : 0, req.params.id);
    if (!info.changes) return res.status(404).json({ error: 'User not found' });
    res.json({ message: 'Updated' });
  } catch (e: any) {
    if (e.message?.includes('UNIQUE')) return res.status(409).json({ error: 'Bu e-posta zaten kullanımda.' });
    next(e);
  }
});

// PUT /api/users/:id/password — şifre değiştir
app.put('/api/users/:id/password', (req, res, next) => {
  try {
    const { password } = req.body;
    if (!password?.trim()) throw new Error('New password is required.');
    const salt = crypto.randomBytes(16).toString('hex');
    const info = db.prepare(`
      UPDATE users SET password_hash=?,salt=?,updated_at=CURRENT_TIMESTAMP WHERE id=?
    `).run(hashPw(password, salt), salt, req.params.id);
    if (!info.changes) return res.status(404).json({ error: 'User not found' });
    res.json({ message: 'Password updated' });
  } catch (e) { next(e); }
});

// DELETE /api/users/:id
app.delete('/api/users/:id', (req, res, next) => {
  try {
    // Son admin'i silme koruması
    const user = db.prepare(`SELECT role FROM users WHERE id=?`).get(req.params.id) as any;
    if (!user) return res.status(404).json({ error: 'User not found' });
    if (user.role === 'admin') {
      const adminCount = (db.prepare(`SELECT COUNT(*) c FROM users WHERE role='admin'`).get() as any).c;
      if (adminCount <= 1) return res.status(400).json({ error: 'Son admin kullanıcı silinemez.' });
    }
    db.prepare(`DELETE FROM users WHERE id=?`).run(req.params.id);
    res.json({ message: 'Deleted' });
  } catch (e) { next(e); }
});

// PUT /api/artworks/:id/viewing-room — toggle
app.put('/api/artworks/:id/viewing-room', (req, res, next) => {
  try {
    const { viewing_room } = req.body;
    db.prepare(`UPDATE artworks SET viewing_room=?,updated_at=CURRENT_TIMESTAMP WHERE id=?`)
      .run(viewing_room ? 1 : 0, req.params.id);
    res.json({ message: 'Updated' });
  } catch (e) { next(e); }
});

// ─── Error handler ────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-unused-vars
app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
  console.error('[ERR]', err.message ?? err);
  if (err.code === 'LIMIT_FILE_SIZE') return res.status(413).json({ error: 'File too large (max 200 MB).' });
  res.status(err.status ?? 400).json({ error: err.message ?? 'Server error' });
});

// ─── Boot ─────────────────────────────────────────────────
async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const dist = path.join(__dirname, 'dist');
    app.use(express.static(dist));
    app.get('*', (_, r) => r.sendFile(path.join(dist, 'index.html')));
  }

  const server = app.listen(PORT, '0.0.0.0', () =>
    console.log(`✦  http://localhost:${PORT}`)
  );

  const shutdown = (sig: string) => {
    console.log(`\n[${sig}] shutting down…`);
    server.close(() => { db.close(); process.exit(0); });
    setTimeout(() => process.exit(1), 8000);
  };
  process.on('SIGINT',  () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));
}

startServer();
# Güvenlik Altyapı Analizi — Fazilet Secgin Art Project
**Tarih:** 2026-03-01
**Kapsam:** `server.ts` — Express + SQLite + Multer backend

---

## Özet Tablo

| Alan | Durum | Önem |
|------|-------|------|
| Admin Kimlik Doğrulama | ❌ Yok | 🔴 KRİTİK |
| SQL Enjeksiyonu | ✅ Korumalı | 🟢 İyi |
| Path Traversal | ✅ Korumalı | 🟢 İyi |
| CORS Konfigürasyonu | ⚠️ Wildcard | 🟡 Orta |
| Dosya Yükleme Güvenliği | ⚠️ Kısmi | 🟡 Orta |
| Rate Limiting | ❌ Yok | 🟠 Yüksek |
| Private Token Sızıntısı | ❌ Var | 🟠 Yüksek |
| Hata Mesajı Güvenliği | ⚠️ Kısmi | 🟡 Orta |
| HTTPS | ⚠️ Yok | 🟡 Orta (prod için) |

---

## 1. 🔴 KRİTİK — Admin Rotalarında Kimlik Doğrulama Yok

### Sorun
Tüm yazma endpoint'leri (`POST`, `PUT`, `DELETE`) tamamen açık. URL'yi bilen herkes:
- Sanatçı ve eserleri silebilir
- Yeni içerik ekleyebilir
- Tüm veritabanını değiştirebilir

```
POST /api/artists/full     → Auth yok
DELETE /api/artists/:id    → Auth yok
DELETE /api/artworks/:id   → Auth yok
DELETE /api/exhibitions/:id → Auth yok
```

### Çözüm
Basit bir admin middleware eklenebilir:

```typescript
// .env dosyasına: ADMIN_SECRET=guclu_bir_sifre_buraya
const adminAuth = (req: Request, res: Response, next: NextFunction) => {
  const key = req.headers['x-admin-key'] || req.query.adminKey;
  if (key !== process.env.ADMIN_SECRET) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
};

// Tüm yazma rotalarına ekle:
app.post('/api/artists/full', adminAuth, uploadFull, ...);
app.delete('/api/artists/:id', adminAuth, ...);
```

Uzun vadede: JWT tabanlı auth veya session-based auth önerilir.

---

## 2. 🟠 YÜKSEK — Private Token API Yanıtında Sızıyor

### Sorun
`GET /api/artists/private/:token` endpoint'i sanatçının tüm verilerini döndürüyor, buna `private_token` alanı da dahil:

```typescript
// server.ts satır 268
res.json({ ...artist, artworks });  // private_token da gönderiliyor!
```

Private link'e erişen bir kişi, developer tools ile `private_token`'ı görebilir. Bu token başkasına iletilerek yeniden kullanılabilir veya token rotasyon sistemini anlayabilir.

### Çözüm
Yanıttan `private_token` çıkarılmalı:

```typescript
const { private_token: _, ...safeArtist } = artist;
res.json({ ...safeArtist, artworks });
```

---

## 3. 🟠 YÜKSEK — Token Endpoint'inde Rate Limiting Yok

### Sorun
`/api/artists/private/:token` endpoint'inde istek sınırı yok. Token 40 hex karakter (20 byte) olduğu için brute force teorik olarak çok zordur, ancak yine de:

```
// Sınırsız istek gönderilebilir:
GET /api/artists/private/aaaaaaaaaa...
GET /api/artists/private/aaaaaaaaab...
```

### Çözüm
`express-rate-limit` paketi kullanılabilir:

```typescript
import rateLimit from 'express-rate-limit';

const tokenLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 dakika
  max: 30,
  message: { error: 'Too many requests, please try again later.' }
});

app.get('/api/artists/private/:token', tokenLimiter, ...);
```

---

## 4. 🟡 ORTA — CORS Wildcard (`*`)

### Sorun
```typescript
res.setHeader('Access-Control-Allow-Origin', '*');
```

Her domain'den istek kabul ediliyor. Üretim ortamında bu, kötü amaçlı sitelerin API'ye istek yapmasına izin verir.

### Çözüm
Origin kısıtlaması:

```typescript
const ALLOWED_ORIGINS = [
  'https://faziletsecgin.com',
  'http://localhost:5173',
  'http://localhost:3000',
];

app.use((req, res, next) => {
  const origin = req.headers.origin || '';
  if (ALLOWED_ORIGINS.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }
  // ...
});
```

---

## 5. 🟡 ORTA — Dosya Yükleme: MIME Sadece Header'dan Kontrol Ediliyor

### Sorun
```typescript
fileFilter: (_, file, cb) =>
  ALLOWED_MIME.has(file.mimetype)  // istemcinin gönderdiği MIME type!
    ? cb(null, true) : cb(new Error(...))
```

`file.mimetype`, istemcinin HTTP isteğinde gönderdiği `Content-Type` başlığından geliyor. Bu kolayca manipüle edilebilir. Gerçek bir kötü amaçlı dosya `.jpg` uzantısıyla ve `image/jpeg` MIME type ile yüklenebilir ama içerik farklı olabilir.

### Çözüm (İyi Güvenlik Için)
[`file-type`](https://github.com/sindresorhus/file-type) paketi ile magic bytes kontrolü:

```typescript
import { fileTypeFromBuffer } from 'file-type';

// Dosyayı memory'e al, magic bytes kontrol et, sonra diske yaz
const SAFE_TYPES = new Set(['jpg', 'png', 'gif', 'webp']);
```

Şu anki yapıyla yine de güvenli çünkü Node.js bu dosyaları çalıştırmıyor, sadece static olarak sunuyor. Ancak üretim ortamında ek bir web sunucusu (Nginx) kullanılıyorsa dikkat edilmeli.

---

## 6. 🟡 ORTA — Hata Mesajları İç Detay Sızdırıyor

### Sorun
```typescript
res.status(err.status ?? 400).json({ error: err.message ?? 'Server error' });
```

`err.message` alanı istemciye gönderiliyor. Bu, veritabanı hataları veya dosya yolu bilgileri içerebilir.

### Çözüm
Üretim ortamında hata mesajlarını genel tutun:

```typescript
const isProduction = process.env.NODE_ENV === 'production';
res.status(err.status ?? 400).json({
  error: isProduction ? 'An error occurred' : (err.message ?? 'Server error')
});
```

---

## 7. ✅ İYİ — SQL Enjeksiyonu Koruması

`better-sqlite3` ile parametreli sorgular kullanılıyor:

```typescript
db.prepare(`SELECT * FROM artists WHERE id = ?`).get(req.params.id)
db.prepare(`UPDATE artists SET ... WHERE id=?`).run(...params, id)
```

Tüm kullanıcı girdileri `?` placeholder ile bağlanıyor. SQL enjeksiyonu riski **yok**.

---

## 8. ✅ İYİ — Path Traversal Koruması

`safeUnlink` fonksiyonu güvenli şekilde yazılmış:

```typescript
const safeUnlink = (relUrl: string | null | undefined) => {
  if (!relUrl) return;
  const abs = path.resolve(path.join(__dirname, relUrl));
  if (!abs.startsWith(UPLOADS_DIR)) return; // traversal guard ✅
  try { if (fs.existsSync(abs)) fs.unlinkSync(abs); } catch { /* noop */ }
};
```

`/uploads/` dışındaki dosyalar asla silinemez.

---

## 9. ✅ İYİ — Token Üretimi

```typescript
const genToken = () => crypto.randomBytes(20).toString('hex');
```

Node.js'in `crypto` modülü kullanılıyor — kriptografik açıdan güvenli rasgele sayı üretimi. 40 karakter hex = 160 bit entropi. **Yeterli güvenlik**.

---

## 10. ✅ İYİ — Dosya Adı Güvenliği

```typescript
const name = file.fieldname + '-' + Date.now() + '-' + crypto.randomBytes(4).toString('hex') + ext;
```

Orijinal dosya adı kullanılmıyor. Tahmin edilemez, çakışmasız dosya adları üretiliyor.

---

## Öncelik Sırası — Yapılacaklar

1. **🔴 Hemen:** Admin route'larına kimlik doğrulama ekle (en azından basit API key)
2. **🟠 Bu Hafta:** Private token yanıttan çıkar (`...safeArtist`)
3. **🟠 Bu Hafta:** Rate limiting ekle (özellikle private link endpoint'ine)
4. **🟡 Üretim Öncesi:** CORS origin kısıtlama
5. **🟡 Üretim Öncesi:** HTTPS (Nginx reverse proxy veya Cloudflare)
6. **🟡 Üretim Öncesi:** Hata mesajlarını üretimde gizle

---

*Bu analiz sadece `server.ts` dosyasını kapsamaktadır. Frontend güvenliği, hosting ortamı ve ağ konfigürasyonu ayrı değerlendirme gerektirir.*

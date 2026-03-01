# 🚀 Railway Deployment Kılavuzu
## Fazilet Secgin Art Project Consultancy

---

## Gereksinimler
- Ücretsiz [Railway](https://railway.app) hesabı
- Ücretsiz [GitHub](https://github.com) hesabı
- Bilgisayarınızda Git kurulu olmalı

---

## Adım 1 — GitHub'a Yükle

### 1a. Git Repo Oluştur
```bash
cd /path/to/faziletweb    # proje klasörü
git init
git add .
git commit -m "ilk commit"
```

### 1b. GitHub'da yeni repo aç
1. [github.com/new](https://github.com/new) adresine git
2. Repo adı: `fazilet-art` (private olarak işaretle)
3. "Create repository" tıkla

### 1c. Lokal kodu GitHub'a bağla
```bash
git remote add origin https://github.com/KULLANICI_ADIN/fazilet-art.git
git branch -M main
git push -u origin main
```

---

## Adım 2 — Railway Hesabı Aç

1. [railway.app](https://railway.app) → "Login with GitHub"
2. GitHub hesabınla giriş yap

---

## Adım 3 — Yeni Proje Oluştur

1. Railway dashboard → **"New Project"**
2. **"Deploy from GitHub repo"** seç
3. `fazilet-art` reposunu seç → **"Deploy Now"**

Railway otomatik olarak `railway.toml` dosyasını okuyacak ve build başlatacak.

---

## Adım 4 — Environment Variables Ayarla

Railway dashboard → projeye tıkla → **"Variables"** sekmesi:

| Değişken | Değer | Açıklama |
|---|---|---|
| `NODE_ENV` | `production` | **Zorunlu** |
| `PORT` | `3000` | Railway otomatik ekler, eklemene gerek yok |
| `DATA_DIR` | `/app/data` | Volume mount noktası |

**Nasıl eklersin:**
1. Variables sekmesi → "New Variable"
2. `NODE_ENV` → `production` ekle
3. `DATA_DIR` → `/app/data` ekle

---

## Adım 5 — Kalıcı Volume Ekle (ÖNEMLİ)

Veritabanı ve yüklenen görseller kaybolmasın diye bir **kalıcı disk** eklemelisin:

1. Railway projesinde **"+ Add a service"** → **"Volume"**
2. Mount Path: `/app/data`
3. Size: `5 GB` (ücretsiz planda 5GB var)
4. **"Create"** tıkla

Bu işlem sayesinde:
- `gallery.db` veritabanı → `/app/data/gallery.db`
- Yüklenen görseller → `/app/data/uploads/`

her deploy'da korunur.

---

## Adım 6 — Domain Ayarla

1. Railway projesinde **"Settings"** sekmesi
2. **"Networking"** → **"Generate Domain"**
3. Sana bir URL verir: `fazilet-art-xxxx.up.railway.app`

**Kendi domain'ini bağlamak istersen:**
1. "Custom Domain" → domain adresinizi yaz (örn: `faziletart.com`)
2. DNS ayarlarında CNAME kaydı oluştur (Railway size gösterir)

---

## Adım 7 — Admin Şifresini Değiştir

**İlk deploy'dan sonra mutlaka yap!**

Admin paneli: `https://siteadresin.railway.app/admin`

Varsayılan giriş:
- Email: `admin@faziletart.com`
- Şifre: `admin123`

Giriş yap → **Users** → Admin kullanıcıya tıkla → **"Change Password"**

---

## Adım 8 — Test Et

1. `https://siteadresin.railway.app` → Ana sayfa görünmeli
2. `/admin` → Admin paneli
3. Bir sanatçı ekle → Private link test et
4. Linki telefonuna gönder → Çalışıyor mu?

---

## Güncelleme Nasıl Yapılır?

Yerel değişikliklerini Railway'e göndermek için:

```bash
git add .
git commit -m "güncelleme açıklaması"
git push
```

Railway otomatik olarak yeni build başlatır (~2-3 dakika).

---

## Sorun Giderme

### Build başarısız
Railway dashboard → **"Deployments"** → kırmızı deploy → log'lara bak

### Görseller kayboldu
Volume mount'ı kontrol et — `/app/data` bağlı mı?

### Sayfa açılmıyor
"Deployments" sekmesinde en son deploy yeşil mi? Log'larda `✦  http://localhost:3000` yazıyor mu?

---

## Maliyet

Railway Hobby planı: **$5/ay** (500 saat CPU, 512MB RAM)

Ücretsiz deneme için yeni hesapta **$5 kredi** geliyor (1 ay kadar ücretsiz kullanabilirsin).

---

## Alternatif: Render.com

Railway yerine [render.com](https://render.com) da kullanabilirsin:
1. "New" → "Web Service" → GitHub repo bağla
2. Build Command: `npm install && npm run build`
3. Start Command: `NODE_ENV=production npx tsx server.ts`
4. "Disks" sekmesinden `/app/data` için disk ekle (ücretsiz planda 1GB)

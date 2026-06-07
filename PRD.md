# CultureJeevan — Product Requirements Document

**Version:** 1.4  
**Date:** March 2026  
**Founder:** Dhawal  
**Status:** Pre-build / Pilot Planning

---

## 1. Vision

CultureJeevan ek pan-India platform hai jo creators ko verified recording spaces (studios, shooting locations, guest houses) se connect karta hai — seamlessly, safely, aur without middlemen. Booking, payment, aur check-in sab ek jagah.

---

## 2. The Core Problem

| Who | Problem |
|-----|---------|
| Creator | Verified, safe studio dhundhna mushkil hai. Cash deal unsafe lagti hai. |
| Studio Manager | Slots waste hote hain no-shows ki wajah se. Discovery limited hai. |
| Both | Koi standard booking system nahi — sab WhatsApp pe hota hai. |

---

## 3. The Solution — Scan-to-Shoot Flow

```
Creator browses app
       ↓
Selects studio + 3hr slot + optional skill worker
       ↓
Pays 50% advance (platform holds it)
       ↓
Arrives → scans QR at studio desk
       ↓
Status: ACTIVE → studio's advance released (T+2)
       ↓
Shoot happens → pays remaining 50% directly to manager
       ↓
Manager clicks "Shoot Complete" → booking closed
```

---

## 4. Tech Stack

| Layer | Technology |
|-------|------------|
| Mobile App | Expo (React Native) — creators + studio managers |
| Admin Dashboard | Next.js — internal use only |
| Backend | Node.js + Express — standalone server |
| Database | PostgreSQL via Supabase |
| Auth | JWT + Supabase Auth |
| Payments | Razorpay |
| QR | node-qrcode (static QR per studio) |
| Hosting | Railway / Render (backend), Vercel (admin) |

---

## 5. User Roles

### 5.1 Creator
- Browse studios by city, type, price, availability
- View 3hr slots, select date + time
- Add optional skill worker (photographer, editor, etc.) to booking
- Pay 50% advance via app
- Scan QR at studio to check in
- Pay remaining 50% directly to manager (cash/UPI)
- View booking history

### 5.2 Studio Manager
- List studio: name, location, photos, type, price per 3hr slot
- **Mandatory:** Fill "What's included" (e.g. AC, ring light, backdrop) and "What's not included" (e.g. camera, makeup) — listing won't go live without these
- Price set karo — GST included final price, platform commission internally added
- Set available slots (calendar)
- View upcoming bookings
- Confirm/reject booking requests
- Click "Shoot Complete" to close booking
- View payout history (T+2 settlement)

### 5.3 Agency (covers solo workers + multi-worker agencies)

**One account type for all** — ek solo photographer bhi agency ki tarah register karta hai, khud ko worker ke roop mein add karta hai. Badi agency apne 10-20 workers add karti hai. Same dashboard, same flow.

- Register as Agency → KYC (Aadhaar for solo, GST + Aadhaar for agency)
- Add workers under agency account (min 1 — khud bhi ho sakta hai)
- Each worker ka profile: skill type, portfolio link, rate per shoot
- Agency bookings accept/reject karti hai
- Payment agency account mein aata hai — wo apne workers ko distribute karti hai
- Worker no-show → agency ka noshow count badhta hai
- Discovery feed mein agency ke workers dikhte hain — creator worker choose karta hai, booking agency ke paas jaati hai

### 5.4 Admin (Internal — Next.js Dashboard)
- View all bookings, users, studios
- Manually trigger payouts
- Ban / suspend studios (30-day or permanent)
- Handle dispute flags
- View revenue breakdown

---

## 6. Database Schema

### `users`
```
id                UUID  PK
name              TEXT
email             TEXT  UNIQUE
phone             TEXT
role              ENUM  (CREATOR, STUDIO_MANAGER, AGENCY, ADMIN)
is_active         BOOL  DEFAULT true
kyc_status        ENUM  (PENDING, VERIFIED, FAILED)  DEFAULT PENDING
kyc_aadhaar_ref   TEXT  NULLABLE
kyc_verified_at   TIMESTAMP  NULLABLE
created_at        TIMESTAMP
```

### `agencies`
```
id                UUID  PK
user_id           UUID  FK → users.id  (agency account)
agency_name       TEXT
bio               TEXT
city              TEXT
noshow_count      INT   DEFAULT 0
suspect_since     TIMESTAMP  NULLABLE  (set on 3rd noshow)
is_suspended      BOOL  DEFAULT false
suspended_until   TIMESTAMP  NULLABLE
created_at        TIMESTAMP
```

### `agency_workers`
```
id                UUID  PK
agency_id         UUID  FK → agencies.id
name              TEXT
skill_type        ENUM  (PHOTOGRAPHER, VIDEOGRAPHER, EDITOR, SOUND, LIGHTING, OTHER)
portfolio_url     TEXT  NULLABLE
rate_per_shoot    INT   (in paise — agency sets this, GST included)
is_available      BOOL  DEFAULT true
created_at        TIMESTAMP
```

### `studios`
```
id                UUID  PK
manager_id        UUID  FK → users.id
name              TEXT
description       TEXT
whats_included    TEXT  — MANDATORY (e.g. "AC, ring light, backdrop, changing room, Wi-Fi")
whats_not_included TEXT  — MANDATORY (e.g. "Camera, lenses, makeup artist, food")
city              TEXT
address           TEXT
type              ENUM  (PHOTO_VIDEO, PODCAST, MUSIC_RECORDING, SHOOTING_LOCATION, OTHER)
price_per_slot    INT   (in paise, 3hr slot — GST included, final price)
photos            TEXT[]
qr_code           TEXT  (static QR string per studio)
is_verified       BOOL  DEFAULT false
is_active         BOOL  DEFAULT true
suspension_count  INT   DEFAULT 0
suspended_until   TIMESTAMP  NULLABLE
created_at        TIMESTAMP
```

> **Pricing rule:** `price_per_slot` is the all-inclusive final price shown to creator. GST is baked in — no surprise charges at checkout. Studio manager sets their own price; platform adds 15% commission on top internally. Creator always sees one clean number.

### `slots`
```
id            UUID  PK
studio_id     UUID  FK → studios.id
date          DATE
start_time    TIME
end_time      TIME  (always start_time + 3hr)
is_available  BOOL  DEFAULT true
```

### `bookings`
```
id                    UUID  PK
creator_id            UUID  FK → users.id
studio_id             UUID  FK → studios.id
slot_id               UUID  FK → slots.id
status                ENUM  (PENDING_PAYMENT, ADVANCE_PAID, ACTIVE, COMPLETED, NO_SHOW, CANCELLED)
total_amount          INT   (in paise — studio slot price, GST included)
advance_paid          INT   (50% of total_amount)
agency_worker_id      UUID  FK → agency_workers.id  NULLABLE
worker_fee_total      INT   NULLABLE  (worker ka agreed fee, in paise)
worker_advance_paid   INT   NULLABLE  (50% of worker_fee_total)
razorpay_order_id     TEXT
created_at            TIMESTAMP
```

### `payments`
```
id                    UUID  PK
booking_id            UUID  FK → bookings.id
razorpay_payment_id   TEXT
amount                INT   (in paise)
type                  ENUM  (ADVANCE_STUDIO, ADVANCE_WORKER, PAYOUT_STUDIO, PAYOUT_WORKER, COMMISSION_CJCS)
status                ENUM  (PENDING, SUCCESS, FAILED, REFUNDED)
created_at            TIMESTAMP
```

### `qr_scans`
```
id            UUID  PK
booking_id    UUID  FK → bookings.id
studio_id     UUID  FK → studios.id
scanned_at    TIMESTAMP
scanned_by    UUID  FK → users.id
```

---

## 7. API Endpoints

### Auth
```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/refresh
```

### Studios
```
GET    /api/studios              — list with filters (city, type, date)
GET    /api/studios/:id          — detail + available slots
POST   /api/studios              — create (manager only)
PUT    /api/studios/:id          — update (manager only)
```

### Slots
```
GET    /api/studios/:id/slots    — available slots for a date range
POST   /api/studios/:id/slots    — add slots (manager only)
DELETE /api/slots/:id            — remove slot (manager only)
```

### Bookings
```
POST   /api/bookings             — create booking + Razorpay order
GET    /api/bookings/me          — creator's bookings
GET    /api/bookings/studio/:id  — studio's bookings (manager)
PUT    /api/bookings/:id/complete — mark shoot complete (manager)
```

### Payments
```
POST   /api/payments/verify      — Razorpay webhook handler
GET    /api/payments/history     — payout history (manager)
```

### QR
```
POST   /api/qr/scan              — scan event → booking status ACTIVE
GET    /api/qr/studio/:id        — get QR code for studio (manager)
```

### Admin
```
GET    /api/admin/bookings        — all bookings
GET    /api/admin/studios         — all studios
POST   /api/admin/studios/:id/suspend  — suspend studio
DELETE /api/admin/studios/:id/suspend  — lift suspension
GET    /api/admin/revenue         — commission breakdown
```

---

## 8. App Screens

### Creator Flow
1. **Splash / Onboarding** — CultureJeevan branding, role select
2. **Home** — city picker, search bar, studio cards grid
3. **Studio Detail** — photos, description, slot calendar, price
4. **Booking Form** — slot confirm, optional skill worker add
5. **Payment Screen** — Razorpay 50% advance
6. **Booking Confirmed** — booking ID, QR scan instructions
7. **Check-in Screen** — camera opens, scan studio QR
8. **My Bookings** — list with status badges
9. **Profile** — name, phone, booking history

### Studio Manager Flow
1. **Dashboard** — today's bookings, upcoming list
2. **Booking Detail** — creator info, slot, payment status
3. **Shoot Complete Button** — one tap to close booking
4. **My Studio** — edit listing, photos, slots calendar
5. **Payouts** — T+2 settlement history
6. **Add Slots** — date picker, time picker (3hr blocks)

### Skill Worker Flow
1. **Profile Setup** — skill type, rate, portfolio
2. **My Shoots** — assigned bookings list

---

## 9. Revenue Model

**Pricing reality:** Studio slots in India range from ₹500–₹800/hr for basic setups to ₹1,500–₹3,000/hr for premium studios. A 3hr slot realistically falls between ₹3,000–₹15,000 depending on city and studio type.

**GST rule:** All prices shown on the app are GST-inclusive. Creator pays one clean price — no extra charges at checkout. CultureJeevan handles GST compliance internally.

```
Example: Studio slot ₹5,000 + Skill Worker fee ₹1,000

── Studio booking ──
Creator pays advance (app):     ₹2,500  (50% of ₹5,000)
  → CJCS commission (15%):      ₹750    ← kept by platform
  → Studio payout (T+2):        ₹1,750
Creator pays balance (direct):  ₹2,500  (cash/UPI to manager on shoot day)

── Skill worker ──
Creator pays advance (app):     ₹500    (50% of ₹1,000)
  → Held by platform
  → Worker payout (T+2 after shoot): ₹500
Creator pays balance (direct):  ₹500    (cash/UPI to worker on shoot day)

── Summary ──
Studio total:       ₹4,250  (after 15% commission)
Worker total:       ₹1,000  (full fee, no commission on worker in v1)
CultureJeevan:      ₹750    per booking (commission on studio only)
```

> **Note:** Platform commission is on studio fee only in v1. Worker marketplace commission (v2 consideration).

---

## 10. Business Rules

### No-Show (Creator)
- Creator ne QR scan nahi kiya within 30 min of slot start
- Status → `NO_SHOW`
- 50% advance NOT refunded
- Studio gets "kill fee" share from advance

### Studio No-Show / Studio Cancels
- Studio unavailable ya cancels karta hai kisi bhi wajah se
- Creator gets 100% refund immediately
- CJCS waives commission
- Repeat cancellations → suspension (same rules as bypass)

### Creator Cancels
- Kisi bhi wajah se, kisi bhi time pe — NO REFUND
- Studio ka slot block hua tha, uska business impact hua
- Status → `CANCELLED`, advance forfeited

### Skill Worker No-Show
- Worker shoot day pe nahi aaya
- Creator ko worker ka advance (50%) **full refund**
- Worker ka `worker_noshow_count` +1
- **1st no-show** → `YELLOWLISTED` — visible badge on profile, creators ko warning dikhti hai
- **2nd no-show** → `BLACKLISTED` — profile hidden, koi naya booking nahi le sakta
- Blacklisted worker admin appeal kar sakta hai only (manual review)

### Skill Worker Payment Flow

Same as studio — QR-based activation:

```
Creator adds worker to booking (agrees on total fee e.g. ₹1,500)
       ↓
Creator pays 50% advance on platform (₹750) along with studio advance
       ↓
Worker arrives at studio → scans same studio QR
       ↓
Worker status → ACTIVE, worker's advance released to them (T+2)
       ↓
Shoot complete → Creator pays remaining ₹750 directly to worker (cash/UPI)
       ↓
Manager clicks "Shoot Complete" → both studio + worker booking closed
```

**Worker no-show rule:** Worker ne QR scan nahi kiya within 30 min of slot start → `NO_SHOW`, creator ko 50% advance full refund.

### Studio Cancellation / Suspension Rules

```
1st–2nd cancellation  → Warning logged, no visible action
3rd cancellation      → SUSPECT label on listing
                         Ranking downgraded in search results
                         Badge visible to creators: "This studio has cancellation history"
4th cancellation      → Admin review triggered
5th cancellation      → 30-day suspension (listing hidden)
2nd suspension        → Permanent ban
```

**Bypass attempt** (studio asks creator to pay 100% cash directly, skip platform):
- 1st offense → immediate 30-day suspension
- 2nd offense → permanent ban

> Suspect label + ranking downgrade is intentional — creators can still book if they want, but they're informed. Hard ban sirf tab jab pattern clearly problematic ho.

### Slot Rules
- Fixed 3-hour blocks only
- Manager sets availability; platform does not auto-generate
- One booking per slot — no double booking

---

## 11. 30-Day Noida Pilot Plan

| Week | Goal |
|------|------|
| Week 1 | Onboard 5 studios in Sector 62/63 Noida |
| Week 2 | Sign up 10 film students as skill workers |
| Week 3 | Target creators at Amity, AAFT, Galgotias |
| Week 4 | First 10 real bookings, measure no-show rate |

**Minimal Tech for Pilot:**
- Backend API + Supabase DB (full)
- Basic Expo app (booking + payment + QR scan)
- Next.js admin dashboard (bookings view + manual payout trigger)

---

## 12. Out of Scope (v1)

- Gear rental
- In-app messaging between creator and manager
- Reviews and ratings
- Subscription plans for studios
- Co-working spaces
- Automated T+2 payout (manual in pilot, Razorpay Route in v2)

---

## 13. KYC — Studio Manager & Agency Verification

**Mandatory for studio managers and agencies before going live.**

### KYC by account type
- **Studio Manager:** Aadhaar OTP verification (individual)
- **Solo Agency (1 worker):** Aadhaar OTP verification
- **Agency (2+ workers):** GST number + one Aadhaar (owner's)

### Third-party API options

| Provider | Cost per verification | Notes |
|----------|-----------------------|-------|
| Surepass | ₹3–₹5 | Most popular, easy integration |
| Signzy | ₹5–₹8 | Better dashboard, slightly pricier |
| Razorpay KYC | Bundled with payouts | Best option if using Razorpay Route in v2 |

### Pilot approach (first 30 days)
Manual KYC — Aadhaar photo WhatsApp pe lo, Google Sheet mein log karo. API integration tab karo jab 20+ onboarded ho jaayein.

### v1 app flow
1. Register → status `PENDING_KYC`
2. KYC screen → Aadhaar + OTP (Surepass API)
3. Verified → `ACTIVE`, listing/profile live
4. Failed → `KYC_FAILED`, email support

---

## 14. Resolved — Suspect Label & Worker Commission

### Suspect Label Removal
- **Automatic:** 60 days ke baad koi aur cancellation nahi aayi → label automatically hata diya jaata hai, ranking restore
- **False report appeal:** Studio humein email karta hai → hum creator se confirm karte hain → agar confirmed false hai toh cancellation record delete, label hata diya jaata hai

### Worker Commission (v2)
- Platform fee skill worker fee pe bhi lagegi — same 15% model as studio
- v1 mein worker fee pe zero commission (trust build karne ke liye)
- v2 se full marketplace model

---

*Document owner: Dhawal | CultureJeevan | v1.3*

---
# -*- coding: utf-8 -*-
# ============================================================
#  MAKTAB BUXGALTERIYA — METIS DIZAYN (v4.0)
#  Foydalanuvchi tanlagan Metis admin template (themewagon)
#  uslubi asosida NOLDAN qurilgan: oq sidebar, oq header
#  (o'rtada qidiruv), och kulrang fonda oq kartalar,
#  ko'k aksent #2563EB, Inter shrifti.
#  Streamlit + Firebase Realtime Database — to'liq o'zbek tilida
# ============================================================

import io
import os
import json
import time
import html
import random
import hashlib
import hmac
from datetime import datetime, date

import requests
import pandas as pd
import altair as alt
import streamlit as st

# ----------------- ASOSIY SOZLAMALAR -----------------
DB_URL = "https://maktab-buxgalteriya-default-rtdb.firebaseio.com"
BOSH = "accounting"  # barcha ma'lumotlar shu bo'lim ichida
try:
    DB_AUTH = st.secrets.get("DB_AUTH", "")
except Exception:
    DB_AUTH = ""

OYLAR = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
         "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]

# Metis palitrasi
C = {
    "primary": "#2563EB", "primary2": "#1D4ED8",
    "bg": "#F8F9FA", "card": "#FFFFFF", "line": "#ECEEF3",
    "txt": "#111827", "sub": "#6B7280",
    "ok": "#16A34A", "okbg": "#DCFCE7",
    "warn": "#B45309", "warnbg": "#FEF3C7",
    "bad": "#DC2626", "badbg": "#FEE2E2",
    "infobg": "#DBEAFE", "tile": "#EFF6FF",
    "blue": "#3B82F6", "teal": "#14B8A6", "orange": "#F97316",
    "purple": "#8B5CF6",
}

st.set_page_config(
    page_title="Maktab Buxgalteriya",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    _v = tuple(int(p) for p in str(st.__version__).split(".")[:2])
except Exception:
    _v = (1, 40)
KENG = {"width": "stretch"} if _v >= (1, 50) else {"use_container_width": True}


def keng(fn, **kw):
    """Streamlit versiyasiga mos kenglik parametri."""
    try:
        return fn(**kw, **KENG)
    except TypeError:
        return fn(**kw, use_container_width=True)


# ----------------- SESIYA HOLATI -----------------
ss = st.session_state
ss.setdefault("kirgan", False)
ss.setdefault("login", "")
ss.setdefault("rol", "admin")
ss.setdefault("urinish", 0)
ss.setdefault("blok", 0.0)
ss.setdefault("tk", "")
ss.setdefault("tv", 0.0)

# ----------------- FIREBASE -----------------
def fb_get(yol):
    try:
        p = {"auth": DB_AUTH} if DB_AUTH else None
        r = requests.get(f"{DB_URL}/{BOSH}/{yol}.json", params=p, timeout=12)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def fb_put(yol, qiymat):
    try:
        p = {"auth": DB_AUTH} if DB_AUTH else None
        r = requests.put(f"{DB_URL}/{BOSH}/{yol}.json", params=p, json=qiymat, timeout=15)
        return r.status_code == 200
    except Exception:
        return False


def fb_del(yol):
    try:
        p = {"auth": DB_AUTH} if DB_AUTH else None
        r = requests.delete(f"{DB_URL}/{BOSH}/{yol}.json", params=p, timeout=15)
        return r.status_code == 200
    except Exception:
        return False


@st.cache_data(ttl=40, show_spinner=False)
def _baza_oqi():
    return {
        "config": fb_get("config") or {},
        "data": fb_get("data") or {},
        "students": fb_get("students") or {},
        "expenses": fb_get("expenses") or {},
        "payments": fb_get("payments") or [],
    }


def oqi():
    return _baza_oqi()


def saqla(yol, qiymat):
    ok = fb_put(yol, qiymat)
    _baza_oqi.clear()
    return ok


def ochir(yol):
    ok = fb_del(yol)
    _baza_oqi.clear()
    return ok


# ----------------- HISOBLASH YORDAMCHILARI -----------------
def num(x):
    if x is None:
        return 0
    if isinstance(x, bool):
        return 1 if x else 0
    if isinstance(x, (int, float)):
        f = float(x)
        return int(f) if f.is_integer() else f
    s = str(x).strip().replace(" ", "").replace("\u00a0", "").replace(",", ".")
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except Exception:
        return 0


def fmt(x):
    v = num(x)
    try:
        fv = float(v)
    except Exception:
        fv = 0.0
    if fv == int(fv):
        return f"{int(fv):,}".replace(",", " ")
    return f"{fv:,.2f}".replace(",", " ").replace(".", ",")


def som(x):
    return fmt(x) + " so'm"


def foiz(a, b):
    a, b = num(a), num(b)
    if b <= 0:
        return 0
    return int(round(a / b * 100))


def sof(r):
    return num(r.get("price"))


def tolangan(r):
    return num(r.get("food"))


def qarz_r(r):
    return max(0, sof(r) - tolangan(r))


def holat_key(p, t):
    p, t = num(p), num(t)
    if p > 0 and t >= p:
        return "st-paid"
    if t > 0:
        return "st-part"
    return "st-debt"


def holat_r(r):
    return holat_key(sof(r), tolangan(r))


def oy_rows(oy):
    return oqi()["data"].get(oy) or []


def yaroqli(rows):
    out = []
    for r in rows:
        if str(r.get("name") or "").strip():
            out.append(r)
    return out


def oy_stat(oy):
    rows = yaroqli(oy_rows(oy))
    reja = sum(sof(r) for r in rows)
    yig = sum(tolangan(r) for r in rows)
    qarz = sum(qarz_r(r) for r in rows)
    keldi = sum(1 for r in rows if r.get("att"))
    n = len(rows)
    return {
        "oy": oy, "n": n, "reja": reja, "yig": yig, "qarz": qarz,
        "und": foiz(yig, reja), "dav": foiz(keldi, n) if n else 0,
        "keldi": keldi, "kelmadi": n - keldi,
    }


def umumiy():
    D = oqi()["data"]
    tushum = yig = qarz = 0.0
    bor = []
    seriya_reja, seriya_yig, seriya_qarz = [], [], []
    for oy in OYLAR:
        rows = yaroqli(D.get(oy) or [])
        s = oy_stat(oy)
        seriya_reja.append(s["reja"])
        seriya_yig.append(s["yig"])
        seriya_qarz.append(s["qarz"])
        if rows:
            bor.append(oy)
        tushum += s["reja"]
        yig += s["yig"]
        qarz += s["qarz"]
    return {
        "tushum": tushum, "yig": yig, "qarz": qarz,
        "und": foiz(yig, tushum), "oylar": bor, "oylar_soni": len(bor),
        "s_reja": seriya_reja, "s_yig": seriya_yig, "s_qarz": seriya_qarz,
    }


def baza_list():
    S = oqi()["students"]
    ch = []
    if isinstance(S, list):
        for i, v in enumerate(S):
            ch.append((i, v or {}))
    elif isinstance(S, dict):
        for k, v in S.items():
            try:
                i = int(k)
            except Exception:
                i = 10 ** 9
            ch.append((i, v or {}))
    ch.sort(key=lambda t: t[0])
    return ch


def students_nusxa():
    """students bazasining ro'yxat ko'rinishidagi nusxasi (saqlash uchun)."""
    return [v for _, v in baza_list()]


def baza_sinf():
    m = {}
    for _, rec in baza_list():
        nm = str(rec.get("name") or "").strip()
        if nm:
            m[nm] = str(rec.get("cls") or "").strip()
    return m


def trend_foiz(seriya):
    qiymatlar = [v for v in seriya if v > 0]
    if len(qiymatlar) < 2:
        return None
    eski, yangi = qiymatlar[-2], qiymatlar[-1]
    if eski <= 0:
        return None
    return round((yangi - eski) / eski * 100)


# ----------------- XAVFSIZLIK -----------------
def hash_pw(p):
    tuz = os.urandom(8)
    dk = hashlib.pbkdf2_hmac("sha256", str(p).encode(), tuz, 120_000)
    return f"pbkdf2${tuz.hex()}${dk.hex()}"


def check_pw(p, saqlangan):
    try:
        qismlar = str(saqlangan).split("$")
        if len(qismlar) != 3 or qismlar[0] != "pbkdf2":
            return False
        tuz = bytes.fromhex(qismlar[1])
        dk = hashlib.pbkdf2_hmac("sha256", str(p).encode(), tuz, 120_000)
        return hmac.compare_digest(dk.hex(), qismlar[2])
    except Exception:
        return False


def faqat_raqam(x):
    return "".join(c for c in str(x or "") if c.isdigit())


# ----------------- TELEGRAM -----------------
def tg_yubor(matn):
    cfg = oqi()["config"] or {}
    token = str(cfg.get("tgToken") or "").strip()
    chat = str(cfg.get("chatId") or "").strip()
    if not token or not chat:
        return False, "Telegram sozlanmagan (Sozlamalar → Telegram)"
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": matn, "parse_mode": "HTML"},
            timeout=12,
        )
        if r.status_code == 200:
            return True, "Yuborildi"
        return False, f"Telegram xatosi: {r.status_code}"
    except Exception as e:
        return False, f"Xatolik: {e}"


# ----------------- EXCEL EKSPORT -----------------
def excel_tugma(df, nom, kalit):
    buf = io.BytesIO()
    tur = "csv"
    try:
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="Hisobot")
        tur = "xlsx"
    except Exception:
        buf = io.BytesIO()
        df.to_csv(buf, index=False)
    buf.seek(0)
    fayl = f"{nom}.{tur}"
    mime = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if tur == "xlsx" else "text/csv")
    keng(
        st.download_button,
        label="⬇️ " + fayl + " yuklab olish",
        data=buf,
        file_name=fayl,
        mime=mime,
        key=kalit,
    )


# ----------------- TO'LOV QO'SHISH (umumiy) -----------------
def tolov_qosh(oy, ism, summa, izoh=""):
    summa = num(summa)
    if summa <= 0:
        return False, "Summa 0 dan katta bo'lishi kerak"
    rows = list(oy_rows(oy))
    topildi = False
    for r in rows:
        if str(r.get("name") or "").strip() == str(ism).strip():
            r["food"] = int(num(r.get("food")) + summa)
            r["st"] = holat_key(r.get("price"), r.get("food"))
            topildi = True
            break
    if not topildi:
        return False, "O'quvchi tanlangan oyda topilmadi"
    if not saqla(f"data/{oy}", rows):
        return False, "Saqlashda xatolik (internet/DB)"
    pays = list(oqi()["payments"] or [])
    pays.append({
        "ts": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "oy": oy, "ism": str(ism).strip(),
        "summa": int(summa), "izoh": str(izoh or ""),
    })
    saqla("payments", pays[-500:])
    return True, f"{ism} uchun {som(summa)} to'lov qabul qilindi"


def oxirgi_tovlovlar(n=6):
    pays = list(oqi()["payments"] or [])
    pays.reverse()
    return pays[:n]


def qarzdorlar_royxati():
    D = oqi()["data"]
    sinflar = baza_sinf()
    natija = []
    for oy in OYLAR:
        for r in yaroqli(D.get(oy) or []):
            q = qarz_r(r)
            if q > 0:
                ism = str(r.get("name")).strip()
                natija.append({
                    "ism": ism, "oy": oy,
                    "sinf": sinflar.get(ism, "") or "—",
                    "reja": sof(r), "tolangan": tolangan(r), "qarz": q,
                })
    natija.sort(key=lambda x: -x["qarz"])
    return natija


# ============================================================
#              METIS DIZAYN TIZIMI (CSS)
# ============================================================
CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root{
  --pri:#2563EB; --pri2:#1D4ED8;
  --bg:#F8F9FA; --card:#FFFFFF; --line:#ECEEF3;
  --txt:#111827; --sub:#6B7280;
  --ok:#16A34A; --okbg:#DCFCE7;
  --warn:#B45309; --warnbg:#FEF3C7;
  --bad:#DC2626; --badbg:#FEE2E2;
  --tile:#EFF6FF;
}

html, body, .stApp{
  font-family:'Inter','Segoe UI',sans-serif !important;
  background:var(--bg); color:var(--txt);
}
.stApp > header{background:transparent}
.block-container{max-width:1260px; padding:108px 30px 34px !important}
h1,h2,h3,h4,p,span,label,div{font-family:'Inter','Segoe UI',sans-serif}

#MainMenu, footer[data-testid="stFooter"], [data-testid="stStatusWidget"],
header[data-testid="stHeader"], .stDeployButton,
div[data-testid="stDecoration"], [data-testid="stToolbar"],
[data-testid="stSidebarCollapseButton"] > div:first-child{
  display:none !important;
}

/* ============ HEADER (Metis: oq, o'rtada qidiruv) ============ */
.m-head{
  position:fixed; top:0; right:0; left:256px; z-index:90;
  height:64px; display:flex; align-items:center; gap:16px;
  padding:0 26px; background:#fff;
  border-bottom:1px solid var(--line);
}
.m-head .h-logo{display:flex; align-items:center; gap:10px; flex:none}
.m-head .h-tile{
  width:38px; height:38px; border-radius:10px; background:var(--pri);
  color:#fff; font-size:19px; display:flex; align-items:center; justify-content:center;
}
.m-head .h-name b{display:block; font-size:15.5px; font-weight:800; letter-spacing:-.2px; color:var(--txt)}
.m-head .h-name span{display:block; font-size:9px; font-weight:700; letter-spacing:2px; color:var(--sub); margin-top:1px}
.m-head .h-burger{
  width:34px; height:34px; border-radius:8px; border:1px solid var(--line);
  background:#fff; color:var(--sub); font-size:15px;
  display:flex; align-items:center; justify-content:center; flex:none;
}
.m-search{
  flex:1; max-width:560px; margin:0 auto; height:42px;
  background:#F3F4F6; border:1px solid transparent; border-radius:10px;
  display:flex; align-items:center; gap:10px; padding:0 14px;
  color:#9CA3AF; font-size:13.5px;
}
.m-search .mag{font-size:14px}
.m-search .kbd{
  margin-left:auto; background:#fff; border:1px solid var(--line);
  border-radius:6px; padding:2px 7px; font-size:11px; color:var(--sub); font-weight:600;
}
.m-head .h-right{display:flex; align-items:center; gap:12px; flex:none; margin-left:auto}
.m-chip{
  height:36px; padding:0 12px; border-radius:9px; background:#fff;
  border:1px solid var(--line); display:flex; align-items:center; gap:7px;
  font-size:12.5px; font-weight:600; color:var(--txt); white-space:nowrap;
}
.m-bell{
  position:relative; width:38px; height:38px; border-radius:50%;
  border:1px solid var(--line); background:#fff; font-size:16px;
  display:flex; align-items:center; justify-content:center;
}
.m-bell .n{
  position:absolute; top:-5px; right:-5px; min-width:18px; height:18px;
  border-radius:9px; background:#EF4444; color:#fff; font-size:10.5px;
  font-weight:700; display:flex; align-items:center; justify-content:center; padding:0 5px;
}
.m-user{
  display:flex; align-items:center; gap:10px; padding:5px 12px 5px 6px;
  border:1px solid var(--line); border-radius:999px; background:#fff;
}
.m-user b{display:block; font-size:13px; font-weight:700; color:var(--txt); line-height:1.15}
.m-user span{display:block; font-size:10.5px; color:var(--sub); font-weight:500}
.m-av{
  width:32px; height:32px; border-radius:50%; color:#fff; font-size:13px; font-weight:700;
  background:linear-gradient(135deg,#2563EB,#60A5FA);
  display:flex; align-items:center; justify-content:center; flex:none;
}
.m-av.k{width:26px; height:26px; font-size:11px}
.stApp:has([data-testid="stSidebar"][aria-expanded="false"]) .m-head{left:0}
@media (max-width: 900px){
  .m-search{display:none}
  .m-head{padding:0 14px; gap:10px}
}

/* ============ SIDEBAR (oq, Metis) ============ */
[data-testid="stSidebar"]{
  background:#FFFFFF !important;
  border-right:1px solid var(--line) !important;
  width:256px !important; min-width:256px !important;
}
[data-testid="stSidebar"] .block-container{padding:22px 16px 26px !important}
[data-testid="stSidebar"] *{color:var(--txt)}
[data-testid="stSidebar"] label{margin-bottom:0}
[data-testid="stSidebar"] p{margin-bottom:0}
.m-cap{
  font-size:10.5px; font-weight:700; letter-spacing:1.6px; color:#9CA3AF;
  padding:16px 12px 8px; text-transform:uppercase;
}
/* radio menyuni Metis elementiga aylantirish */
[data-testid="stSidebar"] div[role="radiogroup"]{gap:2px !important}
[data-testid="stSidebar"] div[role="radiogroup"] > div{margin:0 !important}
[data-testid="stSidebar"] div[role="radiogroup"] label[data-testid="stRadioOption"]{
  display:flex; align-items:center; padding:0; margin:0;
  border-radius:9px; transition:background .15s;
}
/* radio doirachasini yashirish */
[data-testid="stSidebar"] div[role="radiogroup"] label[data-testid="stRadioOption"] > div > div:first-child{
  display:none !important; width:0 !important; margin:0 !important; padding:0 !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] label[data-testid="stRadioOption"] > div{
  width:100% !important; padding:10px 12px !important; border-radius:9px !important;
  font-size:13.5px !important; font-weight:500 !important; color:#374151 !important;
  transition:background .15s, color .15s; border:1px solid transparent;
}
[data-testid="stSidebar"] div[role="radiogroup"] label[data-testid="stRadioOption"]:hover > div{
  background:#F3F4F6 !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] label[data-testid="stRadioOption"][data-selected="true"] > div{
  background:var(--tile) !important; color:var(--pri) !important; font-weight:700 !important;
  border-color:#DBEAFE !important;
}
/* Foydalanuvchi kartochkasi */
.m-ucard{
  background:#F9FAFB; border:1px solid var(--line); border-radius:12px;
  padding:12px; display:flex; align-items:center; gap:10px; margin-top:14px;
}
.m-ucard b{display:block; font-size:13.5px; font-weight:700}
.m-ucard span{display:block; font-size:11px; color:var(--sub); font-weight:500}
.m-alert{
  margin-top:12px; background:var(--badbg); border:1px solid #FECACA;
  color:var(--bad); border-radius:10px; padding:10px 12px;
  font-size:12.5px; font-weight:600; display:flex; gap:8px; align-items:center;
}
.m-refresh{
  margin-top:12px; display:flex; gap:8px;
}

/* ============ SAHIFA SARLAVHASI (Metis Page header) ============ */
.m-phead{
  display:flex; align-items:flex-start; justify-content:space-between;
  gap:14px; margin:2px 0 20px;
}
.m-phead .t{font-size:25px; font-weight:800; letter-spacing:-.5px; color:var(--txt); line-height:1.15}
.m-phead .s{font-size:13.5px; color:var(--sub); margin-top:5px}
.m-phead .right{display:flex; gap:9px; align-items:center; padding-top:4px}

/* ============ STAT KARTALAR (Metis KPI) ============ */
.m-stats{
  display:grid; grid-template-columns:repeat(auto-fit, minmax(215px, 1fr));
  gap:16px; margin-bottom:20px;
}
.m-stat{
  background:var(--card); border:1px solid var(--line); border-radius:14px;
  padding:18px 18px 16px; display:flex; gap:14px; align-items:flex-start;
  box-shadow:0 1px 2px rgba(16,24,40,.04);
}
.m-stat .ic{
  width:46px; height:46px; border-radius:12px; background:var(--tile);
  border:1px solid #DBEAFE; display:flex; align-items:center; justify-content:center;
  font-size:21px; flex:none;
}
.m-stat .lab{
  font-size:11px; font-weight:700; letter-spacing:.8px; color:var(--sub);
  text-transform:uppercase; margin-bottom:3px; white-space:nowrap;
}
.m-stat .val{
  font-size:25px; font-weight:800; letter-spacing:-.6px; color:var(--txt);
  line-height:1.1; white-space:nowrap;
}
.m-stat .val .u{font-size:13px; font-weight:600; color:var(--sub); margin-left:4px}
.m-stat .tr{font-size:12.5px; font-weight:700; margin-top:4px}
.m-stat .tr.up{color:var(--ok)} .m-stat .tr.dn{color:var(--bad)}
.m-stat .tr span{color:var(--sub); font-weight:500; font-size:11.5px}
.m-stat .tr.fl{color:var(--sub)}

/* ============ KARTA (Metis panel) ============ */
.m-card{
  background:var(--card); border:1px solid var(--line); border-radius:14px;
  box-shadow:0 1px 2px rgba(16,24,40,.04); margin-bottom:20px; overflow:hidden;
}
.m-card .cap{
  display:flex; align-items:center; justify-content:space-between; gap:12px;
  padding:16px 20px 12px;
}
.m-card .cap .tt{font-size:15.5px; font-weight:700; letter-spacing:-.2px; color:var(--txt)}
.m-card .cap .ss{font-size:12.5px; color:var(--sub); margin-top:2px}
.m-card .body{padding:0 20px 16px}
.m-card .fx{display:flex; align-items:flex-start; justify-content:space-between; gap:14px; padding:16px 20px 14px}
.m-ic-btn{
  width:36px; height:36px; border-radius:9px; border:1px solid var(--line);
  background:#fff; display:flex; align-items:center; justify-content:center;
  font-size:15px; color:var(--sub); flex:none;
}

/* Toggle guruh (7D / 30D uslubi) */
.m-seg{display:flex; background:#F3F4F6; border-radius:9px; padding:3px; gap:2px}
.m-seg span{padding:5px 12px; border-radius:7px; font-size:12px; font-weight:700; color:var(--sub)}
.m-seg span.on{background:#fff; color:var(--pri); box-shadow:0 1px 2px rgba(16,24,40,.08)}

/* ============ JADVAL (Metis table) ============ */
.m-table{width:100%; border-collapse:collapse}
.m-table th{
  text-align:left; font-size:10.5px; font-weight:700; letter-spacing:.8px;
  color:var(--sub); text-transform:uppercase; padding:10px 12px;
  border-bottom:1px solid var(--line); background:#FCFCFD; white-space:nowrap;
}
.m-table td{
  padding:12px; font-size:13.5px; color:var(--txt);
  border-bottom:1px solid #F3F4F6; vertical-align:middle;
}
.m-table tr:last-child td{border-bottom:none}
.m-table tbody tr:hover{background:#FAFBFC}
.m-table .num{font-weight:700; font-variant-numeric:tabular-nums}
.m-table .cellp{display:flex; align-items:center; gap:10px}
.m-table .cellp .sub{display:block; font-size:11px; color:var(--sub)}
.m-scroll{max-height:440px; overflow:auto}
.m-scroll::-webkit-scrollbar{width:8px; height:8px}
.m-scroll::-webkit-scrollbar-thumb{background:#E5E7EB; border-radius:4px}

/* ============ BADGE (Completed/Shipped uslubi) ============ */
.m-bdg{
  display:inline-flex; align-items:center; gap:5px;
  padding:4px 10px; border-radius:999px;
  font-size:11.5px; font-weight:700; letter-spacing:.3px; white-space:nowrap;
}
.m-bdg.ok{background:var(--okbg); color:var(--ok)}
.m-bdg.warn{background:var(--warnbg); color:var(--warn)}
.m-bdg.bad{background:var(--badbg); color:var(--bad)}
.m-bdg.info{background:var(--infobg); color:var(--pri)}
.m-bdg.mut{background:#F3F4F6; color:var(--sub)}

/* ============ PROGRESS BAR ============ */
.m-pb{height:7px; background:#F1F3F7; border-radius:99px; overflow:hidden; min-width:90px}
.m-pb i{display:block; height:100%; border-radius:99px; background:linear-gradient(90deg,#2563EB,#60A5FA)}
.m-pb i.g{background:linear-gradient(90deg,#16A34A,#4ADE80)}
.m-pb i.r{background:linear-gradient(90deg,#DC2626,#F87171)}
.pbrow{display:flex; align-items:center; gap:8px}
.pbrow .pc{font-size:12px; font-weight:700; color:var(--txt)}

/* ============ ACTIVITY (Recent Activity) ============ */
.m-act{
  display:flex; align-items:center; gap:12px; padding:11px 20px;
  border-bottom:1px solid #F3F4F6;
}
.m-act:last-of-type{border-bottom:none}
.m-act .aic{
  width:36px; height:36px; border-radius:50%; background:var(--tile);
  border:1px solid #DBEAFE; display:flex; align-items:center; justify-content:center;
  font-size:15px; flex:none;
}
.m-act .mi{flex:1; min-width:0}
.m-act .mi b{display:block; font-size:13.5px; font-weight:600; color:var(--txt)}
.m-act .mi span{display:block; font-size:12px; color:var(--sub); margin-top:1px;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
.m-act .mv{font-size:13.5px; font-weight:700; color:var(--ok); white-space:nowrap}

/* ============ EMPTY (bo'sh holat) ============ */
.m-empty{
  text-align:center; padding:34px 20px; color:var(--sub); font-size:13.5px;
}
.m-empty .e{font-size:34px; margin-bottom:8px}

/* ============ TAQQOSLASH ============ */
.m-cmp{
  background:var(--card); border:1px solid var(--line); border-radius:12px;
  padding:14px 18px; margin-bottom:10px;
  display:grid; grid-template-columns:1fr auto 1fr; gap:12px; align-items:center;
}
.m-cmp .side{text-align:left}
.m-cmp .side.r{text-align:right}
.m-cmp .side span{display:block; font-size:11.5px; color:var(--sub); font-weight:600; margin-bottom:2px}
.m-cmp .side b{font-size:16.5px; font-weight:800; color:var(--txt)}
.m-cmp .nm{font-size:13px; font-weight:700; color:var(--sub); text-align:center; min-width:130px}
.m-cmp .d{font-size:11.5px; font-weight:700; margin-top:2px}
.m-cmp .d.up{color:var(--ok)} .m-cmp .d.dn{color:var(--bad)}

/* ============ SOZLAMALAR (Metis Settings) ============ */
/* main sahifadagi yagona radio — Sozlamalar ichki navigatsiyasi */
main [data-testid="stRadio"] div[role="radiogroup"]{gap:2px !important}
main [data-testid="stRadio"] div[role="radiogroup"] > div{margin:0 !important}
main [data-testid="stRadio"] label[data-testid="stRadioOption"]{
  display:flex; align-items:center; padding:0; margin:0; border-radius:9px;
}
main [data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div:first-child{
  display:none !important; width:0 !important; margin:0 !important; padding:0 !important;
}
main [data-testid="stRadio"] label[data-testid="stRadioOption"] > div{
  width:100% !important; padding:11px 14px !important; border-radius:9px !important;
  font-size:13.5px !important; font-weight:600 !important; color:#374151 !important;
  transition:background .15s, color .15s;
}
main [data-testid="stRadio"] label[data-testid="stRadioOption"]:hover > div{background:#F3F4F6 !important}
main [data-testid="stRadio"] label[data-testid="stRadioOption"][data-selected="true"] > div{
  background:var(--pri) !important; color:#fff !important; font-weight:700 !important;
}
.m-setrow{
  display:flex; align-items:center; justify-content:space-between; gap:18px;
  padding:18px 0; border-bottom:1px solid #F3F4F6;
}
.m-setrow:last-child{border-bottom:none}
.m-setrow .l b{display:block; font-size:14px; font-weight:700; color:var(--txt)}
.m-setrow .l span{display:block; font-size:12.5px; color:var(--sub); margin-top:3px; max-width:520px}
.m-setrow .r{flex:none; min-width:200px; display:flex; justify-content:flex-end}

/* ============ O'QUVCHI KARTALARI ============ */
.m-grid{
  display:grid; grid-template-columns:repeat(auto-fill, minmax(250px, 1fr));
  gap:14px;
}
.m-stcard{
  background:var(--card); border:1px solid var(--line); border-radius:12px;
  padding:14px; box-shadow:0 1px 2px rgba(16,24,40,.04);
}
.m-stcard .top{display:flex; align-items:center; justify-content:space-between; margin-bottom:9px}
.m-stcard .nm{font-size:14.5px; font-weight:700; color:var(--txt); margin-bottom:7px}
.m-stcard .rw{
  display:flex; align-items:center; justify-content:space-between;
  font-size:12.5px; color:var(--sub);
}
.m-stcard .rw b{color:var(--txt); font-weight:700}

/* ============ LOGIN ============ */
.m-login-top{text-align:center; padding-top:5vh; margin-bottom:22px}
.m-login-top .lg-t{
  width:56px; height:56px; border-radius:15px; background:var(--pri);
  display:flex; align-items:center; justify-content:center; font-size:27px; margin:0 auto 14px;
}
.m-login-top h1{font-size:23px; font-weight:800; letter-spacing:-.4px; margin:0 0 5px}
.m-login-top .sub{font-size:13.5px; color:var(--sub)}
.m-login-mode [data-testid="stForm"]{
  background:var(--card); border:1px solid var(--line); border-radius:18px;
  padding:26px 26px 18px; box-shadow:0 10px 30px rgba(16,24,40,.07);
}
.m-err{
  background:var(--badbg); border:1px solid #FECACA; color:var(--bad);
  border-radius:10px; padding:10px 13px; font-size:13px; font-weight:600; margin-bottom:10px;
}
.m-lock{
  background:var(--warnbg); border:1px solid #FDE68A; color:var(--warn);
  border-radius:10px; padding:12px 13px; font-size:13px; font-weight:600; text-align:center;
}

/* ============ FOOTER ============ */
.m-foot{
  margin-top:8px; padding:18px 6px 6px; border-top:1px solid var(--line);
  display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap;
  font-size:12.5px; color:var(--sub);
}

/* ============ DONUT ============ */
.m-dn{display:flex; flex-direction:column; align-items:center; padding:8px 0 4px}
.dn-row{display:flex; align-items:center; gap:9px; font-size:12.5px; color:var(--txt); padding:4px 0; width:100%}
.dn-row .dot{width:9px; height:9px; border-radius:50%; flex:none}
.dn-row b{margin-left:auto; font-weight:700; font-variant-numeric:tabular-nums}

/* Sidebar pastdagi tugmalar — ixcham */
[data-testid="stSidebar"] .stButton > button{
  padding:8px 10px !important; font-size:12.5px !important;
}
[data-testid="stSidebar"] .m-refresh .stButton > button{width:100%}

/* ============ STREAMLIT UMUMIY ============ */
.stButton > button{
  border-radius:9px; font-weight:600; font-size:13.5px;
  border:1px solid var(--line); background:#fff; color:var(--txt);
  padding:9px 16px;
}
.stButton > button:hover{border-color:#DBEAFE; color:var(--pri); background:#F8FAFF}
.stButton > button[kind="primary"]{
  background:var(--pri); border-color:var(--pri); color:#fff;
}
.stButton > button[kind="primary"]:hover{background:var(--pri2); color:#fff}
.stButton > button:disabled{opacity:.55}
[data-testid="stForm"]{
  background:transparent; border:none; padding:0;
}
div[data-testid="stFormSubmitButton"] > button{width:100%}
[data-baseweb="tab-list"]{gap:6px; border-bottom:1px solid var(--line); margin-bottom:14px}
[data-baseweb="tab"]{padding:9px 15px; border-radius:9px 9px 0 0}
[data-baseweb="tab"] p{font-size:13.5px; font-weight:600}
[data-baseweb="tab-highlight"]{background:var(--pri); height:2.5px !important; border-radius:2px}
[data-baseweb="tab"] [data-testid="stMarkdownContainer"]{color:var(--sub)}
[aria-selected="true"] [data-testid="stMarkdownContainer"] p{color:var(--pri)}
[data-testid="stExpander"]{
  background:var(--card); border:1px solid var(--line) !important;
  border-radius:12px !important; box-shadow:0 1px 2px rgba(16,24,40,.04);
}
[data-testid="stExpander"] summary{padding:13px 16px}
[data-testid="stForm"] [data-testid="stForm"]{border:none}
.stRadio div[role="radiogroup"]{gap:4px}
.stFormSubmitButton button{
  background:var(--pri) !important; border-color:var(--pri) !important; color:#fff !important;
}
.stFormSubmitButton button:hover{background:var(--pri2) !important}
[data-testid="stNumberInput"] input, [data-testid="stTextInput"] input{
  border-radius:9px !important;
}
[data-testid="stDateInput"] input{border-radius:9px !important}
[data-testid="stSelectbox"] > div > div{border-radius:9px !important}
[data-testid="stDownloadButton"] > button{
  background:#fff; border:1px solid var(--line); color:var(--txt);
}
[data-testid="stDownloadButton"] > button:hover{color:var(--pri); border-color:#DBEAFE}
[data-testid="stDataFrame"]{
  border:1px solid var(--line) !important; border-radius:12px !important;
  box-shadow:0 1px 2px rgba(16,24,40,.04); overflow:hidden;
}
[data-testid="stDataEditor"]{
  border:1px solid var(--line) !important; border-radius:12px !important;
  box-shadow:0 1px 2px rgba(16,24,40,.04); overflow:hidden;
}
[data-testid="stAlert"]{border-radius:11px; border:1px solid rgba(0,0,0,.04)}
.stToggle span{font-size:13.5px; font-weight:600}
[data-testid="stCaptionContainer"] p{font-size:12.5px; color:var(--sub)}
hr{border-color:var(--line); margin:6px 0}
"""


def css_yoz(login=False):
    q = CSS
    if login:
        q += "\n\n/* login rejim */\n" \
             "[data-testid=\"stForm\"]{background:var(--card); border:1px solid var(--line);" \
             " border-radius:18px; padding:26px 26px 18px; box-shadow:0 10px 30px rgba(16,24,40,.07);}"
    st.markdown(f"<style>{q}</style>", unsafe_allow_html=True)


# ----------------- HTML YORDAMCHILAR -----------------
def avatar_html(nom, kichkina=False):
    nom = str(nom or "?").strip() or "?"
    bosh = "\U0001f464" if ord(nom[0]) < 128 else nom[0].upper()
    cls = "m-av k" if kichkina else "m-av"
    return f'<div class="{cls}">{html.escape(bosh)}</div>'


def holat_pill(r):
    k = holat_r(r)
    m = {"st-paid": ("TO'LANDI", "ok"), "st-part": ("QISMAN", "warn"), "st-debt": ("QARZ", "bad")}
    txt, cls = m[k]
    return f'<span class="m-bdg {cls}">{txt}</span>'


def pb_html(p, tur=None):
    p = max(0, min(100, int(p)))
    if tur == "ok":
        cls = "g"
    elif tur == "bad":
        cls = "r"
    else:
        cls = "" if p >= 60 else ("r" if p < 30 else "g")
    return f'<div class="pbrow"><div class="m-pb"><i class="{cls}" style="width:{p}%"></i></div><span class="pc">{p}%</span></div>'


def donut_html(foiz_v, markaz, ost, size=170):
    foiz_v = max(0, min(100, int(foiz_v)))
    r = size / 2 - 12
    circ = 2 * 3.14159 * r
    dash = circ * foiz_v / 100
    sx = (size + 14) / 2
    q = (
        f'<div class="m-dn">'
        f'<svg width="{int(sx * 2)}" height="{int(sx)}" viewBox="0 0 {int(sx * 2)} {int(sx)}" style="display:block">'
        f'<g transform="rotate(90 {int(sx)} {int(sx)})">'
        f'<circle cx="{int(sx)}" cy="{int(sx)}" r="{r:.1f}" fill="none" stroke="#EEF1F6" stroke-width="14"/>'
        f'<circle cx="{int(sx)}" cy="{int(sx)}" r="{r:.1f}" fill="none" stroke="#2563EB" stroke-width="14"'
        f' stroke-linecap="round" stroke-dasharray="{dash:.1f} {circ:.1f}"/>'
        f'</g>'
        f'<text x="{int(sx)}" y="{int(sx) - 2}" text-anchor="middle" font-size="{int(size / 6.2)}" font-weight="800" fill="#111827" font-family="Inter,sans-serif">{markaz}</text>'
        f'<text x="{int(sx)}" y="{int(sx) + 17}" text-anchor="middle" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="#6B7280" font-family="Inter,sans-serif">{html.escape(str(ost))}</text>'
        f'</svg></div>'
    )
    return q


def sahifa_sarlavha(sarlavha, ostki, o_ng_html=""):
    st.markdown(
        '<div class="m-phead"><div>'
        f'<div class="t">{html.escape(str(sarlavha))}</div>'
        f'<div class="s">{html.escape(str(ostki))}</div>'
        "</div>"
        f'<div class="right">{o_ng_html}</div></div>',
        unsafe_allow_html=True,
    )


def sana_chip():
    return ('<div class="m-chip">📅 ' + datetime.now().strftime("%d.%m.%Y") + "</div>")


def stat_cards(kartalar):
    """Metis KPI kartalar. kartalar = [dict(ikon, lab, val, unit, trend, trend_sub, tile_bg, tile_border)]"""
    q = []
    for k in kartalar:
        tile = k.get("tile_bg", "var(--tile)")
        border = k.get("tile_border", "#DBEAFE")
        unit = f' <span class="u">{html.escape(str(k["unit"]))}</span>' if k.get("unit") else ""
        tr = ""
        if k.get("trend") is not None:
            t = k["trend"]
            if t > 0:
                tr = f'<div class="tr up">↑ {abs(num(t))}% <span>· {html.escape(str(k.get("trend_sub", "oldingi oygа nisbatan")))}</span></div>'
            elif t < 0:
                tr = f'<div class="tr dn">↓ {abs(num(t))}% <span>· {html.escape(str(k.get("trend_sub", "oldingi oygа nisbatan")))}</span></div>'
            elif t == 0:
                tr = f'<div class="tr fl">• 0% <span>· {html.escape(str(k.get("trend_sub", "o\'zgarish yo\'q")))}</span></div>'
        q.append(
            '<div class="m-stat">'
            f'<div class="ic" style="background:{tile};border-color:{border}">{k["ikon"]}</div>'
            "<div style=\"min-width:0\">"
            f'<div class="lab">{html.escape(str(k["lab"]))}</div>'
            f'<div class="val">{html.escape(str(k["val"]))}{unit}</div>'
            + tr + "</div></div>"
        )
    st.markdown('<div class="m-stats">' + "".join(q) + "</div>", unsafe_allow_html=True)


def card_open(title, sub="", o_ng_html="", pad=False):
    s = f'<div class="ss">{html.escape(str(sub))}</div>' if sub else ""
    return (
        f'<div class="m-card"><div class="cap"><div><div class="tt">{html.escape(str(title))}</div>{s}</div>'
        f'<div style="display:flex;align-items:center;gap:9px">{o_ng_html}</div></div>'
        + ('<div class="body">' if pad else "")
    )


def card_close(pad=False):
    return ("</div>" if pad else "") + "</div>"


def list_card(title, sub, ustunlar, qatorlar, maxh=440, o_ng_html=""):
    head = "".join(f"<th>{html.escape(str(u))}</th>" for u in ustunlar)
    body = "".join(f"<tr>{r}</tr>" for r in qatorlar)
    st.markdown(
        f'<div class="m-card"><div class="cap"><div><div class="tt">{html.escape(str(title))}</div>'
        f'<div class="ss">{html.escape(str(sub))}</div></div>{o_ng_html}</div>'
        f'<div class="m-scroll" style="max-height:{int(maxh)}px">'
        f'<table class="m-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></div>',
        unsafe_allow_html=True,
    )


def bo_sh(title, ikon="📭", matn="Ma'lumot yo'q"):
    st.markdown(
        f'<div class="m-card"><div class="m-empty"><div class="e">{ikon}</div>'
        f'<div style="font-weight:700;color:var(--txt);margin-bottom:3px">{html.escape(title)}</div>{html.escape(matn)}</div></div>',
        unsafe_allow_html=True,
    )


def faollik_royxati(yozuvlar):
    """Metis 'Recent Activity' uslubi."""
    q = ['<div class="m-card"><div class="cap"><div><div class="tt">🕐 So\'nggi faollik</div>'
         '<div class="ss">oxirgi to\'lovlar</div></div></div>']
    for p in yozuvlar:
        izoh = str(p.get("izoh") or "")
        oy_m = str(p.get("oy") or "")
        ts = str(p.get("ts") or "")
        sub = oy_m + " · " + ts + ((" · " + izoh) if izoh else "")
        q.append(
            '<div class="m-act"><div class="aic">💳</div>'
            '<div class="mi"><b>' + html.escape(str(p.get("ism", ""))) + "</b>"
            "<span>" + html.escape(sub) + "</span></div>"
            '<div class="mv">+' + som(p.get("summa")) + "</div></div>"
        )
    q.append("</div>")
    st.markdown("".join(q), unsafe_allow_html=True)


def yuqori_panel(bell=0):
    """Metis header: logo | qidiruv | sana + qo'ng'iroq + avatar."""
    cfg = oqi()["config"] or {}
    org = str(cfg.get("orgName") or "Maktab")
    bell_html = f'<div class="m-bell">🔔<b class="n">{int(bell)}</b></div>' if bell else '<div class="m-bell">🔔</div>'
    rol_txt = "Asosiy admin" if ss.get("rol") == "admin" else "Kuzatuvchi"
    st.markdown(
        '<div class="m-head">'
        '<div class="h-logo"><div class="h-burger">☰</div>'
        '<div class="h-tile">🏫</div><div class="h-name"><b>' + html.escape(org)
        + "</b><span>ADMIN PANEL</span></div></div>"
        '<div class="m-search"><span class="mag">🔍</span> Qidiruv… '
        '<span class="kbd">Ctrl + K</span></div>'
        '<div class="h-right">'
        f'<div class="m-chip">📅 {datetime.now().strftime("%d.%m.%Y")}</div>'
        + bell_html +
        '<div class="m-user">' + avatar_html(ss.get("login") or "Admin", True)
        + "<div><b>" + html.escape(str(ss.get("login") or "Admin"))
        + "</b><span>" + rol_txt + "</span></div></div>"
        "</div></div>",
        unsafe_allow_html=True,
    )


# ----------------- GRAFIKLAR (Metis uslubi) -----------------
_AX = dict(
    labelColor="#6B7280", gridColor="rgba(17,24,39,.07)", domainColor="transparent",
    labelFontSize=11, labelFontWeight=600,
)


def _legend():
    return alt.Legend(orient="bottom", labelColor="#6B7280", labelFontSize=12,
                      labelFontWeight=600, padding=8, symbolType="circle",
                      symbolSize=120, title=None)


def graf_chiziqli(df, ustunlar, ranglar, balandlik=310):
    """Metis 'Revenue Overview': chiziqli + nuqtalar."""
    uzoq = df.melt("Oy", var_name="Turi", value_name="Qiymat")
    chart = (
        alt.Chart(uzoq)
        .mark_line(strokeWidth=2.6, point={"size": 60, "filled": True, "color": "#fff", "strokeWidth": 2})
        .encode(
            x=alt.X("Oy:N", sort=OYLAR, axis=alt.Axis(**_AX, labelAngle=0)),
            y=alt.Y("Qiymat:Q", axis=alt.Axis(**_AX, format=",.2s")),
            color=alt.Color("Turi:N", scale=alt.Scale(domain=ustunlar, range=ranglar[: len(ustunlar)]),
                            legend=_legend()),
            tooltip=[
                alt.Tooltip("Oy:N", title="Oy"),
                alt.Tooltip("Turi:N", title="Turi"),
                alt.Tooltip("Qiymat:Q", title="Summa", format=",.0f"),
            ],
        )
        .properties(height=balandlik)
        .configure_view(stroke=None)
        .configure(background="#00000000")
    )
    return chart


def graf_maydon(df, ustunlar, ranglar, balandlik=300):
    """Gradient maydon + chiziq (Yillik hisobot)."""
    uzoq = df.melt("Oy", var_name="Turi", value_name="Qiymat")
    layers = []
    base = alt.Chart(uzoq).encode(
        x=alt.X("Oy:N", sort=OYLAR, axis=alt.Axis(**_AX, labelAngle=0)),
        y=alt.Y("Qiymat:Q", axis=alt.Axis(**_AX, format=",.2s")),
        color=alt.Color("Turi:N", scale=alt.Scale(domain=ustunlar, range=ranglar[: len(ustunlar)]),
                        legend=_legend()),
        tooltip=[
            alt.Tooltip("Oy:N", title="Oy"),
            alt.Tooltip("Turi:N", title="Turi"),
            alt.Tooltip("Qiymat:Q", title="Summa", format=",.0f"),
        ],
    )
    layers.append(base.mark_area(opacity=0.14, line={"strokeWidth": 2.4},
                                 point={"size": 45, "filled": True, "color": "#fff"}))
    chart = (
        alt.layer(*layers)
        .properties(height=balandlik)
        .configure_view(stroke=None)
        .configure(background="#00000000")
    )
    return chart


def graf_ustun(df, x_ustun, y_ustun, rang, balandlik=300, format=",.0f"):
    """Metis 'User Growth': ko'k ustunlar, yumaloq burchak."""
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=34,
                  color=rang, opacity=0.92)
        .encode(
            x=alt.X(f"{x_ustun}:N", sort="-y", axis=alt.Axis(**_AX, labelAngle=0)),
            y=alt.Y(f"{y_ustun}:Q", axis=alt.Axis(**_AX, format=format)),
            tooltip=[
                alt.Tooltip(f"{x_ustun}:N", title=x_ustun),
                alt.Tooltip(f"{y_ustun}:Q", title=y_ustun, format=",.0f"),
            ],
        )
        .properties(height=balandlik)
        .configure_view(stroke=None)
        .configure(background="#00000000")
    )
    return chart


def graf_oylar(malumot, ranglar, balandlik=330):
    """Guruhlangan ustunlar: malumot = {oy: {"Tushum": x, ...}}."""
    qatorlar = []
    for oy, qiym in malumot.items():
        for turi, v in qiym.items():
            qatorlar.append({"Oy": oy, "Turi": turi, "Qiymat": num(v)})
    df = pd.DataFrame(qatorlar)
    if df.empty:
        return None
    turlar = list(pd.unique(df["Turi"]))
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=15, opacity=0.92)
        .encode(
            x=alt.X("Oy:N", sort=OYLAR, axis=alt.Axis(**_AX, labelAngle=0)),
            y=alt.Y("Qiymat:Q", axis=alt.Axis(**_AX, format=",.2s")),
            color=alt.Color("Turi:N", scale=alt.Scale(domain=turlar, range=ranglar[: len(turlar)]),
                            legend=_legend()),
            tooltip=[
                alt.Tooltip("Oy:N", title="Oy"),
                alt.Tooltip("Turi:N", title="Turi"),
                alt.Tooltip("Qiymat:Q", title="Summa", format=",.0f"),
            ],
        )
        .properties(height=balandlik)
        .configure_view(stroke=None)
        .configure(background="#00000000")
    )
    return chart


def chart_korsat(chart, balandlik=None):
    if balandlik:
        chart = chart.properties(height=balandlik)
    try:
        st.altair_chart(chart, **KENG)
    except Exception:
        st.altair_chart(chart, use_container_width=True)


# ============================================================
#                    KIRISH OYNASI
# ============================================================
def kirish_oynasi():
    cfg = oqi()["config"] or {}
    org = str(cfg.get("orgName") or "Maktab")
    css_yoz(True)
    st.markdown(
        '<div class="m-login-top"><div class="lg-t">🏫</div>'
        f"<h1>{html.escape(org)}</h1>"
        '<div class="sub">Buxgalteriya tizimi — kiritish uchun login va parol yozing</div></div>',
        unsafe_allow_html=True,
    )

    hozir = time.time()
    if ss.get("blok", 0) > hozir:
        qoldi = int(ss["blok"] - hozir)
        st.markdown(f'<div class="m-lock">🔒 Juda ko\'p xato urinish! {qoldi} soniyadan keyin qayta urinib ko\'ring</div>',
                    unsafe_allow_html=True)
        st.stop()

    lc1, lc2, lc3 = st.columns([1.2, 0.85, 1.2])
    with lc2:
        with st.form("kirish_form", clear_on_submit=False):
            login = st.text_input("👤 Login", placeholder="loginingizni yozing")
            parol = st.text_input("🔐 Parol", type="password", placeholder="parolingiz")
            st.write("")
            ok = st.form_submit_button("Kirish →", use_container_width=True)

    if ok:
        f_login = str(login).strip()
        f_parol = str(parol)
        sa_user = str(cfg.get("user") or "admin").strip()
        sa_hash = cfg.get("pass")
        sa_user2 = str(cfg.get("user2") or "").strip()
        sa_hash2 = cfg.get("pass2")

        togrimi = False
        rol = "admin"
        if f_login == sa_user and f_login:
            togrimi = check_pw(f_parol, sa_hash) if sa_hash else (f_parol == "123")
        elif f_login == sa_user2 and f_login:
            togrimi = check_pw(f_parol, sa_hash2) if sa_hash2 else False
            rol = "view"

        if togrimi:
            ss["kirgan"] = True
            ss["login"] = f_login
            ss["rol"] = rol
            ss["urinish"] = 0
            st.rerun()
        else:
            ss["urinish"] = int(ss.get("urinish", 0)) + 1
            if ss["urinish"] >= 5:
                ss["blok"] = time.time() + 60
                ss["urinish"] = 0
                st.rerun()
            qoldi = 5 - ss["urinish"]
            st.markdown(f'<div class="m-err">❌ Login yoki parol xato! Yana {qoldi} marta urinish qoldi</div>',
                        unsafe_allow_html=True)

    with lc2:
        with st.expander("🔑 Parolni tiklash"):
            tel = st.text_input("📱 Telefon raqamingiz", placeholder="+998 9X XXX XX XX")
            if st.button("Kod yuborish", key="tk_yubor", use_container_width=True):
                sa_tel = faqat_raqam(cfg.get("phone"))
                if not sa_tel:
                    st.error("Tizimda telefon raqam sozlanmagan. Admin bilan bog'laning.")
                elif faqat_raqam(tel) == sa_tel:
                    kod = f"{random.randint(0, 999999):06d}"
                    ss["tk"] = kod
                    ss["tv"] = time.time()
                    yubildi, xabar = tg_yubor(
                        f"🔐 <b>{html.escape(org)}</b> tizimi uchun tiklash kodi: <b>{kod}</b>"
                    )
                    if yubildi:
                        st.success("Kod Telegramga yuborildi ✅")
                    else:
                        st.info(f"Kod: {kod}")
                else:
                    st.error("Raqam mos kelmadi ❌")

            kod_in = st.text_input("6 xonali kod", placeholder="______")
            yangi = st.text_input("Yangi parol", type="password", key="yangi_parol")
            if st.button("Parolni saqlash", key="tk_saq", use_container_width=True):
                if not ss.get("tk") or time.time() - ss.get("tv", 0) > 300:
                    st.error("Kod muddati tugadi. Qaytadan kod oling.")
                elif str(kod_in).strip() != ss.get("tk"):
                    st.error("Kod xato ❌")
                elif len(str(yangi)) < 4:
                    st.error("Parol kamida 4 belgidan iborat bo'lsin")
                else:
                    if saqla("config/pass", hash_pw(yangi)):
                        ss["tk"] = ""
                        st.success("Parol o'zgartirildi ✅ Endi kiring")
                    else:
                        st.error("Saqlashda xatolik")


# ============================================================
#                     1. DASHBOARD
# ============================================================
def sahifa_dashboard():
    cfg = oqi()["config"] or {}
    org = str(cfg.get("orgName") or "Maktab")
    U = umumiy()
    qtor = qarzdorlar_royxati()

    o_ng = '<div class="m-seg"><span class="on">📊 Umumiy holat</span></div>'
    sahifa_sarlavha("Dashboard", org + " — barcha hisoblar bir joyda", o_ng)

    tr = trend_foiz(U["s_yig"])
    stat_cards([
        dict(ikon="👥", lab="O'quvchilar (baza)", val=fmt(len(baza_list())), unit="ta"),
        dict(ikon="💰", lab="Umumiy tushum", val=fmt(U["tushum"]), unit="so'm", trend=tr),
        dict(ikon="✅", lab="Yig'ildi", val=fmt(U["yig"]), unit="so'm",
             trend=None, tile_bg="#F0FDF4", tile_border="#BBF7D0"),
        dict(ikon="🔴", lab="Umumiy qarz", val=fmt(U["qarz"]), unit="so'm",
             tile_bg="#FEF2F2", tile_border="#FECACA"),
        dict(ikon="🎯", lab="Undirish darajasi", val=f'{U["und"]}%',
             tile_bg="#FFFBEB", tile_border="#FDE68A"),
    ])

    # --- Tushum ko'rinishi (Revenue Overview) + Undirish donut ---
    gl, gd = st.columns([2.05, 1], gap="medium")
    with gl:
        st.markdown(card_open("📈 Tushum ko'rinishi", "Yig'ildi · Qarz",
                              '<div class="m-seg"><span class="on">Davr</span></div>'), unsafe_allow_html=True)
        c_z, c3, c6, c12 = st.columns([2.6, 0.75, 0.75, 0.75])
        with c3:
            d3 = st.button("3 oy", key="db_3", use_container_width=True)
        with c6:
            d6 = st.button("6 oy", key="db_6", use_container_width=True)
        with c12:
            d12 = st.button("12 oy", key="db_12", type="primary", use_container_width=True)
        if d3:
            ss["db_davr"] = 3
        if d6:
            ss["db_davr"] = 6
        if d12:
            ss["db_davr"] = 12
        n_oy = int(ss.get("db_davr", 12))
        df_ch = pd.DataFrame({
            "Oy": OYLAR[-n_oy:],
            "Yig'ildi": U["s_yig"][-n_oy:],
            "Qarz": U["s_qarz"][-n_oy:],
        })
        st.markdown('<div style="margin-top:6px"></div>', unsafe_allow_html=True)
        chart_korsat(graf_chiziqli(df_ch, ["Yig'ildi", "Qarz"], [C["blue"], C["bad"]], 315))
        st.markdown("</div>", unsafe_allow_html=True)

    with gd:
        st.markdown(
            card_open("🎯 Undirish", som(U["yig"]) + " / " + som(U["tushum"]))
            + donut_html(U["und"], f'{U["und"]}%', "UNDIRILDI")
            + '<div style="padding:10px 20px 16px">'
            + f'<div class="dn-row"><span>📘 Reja (jami narx)</span><b>{som(U["tushum"])}</b></div>'
            + f'<div class="dn-row"><span>✅ Yig\'ildi</span><b style="color:{C["ok"]}">{som(U["yig"])}</b></div>'
            + f'<div class="dn-row"><span>🔴 Qarz</span><b style="color:{C["bad"]}">{som(U["qarz"])}</b></div>'
            + "</div></div>",
            unsafe_allow_html=True,
        )

    # --- So'nggi faollik + TOP qarzdorlar (Recent Orders uslubida) ---
    fl, tq = st.columns(2, gap="medium")
    with fl:
        pays = oxirgi_tovlovlar(6)
        if pays:
            faollik_royxati(pays)
        else:
            bo_sh("So'nggi faollik", "🕐", "Hozircha to'lovlar yo'q")
    with tq:
        sinflar = baza_sinf()
        jami_qarz = {}
        for q in qtor:
            jami_qarz.setdefault(q["ism"], {"qarz": 0, "oylar": []})
            jami_qarz[q["ism"]]["qarz"] += q["qarz"]
            jami_qarz[q["ism"]]["oylar"].append(q["oy"])
        top_qarz = sorted(jami_qarz.items(), key=lambda kv: -kv[1]["qarz"])[:6]
        if top_qarz:
            qatorlar_q = []
            for ism, mal in top_qarz:
                qatorlar_q.append(
                    '<td><div class="cellp">' + avatar_html(ism) + "<span><b>" + html.escape(ism)
                    + '</b><span class="sub">' + html.escape(sinflar.get(ism, "") or "—")
                    + "</span></span></div></td>"
                    + "<td>" + f'<span class="m-bdg mut">{html.escape(", ".join(mal["oylar"]))}</span>' + "</td>"
                    + f'<td><span class="num" style="color:{C["bad"]}">{som(mal["qarz"])}</span></td>'
                    + "<td>" + f'<span class="m-bdg bad">QARZ</span>' + "</td>"
                )
            list_card("⚠️ TOP qarzdorlar", "Eng katta qarzlar",
                      ["O'quvchi", "Oylar", "Qarz", "Holat"], qatorlar_q, 400)
        else:
            bo_sh("TOP qarzdorlar", "🎉", "Qarzdorlar yo'q — hammasi to'lagan!")

    # --- Sinflar kesimida (Metis User Growth) ---
    st.markdown(card_open("🏫 Sinflar kesimida", "o'quvchilar reja tushumi"), unsafe_allow_html=True)
    sinf_jam = {}
    for oy in U["oylar"]:
        for r in yaroqli(oy_rows(oy)):
            ism = str(r.get("name")).strip()
            kl = sinflar.get(ism, "") or "—"
            sinf_jam.setdefault(kl, 0)
            sinf_jam[kl] += sof(r)
    if sinf_jam and set(sinf_jam) != {"—"}:
        df_s = pd.DataFrame([{"Sinf": k, "Tushum": v} for k, v in sinf_jam.items()])
        chart_korsat(graf_ustun(df_s, "Sinf", "Tushum", C["blue"], 300, ",.2s"))
    else:
        st.info("Sinflar ko'rsatilishi uchun 👨‍🎓 O'quvchilar sahifasida sinf kiritilishi kerak")
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
#                     2. HISOB
# ============================================================
def sahifa_hisob():
    cfg = oqi()["config"] or {}
    D = oqi()["data"]

    bor = [oy for oy in OYLAR if (D.get(oy) or [])]
    default_oy = bor[-1] if bor else "Yanvar"
    idx = OYLAR.index(default_oy)
    oy = st.selectbox("Oy tanlang", OYLAR, index=idx, key="his_oy",
                      label_visibility="collapsed")
    sahifa_sarlavha("Hisob — " + oy, "Oylik hisob-kitob jadvali")

    s = oy_stat(oy)
    stat_cards([
        dict(ikon="👥", lab="O'quvchilar", val=fmt(s["n"]), unit="ta"),
        dict(ikon="📘", lab="Reja", val=fmt(s["reja"]), unit="so'm"),
        dict(ikon="✅", lab="Yig'ildi", val=fmt(s["yig"]), unit="so'm",
             tile_bg="#F0FDF4", tile_border="#BBF7D0"),
        dict(ikon="🔴", lab="Qarz", val=fmt(s["qarz"]), unit="so'm",
             tile_bg="#FEF2F2", tile_border="#FECACA"),
    ])

    if ss.get("rol") == "view":
        st.info("👁 Kuzatuvchi rejimi — tahrirlash faqat asosiy admin uchun")

    st.markdown(card_open("📋 " + oy + " oyi jadvali",
                          "Narx, to'langan va davomatni tahrirlash"), unsafe_allow_html=True)
    rows = list(oy_rows(oy))
    df = pd.DataFrame([
        {"Ism": str(r.get("name") or ""), "Narx": num(r.get("price")),
         "To'langan": num(r.get("food")), "Keladi": bool(r.get("att"))}
        for r in rows
    ], columns=["Ism", "Narx", "To'langan", "Keladi"])

    ustunlar = {
        "Ism": st.column_config.TextColumn("Ism", width="medium"),
        "Narx": st.column_config.NumberColumn("Narx", format="%,d", step=10000),
        "To'langan": st.column_config.NumberColumn("To'langan", format="%,d", step=10000),
        "Keladi": st.column_config.CheckboxColumn("Keladi", default=True),
    }
    tahrir = keng(
        st.data_editor,
        data=df,
        column_config=ustunlar,
        num_rows="dynamic",
        height=max(220, min(540, (len(df) + 2) * 35 + 10)),
        key=f"hisob_ed_{oy}",
        hide_index=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        saqla_bos = st.button("💾 Saqlash", type="primary", use_container_width=True,
                              disabled=(ss.get("rol") == "view"))
    with c2:
        bazadan = st.button("♻️ Bazadan yuklash", use_container_width=True,
                            disabled=(ss.get("rol") == "view"))
    st.markdown("</div>", unsafe_allow_html=True)

    if saqla_bos:
        yangi = []
        for r in tahrir.to_dict("records"):
            nm = str(r.get("Ism") or "").strip()
            p = num(r.get("Narx"))
            t = num(r.get("To'langan"))
            if not nm and p == 0 and t == 0:
                continue
            yangi.append({
                "att": bool(r.get("Keladi")), "food": int(t), "name": nm,
                "price": int(p), "st": holat_key(p, t),
            })
        if saqla(f"data/{oy}", yangi):
            st.success(f"✅ {oy} oyi saqlandi ({len(yangi)} ta yozuv)")
            time.sleep(0.6)
            st.rerun()
        else:
            st.error("❌ Saqlashda xatolik — internetni tekshirib ko'ring")

    if bazadan:
        bazalar = baza_list()
        mavjud = {str(r.get("name") or "").strip() for r in rows}
        qoshildi = 0
        for _, rec in bazalar:
            nm = str(rec.get("name") or "").strip()
            if nm and nm not in mavjud:
                rows.append({
                    "att": True, "food": 0, "name": nm,
                    "price": int(num(rec.get("price")) or num(cfg.get("defaultPrice"))),
                    "st": "st-debt",
                })
                qoshildi += 1
        if qoshildi:
            if saqla(f"data/{oy}", rows):
                st.success(f"✅ Bazadan {qoshildi} ta o'quvchi qo'shildi")
                time.sleep(0.6)
                st.rerun()
            else:
                st.error("❌ Saqlashda xatolik")
        else:
            st.info("Barcha bazadagi o'quvchilar bu oyda allaqachon bor")

    # Holat taqsimoti
    hol_soni = {"st-paid": 0, "st-part": 0, "st-debt": 0}
    for r in yaroqli(rows):
        hol_soni[holat_r(r)] += 1
    h1, h2 = st.columns([2, 1])
    with h1:
        st.markdown(
            card_open("📐 Oy holati", "Undirish: " + str(s["und"]) + "%", pad=True)
            + '<div style="display:flex;gap:9px;flex-wrap:wrap;margin-bottom:14px">'
            + f'<span class="m-bdg ok">TO\'LANDI — {hol_soni["st-paid"]}</span>'
            + f'<span class="m-bdg warn">QISMAN — {hol_soni["st-part"]}</span>'
            + f'<span class="m-bdg bad">QARZ — {hol_soni["st-debt"]}</span>'
            + "</div>"
            + pb_html(s["und"])
            + "</div></div>",
            unsafe_allow_html=True,
        )
    with h2:
        df_h = pd.DataFrame({
            "Holat": ["To'landi", "Qisman", "Qarz"],
            "Soni": [hol_soni["st-paid"], hol_soni["st-part"], hol_soni["st-debt"]],
        })
        df_h = df_h[df_h["Soni"] > 0]
        if not df_h.empty:
            chart_korsat(graf_ustun(df_h, "Holat", "Soni", C["blue"], 230, ",d"))

    # Oy o'chirish
    with st.expander("🗑 Bu oy ma'lumotlarini o'chirish"):
        st.warning(f"{oy} oyi butunlay o'chiriladi — bu amalni qaytarib bo'lmaydi!")
        tasdiq = st.checkbox("Ha, o'chirishni tasdiqlayman")
        if tasdiq and st.button("🗑 O'chirish", type="primary",
                                disabled=(ss.get("rol") == "view")):
            if ochir(f"data/{oy}"):
                st.success("Oy o'chirildi")
                time.sleep(0.6)
                st.rerun()
            else:
                st.error("O'chirishda xatolik")


# ============================================================
#                     3. TO'LOVLAR
# ============================================================
def sahifa_tolovlar():
    D = oqi()["data"]
    bor = [oy for oy in OYLAR if (D.get(oy) or [])]
    default_oy = bor[-1] if bor else "Yanvar"
    oy = st.selectbox("Oy tanlang", OYLAR, index=OYLAR.index(default_oy),
                      key="tol_oy", label_visibility="collapsed")
    sahifa_sarlavha("To'lovlar — " + oy, "To'lovlarni qabul qilish va nazorat")

    s = oy_stat(oy)
    stat_cards([
        dict(ikon="📘", lab="Reja", val=fmt(s["reja"]), unit="so'm"),
        dict(ikon="✅", lab="Yig'ildi", val=fmt(s["yig"]), unit="so'm",
             tile_bg="#F0FDF4", tile_border="#BBF7D0"),
        dict(ikon="🎯", lab="Undirish", val=f'{s["und"]}%',
             tile_bg="#FFFBEB", tile_border="#FDE68A"),
        dict(ikon="👥", lab="O'quvchilar", val=fmt(s["n"]), unit="ta"),
    ])

    # ⚡ Tezkor to'lov
    st.markdown(card_open("⚡ Bu oyga to'lov qo'shish", "Summa o'quvchining to'langaniga qo'shiladi"), unsafe_allow_html=True)
    if ss.get("rol") == "view":
        st.info("👁 Kuzatuvchi rejimi")
    ismlar = [str(r.get("name")).strip() for r in yaroqli(oy_rows(oy))]
    with st.form("tol_form", clear_on_submit=True):
        cc1, cc2, cc3, cc4 = st.columns([2, 1.2, 1.4, 1])
        with cc1:
            ism = st.selectbox("O'quvchi", ismlar) if ismlar else st.selectbox("O'quvchi", ["—"])
        with cc2:
            summa = st.number_input("Summa", min_value=0, step=50000, format="%d")
        with cc3:
            izoh = st.text_input("Izoh (ixtiyoriy)")
        with cc4:
            st.write("")
            ok = st.form_submit_button("💸 Qabul qilish", use_container_width=True)
    if ok:
        if not ismlar:
            st.error("Bu oyda o'quvchi yo'q — Hisob sahifasidan qo'shing")
        else:
            nat, xabar = tolov_qosh(oy, ism, summa, izoh)
            if nat:
                st.success("✅ " + xabar)
                time.sleep(0.6)
                st.rerun()
            else:
                st.error("❌ " + xabar)
    st.markdown("</div>", unsafe_allow_html=True)

    # 📋 Jadval
    rows = yaroqli(oy_rows(oy))
    rows.sort(key=lambda r: -qarz_r(r))
    qatorlar = []
    for r in rows:
        p, t, q = sof(r), tolangan(r), qarz_r(r)
        und = foiz(t, p)
        qatorlar.append(
            '<td><div class="cellp">' + avatar_html(r["name"]) + "<span><b>"
            + html.escape(str(r["name"]).strip()) + "</b></span></div></td>"
            + f'<td><span class="num">{fmt(p)}</span></td>'
            + f'<td><span class="num" style="color:{C["ok"]}">{fmt(t)}</span></td>'
            + f'<td><span class="num" style="color:{C["bad"]}">{fmt(q)}</span></td>'
            + f'<td style="min-width:150px">{pb_html(und)}</td>'
            + "<td>" + holat_pill(r) + "</td>"
        )
    if qatorlar:
        list_card("📋 " + oy + " oyi to'lovlari",
                  str(len(rows)) + " o'quvchi · undirish " + str(s["und"]) + "%",
                  ["O'quvchi", "Reja", "To'langan", "Qarz", "Bajarilishi", "Holat"], qatorlar, 460)
    else:
        bo_sh(oy + " oyi to'lovlari", "📋", "Bu oyda hozircha yozuv yo'q")

    # 🕐 To'lovlar tarixi
    pays = list(oqi()["payments"] or [])
    if pays:
        pays.sort(key=lambda x: str(x.get("ts")), reverse=True)
        df_p = pd.DataFrame([
            {"Vaqt": str(p.get("ts", "")), "Oy": str(p.get("oy", "")),
             "O'quvchi": str(p.get("ism", "")), "Summa": num(p.get("summa")),
             "Izoh": str(p.get("izoh", ""))}
            for p in pays
        ])
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
        with st.expander(f"🕐 To'lovlar tarixi — jami {len(df_p)} ta to'lov", expanded=False):
            keng(st.dataframe, data=df_p, height=min(320, (len(df_p) + 1) * 35 + 10), hide_index=True)
            excel_tugma(df_p, "tolovlar_tarixi", "exc_tol_pays")


# ============================================================
#                     4. DAVOMAT
# ============================================================
def sahifa_davomat():
    D = oqi()["data"]
    bor = [oy for oy in OYLAR if (D.get(oy) or [])]
    default_oy = bor[-1] if bor else "Yanvar"
    oy = st.selectbox("Oy tanlang", OYLAR, index=OYLAR.index(default_oy),
                      key="dav_oy", label_visibility="collapsed")
    sahifa_sarlavha("Davomat — " + oy, "Oylik kelish-kelmasligi")

    s = oy_stat(oy)
    cd, cj = st.columns([1, 2.2], gap="medium")
    with cd:
        st.markdown(
            card_open("📋 Davomat", oy)
            + donut_html(s["dav"], f'{s["dav"]}%', "KELDI")
            + '<div style="padding:10px 20px 16px">'
            + f'<div class="dn-row"><span>✅ Keldi</span><b style="color:{C["ok"]}">{s["keldi"]} ta</b></div>'
            + f'<div class="dn-row"><span>❌ Kelmadi</span><b style="color:{C["bad"]}">{s["kelmadi"]} ta</b></div>'
            + "</div></div>",
            unsafe_allow_html=True,
        )
    with cj:
        st.markdown(card_open("✏️ Tahrirlash", "Kelmagan o'quvchi belgisini olib tashlang"), unsafe_allow_html=True)
        rows = list(oy_rows(oy))
        df = pd.DataFrame([
            {"Ism": str(r.get("name") or ""), "Keladi": bool(r.get("att"))}
            for r in rows
        ], columns=["Ism", "Keladi"])
        ustunlar = {
            "Ism": st.column_config.TextColumn("O'quvchi", width="medium"),
            "Keladi": st.column_config.CheckboxColumn("Keladi", default=True),
        }
        tahrir = keng(
            st.data_editor,
            data=df,
            column_config=ustunlar,
            num_rows="dynamic",
            height=max(220, min(520, (len(df) + 2) * 35 + 10)),
            key=f"dav_ed_{oy}",
            hide_index=True,
        )
        if ss.get("rol") == "view":
            st.info("👁 Kuzatuvchi rejimi — faqat asosiy admin tahrirlashi mumkin")
        if st.button("💾 Davomatni saqlash", type="primary",
                     disabled=(ss.get("rol") == "view")):
            yangi = []
            for r in tahrir.to_dict("records"):
                nm = str(r.get("Ism") or "").strip()
                if not nm:
                    continue
                yangi.append({"att": bool(r.get("Keladi")), "food": 0, "name": nm,
                              "price": 0, "st": "st-debt"})
            eski = {str(r.get("name") or "").strip(): r for r in rows}
            for r in yangi:
                e = eski.get(r["name"])
                if e:
                    r["food"] = num(e.get("food"))
                    r["price"] = num(e.get("price"))
                    r["st"] = holat_key(r["price"], r["food"])
            if saqla(f"data/{oy}", yangi):
                st.success(f"✅ {oy} davomati saqlandi ({len(yangi)} ta)")
                time.sleep(0.6)
                st.rerun()
            else:
                st.error("❌ Saqlashda xatolik")
        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
#                     5. QARZDORLAR
# ============================================================
def sahifa_qarzdorlar():
    sahifa_sarlavha("Qarzdorlar", "Barcha oylar bo'yicha qarz nazorati")

    qtor_all = qarzdorlar_royxati()
    fil_c1, fil_c2 = st.columns([1, 1.6])
    with fil_c1:
        fil_oy = st.selectbox("Oy bo'yicha filtr", ["Barchasi"] + OYLAR, key="qar_oy_f")
    with fil_c2:
        qidir = st.text_input("🔍 O'quvchi bo'yicha qidiruv", placeholder="ism yozing…")

    qtor = qtor_all
    if fil_oy != "Barchasi":
        qtor = [q for q in qtor if q["oy"] == fil_oy]
    if qidir.strip():
        qtor = [q for q in qtor if qidir.strip().lower() in q["ism"].lower()]

    jami_qarz = sum(q["qarz"] for q in qtor)
    eng_katta = qtor[0] if qtor else None
    stat_cards([
        dict(ikon="🔴", lab="Qarzdor yozuvlar", val=fmt(len(qtor)), unit="ta",
             tile_bg="#FEF2F2", tile_border="#FECACA"),
        dict(ikon="💸", lab="Umumiy qarz", val=fmt(jami_qarz), unit="so'm",
             tile_bg="#FFFBEB", tile_border="#FDE68A"),
        dict(ikon="👑", lab="Eng katta qarzdor",
             val=(eng_katta["ism"][:16] if eng_katta else "—"),
             unit=(som(eng_katta["qarz"]) if eng_katta else "")),
    ])

    # Telegram eslatma
    st.markdown(card_open("📣 Telegram eslatma yuborish", "Tanlangan qarzdorga xabar yuboriladi"), unsafe_allow_html=True)
    if qtor:
        tanl = st.selectbox("Qarzdor", [q["ism"] + "  (" + q["oy"] + ")" for q in qtor],
                            key="qar_tg_sel")
        if st.button("📨 Eslatma yuborish", disabled=(ss.get("rol") == "view")):
            tanlangan = None
            for q in qtor:
                if tanl.startswith(q["ism"]):
                    tanlangan = q
                    break
            if tanlangan:
                ok, xabar = tg_yubor(
                    f"🔔 <b>Hurmatli {html.escape(tanlangan['ism'])}!</b>\n\n"
                    "🏫 " + html.escape(str(oqi()["config"].get("orgName") or "Maktab")) + " — "
                    f"<b>{tanlangan['oy']}</b> oyi uchun "
                    f"<b>{som(tanlangan['qarz'])}</b> qarzingiz mavjud.\n"
                    "Iltimos, to'lovni amalga oshiring. Rahmat! 🙏"
                )
                if ok:
                    st.success("✅ Eslatma Telegramga yuborildi")
                else:
                    st.warning("⚠️ " + xabar)
    else:
        st.info("Qarzdorlar topilmadi 🎉")
    st.markdown("</div>", unsafe_allow_html=True)

    # Jadval
    qatorlar = []
    for q in qtor:
        und = foiz(q["tolangan"], q["reja"])
        qatorlar.append(
            '<td><div class="cellp">' + avatar_html(q["ism"]) + "<span><b>" + html.escape(q["ism"])
            + '</b><span class="sub">' + html.escape(str(q["sinf"])) + "</span></span></div></td>"
            + "<td>" + f'<span class="m-bdg info">{html.escape(q["oy"])}</span>' + "</td>"
            + f'<td><span class="num">{fmt(q["reja"])}</span></td>'
            + f'<td><span class="num" style="color:{C["ok"]}">{fmt(q["tolangan"])}</span></td>'
            + f'<td><span class="num" style="color:{C["bad"]}">{fmt(q["qarz"])}</span></td>'
            + f'<td style="min-width:150px">{pb_html(und)}</td>'
        )
    if qatorlar:
        list_card("🔴 Qarzdorlar ro'yxati", str(len(qtor)) + " ta yozuv",
                  ["O'quvchi", "Oy", "Reja", "To'langan", "Qarz", "Bajarilishi"], qatorlar, 460)
    else:
        bo_sh("Qarzdorlar ro'yxati", "🎉", "Barcha to'lovlar o'z vaqtida!")

    if qtor:
        df_q = pd.DataFrame([{
            "O'quvchi": q["ism"], "Sinf": q["sinf"], "Oy": q["oy"],
            "Reja": q["reja"], "To'langan": q["tolangan"], "Qarz": q["qarz"],
        } for q in qtor])
        excel_tugma(df_q, "qarzdorlar", "exc_qar")


# ============================================================
#                     6. TAQQOSLASH
# ============================================================
def sahifa_taqqoslash():
    D = oqi()["data"]
    sahifa_sarlavha("Taqqoslash", "Ikki oyni solishtirish")

    bor = [oy for oy in OYLAR if (D.get(oy) or [])]
    dA = bor[-1] if bor else "Yanvar"
    dB = bor[-2] if len(bor) > 1 else (bor[0] if bor else "Fevral")
    c1, c2 = st.columns(2)
    with c1:
        oyA = st.selectbox("1-oy", OYLAR, index=OYLAR.index(dA), key="cmp_a")
    with c2:
        oyB = st.selectbox("2-oy", OYLAR, index=OYLAR.index(dB), key="cmp_b")

    A = oy_stat(oyA)
    B = oy_stat(oyB)

    metrikalar = [
        ("👥 O'quvchilar", A["n"], B["n"], "ta"),
        ("📘 Reja (tushum)", A["reja"], B["reja"], "som"),
        ("✅ Yig'ildi", A["yig"], B["yig"], "som"),
        ("🔴 Qarz", A["qarz"], B["qarz"], "som"),
        ("🎯 Undirish", A["und"], B["und"], "%"),
        ("📋 Davomat", A["dav"], B["dav"], "%"),
    ]

    qatorlar_html = []
    for nom, va, vb, tur in metrikalar:
        if tur == "som":
            ka, kb = som(va), som(vb)
            delta = (round((va - vb) / vb * 100) if vb > 0 else None)
        elif tur == "%":
            ka, kb = str(va) + "%", str(vb) + "%"
            delta = (va - vb) if (va or vb) else None
        else:
            ka, kb = fmt(va), fmt(vb)
            delta = (va - vb) if (va or vb) else None
        delt_html = ""
        if delta is not None and delta != 0:
            sinf = "up" if delta > 0 else "dn"
            strelka = "↑" if delta > 0 else "↓"
            delt_html = f'<div class="d {sinf}">{strelka} {abs(delta)}%</div>'
        elif delta == 0:
            delt_html = '<div class="d up">= 0</div>'
        qatorlar_html.append(
            '<div class="m-cmp">'
            f'<div class="side"><span>{html.escape(oyA)}</span><b>{ka}</b>{delt_html}</div>'
            f'<div class="nm">{nom}</div>'
            f'<div class="side r"><span>{html.escape(oyB)}</span><b>{kb}</b></div>'
            "</div>"
        )
    st.markdown("".join(qatorlar_html), unsafe_allow_html=True)

    st.markdown(card_open("📊 Ko'rsatkichlar kesimida", oyA + " · " + oyB), unsafe_allow_html=True)
    mal = {
        oyA: {"Tushum": A["reja"], "Yigildi": A["yig"], "Qarz": A["qarz"]},
        oyB: {"Tushum": B["reja"], "Yigildi": B["yig"], "Qarz": B["qarz"]},
    }
    ch = graf_oylar(mal, [C["blue"], C["ok"], C["bad"]], 300)
    if ch is not None:
        chart_korsat(ch)
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
#                     7. YILLIK HISOBOT
# ============================================================
def sahifa_yillik():
    sahifa_sarlavha("Yillik hisobot", "12 oy kesimida to'liq tahlil")

    cfg = oqi()["config"]
    plan = num(cfg.get("monthlyPlan"))
    expenses = oqi()["expenses"] or {}

    rows_data = []
    for oy in OYLAR:
        s = oy_stat(oy)
        xarajat = sum(num(x.get("summa")) for x in (expenses.get(oy) or []))
        rows_data.append({
            "Oy": oy, "Soni": s["n"], "Reja": s["reja"], "Yigildi": s["yig"],
            "Qarz": s["qarz"], "Xarajat": xarajat, "Sof": s["yig"] - xarajat,
            "Undirish": s["und"], "Davomat": s["dav"],
        })
    df = pd.DataFrame(rows_data)

    bor_qatorlar = [r for r in rows_data if r["Soni"] > 0]
    jami = {}
    eng_yaxshi = None
    if bor_qatorlar:
        eng_yaxshi = max(bor_qatorlar, key=lambda r: r["Sof"])
        jami = {k: sum(r[k] for r in rows_data)
                for k in ["Soni", "Reja", "Yigildi", "Qarz", "Xarajat", "Sof"]}
        stat_cards([
            dict(ikon="📅", lab="Faol oylar", val=fmt(len(bor_qatorlar)), unit="/12"),
            dict(ikon="✅", lab="Jami yigildi", val=fmt(jami["Yigildi"]), unit="so'm",
                 tile_bg="#F0FDF4", tile_border="#BBF7D0"),
            dict(ikon="💰", lab="Jami sof foyda", val=fmt(jami["Sof"]), unit="so'm"),
            dict(ikon="🥇", lab="Eng yaxshi oy",
                 val=eng_yaxshi["Oy"], unit=som(eng_yaxshi["Sof"]),
                 tile_bg="#FFFBEB", tile_border="#FDE68A"),
        ])

    st.markdown(card_open("📉 Yigildi va Qarz dinamikasi", "12 oy kesimida"), unsafe_allow_html=True)
    ch = graf_maydon(df[["Oy", "Yigildi", "Qarz"]], ["Yigildi", "Qarz"],
                     [C["ok"], C["bad"]], 300)
    chart_korsat(ch)
    st.markdown("</div>", unsafe_allow_html=True)

    qatorlar = []
    for r in rows_data:
        rang_sof = C["ok"] if r["Sof"] >= 0 else C["bad"]
        if r["Soni"] > 0:
            oy_pill = f'<span class="m-bdg info">{r["Oy"]}</span>'
        else:
            oy_pill = f'<span class="m-bdg mut">{r["Oy"]}</span>'
        qatorlar.append(
            "<td>" + oy_pill + "</td>"
            + f'<td><span class="num">{r["Soni"]}</span></td>'
            + f'<td><span class="num">{fmt(r["Reja"])}</span></td>'
            + f'<td><span class="num" style="color:{C["ok"]}">{fmt(r["Yigildi"])}</span></td>'
            + f'<td><span class="num" style="color:{C["bad"]}">{fmt(r["Qarz"])}</span></td>'
            + f'<td><span class="num">{fmt(r["Xarajat"])}</span></td>'
            + f'<td><span class="num" style="color:{rang_sof}">{fmt(r["Sof"])}</span></td>'
            + f'<td style="min-width:140px">{pb_html(r["Undirish"])}</td>'
            + f'<td><span class="num">{r["Davomat"]}%</span></td>'
        )
    if bor_qatorlar:
        list_card("📋 Yillik jadval", "Jami yigildi: " + som(jami["Yigildi"]),
                  ["Oy", "O'quvchilar", "Reja", "Yigildi", "Qarz", "Xarajat",
                   "Sof foyda", "Undirish", "Davomat"], qatorlar, 520)

        df_exp = df.copy()
        df_exp.loc[len(df_exp)] = {
            "Oy": "JAMI", "Soni": jami["Soni"], "Reja": jami["Reja"],
            "Yigildi": jami["Yigildi"], "Qarz": jami["Qarz"], "Xarajat": jami["Xarajat"],
            "Sof": jami["Sof"], "Undirish": foiz(jami["Yigildi"], jami["Reja"]),
            "Davomat": 0,
        }
        df_exp = df_exp.rename(columns={
            "Soni": "O'quvchilar", "Yigildi": "Yig'ildi", "Sof": "Sof foyda",
            "Undirish": "Undirish %", "Davomat": "Davomat %",
        })
        excel_tugma(df_exp, "yillik_hisobot", "exc_yil")
    else:
        bo_sh("Yillik jadval", "📈", "Hozircha hech qaysi oy to'ldirilmagan — Hisob sahifasidan boshlang")

    if plan > 0 and jami:
        st.markdown(
            card_open("🎯 Oylik reja", "Reja: " + som(plan) + " · Yigildi: " + som(jami["Yigildi"]), pad=True)
            + pb_html(foiz(jami["Yigildi"], plan))
            + "</div></div>",
            unsafe_allow_html=True,
        )


# ============================================================
#                     8. XARAJATLAR
# ============================================================
def sahifa_xarajatlar():
    sahifa_sarlavha("Xarajatlar", "Oylik chiqimlarni nazorat qilish")

    expenses = dict(oqi()["expenses"] or {})
    bor = [oy for oy in OYLAR if (expenses.get(oy) or []) or (oy_rows(oy))]
    default_oy = bor[-1] if bor else "Yanvar"
    oy = st.selectbox("Oy tanlang", OYLAR, index=OYLAR.index(default_oy),
                      key="xar_oy", label_visibility="collapsed")
    sahifa_sarlavha("Xarajatlar — " + oy, "Oylik chiqimlarni nazorat qilish")

    if ss.get("rol") == "view":
        st.info("👁 Kuzatuvchi rejimi — faqat asosiy admin qo'sha oladi")

    st.markdown(card_open("➕ Yangi xarajat qo'shish", "Sana, izoh va summani yozing"), unsafe_allow_html=True)
    with st.form("xar_form", clear_on_submit=True):
        cc1, cc2, cc3, cc4 = st.columns([1, 2, 1, 0.9])
        with cc1:
            sana = st.date_input("Sana", value=date.today())
        with cc2:
            izoh = st.text_input("Izoh", placeholder="masalan: pol markeri, gaz, oshxona…")
        with cc3:
            summa = st.number_input("Summa", min_value=0, step=10000, format="%d")
        with cc4:
            st.write("")
            ok = st.form_submit_button("➕ Qo'shish", use_container_width=True)
    if ok:
        if summa <= 0:
            st.error("Summa 0 dan katta bo'lishi kerak")
        elif not str(izoh).strip():
            st.error("Izoh yozing — keyin nima uchun chiqim bo'lgani esda qoladi")
        else:
            lst = list(expenses.get(oy) or [])
            lst.append({
                "sana": sana.strftime("%d.%m.%Y"),
                "izoh": str(izoh).strip(),
                "summa": int(summa),
            })
            expenses[oy] = lst
            if saqla("expenses", expenses):
                st.success("✅ Xarajat qo'shildi")
                time.sleep(0.6)
                st.rerun()
            else:
                st.error("❌ Saqlashda xatolik")
    st.markdown("</div>", unsafe_allow_html=True)

    s = oy_stat(oy)
    oy_xarajat = sum(num(x.get("summa")) for x in (expenses.get(oy) or []))
    sof_foyda = s["yig"] - oy_xarajat
    stat_cards([
        dict(ikon="✅", lab="Yigildi", val=fmt(s["yig"]), unit="so'm",
             tile_bg="#F0FDF4", tile_border="#BBF7D0"),
        dict(ikon="🛒", lab="Xarajat", val=fmt(oy_xarajat), unit="so'm",
             tile_bg="#FEF2F2", tile_border="#FECACA"),
        dict(ikon="💰", lab="Sof foyda", val=fmt(sof_foyda), unit="so'm",
             tile_bg=("#F0FDF4" if sof_foyda >= 0 else "#FEF2F2"),
             tile_border=("#BBF7D0" if sof_foyda >= 0 else "#FECACA")),
        dict(ikon="🧾", lab="Xarajat yozuvlari", val=fmt(len(expenses.get(oy) or [])),
             unit="ta"),
    ])

    st.markdown(card_open("📊 Oylar kesimida xarajat", "Barcha oylar"), unsafe_allow_html=True)
    mal = {}
    for o in OYLAR:
        jam = sum(num(x.get("summa")) for x in (expenses.get(o) or []))
        if jam > 0:
            mal[o] = {"Xarajat": jam}
    if mal:
        ch = graf_oylar(mal, [C["bad"]], 280)
        if ch is not None:
            chart_korsat(ch)
    else:
        st.info("Hozircha xarajatlar kiritilmagan")
    st.markdown("</div>", unsafe_allow_html=True)

    lst = list(expenses.get(oy) or [])
    if lst:
        qatorlar = []
        for i, x in enumerate(lst):
            qatorlar.append(
                "<td>" + f'<span class="m-bdg mut">{html.escape(x.get("sana", ""))}</span>' + "</td>"
                + "<td><b>" + html.escape(str(x.get("izoh", ""))) + "</b></td>"
                + "<td><span class='num' style='color:" + C["bad"] + "'>" + som(x.get("summa")) + "</span></td>"
                + "<td><span class='num' style='color:" + C["sub"] + "'>#" + str(i + 1) + "</span></td>"
            )
        list_card("🛒 " + oy + " oyi xarajatlari", "Jami: " + som(oy_xarajat),
                  ["Sana", "Izoh", "Summa", "№"], qatorlar, 380)

        c1, c2 = st.columns([2.4, 1])
        with c1:
            tanl = st.selectbox("O'chirish uchun yozuv tanlang",
                                [f"#{i + 1} — {x.get('izoh', '')} ({som(x.get('summa'))})"
                                 for i, x in enumerate(lst)], key="xar_del_sel")
        with c2:
            st.write("")
            if st.button("🗑 O'chirish", disabled=(ss.get("rol") == "view")):
                try:
                    idx = int(tanl.split("—")[0].strip().replace("#", "")) - 1
                    lst.pop(idx)
                    expenses[oy] = lst
                    if saqla("expenses", expenses):
                        st.success("O'chirildi")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Xatolik")
                except Exception:
                    st.error("Xatolik")

        df_x = pd.DataFrame([{"Sana": x.get("sana", ""), "Izoh": x.get("izoh", ""),
                              "Summa": num(x.get("summa"))} for x in lst])
        excel_tugma(df_x, "xarajatlar_" + oy.lower(), "exc_xar")
    else:
        bo_sh(oy + " oyi xarajatlari", "🛒", "Bu oy uchun hozircha xarajat yo'q")


# ============================================================
#                     9. O'QUVCHILAR (BAZA)
# ============================================================
def sahifa_oquvchilar():
    cfg = oqi()["config"] or {}
    sahifa_sarlavha("O'quvchilar", "O'quvchilar bazasini boshqarish")

    bazalar = baza_list()
    sinflar_mavjud = sorted({str(rec.get("cls") or "").strip() for _, rec in bazalar
                             if str(rec.get("cls") or "").strip()})
    jami_narx = sum(num(rec.get("price")) for _, rec in bazalar)

    stat_cards([
        dict(ikon="👥", lab="Jami o'quvchilar", val=fmt(len(bazalar)), unit="ta"),
        dict(ikon="🏫", lab="Sinflar", val=fmt(len(sinflar_mavjud)), unit="ta"),
        dict(ikon="📘", lab="Oylik jami narx", val=fmt(jami_narx), unit="so'm"),
        dict(ikon="💳", lab="Standart narx", val=fmt(cfg.get("defaultPrice")), unit="so'm"),
    ])

    if ss.get("rol") == "view":
        st.info("👁 Kuzatuvchi rejimi — tahrirlash faqat asosiy admin uchun")

    t1, t2, t3, t4 = st.tabs(["➕ Yangi o'quvchi", "✏️ Tahrirlash", "🗑 O'chirish", "📥 Oyga yuklash"])

    with t1:
        with st.form("oq_add", clear_on_submit=True):
            a1, a2 = st.columns(2)
            with a1:
                ism = st.text_input("Ism familiya", placeholder="Ali Valiyev")
                tel = st.text_input("Telefon", placeholder="+998 9X XXX XX XX")
            with a2:
                sinf = st.text_input("Sinf", placeholder="5-a")
                narx = st.number_input("Oylik narx", min_value=0,
                                       step=10000, format="%d",
                                       value=num(cfg.get("defaultPrice")))
            ok = st.form_submit_button("➕ Qo'shish", use_container_width=True)
        if ok:
            if not str(ism).strip():
                st.error("Ism yozing")
            else:
                lst = students_nusxa()
                lst.append({
                    "cls": str(sinf).strip(), "name": str(ism).strip(),
                    "phone": str(tel).strip(), "price": int(narx),
                })
                if saqla("students", lst):
                    st.success("✅ O'quvchi qo'shildi")
                    time.sleep(0.6)
                    st.rerun()
                else:
                    st.error("❌ Saqlashda xatolik")

    with t2:
        if bazalar:
            with st.form("oq_edit", clear_on_submit=False):
                tanl = st.selectbox("O'quvchi tanlang",
                                    [str(i) + " — " + str(rec.get("name") or "")
                                     for i, rec in bazalar])
                tanlangan = None
                for i, rec in bazalar:
                    if tanl.startswith(str(i) + " "):
                        tanlangan = (i, rec)
                        break
                e1, e2 = st.columns(2)
                with e1:
                    ism_e = st.text_input("Ism familiya",
                                          value=str(tanlangan[1].get("name") or "") if tanlangan else "")
                    tel_e = st.text_input("Telefon",
                                          value=str(tanlangan[1].get("phone") or "") if tanlangan else "")
                with e2:
                    sinf_e = st.text_input("Sinf",
                                           value=str(tanlangan[1].get("cls") or "") if tanlangan else "")
                    narx_e = st.number_input("Oylik narx", min_value=0, step=10000,
                                             format="%d",
                                             value=num(tanlangan[1].get("price")) if tanlangan else 0)
                ok = st.form_submit_button("💾 Saqlash", use_container_width=True)
            if ok and tanlangan:
                lst = students_nusxa()
                idx_t = tanlangan[0]
                if 0 <= idx_t < len(lst):
                    lst[idx_t] = {
                        "cls": str(sinf_e).strip(), "name": str(ism_e).strip(),
                        "phone": str(tel_e).strip(), "price": int(narx_e),
                    }
                if saqla("students", lst):
                    st.success("✅ Yangilandi")
                    time.sleep(0.6)
                    st.rerun()
                else:
                    st.error("❌ Saqlashda xatolik")
        else:
            st.info("Bazada hozircha o'quvchi yo'q")

    with t3:
        if bazalar:
            tanl_d = st.selectbox("O'chirish uchun tanlang",
                                  [str(i) + " — " + str(rec.get("name") or "")
                                   for i, rec in bazalar], key="oq_del_sel")
            if st.button("🗑 O'chirish", type="primary",
                         disabled=(ss.get("rol") == "view")):
                try:
                    idx = int(tanl_d.split(" ")[0])
                    lst = students_nusxa()
                    if 0 <= idx < len(lst):
                        lst.pop(idx)
                    if saqla("students", lst):
                        st.success("O'chirildi")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Xatolik")
                except Exception:
                    st.error("Xatolik")
        else:
            st.info("Bazada hozircha o'quvchi yo'q")

    with t4:
        bor_oylar = [oy for oy in OYLAR if (oqi()["data"].get(oy) or [])]
        default_oy = bor_oylar[-1] if bor_oylar else "Yanvar"
        oy_t = st.selectbox("Oy", OYLAR, index=OYLAR.index(default_oy), key="oq_fill_oy")
        st.caption("Bazadagi barcha o'quvchilar tanlangan oyga qo'shiladi "
                   "(bu oyda allaqachon borlari qo'shilmaydi).")
        if st.button("📥 Oyga yuklash", type="primary",
                     disabled=(ss.get("rol") == "view")):
            rows = list(oy_rows(oy_t))
            mavjud = {str(r.get("name") or "").strip() for r in rows}
            qoshildi = 0
            for _, rec in bazalar:
                nm = str(rec.get("name") or "").strip()
                if nm and nm not in mavjud:
                    rows.append({
                        "att": True, "food": 0, "name": nm,
                        "price": int(num(rec.get("price")) or num(cfg.get("defaultPrice"))),
                        "st": "st-debt",
                    })
                    qoshildi += 1
            if qoshildi:
                if saqla("data/" + oy_t, rows):
                    st.success(f"✅ {qoshildi} ta o'quvchi {oy_t} oyiga qo'shildi")
                    time.sleep(0.6)
                    st.rerun()
                else:
                    st.error("❌ Saqlashda xatolik")
            else:
                st.info("Barcha o'quvchilar bu oyda allaqachon bor")

    # 🔍 Qidiruv + kartalar
    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
    qidir = st.text_input("🔍 Qidiruv", placeholder="ism yoki sinf bo'yicha…", key="oq_qidir")
    korinadigan = bazalar
    if qidir.strip():
        s_q = qidir.strip().lower()
        korinadigan = [(i, rec) for i, rec in bazalar
                       if s_q in str(rec.get("name") or "").lower()
                       or s_q in str(rec.get("cls") or "").lower()]

    if korinadigan:
        kartalar = []
        for i, rec in korinadigan:
            nm = str(rec.get("name") or "—").strip() or "—"
            kl = str(rec.get("cls") or "").strip()
            tel_r = str(rec.get("phone") or "").strip()
            kartalar.append(
                '<div class="m-stcard">'
                + "<div class='top'>" + avatar_html(nm)
                + (f'<span class="m-bdg info">{html.escape(kl)}</span>' if kl
                   else '<span class="m-bdg mut">—</span>') + "</div>"
                + f'<div class="nm">{html.escape(nm)}</div>'
                + '<div class="rw"><span>📞 ' + (html.escape(tel_r) if tel_r else "—")
                + f"</span><b>{som(rec.get('price'))}</b></div>"
                + "</div>"
            )
        st.markdown('<div class="m-grid">' + "".join(kartalar) + "</div>",
                    unsafe_allow_html=True)
    else:
        st.info("O'quvchi topilmadi — yuqoridagi ➕ formasidan qo'shing")

    if bazalar:
        df_b = pd.DataFrame([{
            "Ism": str(rec.get("name") or ""), "Sinf": str(rec.get("cls") or ""),
            "Telefon": str(rec.get("phone") or ""), "Oylik narx": num(rec.get("price")),
        } for _, rec in bazalar])
        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
        excel_tugma(df_b, "oquvchilar_bazasi", "exc_baza")


# ============================================================
#                     10. SOZLAMALAR (Metis uslubi)
# ============================================================
SET_BLOKLAR = ["🏫 Umumiy", "🔐 Xavfsizlik", "📣 Telegram", "💾 Zaxira"]


def _set_row(title, desc, widget_html=""):
    return f'<div class="m-setrow"><div class="l"><b>{title}</b><span>{desc}</span></div><div class="r">{widget_html}</div></div>'


def sahifa_sozlamalar():
    cfg = dict(oqi()["config"] or {})
    sahifa_sarlavha("Sozlamalar", "Tizim sozlamalari va xavfsizlik",
                    '<div class="m-seg"><span class="on">v4.0 · Metis</span></div>')

    nav, panel = st.columns([0.95, 3.1], gap="medium")
    with nav:
        st.markdown('<div class="m-set-nav">', unsafe_allow_html=True)
        tanlov = st.radio("bo'lim", SET_BLOKLAR, label_visibility="collapsed", key="set_nav")
        st.markdown("</div>", unsafe_allow_html=True)

    with panel:
        # ----- Umumiy -----
        if tanlov == "🏫 Umumiy":
            st.markdown(card_open("🏫 Umumiy sozlamalar",
                                  "Tashkilot nomi va hisob-kitob standartlari"), unsafe_allow_html=True)
            with st.form("soz_umumiy"):
                org = st.text_input("Tashkilot nomi", value=str(cfg.get("orgName") or "Maktab"))
                plan = st.number_input("Oylik reja (maqsad summa)", min_value=0,
                                       step=100000, format="%d", value=num(cfg.get("monthlyPlan")))
                std_narx = st.number_input("Standart oylik narx", min_value=0,
                                           step=10000, format="%d", value=num(cfg.get("defaultPrice")))
                tel = st.text_input("Admin telefoni (parol tiklash uchun)",
                                    value=str(cfg.get("phone") or ""))
                ok = st.form_submit_button("💾 Saqlash", use_container_width=True)
            if ok:
                cfg.update({"orgName": str(org).strip() or "Maktab",
                            "monthlyPlan": int(plan), "defaultPrice": int(std_narx),
                            "phone": str(tel).strip()})
                if saqla("config", cfg):
                    st.success("✅ Saqlandi")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Saqlashda xatolik")
            st.markdown("</div>", unsafe_allow_html=True)

        # ----- Xavfsizlik -----
        elif tanlov == "🔐 Xavfsizlik":
            st.markdown(card_open("👑 Asosiy admin", "Login va parolni boshqarish"), unsafe_allow_html=True)
            with st.form("soz_admin"):
                user_y = st.text_input("Login", value=str(cfg.get("user") or "admin"))
                eski = st.text_input("Eski parol (tasdiqlash uchun)", type="password")
                yangi = st.text_input("Yangi parol (bo'sh — o'zgarmasdi)", type="password")
                ok = st.form_submit_button("💾 Saqlash", use_container_width=True)
            if ok:
                eski_togri = check_pw(eski, cfg.get("pass")) if cfg.get("pass") else (eski == "123")
                if not eski_togri:
                    st.error("❌ Eski parol mos kelmadi")
                elif yangi and len(str(yangi)) < 4:
                    st.error("Yangi parol kamida 4 belgi bo'lsin")
                else:
                    cfg.update({"user": str(user_y).strip() or "admin"})
                    if yangi:
                        cfg["pass"] = hash_pw(yangi)
                    if saqla("config", cfg):
                        st.success("✅ Saqlandi (keyingi kirishda yangi parol amal qiladi)")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Saqlashda xatolik")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(card_open("👤 Ikkinchi foydalanuvchi",
                                  "Masalan: o'qituvchi — faqat ko'rish rejimi"), unsafe_allow_html=True)
            with st.form("soz_user2"):
                u2 = st.text_input("Login 2", value=str(cfg.get("user2") or ""))
                p2 = st.text_input("Parol 2 (bo'sh — o'zgarmasdi)", type="password")
                r2 = st.selectbox("Ruxsat", ["view", "admin"],
                                  index=0 if str(cfg.get("role2") or "view") == "view" else 1)
                ok = st.form_submit_button("💾 Saqlash", use_container_width=True)
            if ok:
                cfg.update({"user2": str(u2).strip(), "role2": str(r2)})
                if str(p2).strip():
                    cfg["pass2"] = hash_pw(p2)
                if not str(u2).strip():
                    cfg["pass2"] = ""
                if saqla("config", cfg):
                    st.success("✅ Saqlandi")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Saqlashda xatolik")
            st.markdown("</div>", unsafe_allow_html=True)

        # ----- Telegram -----
        elif tanlov == "📣 Telegram":
            st.markdown(card_open("📣 Telegram bot", "Eslatma va parol tiklash kodlari shu bot orqali yuboriladi"), unsafe_allow_html=True)
            st.caption("Bot yaratish: @BotFather → /newbot → tokenni shu yerga qo'ying. "
                       "chat_id ni olish uchun @userinfobot ga xabar yozing.")
            with st.form("soz_tg"):
                token = st.text_input("Bot Token", value=str(cfg.get("tgToken") or ""),
                                      placeholder="123456:ABC-DEF…")
                chat = st.text_input("Chat ID", value=str(cfg.get("chatId") or ""),
                                     placeholder="123456789")
                ok = st.form_submit_button("💾 Saqlash", use_container_width=True)
            if ok:
                cfg.update({"tgToken": str(token).strip(), "chatId": str(chat).strip()})
                if saqla("config", cfg):
                    st.success("✅ Saqlandi")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Saqlashda xatolik")
            if st.button("📨 Test xabar yuborish"):
                ok2, xabar = tg_yubor("✅ <b>Maktab Buxgalteriya</b> — test xabari. Bot ishlayapti!")
                if ok2:
                    st.success("✅ Xabar yuborildi — Telegramni tekshiring")
                else:
                    st.warning("⚠️ " + xabar)
            st.markdown("</div>", unsafe_allow_html=True)

        # ----- Zaxira -----
        else:
            st.markdown(card_open("💾 To'liq zaxira nusxa",
                                  "Barcha ma'lumotlar bir JSON faylga yuklab olinadi"), unsafe_allow_html=True)
            st.caption("Barcha ma'lumotlar (hisoblar, o'quvchilar, xarajatlar, to'lovlar tarixi) "
                       "bir JSON faylga yuklab olinadi. Uni xavfsiz joyda saqlang.")
            zaxira = {
                "config": oqi()["config"],
                "data": oqi()["data"],
                "students": oqi()["students"],
                "expenses": oqi()["expenses"],
                "payments": oqi()["payments"],
                "zaxira_vaqti": datetime.now().strftime("%d.%m.%Y %H:%M"),
            }
            json_bayt = json.dumps(zaxira, ensure_ascii=False, indent=2).encode()
            keng(
                st.download_button,
                label="⬇️ Zaxirani (JSON) yuklab olish",
                data=json_bayt,
                file_name="zaxira_" + datetime.now().strftime("%Y%m%d_%H%M") + ".json",
                mime="application/json",
                key="zax_json",
            )
            st.markdown("</div>", unsafe_allow_html=True)

            jami_yozuvlar = sum(len(v or []) for v in oqi()["data"].values())
            st.markdown(
                card_open("📊 Baza holati", zaxira["zaxira_vaqti"])
                + '<div style="padding:8px 20px 16px">'
                + f'<div class="dn-row"><span>📅 To\'ldirilgan oylar</span><b>{len([o for o in OYLAR if oqi()["data"].get(o)])} ta</b></div>'
                + f'<div class="dn-row"><span>🧾 Hisob yozuvlari</span><b>{jami_yozuvlar} ta</b></div>'
                + f'<div class="dn-row"><span>👥 Bazadagi o\'quvchilar</span><b>{len(baza_list())} ta</b></div>'
                + f'<div class="dn-row"><span>🕐 To\'lov tarixi</span><b>{len(oqi()["payments"] or [])} ta</b></div>'
                + "</div></div>",
                unsafe_allow_html=True,
            )


# ============================================================
#                    ASOSIY OQIM
# ============================================================
SAHIFALAR = {
    "🏠 Dashboard": sahifa_dashboard,
    "💰 Hisob": sahifa_hisob,
    "🧾 To'lovlar": sahifa_tolovlar,
    "📋 Davomat": sahifa_davomat,
    "🔴 Qarzdorlar": sahifa_qarzdorlar,
    "⚖️ Taqqoslash": sahifa_taqqoslash,
    "📈 Yillik hisobot": sahifa_yillik,
    "🛒 Xarajatlar": sahifa_xarajatlar,
    "👨‍🎓 O'quvchilar": sahifa_oquvchilar,
    "⚙️ Sozlamalar": sahifa_sozlamalar,
}

if not ss.get("kirgan"):
    kirish_oynasi()
    st.stop()

css_yoz()

with st.sidebar:
    st.markdown('<div class="m-cap">Menyu</div>', unsafe_allow_html=True)
    tanlov = st.radio("menyu", list(SAHIFALAR.keys()), label_visibility="collapsed", key="sahifa")

    _qtor_sb = qarzdorlar_royxati()
    if _qtor_sb:
        st.markdown(f'<div class="m-alert">🔔 {len(_qtor_sb)} ta qarzdorlik eslatmasi</div>',
                    unsafe_allow_html=True)

    _cfg_sb = oqi()["config"] or {}
    _rol = "Asosiy admin" if ss.get("rol") == "admin" else "Kuzatuvchi"
    st.markdown(
        '<div class="m-ucard">' + avatar_html(ss.get("login") or "Admin", True)
        + "<div><b>" + html.escape(str(ss.get("login") or "Admin")) + "</b>"
        + "<span>" + _rol + "</span></div></div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="m-refresh">', unsafe_allow_html=True)
    rb1, rb2 = st.columns(2)
    with rb1:
        yangilash_bos = st.button("Yangilash", use_container_width=True)
    with rb2:
        chiqish_bos = st.button("Chiqish", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if yangilash_bos:
    _baza_oqi.clear()
    st.rerun()
if chiqish_bos:
    ss["kirgan"] = False
    st.rerun()

# Metis header (fixed)
yuqori_panel(bell=len(_qtor_sb))

SAHIFALAR[tanlov]()

# Footer (Metis uslubida)
_cfg_f = oqi()["config"] or {}
st.markdown(
    '<div class="m-foot"><span>© 2026 '
    + html.escape(str(_cfg_f.get("orgName") or "Maktab Buxgalteriya"))
    + " · Buxgalteriya tizimi</span><span>Streamlit · Firebase · Metis uslubi</span></div>",
    unsafe_allow_html=True,
)

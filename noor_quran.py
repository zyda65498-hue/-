# نور القرآن الكريم
# التشغيل المحلي:
#   pip install -r requirements.txt
#   python noor_quran.py
#
# النشر على Render:
#   استخدم render.yaml الموجود مع المشروع.
#   Render ينشئ SECRET_KEY ويخصص قرصاً دائماً لقاعدة البيانات.

import os
import sqlite3
from functools import wraps
from flask import Flask, Response, g, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "local-development-only-change-before-publishing"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
)

DB = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "noor.db")
)
os.makedirs(os.path.dirname(os.path.abspath(DB)), exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT UNIQUE NOT NULL,
 password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS favorites(
 user_id INTEGER NOT NULL, surah INTEGER NOT NULL, ayah INTEGER NOT NULL,
 surah_name TEXT, text TEXT,
 PRIMARY KEY(user_id,surah,ayah)
);
CREATE TABLE IF NOT EXISTS fav_surahs(
 user_id INTEGER NOT NULL, surah INTEGER NOT NULL,
 PRIMARY KEY(user_id,surah)
);
CREATE TABLE IF NOT EXISTS progress(
 user_id INTEGER PRIMARY KEY, surah INTEGER NOT NULL, ayah INTEGER NOT NULL,
 surah_name TEXT
);
CREATE TABLE IF NOT EXISTS history(
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
 surah INTEGER NOT NULL, ayah INTEGER NOT NULL, surah_name TEXT,
 at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

HTML = r"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#123d2b">
<meta name="description" content="نور القرآن الكريم - قراءة القرآن والاستماع والتفسير والأذكار">
<title>نور القرآن الكريم</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Amiri&family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{--g:#123d2b;--g2:#1d5c42;--gold:#d4af37;--iv:#f8f5ea;--ink:#1d2a22;--card:#fffdf6;--line:rgba(212,175,55,.4)}
body.night{--iv:#0d1812;--ink:#eee9d8;--card:#152419;--line:rgba(212,175,55,.28)}
*{box-sizing:border-box}body{margin:0;background:var(--iv);color:var(--ink);font-family:Tajawal,sans-serif;font-size:17px;padding-bottom:112px;background-image:radial-gradient(circle at 1px 1px,rgba(212,175,55,.13) 1px,transparent 0);background-size:24px 24px}
a{color:inherit;text-decoration:none}button,input,select{font:inherit}button{cursor:pointer}
header{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:12px;padding:10px 16px;background:var(--g);color:white;border-bottom:3px solid var(--gold)}
.logo{font-weight:700;font-size:1.15rem;color:var(--gold);white-space:nowrap}
nav{display:flex;gap:3px;overflow-x:auto;flex:1}nav a{padding:7px 10px;border-radius:20px;white-space:nowrap}nav a.on,nav a:hover{background:var(--gold);color:var(--g)}
#night{background:none;border:1px solid var(--gold);color:white;border-radius:50%;width:38px;height:38px}
main{max-width:1000px;margin:auto;padding:20px 15px}h1,h2{color:var(--g2)}body.night h1,body.night h2{color:var(--gold)}
.hero{text-align:center;padding:38px 16px;border-radius:20px;color:white;border:2px solid var(--gold);background:repeating-conic-gradient(from 45deg,rgba(212,175,55,.07) 0 25%,transparent 0 50%) 0 0/46px 46px,linear-gradient(160deg,var(--g),#0b2a1d)}
.hero h1{color:var(--gold);font-size:2.1rem;margin:0 0 10px}.verse,.quran-text{font-family:'Amiri Quran','Amiri',serif}.verse{font-size:1.65rem;line-height:2.2}
.btn{display:inline-block;padding:9px 19px;border-radius:25px;border:2px solid var(--gold);background:var(--gold);color:var(--g);font-weight:700;margin:4px}.btn.alt{background:transparent;color:var(--gold)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:13px;margin-top:16px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:15px}.card h3{margin-top:0;color:var(--g2)}body.night .card h3{color:var(--gold)}
.sgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(225px,1fr));gap:9px}.srow{display:flex;align-items:center;gap:10px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px}
.srow .no{width:35px;height:35px;display:grid;place-items:center;border:2px solid var(--gold);transform:rotate(45deg);border-radius:6px;flex:none}.srow .no span{transform:rotate(-45deg)}
.srow .nm{flex:1;cursor:pointer;font-family:'Amiri Quran',serif;font-size:1.1rem}.srow small{display:block;opacity:.7;font-family:Tajawal}.ib{background:none;border:0;color:var(--gold);font-size:1.2rem}
.tools,.tabs{display:flex;flex-wrap:wrap;gap:7px;align-items:center;justify-content:center;margin:10px 0}.tools button,.tabs button{border:1px solid var(--gold);background:var(--card);color:var(--ink);border-radius:20px;padding:7px 13px}.tabs button.on{background:var(--gold);color:var(--g)}
.reader{background:var(--card);border:2px solid var(--gold);border-radius:18px;padding:18px}.reader h1{text-align:center;font-family:'Amiri Quran',serif}.bism{text-align:center;font-family:'Amiri Quran',serif;font-size:1.7rem;margin:10px}
.quran-text{text-align:justify;line-height:2.6;font-size:var(--fs,30px)}.ay{cursor:pointer;border-radius:8px;padding:2px}.ay:hover{background:rgba(212,175,55,.15)}.ay.sel{background:rgba(212,175,55,.3)}.ay.mark{border-bottom:3px solid var(--gold)}.ay.fav:before{content:"♥ ";color:#c0392b;font-size:.65em}
.num{color:var(--gold);font-size:.7em;margin:0 3px}.num:before{content:"﴿"}.num:after{content:"﴾"}
#sel{position:sticky;top:60px;z-index:5;display:none;justify-content:center;gap:6px;flex-wrap:wrap;padding:8px;margin:8px 0;background:var(--g);color:white;border-radius:12px}#sel button{border:1px solid var(--gold);background:none;color:white;border-radius:16px;padding:5px 10px}
.player{position:fixed;bottom:0;inset-inline:0;z-index:30;background:var(--g);color:white;border-top:3px solid var(--gold);padding:8px 12px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}.pc{display:flex;gap:7px;align-items:center}.player button{background:var(--gold);border:0;border-radius:50%;width:37px;height:37px;color:var(--g)}.player select{max-width:180px;border-radius:8px;padding:5px}
input[type=text],input[type=password],input[type=number],select.f{padding:10px 12px;border-radius:10px;border:1px solid var(--gold);background:var(--card);color:var(--ink);width:100%;margin:5px 0}.row2{display:flex;gap:8px;flex-wrap:wrap}.row2>*{flex:1;min-width:120px}
.dhikr{display:flex;gap:12px;align-items:center;justify-content:space-between;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:13px;margin:10px 0}.dhikr p{margin:0;font-family:Amiri,serif;font-size:1.3rem;line-height:2}
.cnt{flex:none;width:65px;height:65px;border-radius:50%;border:3px solid var(--gold);background:var(--g);color:white;font-size:1.25rem}.cnt.done{background:var(--gold);color:var(--g)}
.times{display:grid;grid-template-columns:repeat(auto-fit,minmax(78px,1fr));gap:7px;text-align:center}.times div{background:rgba(212,175,55,.12);border-radius:10px;padding:8px}.times b{display:block;color:var(--gold)}
.item{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;margin:8px 0;cursor:pointer}.item .quran-text{font-size:1.35rem;line-height:2.1}.tafsir{font-family:Amiri,serif;font-size:1.25rem;line-height:2.1}
.load{text-align:center;opacity:.7}.err{color:#c0392b;text-align:center}#toast{position:fixed;top:75px;left:50%;transform:translateX(-50%);background:var(--gold);color:var(--g);padding:8px 18px;border-radius:20px;font-weight:bold;opacity:0;pointer-events:none;z-index:60}#toast.on{opacity:1}
@media(max-width:650px){header{flex-wrap:wrap}.logo{font-size:1rem}nav{order:3;flex-basis:100%}.hero h1{font-size:1.7rem}.reader{padding:12px}.player{justify-content:center}.pc{flex-wrap:wrap;justify-content:center}}
</style></head>
<body>
<header><a class="logo" href="#/home">🌙 نور القرآن الكريم</a>
<nav id="nav"><a href="#/home">الرئيسية</a><a href="#/quran">القرآن</a><a href="#/listen">الاستماع</a><a href="#/tafsir">التفسير</a><a href="#/search">البحث</a><a href="#/adhkar">الأذكار</a><a href="#/account">حسابي</a></nav>
<button id="night" title="الوضع الليلي">🌓</button></header>
<main id="app"><p class="load">جارٍ تشغيل نور القرآن الكريم…</p></main>
<div class="player"><div id="pl-label">اختر سورة للاستماع</div><div class="pc">
<button id="pl-prev" title="الآية السابقة">⏮</button><button id="pl-pp" title="تشغيل/إيقاف">▶</button><button id="pl-next" title="الآية التالية">⏭</button>
<input id="pl-vol" type="range" min="0" max="1" step=".05" value="1" style="width:75px">
<select id="pl-rec"><option value="ar.alafasy">مشاري العفاسي</option><option value="ar.abdulbasitmurattal">عبد الباسط (مرتل)</option><option value="ar.husary">محمود الحصري</option><option value="ar.minshawi">المنشاوي</option><option value="ar.shaatree">أبو بكر الشاطري</option></select>
</div></div><audio id="aud"></audio><div id="toast"></div>
<script>
const $=s=>document.querySelector(s),app=$('#app'),aud=$('#aud'),API='https://api.alquran.cloud/v1';
const ar=n=>String(n).replace(/\\d/g,d=>'٠١٢٣٤٥٦٧٨٩'[d]);
let user=null,surahs=[],cache={},pl={s:null,i:0};
const api=async(p,m='GET',b)=>{const r=await fetch('/api/'+p,{method:m,headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):undefined});return r.json()};
const qd=async p=>(await (await fetch(API+p)).json()).data;
const toast=t=>{let e=$('#toast');e.textContent=t;e.classList.add('on');setTimeout(()=>e.classList.remove('on'),2200)};
const getSurahs=async()=>surahs.length?surahs:(surahs=await qd('/surah'));
async function getSurah(n){if(!cache[n])cache[n]=await qd('/surah/'+n+'/quran-uthmani');return cache[n]}
const localProg=()=>{try{return JSON.parse(localStorage.noorProg||'null')}catch{return null}};
const getProg=async()=>user?((await api('progress')).progress||localProg()):localProg();
async function setProg(s,a,name){let p={surah:s,ayah:a,surah_name:name};localStorage.noorProg=JSON.stringify(p);if(user)await api('progress','POST',p)}
const ADH={
 morning:['أذكار الصباح',[
 ['أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ',1],
 ['اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ',1],
 ['رَضِيتُ بِاللَّهِ رَبًّا، وَبِالْإِسْلَامِ دِينًا، وَبِمُحَمَّدٍ ﷺ نَبِيًّا',3],
 ['بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ',3],
 ['سُبْحَانَ اللَّهِ وَبِحَمْدِهِ',100]]],
 evening:['أذكار المساء',[
 ['أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ',1],
 ['اللَّهُمَّ بِكَ أَمْسَيْنَا، وَبِكَ أَصْبَحْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ الْمَصِيرُ',1],
 ['أَعُوذُ بِكَلِمَاتِ اللَّهِ التَّامَّاتِ مِنْ شَرِّ مَا خَلَقَ',3],
 ['بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ',3],
 ['سُبْحَانَ اللَّهِ وَبِحَمْدِهِ',100]]],
 sleep:['أذكار النوم',[['بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا',1],['اللَّهُمَّ قِنِي عَذَابَكَ يَوْمَ تَبْعَثُ عِبَادَكَ',3],['سُبْحَانَ اللَّهِ',33],['الْحَمْدُ لِلَّهِ',33],['اللَّهُ أَكْبَرُ',34]]],
 dua:['أدعية',[['رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ',1],['رَبِّ اشْرَحْ لِي صَدْرِي وَيَسِّرْ لِي أَمْرِي',1],['رَبَّنَا ظَلَمْنَا أَنْفُسَنَا وَإِنْ لَمْ تَغْفِرْ لَنَا وَتَرْحَمْنَا لَنَكُونَنَّ مِنَ الْخَاسِرِينَ',1],['رَبِّ زِدْنِي عِلْمًا',1],['اللَّهُمَّ إِنِّي أَسْأَلُكَ عِلْمًا نَافِعًا، وَرِزْقًا طَيِّبًا، وَعَمَلًا مُتَقَبَّلًا',1]]]
};
async function route(){let parts=location.hash.split('/'),pg=parts[1]||'home',a=parts[2],b=parts[3];document.querySelectorAll('#nav a').forEach(x=>x.classList.toggle('on',x.getAttribute('href')==='#/'+pg));app.innerHTML='<p class="load">جارٍ التحميل…</p>';try{await({home:vHome,quran:vQuran,listen:vListen,tafsir:vTafsir,search:vSearch,adhkar:vAdhkar,account:vAccount}[pg]||vHome)(a,b)}catch(e){console.error(e);app.innerHTML='<p class="err">تعذّر التحميل. تحقق من الإنترنت ثم أعد المحاولة.</p>'}}
async function vHome(){let p=await getProg(),k=new Date().getHours()<12?'morning':'evening',d=ADH[k][1][Math.floor(Date.now()/864e5)%ADH[k][1].length];app.innerHTML=`<section class="hero"><h1>نور القرآن الكريم</h1><div class="verse">ٱلَّذِينَ ءَامَنُوا۟ وَتَطْمَئِنُّ قُلُوبُهُم بِذِكْرِ ٱللَّهِ ۗ أَلَا بِذِكْرِ ٱللَّهِ تَطْمَئِنُّ ٱلْقُلُوبُ</div><small>[الرعد: ٢٨]</small><br><br><a class="btn" href="#/quran">ابدأ القراءة</a><a class="btn alt" href="#/listen">الاستماع للقرآن</a>${p?`<br><a class="btn" href="#/quran/${p.surah}/${p.ayah}">متابعة القراءة</a>`:''}</section><div class="grid"><div class="card"><h3>آخر موضع قراءة</h3>${p?`سورة ${p.surah_name} — الآية ${ar(p.ayah)}`:'لم تحفظ موضع قراءة بعد'}</div><div class="card"><h3>${ADH[k][0]}</h3><div class="tafsir">${d[0]}</div><a href="#/adhkar/${k}">المزيد ←</a></div><div class="card"><h3>مواقيت الصلاة</h3><div id="prayer" class="load">جارٍ تحميل المواقيت…</div><button class="btn alt" id="city">تغيير المدينة</button></div></div>`;$('#city').onclick=()=>{let c=prompt('اكتب اسم المدينة بالإنجليزية',localStorage.city||'Amman'),co=prompt('الدولة بالإنجليزية',localStorage.country||'Jordan');if(c&&co){localStorage.city=c;localStorage.country=co;prayer()}};prayer()}
async function prayer(){let c=localStorage.city||'Amman',co=localStorage.country||'Jordan';try{let d=await(await fetch(`https://api.aladhan.com/v1/timingsByCity?city=${encodeURIComponent(c)}&country=${encodeURIComponent(co)}&method=23`)).json(),t=d.data.timings,N={Fajr:'الفجر',Sunrise:'الشروق',Dhuhr:'الظهر',Asr:'العصر',Maghrib:'المغرب',Isha:'العشاء'};$('#prayer').className='times';$('#prayer').innerHTML=Object.keys(N).map(x=>`<div>${N[x]}<b>${t[x].slice(0,5)}</b></div>`).join('')}catch{$('#prayer').textContent='تعذّر جلب المواقيت'}}
async function vQuran(n,a){let L=await getSurahs();if(!n){let fs=user?(await api('favsurah')).items:[];app.innerHTML=`<h2>سور القرآن الكريم (١١٤)</h2><div class="sgrid">${L.map(s=>`<div class="srow"><div class="no"><span>${ar(s.number)}</span></div><div class="nm" onclick="location.hash='#/quran/${s.number}'">${s.name.replace('سُورَةُ ','')}<small>${s.revelationType==='Meccan'?'مكية':'مدنية'} · ${ar(s.numberOfAyahs)} آية</small></div><button class="ib" onclick="favSurah(${s.number},this)">${fs.includes(s.number)?'★':'☆'}</button></div>`).join('')}</div>`;return}
n=+n;if(n<1||n>114){location.hash='#/quran';return}let d=await getSurah(n),p=await getProg(),favs=user?new Set((await api('fav')).items.filter(x=>x.surah===n).map(x=>x.ayah)):new Set(),fs=+(localStorage.fs||30);
app.innerHTML=`<section class="reader" style="--fs:${fs}px"><div class="tools"><button onclick="location.hash='#/quran/${n-1}'" ${n===1?'disabled':''}>السورة السابقة</button><button onclick="location.hash='#/quran'">قائمة السور</button><button onclick="location.hash='#/quran/${n+1}'" ${n===114?'disabled':''}>السورة التالية</button><button id="fm">أ−</button><button id="fp">أ+</button><button onclick="play(${n},1)">▶ استماع للسورة</button></div><div id="sel"></div><h1>${d.name}</h1>${n!==1&&n!==9?'<div class="bism">بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ</div>':''}<div class="quran-text" id="qt">${d.ayahs.map(x=>`<span class="ay${p&&p.surah==n&&p.ayah==x.numberInSurah?' mark':''}${favs.has(x.numberInSurah)?' fav':''}" data-i="${x.numberInSurah}">${x.text} <span class="num">${ar(x.numberInSurah)}</span></span> `).join('')}</div></section>`;
const size=v=>{localStorage.fs=Math.max(20,Math.min(60,+(localStorage.fs||30)+v));$('.reader').style.setProperty('--fs',localStorage.fs+'px')};$('#fm').onclick=()=>size(-3);$('#fp').onclick=()=>size(3);
$('#qt').onclick=e=>{let el=e.target.closest('.ay');if(!el)return;let i=+el.dataset.i;document.querySelectorAll('.ay.sel').forEach(x=>x.classList.remove('sel'));el.classList.add('sel');let box=$('#sel');box.style.display='flex';box.innerHTML=`<b>الآية ${ar(i)}</b><button id="mark">🔖 علامة هنا</button><button id="fav">♥ مفضلة</button><button id="taf">تفسير</button><button id="listen">▶ استماع</button>`;$('#mark').onclick=async()=>{await setProg(n,i,d.name);document.querySelectorAll('.ay.mark').forEach(x=>x.classList.remove('mark'));el.classList.add('mark');toast('تم حفظ موضع القراءة')};$('#fav').onclick=async()=>{if(!user)return toast('سجّل الدخول لحفظ المفضلة');let r=await api('fav','POST',{surah:n,ayah:i,surah_name:d.name,text:d.ayahs[i-1].text});el.classList.toggle('fav',r.on);toast(r.on?'أضيفت للمفضلة':'أزيلت من المفضلة')};$('#taf').onclick=()=>location.hash=`#/tafsir/${n}/${i}`;$('#listen').onclick=()=>play(n,i)};if(a){let el=document.querySelector(`.ay[data-i="${a}"]`);if(el){el.classList.add('sel');el.scrollIntoView({block:'center'})}}}
async function favSurah(s,b){if(!user)return toast('سجّل الدخول لحفظ السور');let r=await api('favsurah','POST',{surah:s});b.textContent=r.on?'★':'☆'}
const audioUrl=(rec,num)=>`https://cdn.islamic.network/quran/audio/128/${rec}/${num}.mp3`;
async function play(s,i=1){let d=await getSurah(s);pl={s,i,name:d.name};loadAudio()}
function loadAudio(){let d=cache[pl.s],x=d.ayahs[pl.i-1];if(!x)return;aud.src=audioUrl($('#pl-rec').value,x.number);aud.play().catch(()=>toast('تعذّر تشغيل الصوت حالياً'));$('#pl-label').textContent=`${d.name} — الآية ${ar(pl.i)}`;document.querySelectorAll('.ay.playing').forEach(e=>e.classList.remove('playing'));let el=location.hash.startsWith('#/quran/'+pl.s+'/')||location.hash==='#/quran/'+pl.s?document.querySelector(`.ay[data-i="${pl.i}"]`):null;if(el){el.classList.add('playing');el.scrollIntoView({block:'center'})}}
function step(v){if(!pl.s)return;let max=cache[pl.s].ayahs.length,next=pl.i+v;if(next<1||next>max)return;pl.i=next;loadAudio()}
$('#pl-next').onclick=()=>step(1);$('#pl-prev').onclick=()=>step(-1);$('#pl-pp').onclick=()=>aud.src?(aud.paused?aud.play():aud.pause()):toast('اختر سورة للاستماع');$('#pl-vol').oninput=e=>aud.volume=e.target.value;$('#pl-rec').onchange=()=>pl.s&&loadAudio();aud.onended=()=>step(1);aud.onplay=()=>$('#pl-pp').textContent='⏸';aud.onpause=()=>$('#pl-pp').textContent='▶';
async function vListen(){let L=await getSurahs();app.innerHTML=`<h2>الاستماع للقرآن الكريم</h2><p>اختر القارئ من الشريط السفلي ثم اضغط على اسم السورة.</p><div class="sgrid">${L.map(s=>`<div class="srow"><div class="no"><span>${ar(s.number)}</span></div><div class="nm" onclick="play(${s.number})">${s.name.replace('سُورَةُ ','')}<small>${ar(s.numberOfAyahs)} آية</small></div><button class="ib" onclick="play(${s.number})">▶</button></div>`).join('')}</div>`}
async function vTafsir(s=1,a=1){let L=await getSurahs();app.innerHTML=`<h2>تفسير القرآن الكريم</h2><div class="row2"><select class="f" id="ts">${L.map(x=>`<option value="${x.number}" ${x.number==s?'selected':''}>${x.number}. ${x.name}</option>`).join('')}</select><input type="number" id="ta" min="1" value="${a}" placeholder="رقم الآية"><select class="f" id="te"><option value="ar.muyassar">التفسير الميسر</option><option value="ar.jalalayn">تفسير الجلالين</option><option value="ar.qurtubi">القرطبي</option><option value="ar.baghawi">البغوي</option></select></div><button class="btn" id="tg">عرض التفسير</button><div id="tout"></div>`;let go=async()=>{let S=$('#ts').value,A=$('#ta').value||1;$('#tout').innerHTML='<p class="load">…</p>';try{let [v,t]=await Promise.all([qd(`/ayah/${S}:${A}/quran-uthmani`),qd(`/ayah/${S}:${A}/${$('#te').value}`)]);$('#tout').innerHTML=`<div class="card"><h3>${v.surah.name} — الآية ${ar(v.numberInSurah)}</h3><div class="quran-text" style="font-size:1.6rem">${v.text}</div><hr><div class="tafsir">${t.text}</div></div>`}catch{$('#tout').innerHTML='<p class="err">لم يتم العثور على الآية أو التفسير.</p>'}};$('#tg').onclick=go;go()}
async function vSearch(){app.innerHTML='<h2>البحث القرآني</h2><div class="row2"><input type="text" id="sq" placeholder="اكتب كلمة أو عبارة"><button class="btn" id="sg" style="flex:none">بحث</button></div><div id="sr"></div>';let go=async()=>{let w=$('#sq').value.trim();if(!w)return;$('#sr').innerHTML='<p class="load">…</p>';try{let d=await qd(`/search/${encodeURIComponent(w)}/all/quran-simple`),m=d.matches||[];$('#sr').innerHTML=`<p>عدد النتائج: ${ar(d.count)}</p>`+m.slice(0,60).map(x=>`<div class="item" onclick="location.hash='#/quran/${x.surah.number}/${x.numberInSurah}'"><b>${x.surah.name} — الآية ${ar(x.numberInSurah)}</b><div class="quran-text">${x.text}</div></div>`).join('')}catch{$('#sr').innerHTML='<p class="err">لا توجد نتائج.</p>'}};$('#sg').onclick=go;$('#sq').onkeydown=e=>e.key==='Enter'&&go()}
function vAdhkar(k='morning'){if(!ADH[k])k='morning';app.innerHTML=`<h2>الأذكار والأدعية</h2><div class="tabs">${Object.keys(ADH).map(x=>`<button class="${x===k?'on':''}" onclick="location.hash='#/adhkar/${x}'">${ADH[x][0]}</button>`).join('')}<button onclick="location.hash='#/adhkar/tasbih'">مسبحة حرة</button></div><div id="al"></div>`;if(k==='tasbih'){let c=0;$('#al').innerHTML='<div class="dhikr" style="justify-content:center"><button class="cnt" style="width:130px;height:130px;font-size:2.3rem" id="tc">0</button><button class="btn alt" id="tr">تصفير</button></div>';$('#tc').onclick=()=>$('#tc').textContent=++c;$('#tr').onclick=()=>{c=0;$('#tc').textContent=0};return}$('#al').innerHTML=ADH[k][1].map(([t,n])=>`<div class="dhikr"><p>${t}</p><button class="cnt" data-n="${n}">${ar(n)}</button></div>`).join('');$('#al').onclick=e=>{let b=e.target.closest('.cnt');if(!b)return;let n=+b.dataset.n;if(n>0){b.dataset.n=--n;b.textContent=n?ar(n):'✓';b.classList.toggle('done',!n)}}}
async function vAccount(){if(!user){app.innerHTML='<h2>حسابي</h2><div class="card" style="max-width:430px;margin:auto"><input type="text" id="u" placeholder="اسم المستخدم"><input type="password" id="p" placeholder="كلمة المرور"><button class="btn" id="li">تسجيل الدخول</button><button class="btn alt" id="rg">إنشاء حساب</button><div class="err" id="em"></div></div>';let go=mode=>async()=>{let r=await api(mode,'POST',{username:$('#u').value,password:$('#p').value});if(r.error){$('#em').textContent=r.error;return}user=r.user;await syncLocal();route()};$('#li').onclick=go('login');$('#rg').onclick=go('register');return}let [f,h,fs,pg]=await Promise.all([api('fav'),api('history'),api('favsurah'),getProg()]),L=await getSurahs();app.innerHTML=`<h2>أهلاً ${user} 🌙</h2><button class="btn" id="lo">تسجيل الخروج</button>${pg?`<a class="btn alt" href="#/quran/${pg.surah}/${pg.ayah}">متابعة القراءة</a>`:''}<h3>السور المفضلة</h3>${fs.items.map(n=>`<a class="btn alt" href="#/quran/${n}">${L[n-1].name}</a>`).join('')||'<p>لا توجد سور مفضلة.</p>'}<h3>الآيات المفضلة</h3>${f.items.map(x=>`<div class="item" onclick="location.hash='#/quran/${x.surah}/${x.ayah}'"><b>${x.surah_name} — ${ar(x.ayah)}</b><div class="quran-text">${x.text}</div></div>`).join('')||'<p>لا توجد آيات مفضلة.</p>'}<h3>سجل القراءة</h3>${h.items.map(x=>`<div class="item" onclick="location.hash='#/quran/${x.surah}/${x.ayah}'">${x.surah_name} — الآية ${ar(x.ayah)} <small>${x.at}</small></div>`).join('')||'<p>السجل فارغ.</p>'}`;$('#lo').onclick=async()=>{await api('logout','POST');user=null;route()}}
async function syncLocal(){let p=localProg();if(p&&!(await api('progress')).progress)await api('progress','POST',p)}
$('#night').onclick=()=>{document.body.classList.toggle('night');localStorage.night=document.body.classList.contains('night')?'1':''};if(localStorage.night)document.body.classList.add('night');window.onhashchange=route;api('me').then(r=>{user=r.user;route()}).catch(route);
</script></body></html>"""

@app.teardown_appcontext
def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB, timeout=20)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
        g.db.execute("PRAGMA busy_timeout=20000")
    return g.db

def rows(sql, *args):
    return [dict(r) for r in db().execute(sql, args).fetchall()]

def uid():
    return session.get("uid")

def need_login():
    return jsonify(error="يلزم تسجيل الدخول أولاً"), 401

@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")

@app.get("/health")
def health():
    return jsonify(status="ok", app="Noor Quran")

@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if len(username) < 3 or len(username) > 40 or len(password) < 8:
        return jsonify(error="اسم المستخدم من 3 إلى 40 حرفاً وكلمة المرور 8 أحرف على الأقل"), 400
    try:
        cur = db().execute(
            "INSERT INTO users(username,password_hash) VALUES(?,?)",
            (username, generate_password_hash(password))
        )
        db().commit()
    except sqlite3.IntegrityError:
        return jsonify(error="اسم المستخدم مستخدم من قبل"), 400
    session.clear()
    session["uid"] = cur.lastrowid
    session["name"] = username
    return jsonify(user=username)

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    row = db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], data.get("password") or ""):
        return jsonify(error="بيانات الدخول غير صحيحة"), 400
    session.clear()
    session["uid"] = row["id"]
    session["name"] = row["username"]
    return jsonify(user=row["username"])

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)

@app.get("/api/me")
def me():
    return jsonify(user=session.get("name") if uid() else None)

@app.route("/api/fav", methods=["GET", "POST"])
def fav():
    if not uid():
        return need_login()
    if request.method == "GET":
        return jsonify(items=rows("SELECT * FROM favorites WHERE user_id=? ORDER BY surah,ayah", uid()))
    data = request.get_json(silent=True) or {}
    try:
        s, a = int(data["surah"]), int(data["ayah"])
        if not (1 <= s <= 114 and a >= 1):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        return jsonify(error="رقم السورة أو الآية غير صحيح"), 400
    exists = db().execute(
        "SELECT 1 FROM favorites WHERE user_id=? AND surah=? AND ayah=?",
        (uid(), s, a)
    ).fetchone()
    if exists:
        db().execute("DELETE FROM favorites WHERE user_id=? AND surah=? AND ayah=?", (uid(), s, a))
    else:
        db().execute("INSERT INTO favorites VALUES(?,?,?,?,?)",
                     (uid(), s, a, data.get("surah_name", ""), data.get("text", "")))
    db().commit()
    return jsonify(on=not bool(exists))

@app.route("/api/favsurah", methods=["GET", "POST"])
def favsurah():
    if not uid():
        return need_login()
    if request.method == "GET":
        return jsonify(items=[r["surah"] for r in rows("SELECT surah FROM fav_surahs WHERE user_id=?", uid())])
    data = request.get_json(silent=True) or {}
    try:
        s = int(data["surah"])
        if not 1 <= s <= 114:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        return jsonify(error="رقم السورة غير صحيح"), 400
    exists = db().execute("SELECT 1 FROM fav_surahs WHERE user_id=? AND surah=?", (uid(), s)).fetchone()
    if exists:
        db().execute("DELETE FROM fav_surahs WHERE user_id=? AND surah=?", (uid(), s))
    else:
        db().execute("INSERT INTO fav_surahs VALUES(?,?)", (uid(), s))
    db().commit()
    return jsonify(on=not bool(exists))

@app.route("/api/progress", methods=["GET", "POST"])
def progress():
    if not uid():
        return need_login()
    if request.method == "GET":
        found = rows("SELECT surah,ayah,surah_name FROM progress WHERE user_id=?", uid())
        return jsonify(progress=found[0] if found else None)
    data = request.get_json(silent=True) or {}
    try:
        s, a = int(data["surah"]), int(data["ayah"])
        if not (1 <= s <= 114 and a >= 1):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        return jsonify(error="موضع القراءة غير صحيح"), 400
    name = data.get("surah_name", "")
    db().execute(
        """INSERT INTO progress(user_id,surah,ayah,surah_name) VALUES(?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET surah=excluded.surah,ayah=excluded.ayah,surah_name=excluded.surah_name""",
        (uid(), s, a, name)
    )
    db().execute("INSERT INTO history(user_id,surah,ayah,surah_name) VALUES(?,?,?,?)", (uid(), s, a, name))
    db().commit()
    return jsonify(ok=True)

@app.get("/api/history")
def history():
    if not uid():
        return need_login()
    return jsonify(items=rows(
        "SELECT surah,ayah,surah_name,at FROM history WHERE user_id=? ORDER BY id DESC LIMIT 30",
        uid()
    ))

def init_db():
    with sqlite3.connect(DB, timeout=20) as conn:
        conn.executescript(SCHEMA)

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)

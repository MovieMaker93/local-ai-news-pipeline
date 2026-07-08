#!/usr/bin/env python3
"""render_wire_test.py — Lux in Tenebris wire ticker test page.
"""
import sys, os, json, html, shutil
from datetime import datetime

OUT = '/tmp/v2/test-wire'
FONT_SRC = '/home/nttluke/ai-news-deploy/fonts'

ES = html.escape

def tix(aa):
    r = []
    for a in aa:
        h = ES(a.get('headline',''))
        s = ES(a.get('source',''))
        b = ES(a.get('body',''))
        r.append(f'<div class=ti onclick="openArt(this)" data-h="{h}" data-b="{b}" data-s="{s}"><span class=tih>{h}</span> <span class=tis>\u2014 {s}</span></div>')
    return ''.join(r) * 2

def cards(aa):
    r = []
    for a in aa:
        h = ES(a.get('headline',''))
        s = ES(a.get('source',''))
        b = ES(a.get('body',''))
        r.append(f'<div class=wc onclick="openArt(this)" data-h="{h}" data-b="{b}" data-s="{s}"><h3>{h}</h3><p>{b[:200]}\u2026</p><span class=wcs>{s}</span></div>')
    return '\n'.join(r)

def main():
    if len(sys.argv) < 2: print('Usage: render_wire_test.py <wire_articles.json>'); sys.exit(1)
    with open(sys.argv[1]) as f: aa = json.load(f)
    os.makedirs(OUT, exist_ok=True)
    if os.path.isdir(FONT_SRC): shutil.copytree(FONT_SRC, os.path.join(OUT,'fonts'), dirs_exist_ok=True)
    n = datetime.now()
    dh = n.strftime('%B %d, %Y')
    di = n.strftime('%Y-%m-%d')

    # HTML: f-string ok because JS uses split/replace not regex
    # KEY: all CSS { } are doubled {{ }}. JS uses single { } fine inside f-string
    # because they're inside <script> not at top level of f-string
    P = f'''<!DOCTYPE html>
<html lang=en>
<head>
<meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1.0">
<title>Lux in Tenebris &middot; {dh}</title>
<style>
@font-face{{font-family:Newsreader;font-style:normal;font-weight:400;font-display:swap;src:url(fonts/newsreader-latin-400-normal.woff2)format(woff2)}}
@font-face{{font-family:Newsreader;font-style:normal;font-weight:500;font-display:swap;src:url(fonts/newsreader-latin-500-normal.woff2)format(woff2)}}
@font-face{{font-family:Newsreader;font-style:normal;font-weight:600;font-display:swap;src:url(fonts/newsreader-latin-600-normal.woff2)format(woff2)}}
@font-face{{font-family:Newsreader;font-style:normal;font-weight:700;font-display:swap;src:url(fonts/newsreader-latin-700-normal.woff2)format(woff2)}}
@font-face{{font-family:Newsreader;font-style:italic;font-weight:400;font-display:swap;src:url(fonts/newsreader-latin-400-italic.woff2)format(woff2)}}
@font-face{{font-family:Inter;font-style:normal;font-weight:400;font-display:swap;src:url(fonts/inter-latin-400-normal.woff2)format(woff2)}}
@font-face{{font-family:Inter;font-style:normal;font-weight:500;font-display:swap;src:url(fonts/inter-latin-500-normal.woff2)format(woff2)}}
@font-face{{font-family:Inter;font-style:normal;font-weight:600;font-display:swap;src:url(fonts/inter-latin-600-normal.woff2)format(woff2)}}
@font-face{{font-family:Inter;font-style:normal;font-weight:700;font-display:swap;src:url(fonts/inter-latin-700-normal.woff2)format(woff2)}}
:root{{--ink:#0e0e10;--type:#ece6dc;--td:#b6afa3;--mu:#827d73;--lux:#f0a23c;--ls:#caa26a;--em:#ff6b35;--ru:#27272d;--rs:#3a3a42;--se:Newsreader,Georgia,Times New Roman,serif;--sa:Inter,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;--mw:1180px}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:var(--ink);color:var(--type);font-family:var(--se);line-height:1.5;-webkit-font-smoothing:antialiased}}
body::before{{content:"";position:fixed;inset:0 0 auto 0;height:60vh;pointer-events:none;z-index:0;background:radial-gradient(120% 80% at 50% -18%,rgba(240,162,60,.085),rgba(240,162,60,0)60%)}}
a{{color:inherit;text-decoration:none}}
.c{{position:relative;z-index:1;max-width:var(--mw);margin:0 auto;padding:34px 28px 80px}}
.masthead{{text-align:center}}
.masthead .tl{{border-top:1px solid var(--rs)}}
.masthead .ears{{display:flex;align-items:flex-end;justify-content:space-between;font-family:var(--sa);font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--mu);padding:14px 2px 6px}}
.np{{font-family:var(--se);font-weight:700;font-size:clamp(40px,9vw,96px);line-height:.92;letter-spacing:.01em;margin:2px 0 4px;color:var(--type)}}
.np .lx{{color:var(--lux)}}
.rd{{border:0;height:0;border-top:3px solid var(--type);border-bottom:1px solid var(--type);padding-bottom:3px;margin:10px 0 0}}
.masthead .dl{{display:flex;align-items:center;justify-content:center;gap:14px;flex-wrap:wrap;font-family:var(--sa);font-size:11.5px;font-weight:500;letter-spacing:.14em;text-transform:uppercase;color:var(--mu);padding:11px 0 0}}
.masthead .dl .tg{{font-family:var(--se);font-style:italic;font-weight:400;letter-spacing:.02em;text-transform:none;font-size:15px;color:var(--ls)}}
.masthead .rt{{border:0;border-top:1px solid var(--ru);margin:13px 0 0}}
.lz{{margin-top:30px}}
.lead a{{display:block;transition:color .18s ease}}
.lg{{display:grid;grid-template-columns:1.45fr 1fr;gap:0 52px;align-items:end}}
.kk{{font-family:var(--sa);font-size:11px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--em);display:inline-flex;align-items:center;gap:9px;margin:0 0 14px}}
.kk::before{{content:"";width:22px;height:2px;background:var(--em);display:inline-block}}
.lead h1{{font-family:var(--se);font-weight:700;font-size:clamp(33px,4.6vw,58px);line-height:1;letter-spacing:-.014em;margin:0;color:var(--type);text-wrap:balance}}
.lead .dk{{font-family:var(--se);font-weight:400;font-size:clamp(17px,1.35vw,20px);line-height:1.5;color:var(--td);margin:0 0 18px}}
.bl{{font-family:var(--sa);font-size:11.5px;font-weight:500;letter-spacing:.07em;text-transform:uppercase;color:var(--mu);display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.bl .mo{{color:var(--lux);font-weight:600}}
.lead a:hover h1{{color:#fff}}
.lead a>.li{{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:cover;border-radius:8px;margin-bottom:22px;opacity:.92;filter:brightness(.88)contrast(1.06)sepia(.18)saturate(.92);box-shadow:0 2px 12px rgba(0,0,0,.4),inset 0 0 40px rgba(140,100,60,.08)}}
.cf{{margin-top:60px;padding-top:22px;border-top:3px double var(--rs);text-align:center}}
.cf .mk{{font-family:var(--se);font-style:italic;font-size:16px;color:var(--ls);margin:0 0 6px}}
.cf .mt{{font-family:var(--sa);font-size:11px;font-weight:500;letter-spacing:.12em;text-transform:uppercase;color:var(--mu);margin:0}}
.wt{{display:flex;align-items:center;height:38px;background:var(--ink);border-top:1px solid var(--rs);border-bottom:1px solid var(--ru);margin:14px 0 0;overflow:hidden}}
.wtt{{display:flex;align-items:center;white-space:nowrap;padding-left:20px;animation:ws 90s linear infinite}}
.wtt:hover{{animation-play-state:paused}}
@keyframes ws{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}
.ti{{display:inline-flex;align-items:center;gap:7px;padding:0 22px;cursor:pointer;border-right:1px solid var(--ru);height:38px}}
.ti:hover{{background:rgba(240,162,60,.05)}}
.tih{{font-family:var(--se);font-size:13px;color:var(--type)}}
.tis{{font-family:var(--sa);font-size:9.5px;color:var(--mu);text-transform:uppercase;letter-spacing:.06em}}
.wsect{{margin-top:40px}}
.sh{{display:flex;align-items:center;gap:16px;margin:0 0 22px}}
.sh h2{{font-family:var(--sa);font-weight:700;font-size:13.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--em);margin:0;white-space:nowrap}}
.wcg{{display:grid;grid-template-columns:repeat(2,1fr);gap:20px;margin-top:18px}}
.wc{{background:rgba(255,255,255,.02);border:1px solid var(--ru);border-radius:6px;padding:22px 24px;cursor:pointer}}
.wc:hover{{border-color:var(--ls);background:rgba(240,162,60,.03);transform:translateY(-2px)}}
.wc h3{{font-family:var(--se);font-weight:600;font-size:19px;line-height:1.2;letter-spacing:-.004em;color:var(--type);margin:0 0 10px}}
.wc p{{font-family:var(--se);font-size:14.5px;line-height:1.5;color:var(--td);margin:0 0 12px}}
.wcs{{font-family:var(--sa);font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--mu)}}
.mo{{display:none;position:fixed;inset:0;background:rgba(10,10,12,.88);z-index:1000;justify-content:center;align-items:center;backdrop-filter:blur(8px)}}
.mo.a{{display:flex}}
.mb{{background:#121214;border:1px solid var(--rs);max-width:680px;width:90%;max-height:82vh;overflow-y:auto;padding:40px 44px;position:relative;animation:fi .2s ease}}
@keyframes fi{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.mc{{position:absolute;top:14px;right:18px;background:none;border:none;color:var(--mu);font-size:20px;cursor:pointer;font-family:var(--sa);padding:4px 8px}}
.mh{{font-family:var(--se);font-weight:700;font-size:30px;line-height:1.1;letter-spacing:-.01em;color:var(--type);margin:0 0 14px;padding-right:32px}}
.mm{{font-family:var(--sa);font-size:10.5px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--mu);margin:0 0 22px}}
.mbd{{font-family:var(--se);font-size:16.5px;line-height:1.7;color:var(--td)}}
.mbd .as{{display:block;margin-top:18px;padding-top:14px;border-top:1px solid var(--ru);font-family:var(--sa);font-size:11px;color:var(--mu);line-height:1.5}}
.mbd .as .al{{color:var(--ls);font-weight:600;font-family:var(--sa);font-size:10px;letter-spacing:.06em;text-transform:uppercase}}
@keyframes rise{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
.lz,.wsect{{animation:rise .55s ease both}}
.wsect{{animation-delay:.04s}}
@media(max-width:900px){{.lg{{grid-template-columns:1fr;gap:20px 0}}.lead h1{{font-size:clamp(30px,7vw,46px)}}.wcg{{grid-template-columns:1fr}}}}
@media(max-width:620px){{.c{{padding:24px 18px 64px}}}}
@media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation:none!important}}}}
.tt{{background:#1a1412;border-bottom:1px solid var(--ru);padding:7px 24px;font-family:var(--sa);font-size:10.5px;color:var(--mu);text-align:center}}
.tt em{{color:var(--em);font-style:normal;font-weight:600}}
</style>
</head>
<body>
<div class=tt>&#x26a1; TEST &#xb7; Wire ticker &#xb7; <em>NON PROD</em> &#xb7; {dh}</div>
<div class=c>
<header class=masthead>
<div class=tl></div>
<div class=ears><span>Est. MMXXVI</span><span class=r>Test</span></div>
<div class=np>Lux in <span class=lx>Tenebris</span></div>
<hr class=rd>
<div class=dl><span>{dh}</span><span>&#x25c6;</span><span class=tg>AI dispatches from the dark</span><span>&#x25c6;</span><span>{len(aa)} articles</span></div>
<hr class=rt>
</header>
<div class=wt><div class=wtt>{tix(aa)}</div></div>
<div class=lz>
<article class=lead><a href=# onclick="return false">
<img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1180' height='664'%3E%3Crect width='1180' height='664' fill='%231a181c'/%3E%3Ctext x='590' y='332' text-anchor='middle' fill='%233a3a42' font-family='Georgia,serif' font-size='18'%3ELead story image%3C/text%3E%3C/svg%3E" alt class=li>
<div class=lg><div><p class=kk>Top Story</p><h1>Production newspaper<br>appears below this image</h1></div>
<div><p class=dk>The wire articles banner sits directly above the lead image.</p>
<p class=bl><span class=sr>Lux in Tenebris</span>&#xb7;<span>{di}</span>&#xb7;<span class=mo>Read the dispatch &#x2192;</span></p></div></div></a></article></div>
<div class=wsect>
<div class=sh><h2>Signals</h2><span style="flex:1;height:1px;background:var(--rs)"></span><span style="font-family:var(--sa);font-size:11px;color:var(--mu)">{len(aa):02d}</span></div>
<div class=wcg>{cards(aa)}</div></div>
<footer class=cf><p class=mk>Per aspera ad astra</p><p class=mt>Wire test &#xb7; no deploy &#xb7; {di}</p></footer></div>
<div class=mo id=mo onclick=cm(event)>
<div class=mb><button class=mc onclick=cm()>&#x2715;</button>
<h2 class=mh id=mh></h2>
<p class=mm>Source: <span id=ms style=color:var(--lux)></span></p>
<div class=mbd id=mbd></div></div></div>
<script>
function openArt(el){{
  var h=el.getAttribute('data-h'),b=el.getAttribute('data-b'),s=el.getAttribute('data-s');
  document.getElementById('mh').textContent=h;
  document.getElementById('ms').textContent=s;
  var ai='*'+'\u2014'+' Written by AI';
  var i=b.indexOf(ai);
  if(i>=0){{
    var m=b.substring(0,i);
    var a=b.substring(i+ai.length+3).split(')')[0];
    var body=b.substring(0,i).replace(/\\n/g,'<br>');
    var sig='<div class=as><span class=al>\u2B25 AI-GENERATED</span><br>Model: '+a+'</div>';
    document.getElementById('mbd').innerHTML=body+sig;
  }}else{{
    document.getElementById('mbd').innerHTML=b.replace(/\\n/g,'<br>');
  }}
  document.getElementById('mo').classList.add('a');
  document.body.style.overflow='hidden';
}}
function cm(e){{if(e&&e.target!=document.getElementById('mo'))return;document.getElementById('mo').classList.remove('a');document.body.style.overflow='';}}
document.addEventListener('keydown',function(e){{if(e.key==='Escape')cm()}});
</script>
</body>
</html>'''

    op = os.path.join(OUT, 'index.html')
    with open(op, 'w', encoding='utf-8') as f:
        f.write(P)
    print(json.dumps({'status':'ok','output':op,'n':len(aa)}))

if __name__ == '__main__': main()
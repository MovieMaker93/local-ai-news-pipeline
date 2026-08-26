#!/usr/bin/env python3
"""inject_wire_ticker.py — Post-process Local AI News HTML to inject scrolling banner."""
import sys, os, json, html, re, argparse
H = html.escape

def build_ticker(articles):
    if not articles: return ''
    items = []
    for a in articles:
        h = H(a.get('headline',''))
        s = H(a.get('source',''))
        u = H(a.get('source_url','#'))
        b = H(a.get('body','')).replace('\n', '\\n')
        items.append(
            '<div class="ti" onclick="openArt(this)" '
            f'data-h="{h}" data-b="{b}" data-s="{s}" data-u="{u}">'
            f'<span class="tih">{h}</span> <span class="tis">\u2014 {s}</span>'
            '</div>'
        )
    return f'<div class="wt"><div class="wtt">{"".join(items)*2}</div></div>\n'

def build_modal():
    return ('<div class="mo" id="mo" onclick="cm(event)">'
            '<div class="mb"><button class="mc" onclick="cm()">\u2715</button>'
            '<h2 class="mh" id="mh"></h2>'
            '<p class="mm">Source: <span id="ms"></span></p>'
            '<div class="mbd" id="mbd"></div></div></div>\n')

def build_css():
    return (
        '.wt{display:flex;align-items:center;height:38px;background:var(--ink);'
        'border-top:1px solid var(--rule-strong);border-bottom:1px solid var(--rule);'
        'margin:14px 0 0;overflow:hidden}'
        '.wtt{display:flex;align-items:center;white-space:nowrap;padding-left:20px;'
        'animation:ws 90s linear infinite}'
        '.wtt:hover{animation-play-state:paused}'
        '@keyframes ws{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}'
        '.ti{display:inline-flex;align-items:center;gap:7px;padding:0 22px;'
        'cursor:pointer;border-right:1px solid var(--rule);height:38px}'
        '.ti:hover{background:rgba(240,162,60,.05)}'
        '.tih{font-family:var(--serif);font-size:13px;color:var(--type)}'
        '.tis{font-family:var(--sans);font-size:9.5px;color:var(--muted);'
        'text-transform:uppercase;letter-spacing:.06em}'
        '.mo{display:none;position:fixed;inset:0;background:rgba(10,10,12,.88);'
        'z-index:1000;justify-content:center;align-items:center;backdrop-filter:blur(8px)}'
        '.mo.a{display:flex}'
        '.mb{background:#121214;border:1px solid var(--rule-strong);max-width:680px;'
        'width:90%;max-height:82vh;overflow-y:auto;padding:40px 44px;position:relative;animation:fi .2s ease}'
        '@keyframes fi{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}'
        '.mc{position:absolute;top:14px;right:18px;background:none;border:none;color:var(--muted);'
        'font-size:20px;cursor:pointer;font-family:var(--sans);padding:4px 8px}'
        '.mh{font-family:var(--serif);font-weight:700;font-size:30px;line-height:1.1;'
        'letter-spacing:-.01em;color:var(--type);margin:0 0 14px;padding-right:32px}'
        '.mm{font-family:var(--sans);font-size:10.5px;font-weight:500;letter-spacing:.08em;'
        'text-transform:uppercase;color:var(--muted);margin:0 0 22px}'
        '.mm a{color:var(--lux)}.mm a:hover{text-decoration:underline}'
        '.mbd{font-family:var(--serif);font-size:16.5px;line-height:1.7;color:var(--type-dim)}'
        '.mbd .en{display:block;color:var(--lux-soft);font-style:italic;'
        'font-size:15px;margin-top:14px;padding-left:12px;'
        'border-left:2px solid var(--rule-strong)}'
        '.mbd .as{display:block;margin-top:18px;padding-top:14px;border-top:1px solid var(--rule);'
        'font-family:var(--sans);font-size:11px;color:var(--muted);line-height:1.5}'
        '.mbd .as .al{color:var(--lux-soft);font-weight:600;font-family:var(--sans);'
        'font-size:10px;letter-spacing:.06em;text-transform:uppercase}'
    )

def build_js():
    return (
        'function openArt(el){'
        "var h=el.getAttribute('data-h'),b=el.getAttribute('data-b'),"
        "s=el.getAttribute('data-s'),u=el.getAttribute('data-u');"
        "document.getElementById('mh').textContent=h;"
        "var sl=document.getElementById('ms');"
        "if(u&&u!=='#'&&u!==''){"
        "sl.innerHTML='<a href=\"'+u+'\" target=\"_blank\" rel=\"noopener\">'+s+'</a>';"
        "}else{sl.textContent=s;}"
        "var aiS='*\u2014 Written by AI (';"
        'var i=b.indexOf(aiS);'
        'if(i>=0){'
        "var bf=b.substring(0,i);"
        "var af=b.substring(i+aiS.length);"
        "var mdl=af.split(')')[0];"
        "bf=bf.split('\\\\n').join('<br>');"
        "bf=bf.replace(/\\*([^*]+)\\*/g,'<em class=\"en\">$1</em>');"
        "var sg='<div class=\"as\"><span class=\"al\">\u2B25 AI-GENERATED</span><br>Model: '+mdl+'</div>';"
        "document.getElementById('mbd').innerHTML=bf+sg;"
        '}else{'
        "document.getElementById('mbd').innerHTML=b.split('\\\\n').join('<br>');"
        '}'
        "document.getElementById('mo').classList.add('a');"
        "document.body.style.overflow='hidden';}"
        'function cm(e){'
        "if(e&&e.target!=document.getElementById('mo'))return;"
        "document.getElementById('mo').classList.remove('a');"
        "document.body.style.overflow='';}"
        "document.addEventListener('keydown',function(e){if(e.key==='Escape')cm()});"
    )

def main():
    ap = argparse.ArgumentParser(description='Inject wire ticker into Local AI News HTML')
    ap.add_argument('html', help='Path to rendered index.html')
    ap.add_argument('wire', help='Path to wire_articles.json')
    ap.add_argument('--output', '-o', default=None)
    args = ap.parse_args()

    with open(args.html, encoding='utf-8') as f: hc = f.read()
    with open(args.wire, encoding='utf-8') as f: articles = json.load(f)

    if not articles:
        print(json.dumps({'status':'ok','injected':0,'message':'no wire articles'}))
        return

    hc = re.sub(r'(</header>\s*)', r'\1' + build_ticker(articles), hc, count=1)
    hc = re.sub(r'(</body>)', build_modal() + r'\1', hc, count=1)
    hc = re.sub(r'(</head>)', '<style>' + build_css() + '</style>' + r'\1', hc, count=1)
    hc = re.sub(r'(</body>)', '<script>' + build_js() + '</script>' + r'\1', hc, count=1)

    output = args.output or args.html
    with open(output, 'w', encoding='utf-8') as f: f.write(hc)
    print(json.dumps({'status':'ok','injected':len(articles),'output':output}))

if __name__ == '__main__': main()
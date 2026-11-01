#!/usr/bin/env python3
"""Generate self-contained profile artwork; no network, fonts, or image service."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'assets'
THEMES = {
    'dark': dict(bg='#0d1523', panel='#142238', line='#293d59', ink='#f0f5ff', muted='#a3b5cb', mint='#62e4c5', violet='#a89bff', glow='#17453f'),
    'light': dict(bg='#f4f7fb', panel='#e7eef8', line='#cfdbec', ink='#18263b', muted='#52647b', mint='#087e72', violet='#7055c6', glow='#d3f1e8'),
}


def hero(theme, mobile=False):
    c = THEMES[theme]
    w, h = (600, 460) if mobile else (1200, 440)
    content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">
<title id="title">Jasil Meledath — Full-stack + cloud engineer</title>
<desc id="desc">From the first interface to the last mile of infrastructure. Building web products, APIs and cloud systems in Bangalore, India. Decorative architecture lines animate gently; reduced-motion preferences are respected.</desc>
<defs>
 <radialGradient id="glow"><stop stop-color="{c['glow']}"/><stop offset="1" stop-color="{c['bg']}"/></radialGradient>
 <linearGradient id="edge"><stop stop-color="{c['mint']}"/><stop offset="1" stop-color="{c['violet']}"/></linearGradient>
 <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M28 0H0V28" fill="none" stroke="{c['line']}" stroke-width=".6"/></pattern>
 <clipPath id="clip"><rect width="{w}" height="{h}" rx="24"/></clipPath>
</defs>
<style>
 .flow {{stroke-dasharray:5 12; animation:flow 9s linear infinite}}
 .float {{animation:float 7s ease-in-out infinite}}
 .signal {{animation:signal 5s ease-in-out infinite}}
 @keyframes flow {{to {{stroke-dashoffset:-102}}}}
 @keyframes float {{0%,100% {{transform:translateY(0)}} 50% {{transform:translateY(-7px)}}}}
 @keyframes signal {{0%,100% {{opacity:.45}} 50% {{opacity:1}}}}
 @media (prefers-reduced-motion:reduce) {{.flow,.float,.signal {{animation:none}}}}
</style>
<g clip-path="url(#clip)">
 <rect width="{w}" height="{h}" fill="{c['bg']}"/>
 <ellipse cx="{w-50}" cy="130" rx="450" ry="350" fill="url(#glow)"/>
 <rect x="{360 if mobile else 700}" width="500" height="{h}" fill="url(#grid)" opacity=".55"/>
 <rect width="{w}" height="3" fill="url(#edge)"/>
<g font-family="Arial,Helvetica,sans-serif">
'''
    if mobile:
        content += f'''
 <text x="32" y="51" font-size="15" font-weight="700" letter-spacing="1.6" fill="{c['mint']}">FULL-STACK + CLOUD ENGINEER</text>
 <text x="29" y="139" font-size="62" font-weight="700" letter-spacing="-3" fill="{c['ink']}">Jasil Meledath.</text>
 <text x="32" y="201" font-size="29" fill="{c['ink']}">From the first interface</text>
 <text x="32" y="240" font-size="29" fill="{c['ink']}">to the last mile of infrastructure.</text>
 <text x="32" y="290" font-size="18" fill="{c['muted']}">Web products. APIs. Cloud systems.</text>
 <path d="M32 329H568" stroke="{c['line']}"/>
 <text x="32" y="371" font-size="18" fill="{c['muted']}">Bangalore, India</text>
 <text x="32" y="411" font-size="15" font-weight="700" letter-spacing="2" fill="{c['mint']}">BUILD → SHIP → OPERATE</text>
 <path class="flow" d="M367 370H565" stroke="{c['mint']}" fill="none"/>
 <circle class="signal" cx="565" cy="370" r="5" fill="{c['mint']}"/>
'''
    else:
        content += f'''
 <text x="48" y="55" font-size="14" font-weight="700" letter-spacing="2.2" fill="{c['mint']}">FULL-STACK + CLOUD ENGINEER</text>
 <text x="43" y="153" font-size="80" font-weight="700" letter-spacing="-4" fill="{c['ink']}">Jasil Meledath.</text>
 <text x="48" y="217" font-size="30" fill="{c['ink']}">From the first interface</text>
 <text x="48" y="257" font-size="30" fill="{c['ink']}">to the last mile of infrastructure.</text>
 <text x="48" y="310" font-size="17" fill="{c['muted']}">Web products. APIs. Cloud systems.</text>
 <path d="M48 356H650" stroke="{c['line']}"/>
 <text x="48" y="397" font-size="15" fill="{c['muted']}">Bangalore, India</text>
 <text x="650" y="397" font-size="12" font-weight="700" letter-spacing="2" text-anchor="end" fill="{c['mint']}">BUILD / SHIP / OPERATE</text>
 <g class="float">
  <rect x="753" y="65" width="392" height="300" rx="16" fill="{c['panel']}" stroke="{c['line']}"/>
  <path d="M753 108H1145" stroke="{c['line']}"/>
  <circle cx="774" cy="86" r="4" fill="{c['mint']}"/><circle cx="790" cy="86" r="4" fill="{c['violet']}"/><circle cx="806" cy="86" r="4" fill="{c['muted']}"/>
  <text x="1125" y="90" text-anchor="end" font-family="monospace" font-size="11" fill="{c['muted']}">jasil / workspace</text>
  <text x="781" y="145" font-family="monospace" font-size="13" fill="{c['muted']}">$ build something useful</text>
  <path d="M823 221V259H1075V221M949 221V284" fill="none" stroke="{c['line']}" stroke-width="2"/>
  <path class="flow" d="M823 221V259H1075V221M949 221V284" fill="none" stroke="{c['mint']}" stroke-width="2"/>
'''
        for x, label, symbol in [(779, 'INTERFACE', '</>'), (905, 'API', '{ }'), (1031, 'CLOUD', '↑')]:
            content += f'''<rect x="{x}" y="174" width="88" height="49" rx="9" fill="{c['bg']}" stroke="{c['line']}"/>
 <text x="{x+44}" y="195" text-anchor="middle" font-family="monospace" font-size="15" fill="{c['mint']}">{symbol.replace('<','&lt;').replace('>','&gt;')}</text>
 <text x="{x+44}" y="213" text-anchor="middle" font-size="9" letter-spacing="1" fill="{c['muted']}">{label}</text>'''
        content += f'''
 <rect x="860" y="283" width="178" height="40" rx="20" fill="{c['bg']}" stroke="{c['line']}"/>
 <circle class="signal" cx="882" cy="303" r="4" fill="{c['mint']}"/>
 <text x="899" y="307" font-family="monospace" font-size="12" fill="{c['ink']}">ship. learn. repeat.</text>
 </g>
 <text x="949" y="398" text-anchor="middle" font-family="monospace" font-size="11" letter-spacing="2" fill="{c['muted']}">IDEA → PRODUCTION</text>
'''
    return content + f'</g></g><rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="24" fill="none" stroke="{c["line"]}"/></svg>\n'


if __name__ == '__main__':
    for theme in THEMES:
        for mobile in (False, True):
            (ROOT / f'hero-{"mobile-" if mobile else ""}{theme}.svg').write_text(hero(theme, mobile))

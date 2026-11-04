#!/usr/bin/env python3
"""Builds dashboard.svg (ID card + live GitHub stats) from the GitHub API.
Optional files next to this script: fonts.css (embedded fonts) and avatar.jpg (photo for the ID card)."""
import base64, datetime, hashlib, json, os, sys, urllib.request

LOGIN = os.environ.get("GH_LOGIN", "A7m721")
NAME = os.environ.get("DISPLAY_NAME", "Ahmed Ramadan")
ROLE = "FULL STACK DEV"
DOMAIN = "enginer-ahmed.vercel.app"
BASE = "Egypt"
SQUAD = "Freelance"
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT_DIR", ".")
HERE = os.path.dirname(os.path.abspath(__file__))

Q_USER = """query($login:String!){ user(login:$login){ createdAt
  followers{totalCount} repositories(ownerAffiliations:OWNER, privacy:PUBLIC){totalCount}
  contributionsCollection{ contributionCalendar{ totalContributions
    weeks{ contributionDays{ contributionCount } } } } }}"""
Q_REPOS = """query($login:String!,$after:String){ user(login:$login){
  repositories(ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false, first:100, after:$after){
    pageInfo{hasNextPage endCursor}
    nodes{ languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{name} } } } }}}"""


def gql(q, v):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": v}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-dashboard"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    if "errors" in d:
        raise RuntimeError(d["errors"])
    return d["data"]


def fetch():
    u = gql(Q_USER, {"login": LOGIN})["user"]
    langs, after = {}, None
    while True:
        r = gql(Q_REPOS, {"login": LOGIN, "after": after})["user"]["repositories"]
        for n in r["nodes"]:
            for e in n["languages"]["edges"]:
                langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
        if not r["pageInfo"]["hasNextPage"]:
            break
        after = r["pageInfo"]["endCursor"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    counts = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]
    return dict(since=u["createdAt"][:4], repos=u["repositories"]["totalCount"],
                contribs=cal["totalContributions"], counts=counts, langs=langs)


def streaks(counts):
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    i, cur = len(counts) - 1, 0
    if i >= 0 and counts[i] == 0:
        i -= 1
    while i >= 0 and counts[i] > 0:
        cur += 1; i -= 1
    return cur, longest


def read(name, mode="r"):
    for base in (OUT, HERE, "."):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return open(p, mode, **({} if "b" in mode else {"encoding": "utf-8"})).read()
    return None


import random
def particles(n, x0, x1, y0, y1, seed, cols):
    rng = random.Random(seed); out = ""
    for _ in range(n):
        d = rng.uniform(6, 12)
        out += (f'<circle cx="{rng.uniform(x0,x1):.0f}" cy="{rng.uniform(y0,y1):.0f}" r="{rng.uniform(1.1,2.6):.1f}" fill="{rng.choice(cols)}" '
                f'style="--dy:-{rng.uniform(90,220):.0f}px;animation:rise {d:.1f}s linear infinite;animation-delay:-{rng.uniform(0,d):.1f}s"/>')
    return out


PALETTE = {
    "#ff7a1a": "#2dd4bf", "#ffb52e": "#5eead4", "#ff5f1f": "#8b5cf6", "#ffd36b": "#99f6e4",
    "#e2383f": "#f472b6", "#c62832": "#7c3aed", "#4aa3ff": "#a78bfa",
    "#0c0e15": "#08111a", "#121420": "#0d1824",
}


def recolor(x):
    for a, b in PALETTE.items():
        x = x.replace(a, b)
    return x


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(d):
    fonts = read("fonts.css") or ""
    av = read("avatar.jpg", "rb")
    cur, longest = streaks(d["counts"])
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime("%b %Y").upper()
    W, H = 1180, 570

    # ---------- avatar / barcode
    if av:
        photo = (f'<image href="data:image/jpeg;base64,{base64.b64encode(av).decode()}" x="85" y="46" width="130" height="162" preserveAspectRatio="xMidYMid slice" clip-path="url(#avc)"/>')
    else:
        photo = '<rect x="85" y="46" width="130" height="162" rx="14" fill="#1b2030"/><text x="150" y="140" text-anchor="middle" class="sg" font-weight="700" font-size="44" fill="#ff7a1a">AR</text>'
    h = hashlib.md5(LOGIN.encode()).digest() * 4
    bars, x = "", 24
    for b in h:
        w = 1 + (b % 3)
        if x + w > 276: break
        bars += f'<rect x="{x}" y="338" width="{w}" height="30" fill="#e8eaf2" opacity=".85"/>'
        x += w + 1 + (b >> 6)

    # ---------- stat cards
    icons = {
        "repos": '<path d="M1 4h7l2 3h9v11H1z"/>',
        "contrib": '<path d="M2 18V10M8 18V3M14 18v-6M20 18V7"/>',
        "streak": '<path d="M11 1L3 12h6l-1 8 9-12h-6z"/>',
        "long": '<circle cx="10" cy="10" r="8"/><path d="M6.5 10.5l2.5 2.5 5-5.5"/>',
    }
    stats = [("REPOS", "PUBLIC REPOS", d["repos"], "#ff7a1a", "repos"),
             ("CONTRIB", "CONTRIBUTIONS · 1Y", d["contribs"], "#ffb52e", "contrib"),
             ("STREAK", "CURRENT STREAK", cur, "#4aa3ff", "streak"),
             ("LONG", "LONGEST STREAK", longest, "#2fd48a", "long")]
    cards = ""
    for i, (_, label, val, col, ic) in enumerate(stats):
        x = 440 + i * 176
        cards += (f'<g class="fi" style="animation-delay:{.3+i*.15:.2f}s"><rect x="{x}" y="140" width="160" height="86" rx="14" fill="#fff" fill-opacity=".04" stroke="#fff" stroke-opacity=".09"/>'
                  f'<rect x="{x+16}" y="154" width="26" height="3.5" rx="1.7" fill="{col}"/>'
                  f'<g transform="translate({x+126},{y_icon(0)})" fill="none" stroke="{col}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" opacity=".9">{icons[ic]}</g>'
                  f'<text x="{x+16}" y="196" class="sg" font-weight="700" font-size="30" fill="#fff">{val:,}</text>'
                  f'<text x="{x+16}" y="215" class="jb" font-size="8.5" fill="#7c8397" letter-spacing="1.2">{label}</text></g>')

    # ---------- languages
    total = sum(d["langs"].values()) or 1
    top = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:6]
    mx = (top[0][1] / total) if top else 1
    rows = ""
    for i, (name, size) in enumerate(top):
        pct = size / total * 100
        y = 302 + i * 31
        w = max(4, 210 * (size / total) / mx)
        rows += (f'<g class="fi" style="animation-delay:{.6+i*.12:.2f}s"><text x="456" y="{y+8}" class="jb" font-size="10.5" fill="#c9d1e0">{esc(name)}</text>'
                 f'<rect x="580" y="{y}" width="210" height="9" rx="4.5" fill="#fff" fill-opacity=".07"/>'
                 f'<rect class="grw" style="animation-delay:{i*.18:.2f}s" x="580" y="{y}" width="{w:.0f}" height="9" rx="4.5" fill="url(#og)"/>'
                 f'<text x="840" y="{y+8}" class="jb" font-weight="700" font-size="10.5" fill="#fff" text-anchor="end">{pct:.1f}%</text></g>')
    skills = [("FRONTEND", "React · JavaScript · CSS", "#ff7a1a"), ("BACKEND", "Node · Python · Firebase", "#4aa3ff"),
              ("DATA", "SQL · PostgreSQL", "#ffb52e"), ("DEPLOY", "Vercel · Git · GitHub", "#2fd48a")]
    sk = ""
    for i, (t, v, c) in enumerate(skills):
        y = 306 + i * 44
        sk += (f'<g class="fi" style="animation-delay:{.9+i*.15:.2f}s"><circle cx="906" cy="{y-3}" r="3.5" fill="{c}"/>'
               f'<text x="920" y="{y}" class="jb" font-weight="700" font-size="9" fill="{c}" letter-spacing="1.4">{t}</text>'
               f'<text x="920" y="{y+17}" class="sg" font-weight="500" font-size="12.5" fill="#eef1f8">{v}</text></g>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs><style>{fonts}
.sg{{font-family:'SG','Segoe UI',Helvetica,Arial,sans-serif}}
.jb{{font-family:'JB','Consolas','Courier New',monospace}}
.fi{{opacity:0;animation:fi .7s ease-out forwards}}
.pulse{{animation:pl 1.8s ease-in-out infinite}}
.sway{{animation:sw 6s ease-in-out infinite;transform-origin:220px 0}}
.f2{{animation:f2 6s ease-in-out infinite}}
.spin{{animation:rot 40s linear infinite;transform-box:fill-box;transform-origin:center}}
.grw{{animation:grw 9s ease-out infinite;transform-box:fill-box;transform-origin:left center}}
.scn{{animation:scn 5s linear infinite;opacity:0}}
@keyframes f2{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-6px)}}}}
@keyframes rot{{to{{transform:rotate(360deg)}}}}
@keyframes grw{{0%{{transform:scaleX(0)}}22%,100%{{transform:scaleX(1)}}}}
@keyframes scn{{0%{{transform:translateX(0);opacity:0}}8%{{opacity:.5}}92%{{opacity:.5}}100%{{transform:translateX(690px);opacity:0}}}}
@keyframes rise{{0%{{opacity:0;transform:translateY(0)}}12%{{opacity:.85}}85%{{opacity:.45}}100%{{opacity:0;transform:translateY(var(--dy))}}}}
@keyframes fi{{to{{opacity:1}}}}
@keyframes pl{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
@keyframes sw{{0%,100%{{transform:rotate(-.8deg)}}50%{{transform:rotate(.8deg)}}}}
</style>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0c0e15"/><stop offset="1" stop-color="#121420"/></linearGradient>
<linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff7a1a" stop-opacity=".7"/><stop offset=".5" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#4aa3ff" stop-opacity=".75"/></linearGradient>
<linearGradient id="og" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff7a1a"/><stop offset="1" stop-color="#ffb52e"/></linearGradient>
<linearGradient id="cd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d2030"/><stop offset="1" stop-color="#0f1119"/></linearGradient>
<linearGradient id="ls" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#c62832"/><stop offset="1" stop-color="#e2383f"/></linearGradient>
<radialGradient id="gl" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ff7a1a" stop-opacity=".22"/><stop offset="1" stop-color="#ff7a1a" stop-opacity="0"/></radialGradient>
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r=".9" fill="#fff" opacity=".055"/></pattern>
<filter id="sh" x="-20%" y="-10%" width="140%" height="130%"><feDropShadow dx="0" dy="14" stdDeviation="14" flood-color="#000" flood-opacity=".6"/></filter>
<clipPath id="cc"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="24"/></clipPath>
<clipPath id="avc"><rect x="85" y="46" width="130" height="162" rx="14"/></clipPath></defs>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="24" fill="url(#bg)" stroke="url(#bd)" stroke-width="1.6"/>
<g clip-path="url(#cc)"><rect width="{W}" height="{H}" fill="url(#dots)"/>
<circle cx="230" cy="260" r="300" fill="url(#gl)"/>
<circle class="spin" cx="226" cy="330" r="235" fill="none" stroke="#ff7a1a" stroke-opacity=".14" stroke-width="2" stroke-dasharray="3 11"/>
{particles(18, 40, 1140, 160, 560, 7, ["#ff7a1a", "#ffb52e", "#4aa3ff"])}
<g><animateTransform attributeName="transform" type="rotate" values="-3.4 226 0;3.4 226 0;-3.4 226 0" dur="5s" calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1" repeatCount="indefinite"/><g><path d="M200,0H252L246,92H206Z" fill="url(#ls)"/><text transform="translate(229,10) rotate(90)" class="jb" font-size="7" fill="#fff" fill-opacity=".7" letter-spacing="2">DEV · EGYPT</text>
<rect x="206" y="86" width="40" height="14" rx="4" fill="#9aa1b3"/><circle cx="226" cy="110" r="9" fill="none" stroke="#9aa1b3" stroke-width="3"/></g>
<g transform="translate(76,118)" filter="url(#sh)"><g><animateTransform attributeName="transform" type="rotate" values="1.8 150 -8;-1.8 150 -8;1.8 150 -8" dur="5s" begin="-0.5s" calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1" repeatCount="indefinite"/>
<rect width="300" height="430" rx="20" fill="url(#cd)" stroke="#ff7a1a" stroke-opacity=".7" stroke-width="2"/>
<circle cx="24" cy="26" r="7" fill="none" stroke="#ff7a1a" stroke-width="2"/><circle cx="24" cy="26" r="2.2" fill="#ff7a1a"/>
<text x="40" y="30" class="jb" font-weight="700" font-size="9" fill="#ff7a1a" letter-spacing="1.8">DEV REGISTRATION</text>
<text x="276" y="30" class="jb" font-size="8" fill="#7c8397" text-anchor="end">No. {sum(map(ord, LOGIN)) % 10000:04d}</text>
{photo}
<rect x="85" y="46" width="130" height="162" rx="14" fill="none" stroke="#ff7a1a" stroke-width="2"/>
<circle cx="252" cy="62" r="21" fill="#e2383f" fill-opacity=".1" stroke="#e2383f" stroke-width="1.6"/><text x="252" y="67" text-anchor="middle" class="jb" font-weight="700" font-size="12" fill="#e2383f">FS</text>
<text x="150" y="246" text-anchor="middle" class="sg" font-weight="700" font-size="22" fill="#fff">{esc(NAME)}</text>
<text x="150" y="266" text-anchor="middle" class="jb" font-size="9.5" fill="#ff7a1a" letter-spacing="2.4">{ROLE}</text>
<line x1="24" y1="284" x2="276" y2="284" stroke="#fff" stroke-opacity=".1"/>
<text x="24" y="302" class="jb" font-size="7" fill="#6d7488" letter-spacing="1.4">DOMAIN</text><text x="24" y="316" class="jb" font-weight="700" font-size="9.5" fill="#fff">{DOMAIN}</text>
<text x="196" y="302" class="jb" font-size="7" fill="#6d7488" letter-spacing="1.4">BASE</text><text x="196" y="316" class="jb" font-weight="700" font-size="9.5" fill="#fff">{BASE}</text>
{bars}
<circle class="pulse" cx="28" cy="398" r="3.5" fill="#2fd48a"/><text x="38" y="401" class="jb" font-weight="700" font-size="8" fill="#2fd48a" letter-spacing="1.4">AVAILABLE</text>
<text x="276" y="401" class="jb" font-size="8" fill="#7c8397" text-anchor="end">@{LOGIN} · {d["since"]}</text></g></g></g>
<text x="440" y="82" class="jb" font-weight="700" font-size="11" fill="#ff7a1a" letter-spacing="2.6">// DASHBOARD</text>
<text x="440" y="120" class="sg" font-weight="700" font-size="28" fill="#fff">Stats from the field</text>
<rect x="944" y="62" width="186" height="28" rx="14" fill="#2fd48a" fill-opacity=".1" stroke="#2fd48a" stroke-opacity=".5"/>
<circle class="pulse" cx="962" cy="76" r="3.5" fill="#2fd48a"/><text x="974" y="80" class="jb" font-weight="700" font-size="9" fill="#2fd48a" letter-spacing="1.4">LIVE · {stamp}</text>
{cards}
<rect x="440" y="244" width="424" height="262" rx="14" fill="#fff" fill-opacity=".035" stroke="#fff" stroke-opacity=".09"/>
<text x="456" y="272" class="jb" font-size="9" fill="#7c8397" letter-spacing="1.6">TOP LANGUAGES · BY CODE SIZE</text>
{rows}
<rect class="scn" x="440" y="136" width="2" height="370" fill="#ff7a1a"/>
<text x="456" y="496" class="jb" font-size="8" fill="#5f667a">live from github.com/{LOGIN} · refreshed every 6 hours</text>
<rect x="880" y="244" width="250" height="262" rx="14" fill="#fff" fill-opacity=".035" stroke="#fff" stroke-opacity=".09"/>
<text x="896" y="272" class="jb" font-size="9" fill="#7c8397" letter-spacing="1.6">SKILL NATURE</text>
{sk}
</g></svg>'''


def y_icon(_):
    return 152


if __name__ == "__main__":
    if os.environ.get("MOCK"):
        d = dict(since="2025", repos=80, contribs=262, counts=[1]*9 + [0] + [2]*3,
                 langs={"HTML": 8190, "JavaScript": 1120, "CSS": 340, "TypeScript": 320, "Python": 40, "PHP": 2})
    elif not TOKEN:
        sys.exit("GH_TOKEN is missing")
    else:
        d = fetch()
    with open(os.path.join(OUT, "dashboard.svg"), "w", encoding="utf-8") as f:
        f.write(recolor(render(d)))
    print("dashboard.svg written:", d["repos"], "repos,", d["contribs"], "contributions")

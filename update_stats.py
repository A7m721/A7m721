#!/usr/bin/env python3
import json, math, os, sys, datetime, urllib.request

LOGIN = os.environ.get("GH_LOGIN", "A7m721")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT_DIR", ".")

MARKUP = {"HTML", "CSS", "SCSS", "Sass", "Less"}

THEMES = {
    "dark": dict(bg="#0b1220", panel="#0f1a2e", line="#1e2d45", mute="#7d8aa3", text="#e5e7eb",
                 acc="#aa9bef", acc2="#22d3ee"),
    "light": dict(bg="#ffffff", panel="#f6f8fa", line="#d0d7de", mute="#57606a", text="#1f2328",
                  acc="#6d4fd8", acc2="#0e7490"),
}
SANS = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'JetBrains Mono','Fira Code',Consolas,monospace"


def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": "profile-stats"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    if "errors" in d:
        raise RuntimeError(d["errors"])
    return d["data"]


Q_USER = """
query($login:String!){ user(login:$login){
  followers{totalCount}
  repositories(ownerAffiliations:OWNER, privacy:PUBLIC){totalCount}
  contributionsCollection{ contributionCalendar{ totalContributions
    weeks{ contributionDays{ date contributionCount } } } }
}}"""

Q_REPOS = """
query($login:String!,$after:String){ user(login:$login){
  repositories(ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false, first:100, after:$after){
    pageInfo{hasNextPage endCursor}
    nodes{ stargazerCount
      languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{name color} } } }
  }}}"""


def fetch():
    u = gql(Q_USER, {"login": LOGIN})["user"]
    stars, langs, after = 0, {}, None
    while True:
        r = gql(Q_REPOS, {"login": LOGIN, "after": after})["user"]["repositories"]
        for n in r["nodes"]:
            stars += n["stargazerCount"]
            for e in n["languages"]["edges"]:
                name, color = e["node"]["name"], e["node"]["color"] or "#8b949e"
                size = langs.get(name, (0, color))[0] + e["size"]
                langs[name] = (size, color)
        if not r["pageInfo"]["hasNextPage"]:
            break
        after = r["pageInfo"]["endCursor"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    counts = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]
    return dict(stars=stars, repos=u["repositories"]["totalCount"], followers=u["followers"]["totalCount"],
                contribs=cal["totalContributions"], langs=langs, counts=counts)


def streaks(counts):
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    i, cur = len(counts) - 1, 0
    if i >= 0 and counts[i] == 0:
        i -= 1
    while i >= 0 and counts[i] > 0:
        cur += 1
        i -= 1
    return cur, longest


def fmt(n):
    return f"{n:,}"


def card_stats(t, d):
    c = THEMES[t]
    cur, longest = streaks(d["counts"])
    items = [(fmt(d["stars"]), "Total stars"), (fmt(d["repos"]), "Public repos"), (fmt(d["followers"]), "Followers"),
             (fmt(d["contribs"]), "Contributions (1y)"), (fmt(cur), "Current streak"), (fmt(longest), "Longest streak")]
    body = ""
    for i, (num, lab) in enumerate(items):
        x = 28 + (i % 3) * 180
        y = 100 + (i // 3) * 62
        body += (f'<text x="{x}" y="{y}" fill="{c["text"]}" font-size="30" font-weight="700" font-family="{SANS}">{num}</text>'
                 f'<text x="{x}" y="{y+20}" fill="{c["mute"]}" font-size="13" font-family="{SANS}">{lab}</text>')
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 580 230" width="580" height="230">
<rect x="1" y="1" width="578" height="228" rx="14" fill="{c['panel']}" stroke="{c['line']}"/>
<text x="28" y="40" fill="{c['acc']}" font-size="20" font-weight="700" font-family="{SANS}">@{LOGIN}</text>
<text x="552" y="40" fill="{c['mute']}" font-size="13" text-anchor="end" font-family="{SANS}">at a glance</text>
<line x1="28" y1="56" x2="552" y2="56" stroke="{c['line']}"/>
{body}
<text x="552" y="216" fill="{c['mute']}" font-size="10" text-anchor="end" font-family="{MONO}">updated {today} UTC</text>
</svg>'''


def top_langs(d, n=6):
    items = sorted(d["langs"].items(), key=lambda kv: -kv[1][0])[:n]
    total = sum(s for _, (s, _) in d["langs"].items()) or 1
    return [(name, size / total * 100, color) for name, (size, color) in items]


def card_langs(t, d):
    c = THEMES[t]
    langs = top_langs(d)
    W, bx, bw = 480, 24, 432
    seg, x = "", bx
    tot = sum(p for _, p, _ in langs) or 1
    for name, p, col in langs:
        w = bw * p / tot
        seg += f'<rect x="{x:.1f}" y="58" width="{w:.1f}" height="10" fill="{col}"/>'
        x += w
    legend = ""
    for i, (name, p, col) in enumerate(langs):
        lx = 24 + (i % 2) * 216
        ly = 100 + (i // 2) * 26
        legend += (f'<circle cx="{lx+5}" cy="{ly-4}" r="5" fill="{col}"/>'
                   f'<text x="{lx+18}" y="{ly}" fill="{c["text"]}" font-size="13" font-family="{SANS}">{name} <tspan fill="{c["mute"]}">{p:.1f}%</tspan></text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 190" width="{W}" height="190">
<defs><clipPath id="r"><rect x="{bx}" y="58" width="{bw}" height="10" rx="5"/></clipPath></defs>
<rect x="1" y="1" width="{W-2}" height="188" rx="14" fill="{c['panel']}" stroke="{c['line']}"/>
<text x="24" y="38" fill="{c['acc']}" font-size="18" font-weight="700" font-family="{SANS}">Most used languages</text>
<g clip-path="url(#r)">{seg}</g>
{legend}
</svg>'''


def radar_langs(t, d):
    c = THEMES[t]
    code = {k: v for k, v in d["langs"].items() if k not in MARKUP}
    items = sorted(code.items(), key=lambda kv: -kv[1][0])[:6]
    if len(items) < 3:
        return None
    total = sum(s for _, (s, _) in items) or 1
    pcts = [(name, size / total * 100) for name, (size, _) in items]
    mx = max(p for _, p in pcts) or 1
    data = [(n, max(18, 100 * (p / mx) ** 0.5)) for n, p in pcts]
    S, cx, cy, R, n = 400, 200, 205, 120, len(data)
    def pt(i, r):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return cx + r * math.cos(a), cy + r * math.sin(a)
    grid = "".join('<polygon points="%s" fill="none" stroke="%s"/>' % (
        " ".join(f"{pt(i, R*l)[0]:.1f},{pt(i, R*l)[1]:.1f}" for i in range(n)), c["line"]) for l in (.25, .5, .75, 1))
    axes = "".join(f'<line x1="{cx}" y1="{cy}" x2="{pt(i,R)[0]:.1f}" y2="{pt(i,R)[1]:.1f}" stroke="{c["line"]}"/>' for i in range(n))
    poly = " ".join(f"{pt(i, R*v/100)[0]:.1f},{pt(i, R*v/100)[1]:.1f}" for i, (_, v) in enumerate(data))
    labels = ""
    for i, (k, v) in enumerate(data):
        x, y = pt(i, R + 22)
        anc = "middle" if abs(x - cx) < 10 else ("start" if x > cx else "end")
        labels += f'<text x="{x:.1f}" y="{y+4:.1f}" fill="{c["text"]}" font-size="12" text-anchor="{anc}">{k}</text>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}" font-family="{MONO}">
<rect x="1" y="1" width="{S-2}" height="{S-2}" rx="14" fill="{c['panel']}" stroke="{c['line']}"/>
<text x="20" y="30" fill="{c['acc2']}" font-size="13" font-weight="700">LANG.RADAR</text>
{grid}{axes}
<polygon points="{poly}" fill="{c['acc']}" fill-opacity="0.35" stroke="{c['acc']}" stroke-width="2"/>
{labels}
</svg>'''


def write(name, svg):
    if svg:
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)


def render(d):
    for t in ("dark", "light"):
        write(f"card-stats-{t}.svg", card_stats(t, d))
        write(f"card-langs-{t}.svg", card_langs(t, d))
        write(f"radar-langs-{t}.svg", radar_langs(t, d))


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("GH_TOKEN is missing")
    d = fetch()
    render(d)
    print("done:", {k: d[k] for k in ("stars", "repos", "followers", "contribs")})

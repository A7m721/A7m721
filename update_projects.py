#!/usr/bin/env python3
"""Builds designed project cards (projects/*.svg) from the repos pinned on the profile
and fills the PROJECTS section of README.md with linked images."""
import html, json, os, re, sys, textwrap, urllib.request

LOGIN = os.environ.get("GH_LOGIN", "A7m721")
TOKEN = os.environ.get("GH_TOKEN", "")
README = os.environ.get("README_PATH", "README.md")
HERE = os.path.dirname(os.path.abspath(__file__))
START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"

FIELDS = "name url description homepageUrl stargazerCount forkCount primaryLanguage{name color}"
Q_PINNED = "query($l:String!){user(login:$l){pinnedItems(first:6,types:REPOSITORY){nodes{... on Repository{%s}}}}}" % FIELDS
Q_RECENT = ("query($l:String!){user(login:$l){repositories(first:12,privacy:PUBLIC,isFork:false,"
            "orderBy:{field:PUSHED_AT,direction:DESC}){nodes{%s}}}}" % FIELDS)


def gql(q):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"l": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-projects"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    if "errors" in d:
        raise RuntimeError(d["errors"])
    return d["data"]["user"]


def fetch():
    repos = gql(Q_PINNED)["pinnedItems"]["nodes"]
    if not repos:
        repos = [r for r in gql(Q_RECENT)["repositories"]["nodes"] if r["name"].lower() != LOGIN.lower()][:6]
    return repos


def read_fonts():
    for base in (os.path.dirname(os.path.abspath(README)), HERE, "."):
        p = os.path.join(base, "fonts.css")
        if os.path.exists(p):
            return open(p, encoding="utf-8").read()
    return ""


def slug(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "-", name).lower()


def card(r, i, fonts):
    e = html.escape
    W, H = 520, 196
    name = r["name"]
    desc = (r.get("description") or "No description yet. Add one from the repo About.").strip()
    lines = textwrap.wrap(desc, 50)[:2]
    if len(textwrap.wrap(desc, 50)) > 2:
        lines[1] = lines[1].rstrip(".,; ")[:47] + "..."
    lang = r.get("primaryLanguage") or {}
    lcol = lang.get("color") or "#5eead4"
    meta = f'<circle cx="34" cy="168" r="5" fill="{e(lcol)}"/><text x="46" y="172" class="jb" font-size="11" fill="#c9d1e0">{e(lang.get("name", "Code"))}</text>'
    x = 46 + len(lang.get("name", "Code")) * 7 + 22
    meta += f'<text x="{x}" y="172" class="jb" font-size="11" fill="#8a93a8">★ {r["stargazerCount"]}</text>'
    x += 44
    if r.get("forkCount"):
        meta += f'<text x="{x}" y="172" class="jb" font-size="11" fill="#8a93a8">⑂ {r["forkCount"]}</text>'
    live = ""
    if r.get("homepageUrl"):
        live = ('<g class="fl"><rect x="414" y="152" width="86" height="26" rx="13" fill="#2dd4bf" fill-opacity=".12" stroke="#2dd4bf" stroke-opacity=".6"/>'
                '<circle cx="432" cy="165" r="3.5" fill="#2dd4bf"/><text x="443" y="169" class="jb" font-weight="700" font-size="10" fill="#2dd4bf" letter-spacing="1.4">LIVE ↗</text></g>')
    desc_svg = "".join(f'<text x="30" y="{122 + k*20}" class="sg" font-size="14" fill="#9aa3b8">{e(t)}</text>' for k, t in enumerate(lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs><style>{fonts}
.sg{{font-family:'SG','Segoe UI',Helvetica,Arial,sans-serif;font-weight:500}}
.jb{{font-family:'JB',Consolas,'Courier New',monospace}}
.fl{{animation:pl 2s ease-in-out infinite}}
@keyframes pl{{0%,100%{{opacity:1}}50%{{opacity:.55}}}}
</style>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#08111a"/><stop offset="1" stop-color="#0d1824"/></linearGradient>
<linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2dd4bf" stop-opacity=".7"/><stop offset=".5" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#a78bfa" stop-opacity=".75"/></linearGradient>
<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".09"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<linearGradient id="nm" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5eead4"/><stop offset="1" stop-color="#a78bfa"/></linearGradient>
<clipPath id="cc"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="18"/></clipPath></defs>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="18" fill="url(#bg)" stroke="url(#bd)" stroke-width="1.6"/>
<g clip-path="url(#cc)">
<line x1="0" y1="38" x2="{W}" y2="38" stroke="#fff" stroke-opacity=".07"/>
<circle cx="24" cy="19" r="5" fill="#ff5f56"/><circle cx="42" cy="19" r="5" fill="#ffbd2e"/><circle cx="60" cy="19" r="5" fill="#27c93f"/>
<text x="{W-24}" y="23" text-anchor="end" class="jb" font-size="10" fill="#6d7488" letter-spacing="1.6">~/projects/{e(slug(name))}</text>
<text x="30" y="66" class="jb" font-weight="700" font-size="10" fill="#2dd4bf" letter-spacing="2.6">// PROJECT {i+1:02d}</text>
<text x="30" y="98" class="sg" font-weight="700" font-size="25" fill="url(#nm)">{e(name)}</text>
{desc_svg}
{meta}{live}
<rect x="-160" y="0" width="120" height="{H}" fill="url(#shine)" transform="skewX(-18)"><animate attributeName="x" values="-160;640;640" keyTimes="0;.45;1" dur="7s" begin="{i*1.3:.1f}s" repeatCount="indefinite"/></rect>
</g></svg>'''


def main():
    if os.environ.get("MOCK"):
        repos = [dict(name="Enginer-ahmed", url="https://github.com/A7m721/Enginer-ahmed", description="My personal portfolio website, ranked #1 on Google",
                      homepageUrl="https://enginer-ahmed.vercel.app/", stargazerCount=0, forkCount=0, primaryLanguage={"name": "HTML", "color": "#e34c26"}),
                 dict(name="darstore", url="https://github.com/A7m721/darstore", description=None, homepageUrl=None,
                      stargazerCount=3, forkCount=1, primaryLanguage={"name": "JavaScript", "color": "#f1e05a"})]
    elif not TOKEN:
        sys.exit("GH_TOKEN is missing")
    else:
        repos = fetch()
    base = os.path.dirname(os.path.abspath(README))
    out = os.path.join(base, "projects")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):  # drop cards of repos that are no longer pinned
        if f.endswith(".svg"):
            os.remove(os.path.join(out, f))
    fonts = read_fonts()
    imgs = []
    for i, r in enumerate(repos):
        s = slug(r["name"])
        with open(os.path.join(out, s + ".svg"), "w", encoding="utf-8") as f:
            f.write(card(r, i, fonts))
        imgs.append(f'<a href="{html.escape(r["url"])}"><img src="projects/{s}.svg" width="49%" alt="{html.escape(r["name"])}"/></a>')
    block = f"{START}\n" + ("\n".join(imgs) if imgs else "<sub>Pin your best repos on your profile and they will show up here.</sub>") + f"\n{END}"
    text = open(README, encoding="utf-8").read()
    if START not in text or END not in text:
        sys.exit("PROJECTS markers not found in README.md")
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, text, flags=re.S)
    open(README, "w", encoding="utf-8").write(new)
    print("projects:", [r["name"] for r in repos])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import html, json, os, re, sys, urllib.request

LOGIN = os.environ.get("GH_LOGIN", "A7m721")
TOKEN = os.environ.get("GH_TOKEN", "")
README = os.environ.get("README_PATH", "README.md")
START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"

FIELDS = "name url description homepageUrl stargazerCount forkCount primaryLanguage{name}"
Q_PINNED = "query($l:String!){user(login:$l){pinnedItems(first:6,types:REPOSITORY){nodes{... on Repository{%s}}}}}" % FIELDS
Q_RECENT = ("query($l:String!){user(login:$l){repositories(first:12,privacy:PUBLIC,isFork:false,"
            "orderBy:{field:PUSHED_AT,direction:DESC}){nodes{%s}}}}" % FIELDS)


def gql(q):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
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


def cell(r):
    e = html.escape
    desc = e(r["description"]) if r.get("description") else "<i>No description yet</i>"
    meta = []
    if r.get("primaryLanguage"):
        meta.append("● " + e(r["primaryLanguage"]["name"]))
    meta.append(f"★ {r['stargazerCount']}")
    if r.get("forkCount"):
        meta.append(f"⑂ {r['forkCount']}")
    if r.get("homepageUrl"):
        meta.append(f'🌐 <a href="{e(r["homepageUrl"])}">Live</a>')
    return (f'<td width="50%" valign="top" align="left">\n'
            f'<a href="{e(r["url"])}"><b>{e(r["name"])}</b></a><br>\n{desc}<br>\n'
            f'<sub>{" · ".join(meta)}</sub>\n</td>')


def table(repos):
    rows = []
    for i in range(0, len(repos), 2):
        pair = repos[i:i + 2]
        cells = "\n".join(cell(r) for r in pair)
        if len(pair) == 1:
            cells += '\n<td width="50%"></td>'
        rows.append(f"<tr>\n{cells}\n</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def main():
    if not TOKEN:
        sys.exit("GH_TOKEN is missing")
    repos = fetch()
    text = open(README, encoding="utf-8").read()
    if START not in text or END not in text:
        sys.exit("PROJECTS markers not found in README.md")
    block = f"{START}\n{table(repos)}\n{END}" if repos else f"{START}\n<sub>Pin your best repos on your profile and they will show up here.</sub>\n{END}"
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, text, flags=re.S)
    open(README, "w", encoding="utf-8").write(new)
    print("projects:", [r["name"] for r in repos])


if __name__ == "__main__":
    main()

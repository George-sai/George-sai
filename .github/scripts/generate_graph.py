"""Generate ContributionGraph.svg (last 31 days of contributions) for a GitHub profile.

Env vars:
  GITHUB_TOKEN  token used for the GraphQL API (Actions provides one automatically)
  GH_USER       GitHub username
  GRAPH_TITLE   optional title (default: "<user>'s Contribution Graph")
  OUT           optional output path (default: ContributionGraph.svg)
Run with --demo to render sample data, or --empty to render a flat zero graph.
"""
import json, math, os, sys, urllib.request
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

DAYS = 31
USER = os.environ.get("GH_USER", "george-sai")
TITLE = os.environ.get("GRAPH_TITLE", f"{USER}'s Contribution Graph")
OUT = os.environ.get("OUT", "ContributionGraph.svg")

def fetch_counts():
    token = os.environ["GITHUB_TOKEN"]
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS + 1)
    query = """query($login:String!,$from:DateTime!,$to:DateTime!){
      user(login:$login){contributionsCollection(from:$from,to:$to){
        contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    body = json.dumps({"query": query, "variables": {
        "login": USER, "from": start.isoformat(), "to": end.isoformat()}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": "contribution-graph"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {d["date"]: d["contributionCount"] for w in weeks for d in w["contributionDays"]}

def last_days(counts):
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(DAYS - 1, -1, -1)]
    return [(d, counts.get(d.isoformat(), 0)) for d in days]

def build_svg(series):
    W, H = 900, 330
    L, R, T, B = 70, 25, 60, 55
    pw, ph = W - L - R, H - T - B
    peak = max(c for _, c in series)
    ymax = max(3, peak)
    step = 1 if ymax <= 5 else math.ceil(ymax / 5)
    ymax = math.ceil(ymax / step) * step
    x = lambda i: L + pw * i / (len(series) - 1)
    y = lambda v: T + ph - ph * v / ymax

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif">',
           '<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1">'
           '<stop offset="0" stop-color="#4A7AB0" stop-opacity="0.55"/>'
           '<stop offset="1" stop-color="#4A7AB0" stop-opacity="0.02"/></linearGradient></defs>',
           f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" fill="#0A1128" stroke="#4A7AB0" stroke-width="1"/>',
           f'<text x="{W/2}" y="30" text-anchor="middle" font-size="16" font-weight="600" fill="#CFE0FF">{escape(TITLE)}</text>']
    for v in range(0, ymax + 1, step):
        out.append(f'<line x1="{L}" y1="{y(v):.1f}" x2="{W-R}" y2="{y(v):.1f}" stroke="#1B2A52" stroke-width="1"/>')
        out.append(f'<text x="{L-10}" y="{y(v)+4:.1f}" text-anchor="end" font-size="12" fill="#9DB6DD">{v}</text>')
    for i, (d, _) in enumerate(series):
        out.append(f'<line x1="{x(i):.1f}" y1="{T}" x2="{x(i):.1f}" y2="{T+ph}" stroke="#16224A" stroke-width="1"/>')
        out.append(f'<text x="{x(i):.1f}" y="{T+ph+18}" text-anchor="middle" font-size="11" fill="#9DB6DD">{d.day}</text>')
    pts = " ".join(f"{x(i):.1f},{y(c):.1f}" for i, (_, c) in enumerate(series))
    out.append(f'<polygon points="{L},{T+ph} {pts} {x(len(series)-1):.1f},{T+ph}" fill="url(#area)"/>')
    out.append(f'<polyline points="{pts}" fill="none" stroke="#8FB4E8" stroke-width="2.5" stroke-linejoin="round"/>')
    for i, (d, c) in enumerate(series):
        out.append(f'<circle cx="{x(i):.1f}" cy="{y(c):.1f}" r="3.2" fill="#FFFFFF"><title>{d.isoformat()}: {c}</title></circle>')
    out.append(f'<text x="{L+pw/2}" y="{H-12}" text-anchor="middle" font-size="12" fill="#CFE0FF">Days</text>')
    out.append(f'<text transform="translate(18 {T+ph/2}) rotate(-90)" text-anchor="middle" font-size="12" fill="#CFE0FF">Contributions</text>')
    out.append("</svg>")
    return "\n".join(out)

if __name__ == "__main__":
    if "--demo" in sys.argv:
        sample = [0,0,0,1,0,0,2,0,0,0,1,3,0,0,0,0,4,0,1,0,0,2,0,0,5,1,0,0,2,0,3]
        today = datetime.now(timezone.utc).date()
        series = [(today - timedelta(days=DAYS-1-i), sample[i]) for i in range(DAYS)]
    elif "--empty" in sys.argv:
        series = last_days({})
    else:
        series = last_days(fetch_counts())
    open(OUT, "w", encoding="utf-8").write(build_svg(series))
    print(f"wrote {OUT}")

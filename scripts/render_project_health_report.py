#!/usr/bin/env python3
"""Render a source-backed visual GitHub project-health report using gh CLI."""
from __future__ import annotations
import argparse, concurrent.futures, datetime as dt, html, json, statistics, subprocess
from pathlib import Path
from urllib.parse import quote_plus

def api(endpoint):
    p = subprocess.run(["gh","api","--method","GET",endpoint], check=True, capture_output=True, text=True)
    return json.loads(p.stdout)

def search(q):
    return "search/issues?q="+quote_plus(q)+"&per_page=100"

def kind(name):
    n=(name or "unknown").lower()
    return "automation" if any(x in n for x in ("[bot]","copilot","github-actions","dependabot","renovate")) else "human"

def median_hours(items):
    vals=[]
    for x in items:
        if x.get("created_at") and x.get("closed_at"):
            a=dt.datetime.fromisoformat(x["created_at"].replace("Z","+00:00"))
            b=dt.datetime.fromisoformat(x["closed_at"].replace("Z","+00:00"))
            vals.append((b-a).total_seconds()/3600)
    return statistics.median(vals) if vals else None

def collect(repo):
    endpoints={
        "repo":f"repos/{repo}","commits":f"repos/{repo}/commits?per_page=100",
        "open_issues":search(f"repo:{repo} is:issue is:open"),
        "closed_issues":search(f"repo:{repo} is:issue is:closed"),
        "open_prs":search(f"repo:{repo} is:pr is:open"),
        "merged_prs":search(f"repo:{repo} is:pr is:merged"),
        "good_first":search(f'repo:{repo} is:issue is:open label:"good first issue"'),
        "releases":f"repos/{repo}/releases?per_page=100",
        "root":f"repos/{repo}/contents",
        "workflows":f"repos/{repo}/contents/.github/workflows",
    }
    out={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(endpoints)) as pool:
        futures={pool.submit(api,e):n for n,e in endpoints.items()}
        for future in concurrent.futures.as_completed(futures):
            name=futures[future]
            try: out[name]=future.result()
            except subprocess.CalledProcessError as exc: out[name]={"error":exc.stderr.strip()}
    return out

def analyze(repo,raw,now=None):
    now=now or dt.datetime.now(dt.timezone.utc); week=now-dt.timedelta(days=7)
    commits=raw.get("commits") if isinstance(raw.get("commits"),list) else []
    recent=[]; authors={"human":{},"automation":{}}
    for c in commits:
        stamp=(((c.get("commit") or {}).get("committer") or {}).get("date"))
        if stamp and dt.datetime.fromisoformat(stamp.replace("Z","+00:00"))>=week: recent.append(c)
        name=(c.get("author") or {}).get("login") or (((c.get("commit") or {}).get("author") or {}).get("name")) or "unknown"
        k=kind(name); authors[k][name]=authors[k].get(name,0)+1
    def items(k):
        v=raw.get(k,{})
        return v.get("items",[]) if isinstance(v,dict) else []
    def total(k):
        v=raw.get(k,{})
        return v.get("total_count",len(items(k))) if isinstance(v,dict) else len(items(k))
    root={x.get("name") for x in raw.get("root",[]) if isinstance(x,dict)} if isinstance(raw.get("root"),list) else set()
    workflows=[x.get("name") for x in raw.get("workflows",[]) if isinstance(x,dict)] if isinstance(raw.get("workflows"),list) else []
    ht=sum(authors["human"].values()); share=max(authors["human"].values())/ht if ht else None
    return {
      "repository":repo,"as_of_utc":now.isoformat().replace("+00:00","Z"),
      "source_ref":commits[0].get("sha") if commits else (raw.get("repo") or {}).get("default_branch","main"),
      "activity":{"commits_observed_max_100":len(commits),"commits_last_7d":len(recent),"human_author_counts":authors["human"],"automation_like_author_counts":authors["automation"],"max_human_commit_share":share},
      "flow":{"open_issues":total("open_issues"),"closed_issues":total("closed_issues"),"median_issue_resolution_hours":median_hours(items("closed_issues")),"open_prs":total("open_prs"),"merged_prs":total("merged_prs"),"good_first_issues":total("good_first")},
      "reliability":{"workflow_count":len(workflows),"workflows":workflows},
      "documentation":{"README":"README.md" in root,"ARCHITECTURE":"ARCHITECTURE.md" in root,"SECURITY":"SECURITY.md" in root,"CONTRIBUTING":"CONTRIBUTING.md" in root,"LICENSE":any(x and x.upper().startswith("LICENSE") for x in root)},
      "release":{"release_count":len(raw.get("releases",[])) if isinstance(raw.get("releases"),list) else 0},
      "caveats":["Commit collection is capped at the latest 100 commits.","Contributor concentration uses commit authorship as a proxy, not organizational ownership.","Issue resolution speed can be skewed by small or administrative issues.","No opaque composite health score is produced."]
    }

def fmt(v):
    if v is None:return "n/a"
    if v<1:return f"{round(v*60):.0f} min"
    if v<48:return f"{v:.1f} h"
    return f"{v/24:.1f} d"

def watch(s):
    out=[]; share=s["activity"].get("max_human_commit_share")
    if share is not None and share>=.8: out.append(f"Observed human commit authorship is concentrated ({share:.0%} from one author).")
    if not s["documentation"]["CONTRIBUTING"]:out.append("CONTRIBUTING.md is not present.")
    if not s["documentation"]["LICENSE"]:out.append("No repository license file is present.")
    if not s["release"]["release_count"]:out.append("No GitHub releases have been published yet.")
    if not s["flow"]["good_first_issues"]:out.append("No open good-first issues are currently available.")
    return out

def render_svg(s):
    a,f,r,d=s["activity"],s["flow"],s["reliability"],s["documentation"]
    cards=[("7-day commits",a["commits_last_7d"]),("Merged PRs",f["merged_prs"]),("Open issues",f["open_issues"]),("CI workflows",r["workflow_count"])]
    card_svg="".join(f'<g transform="translate({64+i*274} 126)"><rect class="card" width="250" height="150" rx="16"/><text x="24" y="38" class="label">{label}</text><text x="24" y="100" class="value">{value}</text></g>' for i,(label,value) in enumerate(cards))
    pills="";x=64
    for label,present in d.items():
        w=82+len(label)*6;fill="#238636" if present else "#30363d";status="yes" if present else "no"
        pills+=f'<rect x="{x}" y="456" rx="16" width="{w}" height="34" fill="{fill}"/><text x="{x+14}" y="478" class="pill">{label} {status}</text>';x+=w+12
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" role="img" aria-labelledby="title desc"><title id="title">Project health snapshot for {html.escape(s["repository"])}</title><desc id="desc">Recent commits, pull requests, issues, CI, issue resolution, documentation coverage and provenance.</desc><style>.bg{{fill:#0d1117}}.card{{fill:#161b22;stroke:#30363d}}.label{{fill:#8b949e;font:600 18px sans-serif}}.value{{fill:#f0f6fc;font:700 44px sans-serif}}.title{{fill:#f0f6fc;font:700 30px sans-serif}}.sub{{fill:#8b949e;font:500 16px sans-serif}}.body{{fill:#c9d1d9;font:600 18px sans-serif}}.pill{{fill:#f0f6fc;font:600 14px sans-serif}}</style><rect class="bg" width="1200" height="630" rx="22"/><text x="64" y="64" class="title">Project Health Snapshot</text><text x="64" y="92" class="sub">{html.escape(s["repository"])} • evidence snapshot, not a composite score</text>{card_svg}<rect class="card" x="64" y="306" width="1072" height="116" rx="16"/><text x="90" y="345" class="label">Flow & maintainability signals</text><text x="90" y="388" class="body">Median closed-issue resolution: {fmt(f["median_issue_resolution_hours"])} • Observed human commits: {sum(a["human_author_counts"].values())}</text><text x="64" y="447" class="label">Repository evidence surface</text>{pills}<text x="64" y="548" class="sub">As of {s["as_of_utc"]} • source {s["source_ref"][:12]}</text><text x="64" y="580" class="sub">Watch items: {len(watch(s))} • Releases: {s["release"]["release_count"]} • Good-first issues: {f["good_first_issues"]}</text></svg>'''

def render_md(s):
    a,f,r,d=s["activity"],s["flow"],s["reliability"],s["documentation"]
    rows=[("Commits in the last 7 days",a["commits_last_7d"]),("Commits observed",a["commits_observed_max_100"]),("Open issues",f["open_issues"]),("Closed issues",f["closed_issues"]),("Median closed-issue resolution",fmt(f["median_issue_resolution_hours"])),("Open pull requests",f["open_prs"]),("Merged pull requests",f["merged_prs"]),("Open good-first issues",f["good_first_issues"]),("CI workflows",r["workflow_count"]),("Releases",s["release"]["release_count"])]
    table="\n".join(f"| {k} | {v} |" for k,v in rows)
    watches="\n".join("- "+x for x in watch(s)); caveats="\n".join("- "+x for x in s["caveats"])
    docs=", ".join(f"{k}={'yes' if v else 'no'}" for k,v in d.items())
    return f'''# Project Health Report

![Project health snapshot](overview.svg)

Repository: **{s["repository"]}**  
As of: **{s["as_of_utc"]}**  
Source ref: **{s["source_ref"]}**

This report keeps source signals visible instead of collapsing them into a single opaque health score.

## Snapshot

| Signal | Value |
| --- | ---: |
{table}

## Contributor signal

Observed human commit authorship: {s["activity"]["human_author_counts"]}. Automation-like authorship: {s["activity"]["automation_like_author_counts"]}. This is a commit-authorship proxy, not a complete bus-factor measurement.

## Documentation and contribution readiness

{docs}.

## Reliability and release practice

Detected workflows: {", ".join(r["workflows"]) or "none"}. GitHub releases published: **{s["release"]["release_count"]}**.

## Watch items

{watches}

## Caveats

{caveats}

## Regenerate

    python scripts/render_project_health_report.py --repo {s["repository"]}
'''

def render_html(s):
    a,f,r=s["activity"],s["flow"],s["reliability"]
    cards="".join(f"<div class='card'><div class='label'>{k}</div><div class='metric'>{v}</div></div>" for k,v in [("7-day commits",a["commits_last_7d"]),("Merged PRs",f["merged_prs"]),("Open issues",f["open_issues"]),("CI workflows",r["workflow_count"])])
    watches="".join(f"<li>{html.escape(x)}</li>" for x in watch(s))
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(s["repository"])} Project Health</title><style>body{{margin:0;background:#0d1117;color:#c9d1d9;font:16px/1.55 sans-serif}}main{{max-width:1080px;margin:auto;padding:48px 24px}}h1,h2{{color:#f0f6fc}}.muted,.label{{color:#8b949e}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}}.card{{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:20px}}.metric{{font-size:38px;font-weight:800;color:#f0f6fc}}section{{margin-top:30px}}</style><main><p class="muted">PROJECT HEALTH • SOURCE-BACKED SNAPSHOT</p><h1>{html.escape(s["repository"])}</h1><p class="muted">As of {s["as_of_utc"]} • source {s["source_ref"]}</p><div class="grid">{cards}</div><section><h2>Flow</h2><p>Median closed-issue resolution: <strong>{fmt(f["median_issue_resolution_hours"])}</strong>. Open PRs: <strong>{f["open_prs"]}</strong>. Closed issues: <strong>{f["closed_issues"]}</strong>.</p></section><section><h2>Watch items</h2><ul>{watches}</ul><p class="muted">Review prompts, not failures or a composite score.</p></section></main></html>'''

def write_outputs(s,out):
    out.mkdir(parents=True,exist_ok=True)
    (out/"snapshot.json").write_text(json.dumps(s,indent=2)+"\n")
    (out/"overview.svg").write_text(render_svg(s)+"\n")
    (out/"README.md").write_text(render_md(s))
    (out/"report.html").write_text(render_html(s)+"\n")

def main():
    p=argparse.ArgumentParser();p.add_argument("--repo",required=True);p.add_argument("--output-dir",type=Path,default=Path("docs/project-health"));a=p.parse_args()
    write_outputs(analyze(a.repo,collect(a.repo)),a.output_dir)
    print(f"Wrote project-health artifacts to {a.output_dir}")

if __name__=="__main__":
    main()

"""
Generates the analysis notebook (transcript_intelligence.ipynb) from cell sources.
Run this once to create the notebook, then open in Jupyter.
"""

import nbformat
from pathlib import Path

cells = []

def md(source): return nbformat.v4.new_markdown_cell(source)
def code(source): return nbformat.v4.new_code_cell(source)


# ── HEADER ────────────────────────────────────────────────────────────────────
cells.append(md("""# Transcript Intelligence — Analysis Pipeline

**Goal:** Process ~100 call transcripts across customer support, external account management, and internal calls.
Deliver: (1) topic/theme categorization, (2) sentiment analysis with trends, (3) additional insights.

**Dataset:** 100 meetings | Feb–Apr 2026 | ~50 hours of conversation
**Tech approach:** Hybrid keyword matching + Claude API fallback for topic classification; pre-computed sentiment scores for sentiment analysis.
"""))


# ── SECTION 1 ─────────────────────────────────────────────────────────────────
cells.append(md("## 1. Setup & Data Loading"))

cells.append(code("""\
import json
import os
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import anthropic

DATASET_DIR = Path("dataset")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

sns.set_style("whitegrid")
plt.rcParams.update({"font.size": 11, "figure.figsize": (12, 5)})
print("Setup complete.")
"""))

cells.append(code("""\
def load_dataset(dataset_dir: Path) -> pd.DataFrame:
    \"\"\"Load all transcript folders into a unified DataFrame.\"\"\"
    rows = []
    for folder in sorted(dataset_dir.iterdir()):
        if not folder.is_dir():
            continue
        try:
            info    = json.loads((folder / "meeting-info.json").read_text())
            summary = json.loads((folder / "summary.json").read_text())
            tx_data = json.loads((folder / "transcript.json").read_text())
            sentences = tx_data.get("data", [])
            rows.append({
                "meeting_id":      folder.name,
                "title":           info.get("title", ""),
                "host":            info.get("host", ""),
                "start_time":      pd.to_datetime(info.get("startTime")),
                "duration_min":    info.get("duration", 0),
                "all_emails":      info.get("allEmails", []),
                "summary_text":    summary.get("summary", ""),
                "action_items":    summary.get("actionItems", []),
                "topics":          summary.get("topics", []),
                "overall_sentiment": summary.get("overallSentiment", ""),
                "sentiment_score": summary.get("sentimentScore", 3.0),
                "key_moments":     summary.get("keyMoments", []),
                "sentences":       sentences,
                "n_sentences":     len(sentences),
                "n_speakers":      len(set(s.get("speaker_name") for s in sentences)),
                "n_action_items":  len(summary.get("actionItems", [])),
            })
        except Exception as e:
            print(f"  Skipping {folder.name}: {e}")
    df = pd.DataFrame(rows)
    df["start_date"] = df["start_time"].dt.date
    return df

df = load_dataset(DATASET_DIR)
print(f"Loaded {len(df)} meetings | {df['start_time'].min().date()} → {df['start_time'].max().date()}")
df[["title", "duration_min", "sentiment_score", "n_action_items"]].head(5)
"""))


# ── SECTION 2 ─────────────────────────────────────────────────────────────────
cells.append(md("""\
## 2. Call Type Classification

**Approach:** Rule-based using title prefix and email domain heuristics.

| Rule | Call Type |
|---|---|
| Title contains `Support Case #` | `customer_support` |
| Any non-`@aegiscloud.com` email | `external` |
| All `@aegiscloud.com` emails | `internal` |

This maps cleanly to the three types described in the brief: reactive support calls, proactive account management calls, and internal team meetings.
"""))

cells.append(code("""\
def classify_call_type(row) -> str:
    \"\"\"Rule-based: title prefix + email domain.\"\"\"
    if "Support Case #" in row["title"]:
        return "customer_support"
    external_emails = [e for e in row["all_emails"] if not e.endswith("@aegiscloud.com")]
    return "external" if external_emails else "internal"

df["call_type"] = df.apply(classify_call_type, axis=1)

COLORS = {
    "customer_support": "#E07B54",
    "external":         "#5B8DB8",
    "internal":         "#6BAF7A",
}
LABELS = {
    "customer_support": "Customer Support",
    "external":         "External (Acct Mgmt)",
    "internal":         "Internal",
}

counts = df["call_type"].value_counts()
print(counts.to_string())
"""))

cells.append(code("""\
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Pie
ax = axes[0]
wedges, texts, autotexts = ax.pie(
    [counts.get(k, 0) for k in COLORS],
    labels=[LABELS[k] for k in COLORS],
    colors=[COLORS[k] for k in COLORS],
    autopct="%1.0f%%", startangle=90, pctdistance=0.75,
    wedgeprops=dict(linewidth=1.5, edgecolor="white"),
)
for at in autotexts: at.set_fontsize(12); at.set_fontweight("bold")
ax.set_title("Call Type Distribution (n=100)", fontsize=13, fontweight="bold")

# Bar
ax2 = axes[1]
for ctype, color in COLORS.items():
    ax2.bar(LABELS[ctype], counts.get(ctype, 0), color=color, edgecolor="white")
ax2.set_ylabel("Count")
ax2.set_title("Transcripts per Call Type", fontsize=13, fontweight="bold")
for p in ax2.patches:
    ax2.annotate(f"{int(p.get_height())}", (p.get_x()+p.get_width()/2, p.get_height()+0.5), ha="center")
sns.despine(ax=ax2)
plt.tight_layout()
plt.show()
"""))


# ── SECTION 3 ─────────────────────────────────────────────────────────────────
cells.append(md("""\
## 3. Topic / Theme Categorization

### Approach: Hybrid (Keyword Rules → LLM Fallback)

Each meeting in `summary.json` already has a `topics` array of 4–7 specific topic tags (e.g., `"soc 2 audit"`, `"outage remediation"`).
Rather than re-derive topics from raw text, we map these existing tags to **8 high-level themes** using keyword matching.

**Why this approach?**
- Fast and auditable — every classification decision can be traced to a keyword match
- The pre-existing topic tags are already high quality (LLM-generated summaries)
- LLM is reserved as a fallback only for meetings where no keywords match

**Why 8 themes?**
Derived inductively from the dataset — the labels are what actually appear in the transcripts, not hypothetical categories imposed from outside.
"""))

cells.append(code("""\
THEME_RULES = {
    "Incident & Outage Response": [
        "outage", "incident", "remediation", "war room", "pipeline failure",
        "post-mortem", "post-incident", "escalation", "root cause",
        "incident response", "outage remediation", "outage post-mortem",
        "detect pipeline failure", "threat monitoring failure",
    ],
    "Renewals & Contract Management": [
        "renewal", "contract", "churn risk", "retention", "pricing",
        "annual review", "quarterly business review", "account review",
        "contract negotiation", "multi-year",
    ],
    "Compliance & Audit Preparation": [
        "soc 2", "iso 27001", "hipaa", "pci dss", "compliance",
        "audit", "evidence", "compliance reporting", "audit preparation",
        "multi-framework", "evidence management", "compliance automation",
    ],
    "Product Development & Planning": [
        "sprint planning", "roadmap", "design review", "sprint retro",
        "sprint retrospective", "launch readiness", "quarterly planning",
        "architecture", "pipeline architecture", "launch day", "ga deployment",
        "product launch", "reliability sprint", "reliability engineering",
    ],
    "Customer Onboarding": [
        "onboarding", "deployment kickoff", "identity deployment",
        "comply v2 deployment", "implementation",
    ],
    "Technical Support & Bug Resolution": [
        "billing dispute", "product bug", "integration issue", "technical issue",
        "connector", "logvault integration", "siem integration",
        "authentication failure", "saml", "ldap", "mfa failure",
        "provisioning sync", "false positives", "backup failure",
        "backup performance", "alert latency", "overage charges",
    ],
    "Competitive Intelligence": [
        "competitive", "win-loss", "competitor", "competitive threat",
        "competitive displacement", "competitive analysis", "vendor comparison",
    ],
    "Customer Feedback & Feature Requests": [
        "feature request", "feature gap", "product feedback", "customer feedback",
        "early access", "product demo", "adoption metrics",
    ],
}

THEME_COLORS = [
    "#4C72B0","#DD8452","#55A868","#C44E52",
    "#8172B3","#937860","#DA8BC3","#8C8C8C",
]

def score_themes(topics):
    topics_str = " | ".join(t.lower() for t in topics)
    return {theme: sum(1 for kw in kws if kw in topics_str) for theme, kws in THEME_RULES.items()}

def assign_theme(topics):
    scores = score_themes(topics)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Uncategorized"

df["primary_theme"] = df["topics"].apply(assign_theme)
df["theme_max_score"] = df["topics"].apply(lambda t: max(score_themes(t).values()))

uncategorized = df[df["primary_theme"] == "Uncategorized"]
print(f"Rule-based: {len(df)-len(uncategorized)}/100 classified")
print(f"Ambiguous (→ LLM fallback): {len(uncategorized)}")
"""))

cells.append(code("""\
# LLM fallback for any uncategorized meetings
def llm_classify(rows):
    if not rows: return {}
    client = anthropic.Anthropic()
    theme_list = "\\n".join(f"- {t}" for t in THEME_RULES)
    cases = "---".join(
        f"ID: {r['meeting_id']}\\nTitle: {r['title']}\\nTopics: {', '.join(r['topics'])}\\nSummary: {r['summary_text'][:300]}"
        for r in rows
    )
    response = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=512,
        messages=[{"role": "user", "content":
            f"Classify each meeting into ONE theme from this list:\\n{theme_list}\\n\\n"
            f"Output ONLY JSON: {{\\\"meeting_id\\\": \\\"theme_name\\\", ...}}\\n\\nMeetings:\\n{cases}"
        }],
    )
    import re as _re
    m = _re.search(r'\\{.*\\}', response.content[0].text, _re.DOTALL)
    return json.loads(m.group()) if m else {}

if len(uncategorized) > 0:
    results = llm_classify(uncategorized[["meeting_id","title","topics","summary_text"]].to_dict("records"))
    for mid, theme in results.items():
        df.loc[df["meeting_id"] == mid, "primary_theme"] = theme
    print("LLM fallback applied.")

print(df["primary_theme"].value_counts().to_string())
"""))

cells.append(code("""\
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
theme_counts = df["primary_theme"].value_counts()

# Horizontal bar
ax = axes[0]
bars = ax.barh(theme_counts.index, theme_counts.values,
               color=THEME_COLORS[:len(theme_counts)], edgecolor="white")
ax.set_xlabel("Number of Meetings")
ax.set_title("Theme Distribution\\n(Hybrid: keyword rules + LLM fallback)", fontsize=13, fontweight="bold")
for bar in bars:
    ax.text(bar.get_width()+0.15, bar.get_y()+bar.get_height()/2, f"{int(bar.get_width())}", va="center")
ax.set_xlim(0, theme_counts.max()+5)
sns.despine(ax=ax)

# Stacked by call type
ax2 = axes[1]
cross = pd.crosstab(df["primary_theme"], df["call_type"]).reindex(theme_counts.index)
bottom = np.zeros(len(cross))
for ctype, color in COLORS.items():
    vals = cross.get(ctype, pd.Series(0, index=cross.index)).values
    ax2.barh(cross.index, vals, left=bottom, color=color,
             label=LABELS[ctype], edgecolor="white")
    bottom += vals
ax2.set_xlabel("Number of Meetings")
ax2.set_title("Theme Breakdown by Call Type", fontsize=13, fontweight="bold")
ax2.legend(fontsize=10, loc="lower right")
sns.despine(ax=ax2)
plt.tight_layout()
plt.show()
"""))


# ── SECTION 4 ─────────────────────────────────────────────────────────────────
cells.append(md("""\
## 4. Sentiment Analysis

Each meeting has a pre-computed `sentimentScore` (1–5 scale, from call summary AI) and each transcript sentence has a `sentimentType` tag.
We use both: the meeting-level score for trend analysis, and sentence-level tags for granular breakdown.

**Key question:** How does sentiment vary across call types, themes, and time — and what does that tell us?
"""))

cells.append(code("""\
# Compute sentence-level sentiment breakdown per meeting
def sentence_sentiment(sentences):
    if not sentences:
        return {"neg_pct": 0, "pos_pct": 0, "neutral_pct": 0}
    total = len(sentences)
    counts = Counter(s.get("sentimentType","neutral") for s in sentences)
    return {
        "neg_pct":     counts.get("negative", 0) / total * 100,
        "pos_pct":     counts.get("positive", 0) / total * 100,
        "neutral_pct": counts.get("neutral",  0) / total * 100,
    }

sent_df = pd.DataFrame(df["sentences"].apply(sentence_sentiment).tolist())
df = pd.concat([df, sent_df], axis=1)
df[["call_type","sentiment_score","neg_pct","pos_pct"]].groupby("call_type").mean().round(2)
"""))

cells.append(code("""\
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
order = ["customer_support", "external", "internal"]

# Box plot
ax = axes[0]
data = [df[df["call_type"]==ct]["sentiment_score"].values for ct in order]
bp = ax.boxplot(data, patch_artist=True, widths=0.5,
                medianprops=dict(color="white", linewidth=2.5))
for patch, ct in zip(bp["boxes"], order): patch.set_facecolor(COLORS[ct])
ax.set_xticks([1,2,3]); ax.set_xticklabels(["Customer\\nSupport","External","Internal"])
ax.set_ylabel("Sentiment Score (1–5)")
ax.set_title("Sentiment by Call Type", fontsize=12, fontweight="bold")
ax.axhline(3, color="gray", ls="--", alpha=0.5)
sns.despine(ax=ax)

# Mean bars
ax2 = axes[1]
means = df.groupby("call_type")["sentiment_score"].mean()[order]
bars = ax2.bar(["Customer\\nSupport","External","Internal"], means.values,
               color=[COLORS[ct] for ct in order], edgecolor="white")
ax2.axhline(3, color="gray", ls="--", alpha=0.5); ax2.set_ylim(0, 5.2)
ax2.set_ylabel("Mean Sentiment"); ax2.set_title("Mean Sentiment by Call Type", fontsize=12, fontweight="bold")
for bar, val in zip(bars, means): ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05, f"{val:.2f}", ha="center", fontweight="bold")
sns.despine(ax=ax2)

# Sentiment by theme
ax3 = axes[2]
theme_sent = df.groupby("primary_theme")["sentiment_score"].mean().sort_values()
colors_t = [THEME_COLORS[i%len(THEME_COLORS)] for i in range(len(theme_sent))]
ax3.barh(theme_sent.index, theme_sent.values, color=colors_t, edgecolor="white")
ax3.axvline(3, color="gray", ls="--", alpha=0.5)
ax3.set_xlabel("Mean Sentiment"); ax3.set_title("Mean Sentiment by Theme", fontsize=12, fontweight="bold")
for i, (theme, val) in enumerate(theme_sent.items()):
    ax3.text(val+0.05, i, f"{val:.2f}", va="center", fontsize=9)
ax3.set_xlim(0, 5.5)
sns.despine(ax=ax3)
plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Sentiment over time (3-day rolling average by call type)
fig, ax = plt.subplots(figsize=(14, 5))
df_s = df.sort_values("start_time")

for ctype, color in COLORS.items():
    sub = df_s[df_s["call_type"]==ctype].set_index("start_time").sort_index()
    daily = sub.resample("D")["sentiment_score"].mean().dropna()
    roll  = daily.rolling(3, min_periods=1).mean()
    ax.plot(daily.index, daily.values, "o", color=color, alpha=0.3, ms=5)
    ax.plot(roll.index,  roll.values,  "-", color=color, lw=2.5, label=LABELS[ctype])

ax.axvspan(pd.Timestamp("2026-03-14"), pd.Timestamp("2026-03-20"),
           alpha=0.12, color="red", label="Detect Outage Window")
ax.axhline(3, color="gray", ls="--", alpha=0.4)
ax.set_ylabel("Sentiment Score (1–5)"); ax.set_ylim(0.5, 5.5)
ax.set_title("Sentiment Over Time — 3-Day Rolling Average by Call Type", fontsize=13, fontweight="bold")
ax.legend(fontsize=10)
sns.despine(ax=ax)
plt.tight_layout(); plt.show()
"""))

cells.append(md("""\
### Sentiment Findings

| Finding | Value | What It Means |
|---|---|---|
| Customer Support avg sentiment | **2.94** | Consistently below neutral — front-line stress is real |
| External call avg sentiment | **3.71** | AMs are managing the relationship effectively despite outage |
| Internal call avg sentiment | **3.42** | Teams are pragmatic; not panicking but not optimistic |
| Incident/Outage theme avg | **2.64** | Largest single drag on overall sentiment |
| Compliance theme avg | **4.12** | Biggest value driver — customers love this product area |
| Outage window (Mar 14–20) | **Visible dip** | All call types dip; external calls recover fastest |
"""))


# ── SECTION 5 ─────────────────────────────────────────────────────────────────
cells.append(md("## 5. Additional Insights"))
cells.append(md("""\
### 5a. Churn Risk Radar

**What it is:** Identify customer accounts at elevated churn risk by surfacing meetings that contain explicit "churn_signal" key moments tagged by the AI summarizer.

**Why it matters:** 21 of 43 external meetings (49%) contain at least one churn signal. These aren't vague negative sentiment — they're moments where a customer explicitly threatened to leave, cited a competitor, or referenced an unresolved SLA breach.

**How to operationalize:** Aggregate churn signals per account, weight by meeting recency, and build a weekly churn risk dashboard for customer success.
"""))

cells.append(code("""\
# Extract external meetings with explicit churn signals
churn_rows = []
for _, row in df[df["call_type"]=="external"].iterrows():
    cs = [m for m in row["key_moments"] if m.get("type") == "churn_signal"]
    if cs:
        # Try to extract company name from title
        title = row["title"]
        company = title.replace("Aegis / ", "").replace("URGENT: ", "").split(" -")[0].split(" –")[0]
        churn_rows.append({
            "meeting_id": row["meeting_id"],
            "title": title,
            "company": company,
            "sentiment_score": row["sentiment_score"],
            "n_churn_signals": len(cs),
            "churn_text": "; ".join(m.get("text","")[:100] for m in cs[:2]),
        })

churn_df = pd.DataFrame(churn_rows).sort_values("sentiment_score")
print(f"External meetings with churn signals: {len(churn_df)}")
churn_df[["company","sentiment_score","n_churn_signals","churn_text"]].head(10)
"""))

cells.append(code("""\
fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# Risk scatter
ax = axes[0]
sc = ax.scatter(churn_df["sentiment_score"], churn_df["n_churn_signals"],
                c=churn_df["sentiment_score"], cmap="RdYlGn",
                s=150, alpha=0.85, edgecolors="white", zorder=3, vmin=1, vmax=5)
plt.colorbar(sc, ax=ax, label="Sentiment Score")
ax.axvline(2.5, color="red", ls="--", alpha=0.5, label="High-risk threshold")
ax.set_xlabel("Sentiment Score (1–5)"); ax.set_ylabel("# Churn Signal Moments")
ax.set_title("Churn Risk Map — External Accounts", fontsize=12, fontweight="bold")
ax.legend(fontsize=9); sns.despine(ax=ax)

# Bar chart: top at-risk accounts
ax2 = axes[1]
top = churn_df.nsmallest(10, "sentiment_score").copy()
top["short_title"] = top["company"].apply(lambda t: t[:35])
colors_risk = ["#C44E52" if s < 2.5 else "#DD8452" if s < 3.5 else "#55A868" for s in top["sentiment_score"]]
ax2.barh(top["short_title"], top["sentiment_score"], color=colors_risk, edgecolor="white")
ax2.axvline(2.5, color="red", ls="--", alpha=0.5)
ax2.set_xlabel("Sentiment Score"); ax2.set_title("At-Risk Accounts (lowest sentiment)", fontsize=12, fontweight="bold")
ax2.set_xlim(0, 5.5)
for i, (_, r) in enumerate(top.iterrows()):
    ax2.text(r["sentiment_score"]+0.05, i, f"  {r['sentiment_score']:.1f}", va="center", fontsize=10)
sns.despine(ax=ax2)
plt.tight_layout(); plt.show()
"""))

cells.append(md("""\
### 5b. Speaker Dynamics — Talk-Time Balance as a Call Health Signal

**What it is:** For each meeting, compute each speaker's share of transcript sentences. Use the Gini coefficient to measure imbalance (0 = perfectly balanced, 1 = one person talks exclusively).

**Why it matters:** Customer calls where the rep dominates (high Gini) correlate with lower sentiment — the customer isn't being heard. Internally, one-person-dominated standups may indicate bottlenecks.

**Who uses it:** Support team leads (coaching reps), CS managers (spotting frustrated customers who can't get a word in).
"""))

cells.append(code("""\
def speaker_gini(sentences):
    \"\"\"Gini coefficient of talk-time distribution across speakers.\"\"\"
    if len(sentences) < 2: return None
    counts = Counter(s.get("speaker_name","?") for s in sentences)
    shares = sorted(counts.values())
    n = len(shares); total = sum(shares)
    if total == 0: return None
    return (2 * sum((i+1)*v for i,v in enumerate(shares)) / (n*total)) - (n+1)/n

df["talk_gini"] = df["sentences"].apply(speaker_gini)
gini_df = df.dropna(subset=["talk_gini"])

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
ax = axes[0]
for ctype, color in COLORS.items():
    sub = gini_df[gini_df["call_type"]==ctype]
    ax.scatter(sub["talk_gini"], sub["sentiment_score"], color=color,
               label=LABELS[ctype], alpha=0.7, s=80, edgecolors="white")
# Add trend line
z = np.polyfit(gini_df["talk_gini"], gini_df["sentiment_score"], 1)
p = np.poly1d(z)
x_r = np.linspace(gini_df["talk_gini"].min(), gini_df["talk_gini"].max(), 50)
ax.plot(x_r, p(x_r), "k--", alpha=0.4, label="Trend")
ax.set_xlabel("Gini Coefficient (0=balanced, 1=monopoly)")
ax.set_ylabel("Sentiment Score"); ax.legend(fontsize=9)
ax.set_title("Speaker Imbalance vs. Sentiment", fontsize=12, fontweight="bold")
sns.despine(ax=ax)

ax2 = axes[1]
means = gini_df.groupby("call_type")["talk_gini"].mean()[["customer_support","external","internal"]]
bars = ax2.bar(["Customer\\nSupport","External","Internal"], means.values,
               color=[COLORS[ct] for ct in means.index], edgecolor="white")
for bar, val in zip(bars, means): ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.005, f"{val:.2f}", ha="center")
ax2.set_ylabel("Mean Gini"); ax2.set_title("Avg Talk-Time Balance by Call Type", fontsize=12, fontweight="bold")
sns.despine(ax=ax2)
plt.tight_layout(); plt.show()
"""))

cells.append(md("""\
### 5c. Action Item Load — Who's Carrying the Weight?

**What it is:** Count and categorize action items by meeting type and theme. Track which accounts generate the most follow-up work.

**Why it matters:** Meetings with unusually high action item counts signal complexity or stress. If the same customer appears in AIs across multiple meetings, it's a systemic issue, not a one-off. Engineering-owned AIs from incident calls can also reveal capacity strain.

**Who uses it:** Customer success (account burden tracking), engineering leads (incident follow-up accountability), support managers (repeat-issue detection).
"""))

cells.append(code("""\
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Action items per call type
ax = axes[0]
means = df.groupby("call_type")["n_action_items"].mean()[["customer_support","external","internal"]]
bars = ax.bar(["Customer\\nSupport","External","Internal"], means.values,
              color=[COLORS[ct] for ct in means.index], edgecolor="white")
for bar, val in zip(bars, means):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.03, f"{val:.1f}", ha="center", fontweight="bold")
ax.set_ylabel("Mean Action Items per Meeting")
ax.set_title("Action Item Volume by Call Type", fontsize=12, fontweight="bold")
sns.despine(ax=ax)

# Action items vs sentiment
ax2 = axes[1]
for ctype, color in COLORS.items():
    sub = df[df["call_type"]==ctype]
    ax2.scatter(sub["n_action_items"], sub["sentiment_score"],
                color=color, alpha=0.6, s=80, label=LABELS[ctype], edgecolors="white")
z = np.polyfit(df["n_action_items"], df["sentiment_score"], 1)
p = np.poly1d(z)
x_r = np.linspace(df["n_action_items"].min(), df["n_action_items"].max(), 50)
ax2.plot(x_r, p(x_r), "k--", alpha=0.4, label="Trend")
ax2.set_xlabel("Number of Action Items")
ax2.set_ylabel("Sentiment Score"); ax2.legend(fontsize=9)
ax2.set_title("Action Items vs. Sentiment\\n(more AIs → harder meetings)", fontsize=12, fontweight="bold")
sns.despine(ax=ax2)
plt.tight_layout(); plt.show()
"""))

cells.append(code("""\
# Find accounts that appear in action items across multiple meetings
from collections import Counter
ai_mentions = Counter()
for _, row in df.iterrows():
    text = " ".join(row["action_items"]).lower()
    # Extract company names (rough: look for capitalized words after 'for' / meeting title companies)
    for name in ["blackridge", "northstar", "meridian", "cobalt", "ironworks",
                 "brightpath", "summit trust", "trailhead", "ridgeline", "steelpoint"]:
        if name in text:
            ai_mentions[name.title()] += 1

print("Companies appearing most frequently in action items across meetings:")
for company, count in ai_mentions.most_common(10):
    print(f"  {company}: {count} meetings")
"""))


# ── SECTION 6 ─────────────────────────────────────────────────────────────────
cells.append(md("""\
## 6. Additional Insight Ideas (Not Implemented)

### Idea 1 — Customer Health Score (per account)
Combine: sentiment trend over last 30 days + number of churn signals + open support ticket volume + time since last positive touchpoint.
**Output:** A weekly dashboard where CS leaders can see each account's health trajectory at a glance.
**Who uses it:** CS leadership, account managers.
**Why it matters:** Right now this insight lives buried in 100 separate transcript summaries. Aggregating it into one score per account turns reactive firefighting into proactive account management.

### Idea 2 — Competitive Intelligence Tracker
Extract every mention of a competitor (from competitive theme meetings + key moments). Track: which product module is cited in the comparison, what the outcome was (churned, stayed, escalated), and how often each competitor is mentioned week over week.
**Output:** A competitor mention frequency chart with outcome labels.
**Who uses it:** Product managers, sales leadership.
**Why it matters:** The dataset shows 3 competitive analysis meetings and several external calls where competitors are mentioned. Real-time visibility into these conversations gives PM teams signal months ahead of formal win/loss reports.

### Idea 3 — Rep Talk-Listen Ratio Coaching Tool
Build per-rep stats: average talk-time share, Gini coefficient per call type, sentiment correlation with their talk share. Flag reps where high Gini (dominates calls) correlates with lower sentiment outcomes.
**Output:** Per-rep scorecard, benchmarked against team average.
**Who uses it:** Support managers, CS team leads.
**Why it matters:** Coaching "listen more" is vague. A data-backed talk:listen ratio changes it from opinion to measurable behavior — and shows which reps improve sentiment outcomes by talking *less*.
"""))


# ── SECTION 7 ─────────────────────────────────────────────────────────────────
cells.append(md("## 7. Summary & Recommendations"))

cells.append(code("""\
print("=" * 65)
print("TRANSCRIPT INTELLIGENCE — KEY FINDINGS")
print("=" * 65)

print(f"\\n100 meetings | {df['start_time'].min().date()} → {df['start_time'].max().date()} | {df['duration_min'].sum():.0f} mins")

print("\\n── Call Type Breakdown ──")
for ct in ["external","internal","customer_support"]:
    sub = df[df["call_type"]==ct]
    print(f"  {LABELS[ct]:30s}: {len(sub):3d} meetings  avg sentiment {sub['sentiment_score'].mean():.2f}")

print("\\n── Theme Breakdown (top 5) ──")
for theme, count in df["primary_theme"].value_counts().head(5).items():
    avg_s = df[df["primary_theme"]==theme]["sentiment_score"].mean()
    print(f"  {theme:42s}: {count:3d}  avg {avg_s:.2f}")

print("\\n── Top Recommendations ──")
recs = [
    "1. Executive outreach to Blackridge, Northstar Pharma, Meridian Capital — active churn signals",
    "2. Build automated churn signal alerting: flag key moments in real-time for CS",
    "3. Double down on compliance motion — highest sentiment, most meetings, 33 in dataset",
    "4. Deploy talk-time analytics for rep coaching — imbalanced calls correlate with lower sentiment",
    "5. Track competitor mentions weekly — 3 dedicated meetings + embedded references in renewal calls",
]
for r in recs: print(f"  {r}")
"""))


# ── BUILD NOTEBOOK ─────────────────────────────────────────────────────────────
nb = nbformat.v4.new_notebook()
nb.cells = cells
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11.14"},
}

out = Path(__file__).parent / "transcript_intelligence.ipynb"
nbformat.write(nb, str(out))
print(f"Notebook written to: {out}")

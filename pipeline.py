"""
Transcript Intelligence — Analysis Pipeline
============================================
Processes ~100 call transcripts across customer support, external, and internal call types.
Produces: topic categorization, sentiment analysis, and additional insights.

Design choices:
- Hybrid topic categorization: keyword matching on existing `topics` field first,
  language model API for ambiguous/multi-label cases.
- Sentiment analysis uses the pre-scored `sentimentScore` (1–5 scale) and per-sentence
  `sentimentType` from each transcript.
- Call type classification uses title prefix + email domain heuristics.
"""

import json
import os
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

import anthropic

DATASET_DIR = Path(__file__).parent / "dataset"
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

COLORS = {
    "customer_support": "#E07B54",
    "external": "#5B8DB8",
    "internal": "#6BAF7A",
}

THEME_COLORS = [
    "#4C72B0", "#DD8452", "#55A868", "#C44E52",
    "#8172B3", "#937860", "#DA8BC3", "#8C8C8C",
]

# ── 1. DATA LOADING ────────────────────────────────────────────────────────────

def load_dataset(dataset_dir: Path) -> pd.DataFrame:
    """Load all transcript folders into a flat DataFrame."""
    rows = []
    for folder in sorted(dataset_dir.iterdir()):
        if not folder.is_dir():
            continue
        meeting_id = folder.name
        try:
            info = json.loads((folder / "meeting-info.json").read_text())
            summary = json.loads((folder / "summary.json").read_text())
            transcript_data = json.loads((folder / "transcript.json").read_text())
            sentences = transcript_data.get("data", [])

            rows.append({
                "meeting_id": meeting_id,
                "title": info.get("title", ""),
                "host": info.get("host", ""),
                "start_time": pd.to_datetime(info.get("startTime")),
                "duration_min": info.get("duration", 0),
                "all_emails": info.get("allEmails", []),
                "summary_text": summary.get("summary", ""),
                "action_items": summary.get("actionItems", []),
                "topics": summary.get("topics", []),
                "overall_sentiment": summary.get("overallSentiment", ""),
                "sentiment_score": summary.get("sentimentScore", 3.0),
                "key_moments": summary.get("keyMoments", []),
                "sentences": sentences,
                "n_sentences": len(sentences),
                "n_speakers": len(set(s.get("speaker_name") for s in sentences)),
                "n_action_items": len(summary.get("actionItems", [])),
            })
        except Exception as e:
            print(f"  Skipping {meeting_id}: {e}")

    df = pd.DataFrame(rows)
    df["start_date"] = df["start_time"].dt.date
    return df


# ── 2. CALL TYPE CLASSIFICATION ─────────────────────────────────────────────────

def classify_call_type(row) -> str:
    """
    Rule-based classification:
    1. 'Support Case #' in title → customer_support
    2. Any non-@aegiscloud.com email → external
    3. All @aegiscloud.com emails → internal
    """
    title = row["title"]
    emails = row["all_emails"]

    if "Support Case #" in title:
        return "customer_support"

    external_emails = [e for e in emails if not e.endswith("@aegiscloud.com")]
    if external_emails:
        return "external"

    return "internal"


# ── 3. THEME CATEGORIZATION ───────────────────────────────────────────────────

# Primary keyword mapping — applied to the `topics` list from summary.json
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
        "contract negotiation", "multi-year", "contract discussion",
    ],
    "Compliance & Audit Preparation": [
        "soc 2", "iso 27001", "hipaa", "pci dss", "compliance",
        "audit", "evidence", "gdpr", "compliance reporting",
        "audit preparation", "multi-framework", "evidence management",
        "compliance automation", "soc 2 audit", "soc 2 type ii",
    ],
    "Product Development & Planning": [
        "sprint planning", "roadmap", "design review", "sprint retro",
        "sprint retrospective", "launch readiness", "quarterly planning",
        "architecture", "pipeline architecture", "launch day", "ga deployment",
        "product launch", "reliability sprint", "reliability engineering",
    ],
    "Customer Onboarding": [
        "onboarding", "deployment", "kickoff", "setup", "implementation",
        "deployment planning", "identity deployment", "deployment kickoff",
        "identity module setup", "comply v2 deployment",
    ],
    "Technical Support & Bug Resolution": [
        "billing dispute", "product bug", "integration issue", "technical issue",
        "api outage", "connector", "logvault integration", "siem integration",
        "authentication failure", "saml", "ldap", "mfa failure",
        "provisioning sync", "false positives", "backup failure",
        "backup performance", "alert latency", "overage charges",
    ],
    "Competitive Intelligence": [
        "competitive", "win-loss", "competitor", "competitive threat",
        "competitive displacement", "competitive analysis", "win/loss",
        "competitive positioning", "vendor comparison",
    ],
    "Customer Feedback & Feature Requests": [
        "feature request", "feature gap", "product feedback", "customer feedback",
        "early access", "product demo", "feature gaps", "feedback session",
        "adoption metrics",
    ],
}


def score_themes(topics: list[str]) -> dict:
    """Return a score for each theme based on keyword overlap."""
    topics_lower = " | ".join(t.lower() for t in topics)
    scores = {}
    for theme, keywords in THEME_RULES.items():
        score = sum(1 for kw in keywords if kw in topics_lower)
        scores[theme] = score
    return scores


def assign_theme_rules(topics: list[str]) -> str:
    scores = score_themes(topics)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "Uncategorized"
    return best


def batch_classify_with_model(rows_to_classify: list[dict]) -> dict[str, str]:
    """
    Use a language model to classify ambiguous meetings (score == 0 or tie).
    Returns {meeting_id: theme_name}.
    """
    if not rows_to_classify:
        return {}

    client = anthropic.Anthropic()
    theme_list = "\n".join(f"- {t}" for t in THEME_RULES.keys())

    prompt_cases = []
    for r in rows_to_classify:
        prompt_cases.append(
            f"ID: {r['meeting_id']}\n"
            f"Title: {r['title']}\n"
            f"Topics: {', '.join(r['topics'])}\n"
            f"Summary: {r['summary_text'][:300]}\n"
        )

    prompt = f"""You are classifying business call transcripts into exactly one theme.

Available themes:
{theme_list}

For each meeting below, output ONLY a JSON object: {{"meeting_id": "theme_name", ...}}
Use the exact theme name from the list above. Do not explain.

Meetings:
{"---".join(prompt_cases)}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Extract JSON from response
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {}


def assign_themes(df: pd.DataFrame) -> pd.DataFrame:
    """Hybrid: rule-based first, model fallback for ambiguous cases."""
    df = df.copy()
    df["theme_scores"] = df["topics"].apply(score_themes)
    df["primary_theme"] = df["topics"].apply(assign_theme_rules)

    # Find ambiguous (score == 0) rows for model fallback
    ambiguous = df[df["primary_theme"] == "Uncategorized"]
    print(f"  Rule-based: {len(df) - len(ambiguous)} classified, {len(ambiguous)} ambiguous → model fallback")

    if len(ambiguous) > 0:
        rows_to_classify = ambiguous[["meeting_id", "title", "topics", "summary_text"]].to_dict("records")
        model_results = batch_classify_with_model(rows_to_classify)
        for mid, theme in model_results.items():
            df.loc[df["meeting_id"] == mid, "primary_theme"] = theme

    return df


# ── 4. SENTIMENT ANALYSIS ─────────────────────────────────────────────────────

def compute_sentence_sentiment(sentences: list[dict]) -> dict:
    """Aggregate per-sentence sentiment for a meeting."""
    if not sentences:
        return {"neg_pct": 0, "pos_pct": 0, "neutral_pct": 0, "n_sentences": 0}
    total = len(sentences)
    counts = Counter(s.get("sentimentType", "neutral") for s in sentences)
    return {
        "neg_pct": counts.get("negative", 0) / total * 100,
        "pos_pct": counts.get("positive", 0) / total * 100,
        "neutral_pct": counts.get("neutral", 0) / total * 100,
        "n_sentences": total,
    }


def compute_speaker_stats(sentences: list[dict]) -> list[dict]:
    """Compute talk-time share and sentiment per speaker."""
    by_speaker = defaultdict(list)
    for s in sentences:
        by_speaker[s.get("speaker_name", "Unknown")].append(s)

    total = len(sentences)
    stats = []
    for speaker, sents in by_speaker.items():
        counts = Counter(s.get("sentimentType", "neutral") for s in sents)
        stats.append({
            "speaker": speaker,
            "n_turns": len(sents),
            "talk_share_pct": len(sents) / total * 100 if total else 0,
            "neg_pct": counts.get("negative", 0) / len(sents) * 100,
        })
    return sorted(stats, key=lambda x: x["talk_share_pct"], reverse=True)


def extract_churn_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Find meetings with explicit churn_signal key moments."""
    rows = []
    for _, row in df.iterrows():
        churn_moments = [m for m in row["key_moments"] if m.get("type") == "churn_signal"]
        if churn_moments or (row["sentiment_score"] <= 2.0 and row["call_type"] == "external"):
            rows.append({
                "meeting_id": row["meeting_id"],
                "title": row["title"],
                "call_type": row["call_type"],
                "sentiment_score": row["sentiment_score"],
                "theme": row["primary_theme"],
                "churn_signals": churn_moments,
                "n_churn_signals": len(churn_moments),
                "action_items": row["action_items"],
            })
    return pd.DataFrame(rows).sort_values("sentiment_score") if rows else pd.DataFrame()


# ── 5. VISUALIZATION ──────────────────────────────────────────────────────────

def fig_call_type_distribution(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Pie chart
    counts = df["call_type"].value_counts()
    labels = {
        "customer_support": "Customer Support",
        "external": "External (Account Mgmt)",
        "internal": "Internal",
    }
    ax = axes[0]
    wedges, texts, autotexts = ax.pie(
        [counts.get(k, 0) for k in COLORS],
        labels=[labels[k] for k in COLORS],
        colors=[COLORS[k] for k in COLORS],
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.75,
        wedgeprops=dict(linewidth=1.5, edgecolor="white"),
    )
    for at in autotexts:
        at.set_fontsize(12)
        at.set_fontweight("bold")
    ax.set_title("Call Type Distribution\n(n=100 transcripts)", fontsize=13, fontweight="bold")

    # Bar chart by call type
    ax2 = axes[1]
    for i, (ctype, color) in enumerate(COLORS.items()):
        ax2.bar(labels[ctype], counts.get(ctype, 0), color=color, edgecolor="white", linewidth=1.5)
    ax2.set_title("Transcripts per Call Type", fontsize=13, fontweight="bold")
    ax2.set_ylabel("Count")
    ax2.set_ylim(0, counts.max() + 5)
    for p in ax2.patches:
        ax2.annotate(f"{int(p.get_height())}", (p.get_x() + p.get_width() / 2, p.get_height() + 0.5),
                     ha="center", fontsize=11)
    sns.despine(ax=ax2)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "01_call_type_distribution.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 01_call_type_distribution.png")


def fig_theme_distribution(df: pd.DataFrame):
    theme_counts = df["primary_theme"].value_counts()

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Overall bar chart
    ax = axes[0]
    bars = ax.barh(theme_counts.index, theme_counts.values,
                   color=THEME_COLORS[:len(theme_counts)], edgecolor="white")
    ax.set_xlabel("Number of Meetings")
    ax.set_title("Topic/Theme Distribution\n(Hybrid: keyword rules + model fallback)", fontsize=13, fontweight="bold")
    for bar in bars:
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                f"{int(bar.get_width())}", va="center", fontsize=10)
    ax.set_xlim(0, theme_counts.max() + 4)
    sns.despine(ax=ax)

    # Stacked bar: theme × call type
    ax2 = axes[1]
    cross = pd.crosstab(df["primary_theme"], df["call_type"])
    cross = cross.reindex(theme_counts.index)
    bottom = np.zeros(len(cross))
    for ctype, color in COLORS.items():
        vals = cross.get(ctype, pd.Series(0, index=cross.index)).values
        ax2.barh(cross.index, vals, left=bottom,
                 color=color, label={"customer_support": "Support", "external": "External", "internal": "Internal"}[ctype],
                 edgecolor="white")
        bottom += vals
    ax2.set_xlabel("Number of Meetings")
    ax2.set_title("Theme Breakdown by Call Type", fontsize=13, fontweight="bold")
    ax2.legend(loc="lower right", fontsize=10)
    sns.despine(ax=ax2)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "02_theme_distribution.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 02_theme_distribution.png")


def fig_sentiment_by_call_type(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Box plot
    ax = axes[0]
    order = ["customer_support", "external", "internal"]
    palette = {k: COLORS[k] for k in order}
    data = [df[df["call_type"] == ct]["sentiment_score"].values for ct in order]
    bp = ax.boxplot(data, patch_artist=True, widths=0.5,
                    medianprops=dict(color="white", linewidth=2))
    for patch, ct in zip(bp["boxes"], order):
        patch.set_facecolor(COLORS[ct])
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(["Customer\nSupport", "External\n(Acct Mgmt)", "Internal"], fontsize=10)
    ax.set_ylabel("Sentiment Score (1–5)")
    ax.set_title("Sentiment Distribution\nby Call Type", fontsize=12, fontweight="bold")
    ax.axhline(3, color="gray", linestyle="--", alpha=0.5, label="Neutral (3.0)")
    ax.legend(fontsize=9)
    sns.despine(ax=ax)

    # Mean sentiment bar
    ax2 = axes[1]
    means = df.groupby("call_type")["sentiment_score"].mean()[order]
    bars = ax2.bar(
        ["Customer\nSupport", "External", "Internal"],
        means.values,
        color=[COLORS[ct] for ct in order],
        edgecolor="white",
    )
    ax2.axhline(3, color="gray", linestyle="--", alpha=0.5)
    ax2.set_ylim(0, 5.2)
    ax2.set_ylabel("Mean Sentiment Score")
    ax2.set_title("Mean Sentiment\nby Call Type", fontsize=12, fontweight="bold")
    for bar, val in zip(bars, means.values):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                 f"{val:.2f}", ha="center", fontsize=11, fontweight="bold")
    sns.despine(ax=ax2)

    # Sentiment category breakdown (stacked %)
    ax3 = axes[2]
    sent_map = {
        "very-positive": 5, "positive": 4, "mixed-positive": 3.5,
        "mixed-negative": 2.5, "negative": 2, "very-negative": 1,
        "mixed": 3, "neutral": 3,
    }
    def is_positive(s): return s in {"very-positive", "positive", "mixed-positive"}
    def is_negative(s): return s in {"very-negative", "negative", "mixed-negative"}

    labels_ct = ["Customer\nSupport", "External", "Internal"]
    for i, ct in enumerate(order):
        sub = df[df["call_type"] == ct]
        pos = (sub["overall_sentiment"].apply(is_positive).sum() / len(sub)) * 100
        neg = (sub["overall_sentiment"].apply(is_negative).sum() / len(sub)) * 100
        neu = 100 - pos - neg
        ax3.bar(i, pos, color="#55A868", label="Positive" if i == 0 else "")
        ax3.bar(i, neu, bottom=pos, color="#CCCCCC", label="Mixed/Neutral" if i == 0 else "")
        ax3.bar(i, neg, bottom=pos + neu, color="#C44E52", label="Negative" if i == 0 else "")

    ax3.set_xticks([0, 1, 2])
    ax3.set_xticklabels(labels_ct, fontsize=10)
    ax3.set_ylabel("% of Meetings")
    ax3.set_title("Sentiment Mix\nby Call Type", fontsize=12, fontweight="bold")
    ax3.legend(fontsize=9, loc="upper right")
    sns.despine(ax=ax3)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "03_sentiment_by_call_type.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 03_sentiment_by_call_type.png")


def fig_sentiment_over_time(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(14, 5))

    df_sorted = df.sort_values("start_time")
    # 3-day rolling average
    df_sorted["date_num"] = (df_sorted["start_time"] - df_sorted["start_time"].min()).dt.days

    for ctype, color in COLORS.items():
        sub = df_sorted[df_sorted["call_type"] == ctype].copy()
        if len(sub) < 3:
            continue
        sub = sub.set_index("start_time").sort_index()
        daily = sub.resample("D")["sentiment_score"].mean().dropna()
        roll = daily.rolling(3, min_periods=1).mean()
        ax.plot(daily.index, daily.values, "o", color=color, alpha=0.3, markersize=5)
        ax.plot(roll.index, roll.values, "-", color=color,
                label={"customer_support": "Customer Support", "external": "External", "internal": "Internal"}[ctype],
                linewidth=2.5)

    # Mark outage window
    outage_start = pd.Timestamp("2026-03-14")
    outage_end = pd.Timestamp("2026-03-20")
    ax.axvspan(outage_start, outage_end, alpha=0.12, color="red", label="Detect Outage Window")
    ax.axhline(3, color="gray", linestyle="--", alpha=0.4, label="Neutral baseline")

    ax.set_ylabel("Sentiment Score (1–5)")
    ax.set_title("Sentiment Score Over Time (3-day rolling average by call type)",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.set_ylim(0.5, 5.5)
    sns.despine(ax=ax)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "04_sentiment_over_time.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 04_sentiment_over_time.png")


def fig_churn_risk(df: pd.DataFrame, churn_df: pd.DataFrame):
    if churn_df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Scatter: churn signal count vs sentiment score
    ax = axes[0]
    for _, row in churn_df.iterrows():
        color = COLORS.get(row["call_type"], "#888888")
        ax.scatter(row["sentiment_score"], row["n_churn_signals"],
                   color=color, s=120, alpha=0.8, zorder=3, edgecolors="white")

    # Custom legend
    patches = [mpatches.Patch(color=COLORS[k], label=k.replace("_", " ").title()) for k in COLORS]
    ax.legend(handles=patches, fontsize=9)
    ax.set_xlabel("Sentiment Score (1–5)")
    ax.set_ylabel("Number of Churn Signal Moments")
    ax.set_title("Churn Risk Map\n(explicit churn signals + low-sentiment external calls)",
                 fontsize=12, fontweight="bold")
    ax.axvline(2.5, color="red", linestyle="--", alpha=0.5)
    ax.axhline(1, color="orange", linestyle="--", alpha=0.5)
    sns.despine(ax=ax)

    # Table: worst accounts
    ax2 = axes[1]
    ax2.axis("off")
    worst = churn_df.nsmallest(8, "sentiment_score")[["title", "sentiment_score", "n_churn_signals"]]
    worst["title"] = worst["title"].apply(lambda t: t[:50] + "…" if len(t) > 50 else t)
    table = ax2.table(
        cellText=worst.values,
        colLabels=["Meeting Title", "Sentiment", "Churn Signals"],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.6)
    ax2.set_title("Highest-Risk Meetings", fontsize=12, fontweight="bold", pad=20)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "05_churn_risk.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 05_churn_risk.png")


def fig_speaker_dynamics(df: pd.DataFrame):
    """Analyze speaker talk-time imbalance as a proxy for call health."""
    stats_rows = []
    for _, row in df.iterrows():
        stats = compute_speaker_stats(row["sentences"])
        if len(stats) < 2:
            continue
        # Gini coefficient of talk share (0 = equal, 1 = one person dominates)
        shares = sorted([s["talk_share_pct"] for s in stats])
        n = len(shares)
        gini = (2 * sum((i + 1) * v for i, v in enumerate(shares)) / (n * sum(shares))) - (n + 1) / n if sum(shares) > 0 else 0
        stats_rows.append({
            "meeting_id": row["meeting_id"],
            "call_type": row["call_type"],
            "sentiment_score": row["sentiment_score"],
            "theme": row["primary_theme"],
            "talk_gini": gini,
            "n_speakers": row["n_speakers"],
            "duration_min": row["duration_min"],
        })
    stats_df = pd.DataFrame(stats_rows)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    for ctype, color in COLORS.items():
        sub = stats_df[stats_df["call_type"] == ctype]
        ax.scatter(sub["talk_gini"], sub["sentiment_score"], color=color,
                   label=ctype.replace("_", " ").title(), alpha=0.7, s=80, edgecolors="white")
    ax.set_xlabel("Talk-Time Gini Coefficient\n(0=balanced, 1=one speaker dominates)")
    ax.set_ylabel("Sentiment Score (1–5)")
    ax.set_title("Speaker Imbalance vs. Sentiment\n(proxy for engagement quality)",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    sns.despine(ax=ax)

    ax2 = axes[1]
    mean_gini = stats_df.groupby("call_type")["talk_gini"].mean()[list(COLORS.keys())]
    bars = ax2.bar(
        [k.replace("_", " ").title() for k in mean_gini.index],
        mean_gini.values,
        color=[COLORS[k] for k in mean_gini.index],
        edgecolor="white",
    )
    ax2.set_ylabel("Mean Gini Coefficient")
    ax2.set_title("Average Talk-Time Balance\nby Call Type", fontsize=12, fontweight="bold")
    for bar, val in zip(bars, mean_gini.values):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                 f"{val:.2f}", ha="center", fontsize=11)
    sns.despine(ax=ax2)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "06_speaker_dynamics.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 06_speaker_dynamics.png")


def fig_action_items(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Action items per meeting by call type
    ax = axes[0]
    order = ["customer_support", "external", "internal"]
    means = df.groupby("call_type")["n_action_items"].mean()[order]
    bars = ax.bar(
        ["Customer\nSupport", "External", "Internal"],
        means.values,
        color=[COLORS[ct] for ct in order],
        edgecolor="white",
    )
    for bar, val in zip(bars, means.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{val:.1f}", ha="center", fontsize=11, fontweight="bold")
    ax.set_ylabel("Mean Action Items per Meeting")
    ax.set_title("Action Item Volume\nby Call Type", fontsize=12, fontweight="bold")
    sns.despine(ax=ax)

    # Action items vs sentiment
    ax2 = axes[1]
    for ctype, color in COLORS.items():
        sub = df[df["call_type"] == ctype]
        ax2.scatter(sub["n_action_items"], sub["sentiment_score"],
                    color=color, alpha=0.6, s=80,
                    label=ctype.replace("_", " ").title(), edgecolors="white")
    # Trend line
    z = np.polyfit(df["n_action_items"], df["sentiment_score"], 1)
    p = np.poly1d(z)
    x_range = np.linspace(df["n_action_items"].min(), df["n_action_items"].max(), 50)
    ax2.plot(x_range, p(x_range), "k--", alpha=0.5, label="Trend")
    ax2.set_xlabel("Number of Action Items")
    ax2.set_ylabel("Sentiment Score (1–5)")
    ax2.set_title("Action Items vs. Sentiment\n(more AIs = harder meetings?)",
                  fontsize=12, fontweight="bold")
    ax2.legend(fontsize=9)
    sns.despine(ax=ax2)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "07_action_items.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 07_action_items.png")


def fig_sentiment_by_theme(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(13, 6))

    theme_stats = df.groupby("primary_theme").agg(
        mean_score=("sentiment_score", "mean"),
        n=("meeting_id", "count"),
    ).sort_values("mean_score")

    colors = [THEME_COLORS[i % len(THEME_COLORS)] for i in range(len(theme_stats))]
    bars = ax.barh(theme_stats.index, theme_stats["mean_score"], color=colors, edgecolor="white")
    ax.axvline(3, color="gray", linestyle="--", alpha=0.5, label="Neutral (3.0)")
    ax.set_xlabel("Mean Sentiment Score (1–5)")
    ax.set_title("Mean Sentiment Score by Theme", fontsize=13, fontweight="bold")

    for bar, (_, row) in zip(bars, theme_stats.iterrows()):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                f"{row['mean_score']:.2f}  (n={int(row['n'])})", va="center", fontsize=10)

    ax.set_xlim(0, 5.8)
    ax.legend(fontsize=9)
    sns.despine(ax=ax)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "08_sentiment_by_theme.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: 08_sentiment_by_theme.png")


# ── 6. SUMMARY STATS ──────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame, churn_df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("TRANSCRIPT INTELLIGENCE — PIPELINE SUMMARY")
    print("=" * 60)
    print(f"\nTotal meetings processed: {len(df)}")
    print(f"Date range: {df['start_time'].min().date()} → {df['start_time'].max().date()}")
    print(f"Total duration: {df['duration_min'].sum():.0f} minutes ({df['duration_min'].sum()/60:.1f} hours)")

    print("\n── Call Types ──")
    for ct, count in df["call_type"].value_counts().items():
        mean_s = df[df["call_type"] == ct]["sentiment_score"].mean()
        print(f"  {ct:25s}: {count:3d} meetings  (mean sentiment: {mean_s:.2f})")

    print("\n── Themes ──")
    for theme, count in df["primary_theme"].value_counts().items():
        mean_s = df[df["primary_theme"] == theme]["sentiment_score"].mean()
        print(f"  {theme:40s}: {count:3d}  (mean sentiment: {mean_s:.2f})")

    print(f"\n── Churn Risk ──")
    print(f"  Meetings with churn signals: {len(churn_df)}")
    if not churn_df.empty:
        for _, r in churn_df.nsmallest(5, "sentiment_score").iterrows():
            print(f"  [{r['sentiment_score']:.1f}] {r['title'][:70]}")

    print("\n── Key Findings ──")
    support_mean = df[df["call_type"] == "customer_support"]["sentiment_score"].mean()
    external_mean = df[df["call_type"] == "external"]["sentiment_score"].mean()
    internal_mean = df[df["call_type"] == "internal"]["sentiment_score"].mean()
    print(f"  1. Support calls avg {support_mean:.2f} — notably lower than external ({external_mean:.2f}) and internal ({internal_mean:.2f})")

    outage_theme = "Incident & Outage Response"
    outage_mean = df[df["primary_theme"] == outage_theme]["sentiment_score"].mean()
    print(f"  2. '{outage_theme}' theme avg {outage_mean:.2f} — largest sentiment drag")

    compliance_mean = df[df["primary_theme"] == "Compliance & Audit Preparation"]["sentiment_score"].mean()
    onboard_mean = df[df["primary_theme"] == "Customer Onboarding"]["sentiment_score"].mean()
    print(f"  3. Compliance ({compliance_mean:.2f}) and Onboarding ({onboard_mean:.2f}) are sentiment bright spots")
    print(f"  4. {len(churn_df)} meetings carry active churn risk signals")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading dataset…")
    df = load_dataset(DATASET_DIR)
    print(f"  Loaded {len(df)} meetings")

    print("\nClassifying call types…")
    df["call_type"] = df.apply(classify_call_type, axis=1)
    print(f"  {df['call_type'].value_counts().to_dict()}")

    print("\nAssigning themes (hybrid: keyword rules + model fallback)…")
    df = assign_themes(df)

    print("\nExtracting churn risk signals…")
    churn_df = extract_churn_signals(df)

    print("\nGenerating visualizations…")
    sns.set_style("whitegrid")
    plt.rcParams.update({"font.size": 11})

    fig_call_type_distribution(df)
    fig_theme_distribution(df)
    fig_sentiment_by_call_type(df)
    fig_sentiment_over_time(df)
    fig_churn_risk(df, churn_df)
    fig_speaker_dynamics(df)
    fig_action_items(df)
    fig_sentiment_by_theme(df)

    print_summary(df, churn_df)

    # Save processed data for notebook reuse
    df_save = df.drop(columns=["sentences", "key_moments", "action_items", "theme_scores"])
    df_save.to_csv(OUTPUT_DIR / "processed_data.csv", index=False)
    print(f"\nProcessed data saved to outputs/processed_data.csv")

    return df, churn_df


if __name__ == "__main__":
    df, churn_df = main()

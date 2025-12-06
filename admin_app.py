
import os
import json
import streamlit as st
import pandas as pd
from utils import call_llm, ensure_data_dir
from datetime import datetime

DATA_FILE = ensure_data_dir("data/feedback.jsonl")

st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("Admin — Feedback Dashboard (Internal)")

if not os.path.exists(DATA_FILE):
    st.warning("No data found yet. Wait for user submissions or upload data/feedback.jsonl")
    st.stop()
if os.path.getsize(DATA_FILE) == 0:
    st.warning("The data file exists but is empty. Waiting for first submission...")
    st.stop()

def read_jsonl(path: str):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return pd.DataFrame(rows)

@st.cache_data(ttl=3)
def load_data(path):
    df = read_jsonl(path)
    if "timestamp" in df.columns:
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        except Exception:
            pass
    return df

df = load_data(DATA_FILE)

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total submissions", len(df))
col2.metric("Avg rating", round(df["rating"].mean(), 2) if "rating" in df.columns else "N/A")
col3.metric("5-star %", f"{(df['rating'] == 5).mean() * 100:.1f}%" if "rating" in df.columns else "N/A")
col4.metric("1-star %", f"{(df['rating'] == 1).mean() * 100:.1f}%" if "rating" in df.columns else "N/A")

st.subheader("Live submissions")
st.dataframe(df.sort_values("timestamp", ascending=False).reset_index(drop=True))

st.subheader("Analytics")
if "rating" in df.columns:
    counts = df["rating"].value_counts().reindex([1,2,3,4,5], fill_value=0)
    st.bar_chart(counts)
    st.write(df[["rating"]].describe())
else:
    st.write("No rating column found.")

st.subheader("Generate / Refresh AI Summaries & Actions for selected rows")
indexed = df.reset_index(drop=True)
selected = st.multiselect("Select rows (by index)", indexed.index.tolist())

def write_jsonl(path: str, records: list):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

if st.button("Generate insights for selected rows"):
    if not selected:
        st.info("No rows selected.")
    else:
        full_df = read_jsonl(DATA_FILE)
        updated = False
        for idx in selected:
            row = indexed.loc[int(idx)]
            # skip if already has both summary and action
            if str(row.get("ai_summary", "")).strip() and str(row.get("ai_action", "")).strip():
                continue
            prompt = (
                "You are an operations analyst. Given the user review and rating, produce a short JSON object "
                "with keys 'ai_summary' (one sentence) and 'ai_action' (one short recommended action).\n\n"
                f"Rating: {row.get('rating','')}\nReview: {row.get('review','')}\n\n"
                "Return ONLY valid JSON. Example: {\"ai_summary\":\"...\",\"ai_action\":\"...\"}"
            )
            out = call_llm(prompt, max_new_tokens=150, temperature=0.2, hf_fallback_model="gpt2")
            ai_summary = ""
            ai_action = ""
            if isinstance(out, str) and out.strip().startswith("{"):
                try:
                    j = json.loads(out)
                    if isinstance(j, dict):
                        ai_summary = j.get("ai_summary","") or ""
                        ai_action = j.get("ai_action","") or ""
                except Exception:
                    ai_summary = out
            else:
                ai_summary = out

            # update the matching row(s) in full_df (match by timestamp + review)
            mask = (full_df["timestamp"] == row["timestamp"]) & (full_df["review"] == row["review"])
            if mask.any():
                full_df.loc[mask, "ai_summary"] = ai_summary
                full_df.loc[mask, "ai_action"] = ai_action
                updated = True

        if updated:
            # overwrite JSONL
            write_jsonl(DATA_FILE, full_df.to_dict(orient="records"))
            st.success("Updated selected rows. Refreshing view...")
            st.experimental_rerun()
        else:
            st.info("No rows were updated (they may already have summaries).")

st.subheader("Inspect / Export")
with open(DATA_FILE, "rb") as f:
    st.download_button("Download data JSONL", data=f, file_name="feedback.jsonl")

st.caption("Dashboards read/write the same data/feedback.jsonl file. Admin UI auto-refreshes (cache TTL 3s).")


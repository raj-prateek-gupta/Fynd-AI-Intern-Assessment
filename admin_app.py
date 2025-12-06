# # admin_app.py
# import os
# import streamlit as st
# import pandas as pd
# import json
# from utils import call_llm, ensure_data_dir

# DATA_FILE = ensure_data_dir("data/feedback.csv")

# st.set_page_config(page_title="Admin Dashboard", layout="wide")
# st.title("Admin — Feedback Dashboard")

# if not os.path.exists(DATA_FILE):
#     st.warning("No data found yet. Wait for user submissions or upload a CSV named data/feedback.csv")
#     st.stop()

# if os.path.getsize(DATA_FILE) == 0:
#     st.warning("The data file exists but is empty. Waiting for first submission...")
#     st.stop()

# @st.cache_data
# def load_data(path):
#     df = pd.read_csv(path)
#     if "timestamp" in df.columns:
#         try:
#             df["timestamp"] = pd.to_datetime(df["timestamp"])
#         except Exception:
#             pass
#     return df

# df = load_data(DATA_FILE)

# col1, col2, col3, col4 = st.columns(4)
# col1.metric("Total submissions", len(df))
# col2.metric("Avg rating", round(df["rating"].mean(), 2) if "rating" in df.columns else "N/A")
# col3.metric("5-star %", f"{(df['rating'] == 5).mean() * 100:.1f}%" if "rating" in df.columns else "N/A")
# col4.metric("1-star %", f"{(df['rating'] == 1).mean() * 100:.1f}%" if "rating" in df.columns else "N/A")

# st.subheader("Recent Submissions")
# st.dataframe(df.sort_values("timestamp", ascending=False).reset_index(drop=True))

# st.subheader("Generate AI Summaries & Recommended Actions")
# with st.expander("Batch: Summarize reviews and recommend actions"):
#     if st.button("Generate batch summary"):
#         reviews = df["review"].dropna().astype(str).tolist()
#         sample_text = "\n---\n".join(reviews[:200]) if reviews else ""
#         prompt = (
#             "You are an operations manager. Provide a concise summary (3-5 bullet points) "
#             "of the customer feedback and suggest 5 actionable recommendations that the product or ops team can take. "
#             "Be specific and prioritized.\n\nFeedback:\n"
#             + sample_text
#         )
#         with st.spinner("Generating summary via LangChain + HF..."):
#             summary = call_llm(prompt, max_new_tokens=512, temperature=0.2, hf_fallback_model="gpt2")
#         if isinstance(summary, str) and summary.startswith("[LLM"):
#             st.error("LLM error when generating batch summary.")
#             st.write(summary)
#         else:
#             st.markdown("**Summary & Actions**")
#             st.write(summary)

# st.subheader("Per-Row AI Insights")
# indexed_df = df.reset_index(drop=True)
# selected = st.multiselect("Select rows (by index)", indexed_df.index.tolist(), default=[])

# insights_placeholder = st.container()

# if st.button("Generate insights for selected rows"):
#     insights = []
#     if not selected:
#         st.info("No rows selected.")
#     else:
#         with st.spinner("Generating insights..."):
#             for idx in selected:
#                 row = indexed_df.loc[int(idx)]
#                 prompt = (
#                     f"Given this review, produce a one-line summary and one suggested action in JSON format.\n\n"
#                     f"Rating: {row.get('rating', '')}\n"
#                     f"Review: {row.get('review', '')}\n\n"
#                     f"Return ONLY valid JSON: {{\"summary\":\"...\",\"action\":\"...\"}}"
#                 )
#                 out = call_llm(prompt, max_new_tokens=200, temperature=0.2, hf_fallback_model="gpt2")
#                 parsed = None
#                 try:
#                     # Try to extract JSON from LLM output
#                     start = out.find("{")
#                     if start != -1:
#                         candidate = out[start:]
#                         parsed = json.loads(candidate)
#                 except Exception:
#                     parsed = None
#                 insights.append({
#                     "index": int(idx),
#                     "llm_raw": out,
#                     "summary": parsed.get("summary") if isinstance(parsed, dict) else "",
#                     "action": parsed.get("action") if isinstance(parsed, dict) else ""
#                 })
#         insights_df = pd.DataFrame(insights)
#         insights_placeholder.write(insights_df)

# st.subheader("Analytics")
# if "rating" in df.columns:
#     counts = df["rating"].value_counts().reindex([1,2,3,4,5], fill_value=0)
#     st.bar_chart(counts)
# else:
#     st.write("No rating column found to show analytics.")



# admin_app.py
# import os
# import streamlit as st
# import pandas as pd
# from utils import call_llm, ensure_data_dir
# from datetime import datetime

# DATA_FILE = ensure_data_dir("data/feedback.csv")

# st.set_page_config(page_title="Admin Dashboard", layout="wide")
# st.title("Admin — Feedback Dashboard (Internal)")

# if not os.path.exists(DATA_FILE):
#     st.warning("No data found yet. Wait for user submissions or upload a CSV named data/feedback.csv")
#     st.stop()
# if os.path.getsize(DATA_FILE) == 0:
#     st.warning("The data file exists but is empty. Waiting for first submission...")
#     st.stop()

# # cached loader with TTL to behave like a live-updating list
# @st.cache_data(ttl=3)
# def load_data(path):
#     df = pd.read_csv(path)
#     if "timestamp" in df.columns:
#         try:
#             df["timestamp"] = pd.to_datetime(df["timestamp"])
#         except Exception:
#             pass
#     return df

# df = load_data(DATA_FILE)

# # KPIs
# col1, col2, col3, col4 = st.columns(4)
# col1.metric("Total submissions", len(df))
# col2.metric("Avg rating", round(df["rating"].mean(), 2) if "rating" in df.columns else "N/A")
# col3.metric("5-star %", f"{(df['rating'] == 5).mean() * 100:.1f}%" if "rating" in df.columns else "N/A")
# col4.metric("1-star %", f"{(df['rating'] == 1).mean() * 100:.1f}%" if "rating" in df.columns else "N/A")

# st.subheader("Live submissions")
# st.dataframe(df.sort_values("timestamp", ascending=False).reset_index(drop=True))

# st.subheader("Analytics")
# if "rating" in df.columns:
#     counts = df["rating"].value_counts().reindex([1,2,3,4,5], fill_value=0)
#     st.bar_chart(counts)
#     st.write(df[["rating"]].describe())
# else:
#     st.write("No rating column found.")

# st.subheader("Generate / Refresh AI Summaries & Actions for selected rows")
# indexed = df.reset_index(drop=True)
# selected = st.multiselect("Select rows (by index)", indexed.index.tolist())

# if st.button("Generate insights for selected rows"):
#     if not selected:
#         st.info("No rows selected.")
#     else:
#         updated = False
#         for idx in selected:
#             row = indexed.loc[int(idx)]
#             # If already has ai_summary and ai_action, skip unless user wants forced regenerate
#             if str(row.get("ai_summary", "")).strip() and str(row.get("ai_action", "")).strip():
#                 continue
#             prompt = (
#                 "You are an operations analyst. Given the user review and rating, produce a short JSON object "
#                 "with keys 'ai_summary' (one sentence) and 'ai_action' (one short recommended action).\n\n"
#                 f"Rating: {row.get('rating', '')}\nReview: {row.get('review', '')}\n\n"
#                 "Return ONLY valid JSON. Example: {\"ai_summary\":\"...\",\"ai_action\":\"...\"}"
#             )
#             out = call_llm(prompt, max_new_tokens=150, temperature=0.2, hf_fallback_model="gpt2")
#             # try parse JSON
#             ai_summary = ""
#             ai_action = ""
#             if isinstance(out, str) and out.strip().startswith("{"):
#                 try:
#                     j = pd.json.loads(out)
#                     ai_summary = j.get("ai_summary", "") if isinstance(j, dict) else ""
#                     ai_action = j.get("ai_action", "") if isinstance(j, dict) else ""
#                 except Exception:
#                     ai_summary = out
#                     ai_action = ""
#             else:
#                 ai_summary = out
#             # write back to CSV (update that row)
#             try:
#                 full = pd.read_csv(DATA_FILE)
#                 # locate by exact timestamp+review combination (safe-ish)
#                 mask = (full["timestamp"] == row["timestamp"]) & (full["review"] == row["review"])
#                 if mask.any():
#                     full.loc[mask, "ai_summary"] = ai_summary
#                     full.loc[mask, "ai_action"] = ai_action
#                     full.to_csv(DATA_FILE, index=False)
#                     updated = True
#             except Exception as e:
#                 st.error(f"Failed to update row {idx}: {e}")
#         if updated:
#             st.success("Updated selected rows. Refreshing view...")
#             st.experimental_rerun()
#         else:
#             st.info("No rows were updated (they may already have summaries).")

# st.subheader("Inspect / Export")
# if st.button("Download CSV"):
#     st.download_button("Download data CSV", data=open(DATA_FILE, "rb"), file_name="feedback.csv")

# st.caption("Dashboards read/write the same data/feedback.csv file. Admin UI auto-refreshes (cache TTL 3s).")


# admin_app.py
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


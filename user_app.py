
import os
import json
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from utils import call_llm, ensure_data_dir

DATA_FILE = ensure_data_dir("data/feedback.jsonl")

st.set_page_config(page_title="User Feedback", layout="centered")
st.title("Feedback — User Portal")
st.write("Write a short review and select a star rating. The AI will reply and your submission will be stored.")

with st.form("feedback_form", clear_on_submit=True):
    rating = st.selectbox("Select rating", [5, 4, 3, 2, 1], index=0)
    review = st.text_area("Write your review", height=150)
    submitted = st.form_submit_button("Submit")

def append_jsonl(path: str, record: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def read_jsonl(path: str):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return pd.DataFrame(rows)

if submitted:
    if not review.strip():
        st.error("Please write a short review before submitting.")
    else:
        # 1) user-facing reply
        user_prompt = (
            "You are a friendly customer support assistant. "
            "Given the user's rating and review, write a short empathetic reply (1-3 sentences) "
            "acknowledging their feedback and suggesting a next step if relevant.\n\n"
            f"Rating: {rating}\nReview: {review}\n\nReturn only the assistant reply text."
        )
        st.info("Generating AI response...")
        ai_reply = call_llm(user_prompt, max_new_tokens=150, temperature=0.2, hf_fallback_model="gpt2")

        # 2) admin-facing summary + action (ask for JSON)
        insights_prompt = (
            "You are an operations analyst. Given the user review and rating, produce a short JSON object "
            "with keys 'ai_summary' (one sentence) and 'ai_action' (one short recommended action).\n\n"
            f"Rating: {rating}\nReview: {review}\n\n"
            "Return ONLY valid JSON. Example: {\"ai_summary\":\"...\",\"ai_action\":\"...\"}"
        )
        insights_out = call_llm(insights_prompt, max_new_tokens=150, temperature=0.2, hf_fallback_model="gpt2")

        # parse JSON safely
        ai_summary = ""
        ai_action = ""
        if isinstance(insights_out, str) and insights_out.strip().startswith("{"):
            try:
                j = json.loads(insights_out)
                if isinstance(j, dict):
                    ai_summary = j.get("ai_summary", "") or ""
                    ai_action = j.get("ai_action", "") or ""
            except Exception:
                # fallback: keep raw text in ai_summary
                ai_summary = insights_out

        if not ai_summary and not ai_action and isinstance(insights_out, str) and insights_out:
            ai_summary = insights_out

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rating": int(rating),
            "review": review,
            "ai_reply": ai_reply or "",
            "ai_summary": ai_summary or "",
            "ai_action": ai_action or "",
        }

        try:
            append_jsonl(DATA_FILE, record)
            st.success("Thanks — your feedback was submitted.")
        except Exception as e:
            st.error(f"Failed to save submission locally: {e}")

        st.markdown("**AI response:**")
        st.write(ai_reply or "No response returned.")
        if ai_summary:
            st.markdown("**AI summary (admin-facing):**")
            st.write(ai_summary)
        if ai_action:
            st.markdown("**AI recommended action (admin-facing):**")
            st.write(ai_action)

st.divider()

# Preview recent submissions
if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
    try:
        preview_df = read_jsonl(DATA_FILE).sort_values("timestamp", ascending=False).head(6)
        st.table(preview_df[["timestamp", "rating", "review"]])
    except Exception as e:
        st.write("Could not read preview:", e)
else:
    st.write("No submissions yet.")

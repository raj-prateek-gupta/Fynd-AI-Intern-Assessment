# # utils.py (diagnostic + robust multi-strategy HF invocation)
# import os
# import json
# from functools import lru_cache
# from typing import Optional
# from dotenv import load_dotenv

# load_dotenv()

# from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace

# HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
# HF_MODEL = os.getenv("HF_MODEL", "gpt2")  # change to your preferred model

# def ensure_data_dir(path: str) -> str:
#     parent = os.path.dirname(path)
#     if parent and not os.path.exists(parent):
#         os.makedirs(parent, exist_ok=True)
#     return path

# @lru_cache(maxsize=4)
# def _make_endpoint(repo_id: str, task: str = "text-generation", max_new_tokens: int = 256, temperature: float = 0.2):
#     """
#     Create and cache a HuggingFaceEndpoint + ChatHuggingFace wrapper for the given repo_id and task.
#     """
#     if not HUGGINGFACE_API_KEY:
#         raise RuntimeError("HUGGINGFACE_API_KEY not set in environment.")
#     ep = HuggingFaceEndpoint(
#         repo_id=repo_id,
#         task=task,
#         huggingfacehub_api_token=HUGGINGFACE_API_KEY,
#         max_new_tokens=max_new_tokens,
#         temperature=temperature,
#     )
#     # Chat wrapper around the endpoint gives .invoke() and chat-friendly behavior
#     chat = ChatHuggingFace(llm=ep)
#     return ep, chat

# def _normalize_result(result):
#     """
#     Try to convert the returned result into a plain string where possible.
#     Also return the raw type and repr for diagnostics.
#     """
#     raw_type = type(result).__name__
#     try:
#         raw_repr = repr(result)
#     except Exception:
#         raw_repr = "<unreprable>"
#     # If the object has .content, prefer that
#     if hasattr(result, "content"):
#         try:
#             content = result.content
#             return str(content).strip(), raw_type, raw_repr
#         except Exception:
#             pass
#     # If it's a string
#     if isinstance(result, str):
#         return result.strip(), raw_type, raw_repr
#     # If it's a list/dict, attempt to extract common keys
#     if isinstance(result, list) and result:
#         first = result[0]
#         if isinstance(first, dict):
#             # common HF shape: {"generated_text": "..."}
#             if "generated_text" in first:
#                 return str(first["generated_text"]).strip(), raw_type, raw_repr
#             # fallback: stringify first
#             return json.dumps(first)[:4000], raw_type, raw_repr
#     if isinstance(result, dict):
#         if "generated_text" in result:
#             return str(result["generated_text"]).strip(), raw_type, raw_repr
#         if "error" in result:
#             return f"[HF error: {result.get('error')}]", raw_type, raw_repr
#         return json.dumps(result)[:4000], raw_type, raw_repr
#     # Generic fallback
#     try:
#         return str(result)[:4000], raw_type, raw_repr
#     except Exception:
#         return "", raw_type, raw_repr

# def call_llm(
#     prompt: str,
#     max_new_tokens: int = 256,
#     temperature: float = 0.2,
#     hf_fallback_model: Optional[str] = None,
#     timeout: Optional[int] = None,
# ) -> str:
#     """
#     Robust HF call that tries multiple strategies and returns either generated text or
#     a diagnostic string starting with '[LLM error:' or '[LLM diag:' when helpful.
#     """
#     if not HUGGINGFACE_API_KEY:
#         return "[LLM not configured: set HUGGINGFACE_API_KEY or HUGGINGFACEHUB_API_TOKEN in environment]"

#     primary = HF_MODEL

#     # Try strategies in order; collect diagnostics
#     diagnostics = []

#     # Strategy 1: text-generation task (common)
#     try:
#         ep, chat = _make_endpoint(repo_id=primary, task="text-generation", max_new_tokens=max_new_tokens, temperature=temperature)
#         # ChatHuggingFace.invoke usually works; try it
#         try:
#             res = chat.invoke(prompt, timeout=timeout) if timeout else chat.invoke(prompt)
#         except TypeError:
#             # some versions don't accept timeout kwarg
#             res = chat.invoke(prompt)
#         text, rtype, rrepr = _normalize_result(res)
#         diagnostics.append(f"STRAT:text-gen -> type={rtype}; repr={rrepr[:500]}")
#         if text:
#             return text
#     except Exception as e:
#         diagnostics.append(f"STRAT:text-gen EXCEPTION: {e}")

#     # Strategy 2: chat task (some models need chat specification)
#     try:
#         ep2, chat2 = _make_endpoint(repo_id=primary, task="chat", max_new_tokens=max_new_tokens, temperature=temperature)
#         try:
#             res2 = chat2.invoke(prompt, timeout=timeout) if timeout else chat2.invoke(prompt)
#         except TypeError:
#             res2 = chat2.invoke(prompt)
#         text2, rtype2, rrepr2 = _normalize_result(res2)
#         diagnostics.append(f"STRAT:chat -> type={rtype2}; repr={rrepr2[:500]}")
#         if text2:
#             return text2
#     except Exception as e2:
#         diagnostics.append(f"STRAT:chat EXCEPTION: {e2}")

#     # Strategy 3: call endpoint.invoke directly (some endpoints expose raw outputs)
#     try:
#         ep3, _ = _make_endpoint(repo_id=primary, task="text-generation", max_new_tokens=max_new_tokens, temperature=temperature)
#         try:
#             # endpoint.invoke may return raw dict/list/string
#             resp3 = ep3.invoke(prompt, timeout=timeout) if timeout else ep3.invoke(prompt)
#         except TypeError:
#             resp3 = ep3.invoke(prompt)
#         text3, rtype3, rrepr3 = _normalize_result(resp3)
#         diagnostics.append(f"STRAT:endpoint.invoke -> type={rtype3}; repr={rrepr3[:500]}")
#         if text3:
#             return text3
#     except Exception as e3:
#         diagnostics.append(f"STRAT:endpoint.invoke EXCEPTION: {e3}")

#     # If primary failed to produce text, try fallback if provided
#     if hf_fallback_model and hf_fallback_model != primary:
#         try:
#             ep_f, chat_f = _make_endpoint(repo_id=hf_fallback_model, task="text-generation", max_new_tokens=max_new_tokens, temperature=temperature)
#             try:
#                 res_f = chat_f.invoke(prompt, timeout=timeout) if timeout else chat_f.invoke(prompt)
#             except TypeError:
#                 res_f = chat_f.invoke(prompt)
#             textf, rtypef, rreprf = _normalize_result(res_f)
#             diagnostics.append(f"STRAT:fallback -> model={hf_fallback_model}; type={rtypef}; repr={rreprf[:500]}")
#             if textf:
#                 return "[NOTE: used fallback model]\n\n" + textf
#         except Exception as ef:
#             diagnostics.append(f"STRAT:fallback EXCEPTION: {ef}")

#     # Nothing produced — return diagnostic string with collected info
#     diag_text = "[LLM diag: model produced no text]\n\n" + "\n".join(diagnostics)
#     # Include a short hint about trying a different model/task
#     diag_text += "\n\nHint: Try setting HF_MODEL to a different model (e.g., 'gpt2' or 'google/flan-t5-small') or change the task (chat vs text-generation)."
#     return diag_text


# user_app.py
# import os
# import streamlit as st
# import pandas as pd
# from datetime import datetime, timezone
# from utils import call_llm, ensure_data_dir

# DATA_FILE = ensure_data_dir("data/feedback.csv")

# st.set_page_config(page_title="User Feedback", layout="centered")
# st.title("Feedback — User Portal")
# st.write("Write a short review and select a star rating. The AI will reply and your submission will be stored.")

# with st.form("feedback_form", clear_on_submit=True):
#     rating = st.selectbox("Select rating", [5, 4, 3, 2, 1], index=0)
#     review = st.text_area("Write your review", height=150)
#     submitted = st.form_submit_button("Submit")

# if submitted:
#     if not review.strip():
#         st.error("Please write a short review before submitting.")
#     else:
#         # 1) Generate user-facing reply
#         user_prompt = (
#             "You are a friendly customer support assistant. "
#             "Given the user's rating and review, write a short empathetic reply (1-3 sentences) "
#             "acknowledging their feedback and suggesting a next step if relevant.\n\n"
#             f"Rating: {rating}\nReview: {review}\n\nReturn only the assistant reply text."
#         )
#         st.info("Generating AI response...")
#         ai_reply = call_llm(user_prompt, max_new_tokens=150, temperature=0.2, hf_fallback_model="gpt2")

#         # 2) Generate admin insights (summary + recommended action) as JSON-like text
#         insights_prompt = (
#             "You are an operations analyst. Given the user review and rating, produce a short JSON object "
#             "with keys 'ai_summary' (one sentence) and 'ai_action' (one short recommended action).\n\n"
#             f"Rating: {rating}\nReview: {review}\n\n"
#             "Return ONLY valid JSON. Example: {\"ai_summary\":\"...\",\"ai_action\":\"...\"}"
#         )
#         insights_out = call_llm(insights_prompt, max_new_tokens=150, temperature=0.2, hf_fallback_model="gpt2")

#         # Try to parse JSON, fall back to raw strings
#         ai_summary = ""
#         ai_action = ""
#         if isinstance(insights_out, str) and insights_out.strip().startswith("{"):
#             try:
#                 j = pd.json.loads(insights_out)
#                 ai_summary = j.get("ai_summary", "") if isinstance(j, dict) else ""
#                 ai_action = j.get("ai_action", "") if isinstance(j, dict) else ""
#             except Exception:
#                 # fallback parse attempt: attempt to find keys manually
#                 try:
#                     obj = eval(insights_out, {}, {})  # last resort (safe in dev). If you dislike eval, skip.
#                     if isinstance(obj, dict):
#                         ai_summary = obj.get("ai_summary", "")
#                         ai_action = obj.get("ai_action", "")
#                 except Exception:
#                     ai_summary = ""
#                     ai_action = ""
#         # If parsing failed, store raw
#         if not ai_summary and not ai_action:
#             ai_summary = insights_out if insights_out else ""
#             ai_action = ""

#         # Save record
#         record = {
#             "timestamp": datetime.now(timezone.utc).isoformat(),
#             "rating": int(rating),
#             "review": review,
#             "ai_reply": ai_reply or "",
#             "ai_summary": ai_summary or "",
#             "ai_action": ai_action or "",
#         }
#         try:
#             df = pd.DataFrame([record])
#             if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
#                 df.to_csv(DATA_FILE, index=False)
#             else:
#                 df.to_csv(DATA_FILE, mode="a", header=False, index=False)
#             st.success("Thanks — your feedback was submitted.")
#         except Exception as e:
#             st.error(f"Failed to save submission locally: {e}")

#         st.markdown("**AI response:**")
#         st.write(ai_reply or "No response returned.")
#         if ai_summary:
#             st.markdown("**AI summary (admin-facing):**")
#             st.write(ai_summary)
#         if ai_action:
#             st.markdown("**AI recommended action (admin-facing):**")
#             st.write(ai_action)

# st.divider()

# # Preview recent submissions safely
# if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
#     try:
#         preview = pd.read_csv(DATA_FILE).sort_values("timestamp", ascending=False).head(6)
#         st.table(preview[["timestamp", "rating", "review"]])
#     except Exception as e:
#         st.write("Could not read preview:", e)
# else:
#     st.write("No submissions yet.")


# user_app.py
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

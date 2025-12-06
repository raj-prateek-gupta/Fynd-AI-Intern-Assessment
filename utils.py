import os
import json
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "gpt2")  # default for testing


def ensure_data_dir(path: str) -> str:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    return path


def _call_router_model(model_id: str, prompt: str, max_new_tokens: int = 256, temperature: float = 0.2, timeout: int = 60):
    if not HUGGINGFACE_API_KEY:
        raise RuntimeError("HUGGINGFACE_API_KEY not set in environment.")
    url = f"https://router.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": max_new_tokens, "temperature": temperature},
        "options": {"use_cache": False},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code != 200:
        # include server body in exception for debugging
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        raise RuntimeError(f"HTTP {resp.status_code} - {body}")
    try:
        data = resp.json()
    except ValueError:
        return resp.text.strip()

    # parse common shapes
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and "generated_text" in first:
            return str(first["generated_text"]).strip()
        return json.dumps(first)[:4000]
    if isinstance(data, dict):
        if "generated_text" in data:
            return str(data["generated_text"]).strip()
        if "outputs" in data and isinstance(data["outputs"], list) and data["outputs"]:
            out0 = data["outputs"][0]
            if isinstance(out0, dict) and "generated_text" in out0:
                return str(out0["generated_text"]).strip()
            return json.dumps(out0)[:4000]
        if "error" in data:
            raise RuntimeError(f"HF Router error: {data.get('error')}")
        return json.dumps(data)[:4000]
    return str(data)[:4000]


def call_llm(prompt: str, max_new_tokens: int = 256, temperature: float = 0.2,
             hf_fallback_model: Optional[str] = None, timeout: int = 60) -> str:
    """
    Returns generated text, or error/diagnostic string starting with [LLM error:] or [LLM diag:].
    """
    if not HUGGINGFACE_API_KEY:
        return "[LLM not configured: set HUGGINGFACE_API_KEY in environment]"

    primary = HF_MODEL
    try:
        res = _call_router_model(primary, prompt, max_new_tokens=max_new_tokens, temperature=temperature, timeout=timeout)
        if res is None or str(res).strip() == "":
            return "[LLM diag: model returned no text]"
        return res
    except Exception as primary_exc:
        if hf_fallback_model and hf_fallback_model != primary:
            try:
                fallback_res = _call_router_model(hf_fallback_model, prompt, max_new_tokens=max_new_tokens, temperature=temperature, timeout=timeout)
                note = f"[NOTE: primary model '{primary}' failed: {primary_exc}; used fallback '{hf_fallback_model}']\n\n"
                return note + fallback_res
            except Exception as fallback_exc:
                return f"[LLM error: primary failed: {primary_exc} ; fallback failed: {fallback_exc}]"
        return f"[LLM error: {primary_exc}]"

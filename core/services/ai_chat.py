from __future__ import annotations
import os
import json
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


DEFAULT_SYSTEM_PROMPT = (
    "You are Solixa, a power grid emergency assistant. "
    "Given county risk data, respond in under 120 words: "
    "one sentence on current risk, then 3 bullet-point action steps. "
    "Be direct and practical."
)


# ── Azure OpenAI (Responses API) ─────────────────────────────────────────────
def _try_azure(user_text: str) -> str | None:
    endpoint = os.environ.get("AZURE_OPENAI_RESPONSES_URL")
    api_key  = os.environ.get("AZURE_OPENAI_KEY")
    model    = os.environ.get("AZURE_OPENAI_MODEL", "gpt-4o-mini")
    if not endpoint or not api_key:
        print("[ai_chat] Azure skipped — AZURE_OPENAI_RESPONSES_URL or AZURE_OPENAI_KEY not set")
        return None

    # Try Responses API format first (newer models)
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": DEFAULT_SYSTEM_PROMPT}]},
            {"role": "user",   "content": [{"type": "input_text", "text": user_text}]},
        ],
        "max_output_tokens": 300,
    }
    print(f"[ai_chat] Trying Azure endpoint: {endpoint[:60]}... model={model}")
    resp = requests.post(
        endpoint,
        headers={"Content-Type": "application/json", "api-key": api_key},
        json=payload,
        timeout=30,
    )
    print(f"[ai_chat] Azure HTTP {resp.status_code}")
    if resp.status_code >= 400:
        error_body = resp.text[:500]
        print(f"[ai_chat] Azure error body: {error_body}")
        # If Responses API is not supported, fall back to Chat Completions on the same endpoint
        base_url = endpoint.split("/openai/responses")[0]
        chat_url = f"{base_url}/openai/deployments/{model}/chat/completions?api-version=2024-02-15-preview"
        print(f"[ai_chat] Retrying as Chat Completions: {chat_url[:60]}...")
        chat_payload = {
            "messages": [
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user",   "content": user_text},
            ],
            "max_tokens": 800,
        }
        chat_resp = requests.post(
            chat_url,
            headers={"Content-Type": "application/json", "api-key": api_key},
            json=chat_payload,
            timeout=30,
        )
        print(f"[ai_chat] Azure Chat Completions HTTP {chat_resp.status_code}")
        if chat_resp.status_code >= 400:
            print(f"[ai_chat] Azure Chat Completions error: {chat_resp.text[:500]}")
            raise ValueError(f"Azure OpenAI error {chat_resp.status_code}: {chat_resp.text[:300]}")
        data = chat_resp.json()
        return data["choices"][0]["message"]["content"]

    data = resp.json()
    print(f"[ai_chat] Azure status={data.get('status')} keys={list(data.keys())[:8]}")

    def _extract_text(d):
        """Try every known location where Azure may place the response text."""
        # Top-level shortcuts
        if d.get("output_text"):
            return d["output_text"]
        # text.value (Responses API v2)
        txt = d.get("text")
        if isinstance(txt, dict) and txt.get("value"):
            return txt["value"]
        if isinstance(txt, str) and txt:
            return txt
        # output array
        for item in d.get("output", []):
            # message → content blocks
            for block in item.get("content", []):
                if block.get("type") in {"output_text", "text"} and block.get("text"):
                    return block["text"]
            if item.get("type") in {"output_text", "text"} and item.get("text"):
                return item["text"]
        # Chat Completions fallback
        if d.get("choices"):
            return d["choices"][0]["message"]["content"]
        return None

    text = _extract_text(data)
    if text:
        return text

    # If incomplete, still try to return whatever partial text was generated
    if data.get("status") == "incomplete":
        partial = _extract_text(data)  # already tried above, but keep for clarity
        if partial:
            return partial
        reason = data.get("incomplete_details", {}).get("reason", "max_tokens")
        print(f"[ai_chat] Azure incomplete ({reason}) — no partial text available")
        return None  # let local fallback handle it

    print(f"[ai_chat] Azure: could not parse text. Keys: {list(data.keys())}")
    return None


# ── Standard OpenAI API (Chat Completions) ────────────────────────────────────
def _try_openai(user_text: str) -> str | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user",   "content": user_text},
        ],
        "max_tokens": 800,
        "temperature": 0.4,
    }
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=30,
    )
    if resp.status_code >= 400:
        raise ValueError(f"OpenAI error {resp.status_code}: {resp.text}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ── Local rule-based fallback (no API key required) ───────────────────────────
def _local_fallback(county_payload: dict) -> str:
    county  = county_payload.get("county", "this county")
    state   = county_payload.get("state", "")
    risk    = float(county_payload.get("risk", 0))
    risk_pct = f"{risk * 100:.1f}%"

    weather = county_payload.get("weather_summary", {})
    nri     = county_payload.get("nri_profile", {})
    gen     = county_payload.get("gen_profile", {})
    prompt  = county_payload.get("prompt", "")

    # Risk tier language
    if risk >= 0.20:
        tier = "HIGH"; tier_desc = "significant"; urgency = "Immediate action is recommended."
    elif risk >= 0.10:
        tier = "ELEVATED"; tier_desc = "moderate"; urgency = "Proactive monitoring is advised."
    elif risk >= 0.05:
        tier = "MODERATE"; tier_desc = "low-to-moderate"; urgency = "Routine preparedness is appropriate."
    else:
        tier = "LOW"; tier_desc = "minimal"; urgency = "No immediate concerns at this time."

    location_str = f"{county}, {state}".strip(", ")

    # Weather context
    weather_lines = []
    max_wind = weather.get("max_wind", 0)
    max_temp = weather.get("max_temp_c", 20)
    alerts   = weather.get("active_alerts", 0)
    if max_wind > 30:
        weather_lines.append(f"Strong winds up to {max_wind} km/h are forecast — a significant factor for transmission lines.")
    if max_temp > 35:
        weather_lines.append(f"Extreme heat ({max_temp}°C) increases grid demand and equipment stress.")
    if alerts > 0:
        weather_lines.append(f"There are {alerts} active NWS weather alert(s) in effect for this area.")
    if not weather_lines:
        weather_lines.append("Weather conditions are within normal operational parameters.")
    weather_text = " ".join(weather_lines)

    # NRI hazards
    hazards = nri.get("hazards", {})
    top_hazards = sorted(hazards.items(), key=lambda x: -x[1])[:3] if hazards else []
    hazard_text = ""
    if top_hazards:
        hazard_list = ", ".join(f"{h} ({v*100:.0f}th percentile)" for h, v in top_hazards)
        hazard_text = f"FEMA's National Risk Index flags the following as top hazards for {location_str}: {hazard_list}."

    # Generation mix
    gen_text = ""
    if gen.get("total_mw", 0) > 0:
        fossil_pct = gen.get("fossil_pct", 0) * 100
        renew_pct  = gen.get("renewable_pct", 0) * 100
        total_mw   = gen.get("total_mw", 0)
        dom        = gen.get("dominant_source", "mixed")
        gen_text = (
            f"The county grid has {total_mw:,.0f} MW of installed capacity, "
            f"with {fossil_pct:.0f}% fossil fuel and {renew_pct:.0f}% renewable generation. "
            f"Dominant source: {dom.title()}."
        )

    # Action steps based on risk tier
    if risk >= 0.20:
        steps = [
            "1. **Alert critical facilities** — notify hospitals, emergency services, and schools immediately.",
            "2. **Pre-position utility crews** in likely impact zones to reduce restoration time.",
            "3. **Activate backup generators** at critical infrastructure and verify fuel levels.",
            "4. **Issue public preparedness advisory** — residents should charge devices and stock 72-hour emergency supplies.",
            "5. **Monitor NOAA/NWS alerts** continuously and update your incident command with hourly risk checks.",
        ]
    elif risk >= 0.10:
        steps = [
            "1. **Brief emergency operations** on current risk level and keep response teams on standby.",
            "2. **Verify backup power systems** at critical facilities are operational.",
            "3. **Review mutual aid agreements** with neighboring utilities in case rapid support is needed.",
            "4. **Advise vulnerable residents** (elderly, medical-dependent) to prepare for potential disruptions.",
            "5. **Increase patrol frequency** on transmission infrastructure in high-wind or high-heat corridors.",
        ]
    else:
        steps = [
            "1. **Maintain routine monitoring** — run scheduled risk checks and log any anomalies in the Monitor tab.",
            "2. **Keep emergency contact lists current** for utility operators and local emergency managers.",
            "3. **Review preparedness plans** seasonally — heat season and storm season require different protocols.",
            "4. **Encourage community awareness** about basic preparedness (72-hour kits, backup phone charging).",
            "5. **Upload inverter or asset telemetry** to the dashboard to improve anomaly detection accuracy.",
        ]

    # Handle custom prompt
    prompt_response = ""
    if prompt:
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["hospital", "school", "shelter", "facility", "critical"]):
            prompt_response = (
                f"\n\n**Regarding critical facilities:** Given a {tier} risk level, "
                "critical facilities should verify backup generator fuel and test transfer switches. "
                "Hospitals should ensure 72+ hour fuel reserves. Schools should review early dismissal protocols."
            )
        elif any(w in prompt_lower for w in ["solar", "inverter", "panel", "pv"]):
            prompt_response = (
                "\n\n**Regarding solar/inverter assets:** Upload your telemetry CSV via the Energy Asset Upload "
                "panel on the Dashboard. The Isolation Forest model will automatically flag anomalous inverters. "
                "High cloud cover or temperature extremes may reduce output — check the Weather panel for forecasts."
            )
        elif any(w in prompt_lower for w in ["sms", "alert", "notify", "text", "message"]):
            prompt_response = (
                "\n\n**Regarding alerts:** Configure SMS notifications in the Alerts page. "
                "Enter a phone number and set your risk threshold. When the live risk check exceeds "
                f"that threshold, a Twilio SMS will dispatch automatically."
            )
        elif any(w in prompt_lower for w in ["compare", "neighbor", "adjacent", "nearby"]):
            prompt_response = (
                "\n\n**Regarding comparisons:** Use the Compare page to add multiple counties side-by-side. "
                "You can search by name or click 'Add From Map' after selecting counties on the Dashboard."
            )
        else:
            prompt_response = (
                f"\n\n**Regarding your question:** Based on current data for {location_str}, "
                f"the {tier_desc} risk level ({risk_pct}) suggests {urgency.lower()} "
                "For specific asset or facility guidance, please provide more details about your infrastructure type."
            )

    # Compose full response
    lines = [
        f"## Solixa Risk Brief — {location_str}",
        f"**Current Risk: {risk_pct} ({tier})** — {tier_desc.capitalize()} blackout probability. {urgency}",
        "",
        f"**Weather Outlook:** {weather_text}",
    ]
    if hazard_text:
        lines += ["", f"**Hazard Profile:** {hazard_text}"]
    if gen_text:
        lines += ["", f"**Grid Profile:** {gen_text}"]
    lines += [
        "",
        "**Recommended Actions:**",
        *steps,
    ]
    if prompt_response:
        lines.append(prompt_response)
    lines += [
        "",
        "*This analysis is generated by Solixa's local risk engine. Connect an Azure OpenAI or OpenAI API key in your .env for AI-powered responses.*",
    ]
    return "\n".join(lines)


# ── Public entry point ────────────────────────────────────────────────────────
def ask_county_summary(county_payload: dict) -> str:
    # Build a compact summary — avoids burning tokens on raw dict formatting
    county  = county_payload.get("county", "Unknown County")
    state   = county_payload.get("state", "")
    risk    = float(county_payload.get("risk", 0))
    source  = county_payload.get("energy_source", "grid")
    wx      = county_payload.get("weather_summary", {})
    prompt  = county_payload.get("prompt", "")

    summary = (
        f"Location: {county}, {state} | Risk: {risk*100:.1f}% | Energy: {source} | "
        f"Wind: {wx.get('max_wind','?')} m/s | Temp: {wx.get('max_temp_c','?')}°C | "
        f"Precip: {wx.get('total_precip_72h','?')}mm | NWS alerts: {wx.get('active_alerts',0)}"
    )
    user_text = summary
    if prompt:
        user_text += f"\n\nQuestion: {prompt}"
    else:
        user_text += "\n\nBriefly assess the risk and give 3 action steps."

    # Try each provider in order; fall back to local engine
    for provider_fn in (_try_azure, _try_openai):
        try:
            result = provider_fn(user_text)
            if result:
                print(f"[ai_chat] Success via {provider_fn.__name__}")
                return result
        except Exception as e:
            print(f"[ai_chat] {provider_fn.__name__} FAILED: {type(e).__name__}: {e}")

    print("[ai_chat] All providers failed — using local rule-based engine")
    return _local_fallback(county_payload)

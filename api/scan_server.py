#!/usr/bin/env python3
"""
Data Pilots - Trust Scan API  v2
Partial (free-tier) website trust check + Papaya consent analysis.

Usage:
    python3 api/scan_server.py [--port 3001]

Endpoints:
    POST /scan                     { "url": "https://example.com" }
    GET  /papaya/<session_id>      Poll for Papaya findings after initial scan
    GET  /health
"""

import json
import sys
import re
import ssl
import time
import threading
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
PORT              = 3001
TIMEOUT           = 6            # seconds per individual HTTP check
MAX_HTML_BYTES    = 80_000        # bytes for content checks (keywords, etc.)
MAX_FOOTER_BYTES  = 400_000       # enough to reach footer on large CMS-built sites
PAPAYA_API_BASE   = "https://papaya-consent-check-be11a0846ed5.herokuapp.com/api/v1"
PAPAYA_API_KEY    = "cck_live_270ac2d1_NUoykoCcU_5ux3cvXRy0enhmysyvTgjX"
PAPAYA_MAX_WAIT   = 180          # max seconds to wait for a Papaya run to complete
PAPAYA_POLL_SLEEP = 6            # seconds between status polls

PRIVACY_PATHS = ["/privacy-policy", "/privacy", "/privacy.html",
                 "/data-protection", "/data-privacy", "/cookie-policy", "/gdpr"]
TERMS_PATHS   = ["/terms", "/terms-of-service", "/terms-and-conditions",
                 "/legal", "/tos", "/terms.html", "/legal-notice"]
CONTACT_PATHS = ["/contact", "/contact-us", "/about", "/get-in-touch", "/about-us"]

AI_KEYWORDS = [
    "artificial intelligence", "ai-powered", "ai powered", "powered by ai",
    "machine learning", "chatgpt", "openai", "generative ai", "llm",
    "large language model", "ai assistant", "ai insights",
    "ai-generated", "ai generated",
]
COOKIE_KEYWORDS = [
    "cookie", "gdpr", "ccpa", "consent", "data protection",
    "we use cookies", "privacy preference",
]
GDPR_KEYWORDS = [
    "gdpr", "general data protection regulation", "data controller",
    "data processor", "right to access", "right to erasure", "right to be forgotten",
    "lawful basis", "legitimate interest", "data subject rights", "supervisory authority",
]
CCPA_KEYWORDS = [
    "ccpa", "california consumer privacy", "do not sell my",
    "right to know", "right to delete", "opt-out of sale",
]
DPA_KEYWORDS = [
    "data processing agreement", " dpa ", "data processor agreement",
    "sub-processor", "standard contractual clauses", "model clauses",
]
POLICY_REQUIRED_TOPICS = {
    "what is collected": ["we collect", "information we collect", "data we collect", "personal data we collect", "personal information we collect"],
    "why it is collected": ["we use your", "purposes", "why we collect", "legal basis", "how we use"],
    "third-party sharing": ["third party", "third-party", "share your data", "we share", "disclose to", "our partners"],
    "your rights":         ["your rights", "right to access", "right to delete", "right to object", "opt out", "opt-out"],
    "contact details":     ["contact us", "data controller", "data protection officer", "dpo@", "privacy@", "info@"],
}
COOKIE_POLICY_PATHS = ["/cookie-policy", "/cookie-notice", "/cookies", "/cookie-disclosure"]

# In-memory cache: session_id → { status, findings, error, started_at }
_papaya_cache = {}
_papaya_lock  = threading.Lock()


# ─────────────────────────────────────────────
# Generic HTTP helpers
# ─────────────────────────────────────────────
def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_OPTIONAL
    return ctx


def fetch(url: str, method="GET", headers=None, body=None, max_bytes=MAX_HTML_BYTES) -> dict:
    """Returns { ok, status, headers, body, text, error }"""
    req_headers = {
        "User-Agent": "DataPilots-TrustCheck/1.0 (+https://datapilots.tech)",
    }
    if headers:
        req_headers.update(headers)

    data = json.dumps(body).encode() if body else None
    if data:
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ssl_ctx()) as resp:
            raw = resp.read(max_bytes)
            ct  = resp.headers.get("Content-Type", "")
            text = raw.decode("utf-8", errors="replace")
            parsed = None
            try:
                if "json" in ct:
                    parsed = json.loads(raw)
            except Exception:
                pass
            return {
                "ok": True, "status": resp.status,
                "headers": dict(resp.headers),
                "text": text, "data": parsed, "error": None,
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "headers": {}, "text": "", "data": None, "error": str(e)}
    except Exception as e:
        return {"ok": False, "status": None, "headers": {}, "text": "", "data": None, "error": str(e)}


def page_exists(base: str, paths: list) -> tuple:
    """Check if any of the given paths exist. Uses GET with tiny read to follow redirects."""
    for path in paths:
        r = fetch(base + path, method="GET", max_bytes=500)
        if r["ok"] and r["status"] and r["status"] < 400:
            return True, path
    return False, None


# ─────────────────────────────────────────────
# Papaya API helpers
# ─────────────────────────────────────────────
def papaya_call(method: str, path: str, body=None, max_bytes=100_000) -> dict:
    """Authenticated call to Papaya API. Returns fetch-style dict."""
    url = PAPAYA_API_BASE + path
    return fetch(
        url, method=method,
        headers={"Authorization": f"Bearer {PAPAYA_API_KEY}"},
        body=body, max_bytes=max_bytes,
    )


def papaya_start_run(url: str):
    """Start a Papaya consent check run. Returns session_id or None on failure."""
    resp = papaya_call("POST", "/runs", {
        "url": url,
        "task": "reject_all",
        "state": "US-CA",
        "wait_for_debug_url_seconds": 2,
    })
    if not resp["ok"] or not resp["data"]:
        print(f"  [Papaya] start failed: {resp.get('error')} status={resp.get('status')}", flush=True)
        return None
    sid = resp["data"].get("session_id")
    print(f"  [Papaya] run started  session_id={sid}", flush=True)
    return sid


def papaya_poll_until_done(session_id: str) -> dict:
    """
    Block until the Papaya run is complete.
    Returns the final run data dict on success, or {} on timeout/failure.
    The run data may include screenshot_url / debug_url from Papaya's response.
    """
    deadline = time.time() + PAPAYA_MAX_WAIT
    while time.time() < deadline:
        resp = papaya_call("GET", f"/runs/{session_id}")
        if not resp["ok"] or not resp["data"]:
            print(f"  [Papaya] poll error: {resp.get('error')}", flush=True)
            return {}
        run_data = resp["data"]
        status   = run_data.get("status", "")
        progress = run_data.get("progress", 0)
        print(f"  [Papaya] status={status} progress={progress}%", flush=True)
        if status == "completed":
            return run_data
        if status in ("failed", "error"):
            return {}
        time.sleep(PAPAYA_POLL_SLEEP)
    print(f"  [Papaya] timed out after {PAPAYA_MAX_WAIT}s", flush=True)
    return {}


def papaya_fetch_report(session_id: str) -> str:
    """Fetch the markdown report for a completed run."""
    resp = papaya_call("GET", f"/runs/{session_id}/report", max_bytes=200_000)
    if resp["ok"] and resp["text"]:
        print(f"  [Papaya] report fetched  {len(resp['text'])} chars", flush=True)
        return resp["text"]
    return ""


def papaya_fetch_analysis(session_id: str) -> str:
    """
    Kick off and wait for the AI analysis summary HTML.
    Returns the summary HTML string or empty string.
    """
    # Start background generation
    papaya_call("POST", f"/runs/{session_id}/analysis", {"force_regenerate": False})
    # Poll until complete (shorter timeout — analysis is optional)
    deadline = time.time() + 60
    while time.time() < deadline:
        resp = papaya_call("GET", f"/runs/{session_id}/analysis")
        if resp["ok"] and resp["data"]:
            st  = resp["data"].get("status", "")
            sum = resp["data"].get("summary") or ""
            if st == "completed" and sum:
                print(f"  [Papaya] analysis ready  {len(sum)} chars", flush=True)
                return sum
            if st in ("failed", "error"):
                return ""
        time.sleep(5)
    return ""


def papaya_delete_run(session_id: str) -> bool:
    """
    Request deletion of a Papaya run.
    Called immediately after we have parsed results — Papaya's copy is no longer needed.
    Returns True if deletion was confirmed, False if the endpoint is unavailable or errors.
    Failures are non-fatal: results are already in local cache regardless.
    """
    resp = papaya_call("DELETE", f"/runs/{session_id}")
    if resp["ok"] or resp.get("status") in (200, 204):
        print(f"  [Papaya] run deleted  session={session_id}", flush=True)
        return True
    # Some APIs return 404 if already deleted — treat as success
    if resp.get("status") == 404:
        print(f"  [Papaya] run already gone  session={session_id}", flush=True)
        return True
    print(f"  [Papaya] delete failed (non-fatal)  status={resp.get('status')}  session={session_id}", flush=True)
    return False


# ─────────────────────────────────────────────
# Papaya report parser → trust findings
# ─────────────────────────────────────────────
def _extract_tracker_count(text: str, section_keyword: str) -> int:
    """Pull 'Trackers Detected: N' from a named section of the report."""
    idx = text.lower().find(section_keyword.lower())
    if idx == -1:
        return -1
    snippet = text[idx: idx + 600]
    m = re.search(r"trackers detected[:\s]+(\d+)", snippet, re.IGNORECASE)
    return int(m.group(1)) if m else -1


def _extract_tracking_companies(text: str) -> list:
    """Extract named tracking companies from the report."""
    companies = re.findall(r"\*\*([^*]+)\*\*\s*\n\s*\n", text)
    # Also look for '- **Company Name**' pattern
    companies += re.findall(r"[-•]\s+\*\*([^*]+)\*\*", text)
    # Deduplicate, ignore section headers
    seen, result = set(), []
    for c in companies:
        c = c.strip()
        if c and c not in seen and len(c) < 80:
            seen.add(c)
            result.append(c)
    return result


def _extract_cmp_name(text: str) -> str:
    """Try to identify the Consent Management Platform from the Papaya report."""
    cmp_map = {
        "OneTrust":    r"onetrust",
        "Cookiebot":   r"cookiebot|cybot",
        "Quantcast":   r"quantcast",
        "TrustArc":    r"trustarc",
        "Didomi":      r"didomi",
        "Usercentrics":r"usercentrics",
        "Osano":       r"osano",
        "CookieYes":   r"cookieyes",
        "Borlabs":     r"borlabs",
        "CookiePro":   r"cookiepro",
    }
    lower = text.lower()
    for name, pattern in cmp_map.items():
        if re.search(pattern, lower):
            return name
    return ""


def _extract_consent_categories(text: str) -> list:
    """Extract consent category names offered in the consent banner."""
    lower = text.lower()
    # Common consent category names
    standard = [
        "necessary", "essential", "strictly necessary",
        "analytics", "performance", "statistics",
        "marketing", "advertising", "targeting",
        "preferences", "functional",
        "social media",
    ]
    found = [c for c in standard if c in lower]
    return found[:6]


def parse_papaya_report(report_md: str, analysis_html: str = "") -> list:
    """
    Convert a Papaya markdown report into Data Pilots trust findings.
    Parses the actual Papaya report format: tracker counts pre/post consent,
    action log, banner detection, company names.
    """
    findings = []
    text = report_md  # keep original case for regex; use .lower() for keywords

    # ── 1. Cookie consent banner ──────────────
    # Papaya report has "Cookie Banner Analysis" section + action log entries
    has_banner = bool(re.search(
        r"(cookie banner analysis|consent banner|decline all|reject all button|accept.*button.*external)",
        text, re.IGNORECASE
    ))
    reject_btn_found = bool(re.search(
        r"(reject all button.*✅|successfully clicked reject|decline all.*button|reject_all_button)",
        text, re.IGNORECASE
    ))

    if has_banner:
        findings.append({
            "id": "papaya_banner", "pillar": "transparency", "status": "pass",
            "title": "Cookie consent banner confirmed (Papaya)",
            "detail": (
                "Papaya's AI browser agent visited your site and confirmed a cookie consent "
                "banner is present with Accept, Decline All, and Settings options."
            ),
            "tag": None, "source": "papaya",
        })
    else:
        findings.append({
            "id": "papaya_banner", "pillar": "transparency", "status": "fail",
            "title": "No cookie consent banner detected (Papaya)",
            "detail": (
                "Papaya's browser agent found no cookie consent mechanism. "
                "GDPR and CCPA require most sites to give visitors a clear choice "
                "about data collection before it starts."
            ),
            "tag": "FIX THIS WEEK", "source": "papaya",
        })

    # ── 2. Reject-all effectiveness ───────────
    # Compare pre-consent vs post-consent tracker counts
    pre_count  = _extract_tracker_count(text, "Initial Page Load (Before Consent)")
    post_count = _extract_tracker_count(text, "Post-Consent Analysis")

    if pre_count >= 0 and post_count >= 0:
        if post_count >= pre_count * 0.9:
            # Trackers barely changed after rejection — not honoured
            findings.append({
                "id": "papaya_reject", "pillar": "transparency", "status": "fail",
                "title": f"Reject-all not honoured — {post_count} trackers still active (Papaya)",
                "detail": (
                    f"Papaya found {pre_count} trackers before consent and {post_count} after "
                    f"a visitor clicked 'Decline All'. Tracking should stop on rejection. "
                    f"This is a GDPR violation and the kind of issue that gets flagged in "
                    f"enterprise procurement security reviews."
                ),
                "tag": "FIX THIS WEEK", "source": "papaya",
            })
        elif post_count == 0 or post_count < pre_count * 0.2:
            findings.append({
                "id": "papaya_reject", "pillar": "transparency", "status": "pass",
                "title": "Reject-all correctly honoured (Papaya)",
                "detail": (
                    f"Papaya confirmed tracking dropped from {pre_count} to {post_count} "
                    f"after a visitor clicked 'Decline All'. Well handled."
                ),
                "tag": None, "source": "papaya",
            })
        else:
            findings.append({
                "id": "papaya_reject", "pillar": "transparency", "status": "warn",
                "title": f"Partial tracking reduction after rejection — {post_count} trackers remain (Papaya)",
                "detail": (
                    f"Papaya found {pre_count} trackers before consent. After 'Decline All', "
                    f"{post_count} were still active. All non-essential tracking should stop "
                    f"on rejection to meet GDPR requirements."
                ),
                "tag": "FIX THIS WEEK", "source": "papaya",
            })

    # ── 3. Pre-consent tracking volume ────────
    if pre_count > 20:
        companies = _extract_tracking_companies(text)
        company_str = ", ".join(companies[:3]) if companies else "third-party services"
        findings.append({
            "id": "papaya_preload", "pillar": "transparency", "status": "warn",
            "title": f"{pre_count} trackers active before any consent is given (Papaya)",
            "detail": (
                f"Papaya detected {pre_count} tracking requests firing on page load — "
                f"before a visitor has accepted anything. "
                f"Tracking companies include: {company_str}. "
                f"GDPR requires consent to be collected before non-essential tracking starts."
            ),
            "tag": "FIX THIS WEEK" if pre_count > 50 else "REVIEW",
            "source": "papaya",
        })
    elif pre_count == 0:
        findings.append({
            "id": "papaya_preload", "pillar": "transparency", "status": "pass",
            "title": "No trackers active before consent (Papaya)",
            "detail": "Papaya found no third-party tracking firing before a visitor gives consent. Good privacy practice.",
            "tag": None, "source": "papaya",
        })

    # ── 4. CMP identification ─────────────────
    cmp = _extract_cmp_name(text)
    if cmp:
        findings.append({
            "id": "papaya_cmp", "pillar": "transparency", "status": "pass",
            "title": f"Consent managed via {cmp} (Papaya)",
            "detail": (
                f"Papaya identified {cmp} as your Consent Management Platform. "
                f"Using a recognised CMP signals mature data governance — enterprise "
                f"procurement teams often verify this."
            ),
            "tag": None, "source": "papaya",
        })
    else:
        findings.append({
            "id": "papaya_cmp", "pillar": "transparency", "status": "info",
            "title": "Consent platform vendor not identified (Papaya)",
            "detail": (
                "Papaya could not identify a standard CMP on your site. "
                "If you are self-building consent logic, make sure it meets GDPR requirements "
                "for explicit, granular, withdrawable consent."
            ),
            "tag": None, "source": "papaya",
        })

    # ── 5. Consent categories ─────────────────
    categories = _extract_consent_categories(text)
    if categories:
        findings.append({
            "id": "papaya_categories", "pillar": "transparency", "status": "pass",
            "title": f"{len(categories)} consent categories detected in banner (Papaya)",
            "detail": (
                f"Categories offered: {', '.join(c.title() for c in categories)}. "
                f"Granular consent categories are required under GDPR and signal to "
                f"enterprise clients that your consent framework is properly structured."
            ),
            "tag": None, "source": "papaya",
        })
    elif has_banner:
        findings.append({
            "id": "papaya_categories", "pillar": "transparency", "status": "warn",
            "title": "Consent banner found but no granular categories detected (Papaya)",
            "detail": (
                "Your consent banner exists but may not offer category-level choice. "
                "GDPR requires separate consent for analytics, marketing, and functional cookies "
                "— a blanket accept/reject may not be sufficient."
            ),
            "tag": "REVIEW", "source": "papaya",
        })

    return findings


# ─────────────────────────────────────────────
# Papaya background worker
# ─────────────────────────────────────────────
def _papaya_worker(session_id: str, target_url: str, tier: str = "free"):
    """
    Runs in a background thread.
    Polls until Papaya completes, fetches report + analysis, parses findings,
    stores everything in _papaya_cache.

    tier="free"  → Papaya run deleted immediately after parsing (privacy-first).
    tier="paid"  → Papaya run preserved; session_id stays valid for deeper access
                   by the user's account. Deletion happens explicitly on account
                   request or after the paid retention TTL.
    """
    try:
        run_data = papaya_poll_until_done(session_id)
        if not run_data:
            with _papaya_lock:
                _papaya_cache[session_id] = {
                    "status": "failed", "findings": [], "error": "Papaya timed out or failed",
                    "cached_at": time.time(), "tier": tier,
                }
            return

        # Extract screenshot URL from run data (Papaya may return screenshot_url or debug_url)
        screenshot_url = (
            run_data.get("screenshot_url") or
            run_data.get("debug_url") or
            run_data.get("screenshot") or
            ""
        )

        report_md     = papaya_fetch_report(session_id)
        analysis_html = papaya_fetch_analysis(session_id)
        findings      = parse_papaya_report(report_md, analysis_html)

        # ── Privacy: free scans → delete from Papaya immediately ──
        # Paid scans → preserve Papaya session for account-level access
        deleted = False
        if tier == "free":
            deleted = papaya_delete_run(session_id)
        else:
            print(f"  [Papaya] paid scan — run preserved  session={session_id}", flush=True)

        results_url = f"https://papaya-consent-check-be11a0846ed5.herokuapp.com/results/{session_id}"

        with _papaya_lock:
            _papaya_cache[session_id] = {
                "status":               "completed",
                "findings":             findings,
                "screenshot_url":       screenshot_url,
                "results_url":          results_url,
                "report_len":           len(report_md),
                "tier":                 tier,
                "papaya_data_deleted":  deleted,
                "cached_at":            time.time(),
                "error":                None,
            }
        print(f"  [Papaya] worker done  tier={tier}  {len(findings)} findings  screenshot={'yes' if screenshot_url else 'no'}  deleted={deleted}  session={session_id}", flush=True)

    except Exception as e:
        print(f"  [Papaya] worker error: {e}", flush=True)
        with _papaya_lock:
            _papaya_cache[session_id] = {
                "status": "failed", "findings": [], "error": str(e),
                "cached_at": time.time(), "tier": tier,
            }


def launch_papaya_background(target_url: str, tier: str = "free"):
    """
    Start a Papaya run and kick off a background thread to wait for it.
    Returns the session_id immediately (or None on failure to start).
    tier is passed through to _papaya_worker to control deletion behaviour.
    """
    session_id = papaya_start_run(target_url)
    if not session_id:
        return None

    with _papaya_lock:
        _papaya_cache[session_id] = {
            "status": "running", "findings": [], "error": None,
            "cached_at": time.time(), "tier": tier,
        }

    t = threading.Thread(target=_papaya_worker, args=(session_id, target_url, tier), daemon=True)
    t.start()
    return session_id


# ── Local cache TTL cleanup ──────────────────────────────────────────────────
# Papaya's copy is deleted immediately after parsing (above).
# Our local in-memory cache is cleared after 1 hour so the server doesn't
# accumulate stale sessions across a long uptime.
_CACHE_TTL_SECONDS = 3600  # 1 hour

def _cache_cleanup_worker():
    """Background thread: remove _papaya_cache entries older than TTL."""
    while True:
        time.sleep(600)  # run every 10 minutes
        cutoff = time.time() - _CACHE_TTL_SECONDS
        with _papaya_lock:
            stale = [sid for sid, v in _papaya_cache.items()
                     if v.get("cached_at", 0) < cutoff]
            for sid in stale:
                del _papaya_cache[sid]
        if stale:
            print(f"  [Cache] evicted {len(stale)} stale session(s)", flush=True)

_cleanup_thread = threading.Thread(target=_cache_cleanup_worker, daemon=True)
_cleanup_thread.start()


# ─────────────────────────────────────────────
# Individual trust checks  (fast, own logic)
# ─────────────────────────────────────────────
def check_https(base: str, home: dict) -> dict:
    is_https = base.startswith("https://")
    if is_https and home["ok"]:
        return {"id": "https", "pillar": "safety", "status": "pass",
                "title": "Site uses HTTPS",
                "detail": "Your connection is encrypted. Buyers can see the padlock in the browser bar.",
                "tag": None}
    elif not is_https:
        return {"id": "https", "pillar": "safety", "status": "fail",
                "title": "Site is not on HTTPS",
                "detail": "Browsers mark non-HTTPS sites as 'Not Secure'. This is an immediate red flag for any buyer checking your site before a meeting.",
                "tag": "FIX THIS WEEK"}
    else:
        return {"id": "https", "pillar": "safety", "status": "warn",
                "title": "HTTPS but site did not respond cleanly",
                "detail": "Your URL starts with HTTPS but the site returned an error. Check your hosting.",
                "tag": "REVIEW"}


def check_security_headers(headers: dict) -> list:
    findings = []
    h = {k.lower(): v for k, v in headers.items()}

    if "content-security-policy" not in h:
        findings.append({
            "id": "csp", "pillar": "safety", "status": "warn",
            "title": "No Content Security Policy header",
            "detail": "CSP is a standard browser protection. Procurement security questionnaires often ask about it. A developer can add it in under an hour.",
            "tag": "REVIEW"
        })
    else:
        findings.append({"id": "csp", "pillar": "safety", "status": "pass",
                         "title": "Content Security Policy header present", "detail": None, "tag": None})

    if "x-frame-options" not in h and "content-security-policy" not in h:
        findings.append({
            "id": "xfo", "pillar": "safety", "status": "warn",
            "title": "No clickjacking protection header",
            "detail": "X-Frame-Options or CSP prevents your site being embedded in malicious pages. Easy to add.",
            "tag": "REVIEW"
        })

    if "strict-transport-security" not in h:
        findings.append({
            "id": "hsts", "pillar": "safety", "status": "warn",
            "title": "HSTS not enabled",
            "detail": "HSTS tells browsers to always use HTTPS. Without it, the first connection could be intercepted.",
            "tag": "QUICK WIN"
        })
    else:
        findings.append({"id": "hsts", "pillar": "safety", "status": "pass",
                         "title": "HSTS enabled", "detail": None, "tag": None})

    return findings


def check_privacy_page(base: str) -> dict:
    found, path = page_exists(base, PRIVACY_PATHS)
    if found:
        return {"id": "privacy", "pillar": "transparency", "status": "pass",
                "title": f"Privacy page found ({path})",
                "detail": "Buyers and procurement teams expect to see a privacy policy. You have one.",
                "tag": None}
    return {"id": "privacy", "pillar": "transparency", "status": "fail",
            "title": "No privacy page detected",
            "detail": "Over 70% of B2B buyers check for a privacy policy before signing. A missing policy is the most common trust-killer we find.",
            "tag": "FIX THIS WEEK"}


def check_terms_page(base: str) -> dict:
    found, path = page_exists(base, TERMS_PATHS)
    if found:
        return {"id": "terms", "pillar": "transparency", "status": "pass",
                "title": f"Terms of service found ({path})",
                "detail": "Your terms are findable. Good.", "tag": None}
    return {"id": "terms", "pillar": "transparency", "status": "warn",
            "title": "No terms of service page detected",
            "detail": "Enterprise procurement often requires a link to your terms. A missing terms page can stall a deal.",
            "tag": "QUICK WIN"}


def check_contact_page(base: str) -> dict:
    found, path = page_exists(base, CONTACT_PATHS)
    if found:
        return {"id": "contact", "pillar": "ux", "status": "pass",
                "title": f"Contact page found ({path})",
                "detail": "Buyers can find a way to reach you. This matters for trust.", "tag": None}
    return {"id": "contact", "pillar": "ux", "status": "warn",
            "title": "No contact page detected",
            "detail": "If a buyer can't easily find how to contact you, they lose confidence. A visible contact page lifts trust scores.",
            "tag": "QUICK WIN"}


def check_ai_disclosure(html: str) -> dict:
    lower = html.lower()
    if any(kw in lower for kw in AI_KEYWORDS):
        return {"id": "ai_disclose", "pillar": "ai_trust", "status": "pass",
                "title": "AI tool mention found on site",
                "detail": "Your site mentions AI tools or partners. Transparent AI disclosure builds buyer confidence.",
                "tag": None}
    return {"id": "ai_disclose", "pillar": "ai_trust", "status": "warn",
            "title": "No AI disclosure found on public site",
            "detail": "Over half of enterprise L&D buyers now ask about AI use before signing. If you use AI tools, a short note on your site prevents the question coming up in procurement.",
            "tag": "QUICK WIN"}


def check_cookie_consent(html: str) -> dict:
    lower = html.lower()
    found = [kw for kw in COOKIE_KEYWORDS if kw in lower]
    if len(found) >= 2:
        return {"id": "cookies", "pillar": "transparency", "status": "pass",
                "title": "Cookie or consent language found",
                "detail": "Your site appears to address cookies and consent. This is expected by EU and enterprise buyers.",
                "tag": None}
    return {"id": "cookies", "pillar": "transparency", "status": "warn",
            "title": "No cookie consent language detected",
            "detail": "GDPR requires most sites to inform visitors about cookies. Missing consent banners are a common finding in procurement reviews.",
            "tag": "REVIEW"}


def check_footer_policy_links(html: str, full_html: str = "") -> list:
    """
    Check whether Privacy, Terms, and Cookie policy links appear in the footer.
    full_html may be a larger fetch of the page used only for footer detection.
    """
    findings = []
    # Prefer the larger full_html for footer search if provided
    search_html = full_html if full_html else html
    lower = search_html.lower()

    # Prefer footer section; fall back to last 8000 chars of whatever we have
    footer_start = lower.rfind("<footer")
    footer_text  = lower[footer_start:] if footer_start != -1 else lower[-8000:]

    has_privacy = bool(re.search(r'href=["\'][^"\']*privac[^"\']*["\']', footer_text))
    has_terms   = bool(re.search(r'href=["\'][^"\']*term[^"\']*["\']',   footer_text))
    has_cookie  = bool(re.search(r'href=["\'][^"\']*cook[^"\']*["\']',   footer_text))

    if has_privacy and has_terms:
        findings.append({
            "id": "footer_links", "pillar": "ux", "status": "pass",
            "title": "Privacy Policy and Terms links found in footer",
            "detail": "Policy links are where buyers expect them. This passes the basic procurement page-check.",
            "tag": None,
        })
    elif has_privacy:
        findings.append({
            "id": "footer_links", "pillar": "ux", "status": "warn",
            "title": "Privacy link in footer — Terms link missing",
            "detail": "Enterprise procurement teams look for both. Adding a Terms link is a quick win.",
            "tag": "QUICK WIN",
        })
    else:
        findings.append({
            "id": "footer_links", "pillar": "ux", "status": "fail",
            "title": "Policy links not found in footer",
            "detail": (
                "Buyers scan the footer for Privacy Policy and Terms before any meeting. "
                "Not finding them is one of the most common reasons trust drops silently."
            ),
            "tag": "FIX THIS WEEK",
        })

    if has_cookie:
        findings.append({
            "id": "cookie_policy_link", "pillar": "transparency", "status": "pass",
            "title": "Cookie policy/disclosure link found in footer",
            "detail": "A visible cookie disclosure link is good practice and increasingly expected by privacy-aware buyers.",
            "tag": None,
        })

    return findings


def check_policy_content(base: str) -> list:
    """
    Fetch the privacy policy page and analyse its content for:
    - GDPR/CCPA language
    - Coverage of required topics (what, why, sharing, rights, contact)
    - Data Processing Agreement language
    - Cookie policy existence
    - Last-updated date
    """
    findings = []

    # Find the privacy policy URL
    privacy_url = None
    for path in PRIVACY_PATHS:
        r = fetch(base + path, method="HEAD")
        if r["ok"] and r["status"] and r["status"] < 400:
            privacy_url = base + path
            break
    if not privacy_url:
        return findings  # check_privacy_page already reports this

    # Fetch full content (larger limit for policy pages)
    r    = fetch(privacy_url, method="GET", max_bytes=200_000)
    text = r.get("text", "").lower()
    if not text:
        return findings

    # ── GDPR language ──
    has_gdpr = any(kw in text for kw in GDPR_KEYWORDS)
    has_ccpa = any(kw in text for kw in CCPA_KEYWORDS)

    if has_gdpr:
        findings.append({
            "id": "policy_gdpr", "pillar": "transparency", "status": "pass",
            "title": "Privacy policy includes GDPR-aligned language",
            "detail": (
                "Your policy references GDPR concepts (data subject rights, lawful basis, etc.). "
                "This is what EU clients and enterprise procurement teams need to see."
            ),
            "tag": None,
        })
    else:
        findings.append({
            "id": "policy_gdpr", "pillar": "transparency", "status": "warn",
            "title": "Privacy policy doesn't reference GDPR",
            "detail": (
                "If any of your clients are EU-based, your privacy policy should explicitly "
                "address GDPR rights. Enterprise procurement in the UK and Europe will check this."
            ),
            "tag": "REVIEW",
        })

    if has_ccpa:
        findings.append({
            "id": "policy_ccpa", "pillar": "transparency", "status": "pass",
            "title": "Privacy policy addresses CCPA / California consumer rights",
            "detail": "Your policy covers California privacy rights. Good for US enterprise clients.",
            "tag": None,
        })

    # ── Required topic coverage ──
    missing = []
    for topic, keywords in POLICY_REQUIRED_TOPICS.items():
        if not any(kw in text for kw in keywords):
            missing.append(topic)

    if not missing:
        findings.append({
            "id": "policy_coverage", "pillar": "transparency", "status": "pass",
            "title": "Privacy policy covers all required topics",
            "detail": (
                "Your policy explains what data is collected, why, third-party sharing, "
                "visitor rights, and how to get in touch. Strong foundation."
            ),
            "tag": None,
        })
    elif len(missing) <= 2:
        findings.append({
            "id": "policy_coverage", "pillar": "transparency", "status": "warn",
            "title": f"Privacy policy may be missing {len(missing)} required section(s)",
            "detail": (
                f"We couldn't find clear coverage of: {'; '.join(missing)}. "
                f"GDPR Article 13/14 requires these topics to be addressed."
            ),
            "tag": "REVIEW",
        })
    else:
        findings.append({
            "id": "policy_coverage", "pillar": "transparency", "status": "fail",
            "title": f"Privacy policy is missing {len(missing)} required sections",
            "detail": (
                f"Missing: {'; '.join(missing)}. "
                f"A privacy policy that doesn't explain what's collected, why, and how to exercise rights "
                f"is unlikely to satisfy enterprise procurement requirements."
            ),
            "tag": "FIX THIS WEEK",
        })

    # ── DPA language ──
    has_dpa = any(kw in text for kw in DPA_KEYWORDS)
    if has_dpa:
        findings.append({
            "id": "policy_dpa", "pillar": "transparency", "status": "pass",
            "title": "Data Processing Agreement language present",
            "detail": (
                "Your policy references data processing agreements or standard contractual clauses. "
                "Enterprise clients in regulated sectors will often ask for a signed DPA — "
                "having the language in your policy is a good first step."
            ),
            "tag": None,
        })
    else:
        findings.append({
            "id": "policy_dpa", "pillar": "transparency", "status": "info",
            "title": "No Data Processing Agreement language found",
            "detail": (
                "Many enterprise and public sector L&D clients require a Data Processing Agreement "
                "before signing. Adding DPA language to your privacy policy (or offering a separate DPA) "
                "removes a common procurement blocker."
            ),
            "tag": None,
        })

    # ── Last updated date ──
    has_date = bool(re.search(
        r"(last updated|last revised|effective date|updated:)\s*[:\-]?\s*\w+\s+\d{4}",
        text, re.IGNORECASE
    ))
    if not has_date:
        findings.append({
            "id": "policy_date", "pillar": "transparency", "status": "warn",
            "title": "Privacy policy has no 'last updated' date",
            "detail": (
                "Policies without a visible update date look stale. "
                "A dated policy signals active governance — buyers notice when a policy "
                "looks like it hasn't been reviewed in years."
            ),
            "tag": "QUICK WIN",
        })

    # ── Separate cookie policy ──
    found_cookie_policy, _ = page_exists(base, COOKIE_POLICY_PATHS)
    if found_cookie_policy:
        findings.append({
            "id": "cookie_policy_page", "pillar": "transparency", "status": "pass",
            "title": "Separate cookie policy/disclosure page found",
            "detail": "A dedicated cookie disclosure page shows buyers and regulators you take data governance seriously.",
            "tag": None,
        })

    return findings


def check_sitemap(base: str) -> dict:
    r = fetch(base + "/sitemap.xml", method="HEAD")
    if r["ok"] and r["status"] and r["status"] < 400:
        return {"id": "sitemap", "pillar": "ux", "status": "pass",
                "title": "sitemap.xml found",
                "detail": "Good. Your site structure is discoverable.", "tag": None}
    return {"id": "sitemap", "pillar": "ux", "status": "info",
            "title": "No sitemap.xml found",
            "detail": "A sitemap helps search engines and accessibility tools navigate your site. Not critical but worth adding.",
            "tag": None}


# ─────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────
PILLAR_WEIGHTS = {"ux": 25, "transparency": 30, "safety": 30, "ai_trust": 15}
STATUS_SCORE   = {"pass": 1.0, "warn": 0.5, "fail": 0.0, "info": 0.8}

def compute_scores(findings: list) -> dict:
    pillar_totals = {p: [] for p in PILLAR_WEIGHTS}
    for f in findings:
        p = f.get("pillar")
        if p in pillar_totals and f["status"] in STATUS_SCORE:
            pillar_totals[p].append(STATUS_SCORE[f["status"]])

    pillar_scores = {}
    for p, vals in pillar_totals.items():
        pillar_scores[p] = round(sum(vals) / len(vals) * 100) if vals else 50

    weighted = sum(pillar_scores[p] * PILLAR_WEIGHTS[p] / 100 for p in PILLAR_WEIGHTS)
    overall  = round(weighted)

    if overall >= 80:
        label = "Mission Ready"
    elif overall >= 60:
        label = "Pilot Ready"
    elif overall >= 40:
        label = "Pre-Flight"
    else:
        label = "Ground Check Needed"

    return {"overall": overall, "label": label, "pillars": pillar_scores}


# ─────────────────────────────────────────────
# Main scan orchestrator
# ─────────────────────────────────────────────
def normalise_url(raw: str) -> str:
    raw = raw.strip()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    return raw.rstrip("/")


def run_scan(raw_url: str, tier: str = "free") -> dict:
    """
    tier = "free"  → Papaya run deleted immediately after parsing (privacy-first)
    tier = "paid"  → Papaya run preserved; session_id returned for deeper client use
    """
    base = normalise_url(raw_url)

    # Fetch home page: standard read for content checks, larger read for footer
    home         = fetch(base, method="GET", max_bytes=MAX_HTML_BYTES)
    home_full    = fetch(base, method="GET", max_bytes=MAX_FOOTER_BYTES)
    html         = home.get("text", "")
    html_full    = home_full.get("text", html)   # fallback to standard if larger fetch fails
    headers      = home.get("headers", {})

    findings = []

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(check_https,          base, home): "https",
            ex.submit(check_privacy_page,   base):       "privacy",
            ex.submit(check_terms_page,     base):       "terms",
            ex.submit(check_contact_page,   base):       "contact",
            ex.submit(check_ai_disclosure,  html):       "ai",
            ex.submit(check_cookie_consent, html):       "cookies",
            ex.submit(check_sitemap,        base):       "sitemap",
            ex.submit(check_footer_policy_links, html, html_full): "footer_links",
            ex.submit(check_policy_content,      base): "policy_content",
        }
        for future in as_completed(futures, timeout=TIMEOUT + 4):
            try:
                result = future.result()
                if isinstance(result, list):
                    findings.extend(result)
                else:
                    findings.append(result)
            except Exception:
                pass

    # Security headers (uses already-fetched headers — no extra request)
    findings.extend(check_security_headers(headers))

    scores = compute_scores(findings)

    # Surface actionable findings (fail/warn with a tag), priority-sorted
    actionable = [f for f in findings if f["status"] in ("fail", "warn") and f.get("tag")]
    actionable.sort(key=lambda f: {"FIX THIS WEEK": 0, "QUICK WIN": 1, "REVIEW": 2}.get(f.get("tag", ""), 3))

    # Start Papaya in background — don't wait
    papaya_session_id = launch_papaya_background(base, tier=tier)

    return {
        "url":              base,
        "scanned_at":       datetime.utcnow().isoformat() + "Z",
        "score":            scores["overall"],
        "score_label":      scores["label"],
        "tier":             tier,
        "pillars": {
            "ux":           {"score": scores["pillars"]["ux"],           "label": "User Experience"},
            "transparency": {"score": scores["pillars"]["transparency"], "label": "Transparency"},
            "safety":       {"score": scores["pillars"]["safety"],       "label": "Safety"},
            "ai_trust":     {"score": scores["pillars"]["ai_trust"],     "label": "AI Trust"},
        },
        "free_findings":    actionable[:3],
        "total_issues":     len([f for f in findings if f["status"] in ("fail", "warn")]),
        "papaya_session_id": papaya_session_id,
        "papaya_retained":  (tier == "paid"),   # tells frontend whether Papaya data is kept
        "partial":          True,
        "powered_by":       "Papaya",
        "note": (
            "Free check covers your public-facing website. "
            "Upgrade to Co-Pilot to scan your learning portal or platform "
            "and unlock full step-by-step fix guides."
            if tier == "free" else
            "Full Co-Pilot scan. Papaya consent data retained for your account."
        ),
    }


# ─────────────────────────────────────────────
# HTTP Server
# ─────────────────────────────────────────────
class ScanHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {fmt % args}", flush=True)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "service": "Data Pilots Scan API", "version": "2.0"})

        elif self.path.startswith("/papaya/") and self.path.endswith("/report"):
            # GET /papaya/<session_id>/report  →  full results: findings + screenshot
            # Only available once status = completed
            session_id = self.path[len("/papaya/"):][:-len("/report")].strip("/")
            with _papaya_lock:
                cached = _papaya_cache.get(session_id)
            if cached is None:
                self._send_json({"error": "Session not found"}, 404)
            elif cached.get("status") != "completed":
                self._send_json({"error": "Report not ready", "status": cached.get("status", "running")}, 202)
            else:
                self._send_json({
                    "status":        "completed",
                    "findings":      cached.get("findings", []),
                    "screenshot_url": cached.get("screenshot_url", ""),
                    "report_url":    cached.get("results_url", ""),
                })

        elif self.path.startswith("/papaya/"):
            # GET /papaya/<session_id>  →  status only (lightweight poll)
            session_id = self.path[len("/papaya/"):].strip("/")
            with _papaya_lock:
                cached = _papaya_cache.get(session_id)
            if cached is None:
                self._send_json({"error": "Session not found"}, 404)
            else:
                # Return minimal status response — no findings in status poll
                self._send_json({
                    "status":  cached.get("status", "running"),
                    "error":   cached.get("error"),
                })

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path != "/scan":
            self._send_json({"error": "Not found"}, 404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        raw_url = payload.get("url", "").strip()
        if not raw_url:
            self._send_json({"error": "url is required"}, 400)
            return

        tier = payload.get("tier", "free")
        if tier not in ("free", "paid"):
            tier = "free"

        print(f"  Scanning: {raw_url}  tier={tier}", flush=True)
        try:
            result = run_scan(raw_url, tier=tier)
            self._send_json(result)
        except Exception as e:
            self._send_json({"error": f"Scan failed: {str(e)}"}, 500)


def main():
    port = PORT
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])

    server = HTTPServer(("0.0.0.0", port), ScanHandler)
    print(f"Data Pilots Scan API v2  http://localhost:{port}", flush=True)
    print(f"  POST /scan                  {{\"url\":\"https://example.com\"}}", flush=True)
    print(f"  GET  /papaya/<id>           poll status (lightweight — no findings)", flush=True)
    print(f"  GET  /papaya/<id>/report    full results: findings + screenshot (completed only)", flush=True)
    print(f"  GET  /health", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

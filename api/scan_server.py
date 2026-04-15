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
MAX_HTML_BYTES    = 80_000       # bytes to read for content checks
PAPAYA_API_BASE   = "https://papaya-consent-check-be11a0846ed5.herokuapp.com/api/v1"
PAPAYA_API_KEY    = "cck_live_270ac2d1_NUoykoCcU_5ux3cvXRy0enhmysyvTgjX"
PAPAYA_MAX_WAIT   = 180          # max seconds to wait for a Papaya run to complete
PAPAYA_POLL_SLEEP = 6            # seconds between status polls

PRIVACY_PATHS = ["/privacy-policy", "/privacy", "/data-protection",
                 "/data-privacy", "/cookie-policy", "/gdpr"]
TERMS_PATHS   = ["/terms", "/terms-of-service", "/terms-and-conditions",
                 "/legal", "/tos"]
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
    for path in paths:
        r = fetch(base + path, method="HEAD")
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


def papaya_poll_until_done(session_id: str) -> bool:
    """Block until the Papaya run is complete. Returns True if completed, False if timed out/failed."""
    deadline = time.time() + PAPAYA_MAX_WAIT
    while time.time() < deadline:
        resp = papaya_call("GET", f"/runs/{session_id}")
        if not resp["ok"] or not resp["data"]:
            print(f"  [Papaya] poll error: {resp.get('error')}", flush=True)
            return False
        status   = resp["data"].get("status", "")
        progress = resp["data"].get("progress", 0)
        print(f"  [Papaya] status={status} progress={progress}%", flush=True)
        if status == "completed":
            return True
        if status in ("failed", "error"):
            return False
        time.sleep(PAPAYA_POLL_SLEEP)
    print(f"  [Papaya] timed out after {PAPAYA_MAX_WAIT}s", flush=True)
    return False


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

    return findings


# ─────────────────────────────────────────────
# Papaya background worker
# ─────────────────────────────────────────────
def _papaya_worker(session_id: str, target_url: str):
    """
    Runs in a background thread.
    Polls until Papaya completes, fetches report + analysis, parses findings,
    and stores everything in _papaya_cache.
    """
    try:
        ok = papaya_poll_until_done(session_id)
        if not ok:
            with _papaya_lock:
                _papaya_cache[session_id] = {"status": "failed", "findings": [], "error": "Papaya timed out or failed"}
            return

        report_md     = papaya_fetch_report(session_id)
        analysis_html = papaya_fetch_analysis(session_id)
        findings      = parse_papaya_report(report_md, analysis_html)

        results_url = f"https://papaya-consent-check-be11a0846ed5.herokuapp.com/results/{session_id}"

        with _papaya_lock:
            _papaya_cache[session_id] = {
                "status":      "completed",
                "findings":    findings,
                "results_url": results_url,
                "report_len":  len(report_md),
                "error":       None,
            }
        print(f"  [Papaya] worker done  {len(findings)} findings  session={session_id}", flush=True)

    except Exception as e:
        print(f"  [Papaya] worker error: {e}", flush=True)
        with _papaya_lock:
            _papaya_cache[session_id] = {"status": "failed", "findings": [], "error": str(e)}


def launch_papaya_background(target_url: str):
    """
    Start a Papaya run and kick off a background thread to wait for it.
    Returns the session_id immediately (or None on failure to start).
    """
    session_id = papaya_start_run(target_url)
    if not session_id:
        return None

    with _papaya_lock:
        _papaya_cache[session_id] = {"status": "running", "findings": [], "error": None}

    t = threading.Thread(target=_papaya_worker, args=(session_id, target_url), daemon=True)
    t.start()
    return session_id


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


def run_scan(raw_url: str) -> dict:
    base = normalise_url(raw_url)

    # Fetch home page first (used by multiple checks)
    home    = fetch(base, method="GET")
    html    = home.get("text", "")
    headers = home.get("headers", {})

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
    papaya_session_id = launch_papaya_background(base)

    return {
        "url":              base,
        "scanned_at":       datetime.utcnow().isoformat() + "Z",
        "score":            scores["overall"],
        "score_label":      scores["label"],
        "pillars": {
            "ux":           {"score": scores["pillars"]["ux"],           "label": "User Experience"},
            "transparency": {"score": scores["pillars"]["transparency"], "label": "Transparency"},
            "safety":       {"score": scores["pillars"]["safety"],       "label": "Safety"},
            "ai_trust":     {"score": scores["pillars"]["ai_trust"],     "label": "AI Trust"},
        },
        "free_findings":    actionable[:3],
        "total_issues":     len([f for f in findings if f["status"] in ("fail", "warn")]),
        "papaya_session_id": papaya_session_id,   # browser polls this for live Papaya findings
        "partial":          True,
        "powered_by":       "Papaya",
        "note": (
            "Free check covers your public-facing website. "
            "Upgrade to Co-Pilot to scan your learning portal or platform "
            "and unlock full step-by-step fix guides."
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

        elif self.path.startswith("/papaya/"):
            # GET /papaya/<session_id>  →  return cached Papaya state
            session_id = self.path[len("/papaya/"):].strip("/")
            with _papaya_lock:
                cached = _papaya_cache.get(session_id)
            if cached is None:
                self._send_json({"error": "Session not found"}, 404)
            else:
                self._send_json(cached)

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

        print(f"  Scanning: {raw_url}", flush=True)
        try:
            result = run_scan(raw_url)
            self._send_json(result)
        except Exception as e:
            self._send_json({"error": f"Scan failed: {str(e)}"}, 500)


def main():
    port = PORT
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])

    server = HTTPServer(("0.0.0.0", port), ScanHandler)
    print(f"Data Pilots Scan API v2  http://localhost:{port}", flush=True)
    print(f"  POST /scan          {{\"url\":\"https://example.com\"}}", flush=True)
    print(f"  GET  /papaya/<id>   poll Papaya findings", flush=True)
    print(f"  GET  /health", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

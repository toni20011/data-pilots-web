// Thin proxy to Papaya consent check API — keeps API key off the client.
// Cloudflare Pages Function: auto-deployed at /api/papaya

const PAPAYA_API_BASE = 'https://papaya-consent-check-be11a0846ed5.herokuapp.com/api/v1';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

// POST /api/papaya — start a Papaya run
// Body: { url: string }
export async function onRequestPost(context) {
  const { request, env } = context;
  const PAPAYA_API_KEY = env.PAPAYA_API_KEY || 'cck_live_270ac2d1_NUoykoCcU_5ux3cvXRy0enhmysyvTgjX';

  let body;
  try { body = await request.json(); } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), { status: 400, headers: { ...CORS, 'Content-Type': 'application/json' } });
  }

  const url = (body.url || '').trim();
  if (!url) {
    return new Response(JSON.stringify({ error: 'url is required' }), { status: 400, headers: { ...CORS, 'Content-Type': 'application/json' } });
  }

  const resp = await fetch(`${PAPAYA_API_BASE}/runs`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${PAPAYA_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, task: 'reject_all', state: 'US-CA', wait_for_debug_url_seconds: 2 }),
  });

  const data = await resp.json().catch(() => ({}));
  return new Response(JSON.stringify(data), {
    status: resp.ok ? 200 : resp.status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}

// GET /api/papaya?session_id=xxx — poll run status
export async function onRequestGet(context) {
  const { request, env } = context;
  const PAPAYA_API_KEY = env.PAPAYA_API_KEY || 'cck_live_270ac2d1_NUoykoCcU_5ux3cvXRy0enhmysyvTgjX';

  const sessionId = new URL(request.url).searchParams.get('session_id');
  if (!sessionId) {
    return new Response(JSON.stringify({ error: 'session_id is required' }), { status: 400, headers: { ...CORS, 'Content-Type': 'application/json' } });
  }

  const resp = await fetch(`${PAPAYA_API_BASE}/runs/${sessionId}`, {
    headers: { 'Authorization': `Bearer ${PAPAYA_API_KEY}` },
  });

  const data = await resp.json().catch(() => ({}));
  return new Response(JSON.stringify(data), {
    status: resp.ok ? 200 : resp.status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}

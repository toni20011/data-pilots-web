// Cloudflare Worker — Data Pilots
// Serves static assets + proxies Papaya consent-check API at /api/papaya

const PAPAYA_API_BASE = 'https://papaya-consent-check-be11a0846ed5.herokuapp.com/api/v1';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}

async function handlePapaya(request, env) {
  const PAPAYA_API_KEY = env.PAPAYA_API_KEY || 'cck_live_788628eb_z_-kCKw8wT0iniMT_79nZmZHDGGrCXZm';
  const url = new URL(request.url);
  const method = request.method;
  const auth = { 'Authorization': `Bearer ${PAPAYA_API_KEY}` };

  // Preflight
  if (method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: CORS });
  }

  // POST — start a Papaya run
  if (method === 'POST') {
    let body;
    try { body = await request.json(); } catch {
      return json({ error: 'Invalid JSON' }, 400);
    }
    const siteUrl = (body.url || '').trim();
    if (!siteUrl) return json({ error: 'url is required' }, 400);

    const resp = await fetch(`${PAPAYA_API_BASE}/runs`, {
      method: 'POST',
      headers: { ...auth, 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: siteUrl, task: 'reject_all', state: 'US-CA', wait_for_debug_url_seconds: 2 }),
    });
    const data = await resp.json().catch(() => ({}));
    return json(data, resp.ok ? 200 : resp.status);
  }

  // GET — poll status, fetch screenshots, or fetch report
  if (method === 'GET') {
    const params = url.searchParams;
    const sessionId = params.get('session_id');
    if (!sessionId) return json({ error: 'session_id is required' }, 400);

    // Screenshots
    if (params.get('screenshots') === '1') {
      const resp = await fetch(`${PAPAYA_API_BASE}/runs/${sessionId}/screenshots`, { headers: auth });
      const data = await resp.json().catch(() => ([]));
      return json(data, resp.ok ? 200 : resp.status);
    }

    // Markdown report
    if (params.get('report') === '1') {
      const resp = await fetch(`${PAPAYA_API_BASE}/runs/${sessionId}/report`, { headers: auth });
      const text = await resp.text().catch(() => '');
      return new Response(text, {
        status: resp.ok ? 200 : resp.status,
        headers: { ...CORS, 'Content-Type': 'text/markdown' },
      });
    }

    // Default: run status
    const resp = await fetch(`${PAPAYA_API_BASE}/runs/${sessionId}`, { headers: auth });
    const data = await resp.json().catch(() => ({}));
    return json(data, resp.ok ? 200 : resp.status);
  }

  return json({ error: 'Method not allowed' }, 405);
}

export default {
  async fetch(request, env, ctx) {
    const { pathname } = new URL(request.url);

    // Route API calls to Papaya proxy
    if (pathname === '/api/papaya') {
      return handlePapaya(request, env);
    }

    // Everything else → static assets
    return env.ASSETS.fetch(request);
  },
};

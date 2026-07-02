const MAX_BODY_BYTES = 10_000;
const TABLE_NAME = process.env.SUPABASE_ASSIGNMENTS_TABLE || "nudge_pilot_assignments";
const CONDITIONS = [
  "control",
  "transport_access",
  "opening_hours_availability",
  "itinerary_fit_time_cost",
  "combined"
];

module.exports = async function handler(request, response) {
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.setHeader("Cache-Control", "no-store");

  if (request.method !== "POST") {
    response.setHeader("Allow", "POST");
    response.status(405).json({ ok: false, error: "Method not allowed" });
    return;
  }
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    response.status(503).json({
      ok: false,
      error: "Supabase environment variables are not configured"
    });
    return;
  }
  if (!isAllowedOrigin(request)) {
    response.status(403).json({ ok: false, error: "Origin is not allowed" });
    return;
  }
  const contentLength = Number(request.headers["content-length"] || 0);
  if (contentLength > MAX_BODY_BYTES) {
    response.status(413).json({ ok: false, error: "Request body is too large" });
    return;
  }

  try {
    const body = await readJsonBody(request);
    const sessionId = requiredString(body.session_id, "session_id");
    const stratum = requiredString(body.stratum, "stratum");
    const position = await countAssignments(stratum);
    const blockIndex = Math.floor(position / CONDITIONS.length);
    const slot = position % CONDITIONS.length;
    const condition = seededPermutation(stratum, blockIndex)[slot];
    await insertAssignment({
      stratum,
      position,
      condition,
      session_id: sessionId
    });
    response.status(200).json({
      condition,
      assignment_method: "server_block"
    });
  } catch (error) {
    response.status(500).json({
      ok: false,
      error: error instanceof Error ? error.message : "Unexpected server error"
    });
  }
};

function requiredString(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${field} is required`);
  }
  return value.trim();
}

function stringHash(value) {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function mulberry32(seed) {
  return function random() {
    let value = seed += 0x6D2B79F5;
    value = Math.imul(value ^ value >>> 15, value | 1);
    value ^= value + Math.imul(value ^ value >>> 7, value | 61);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
}

function seededPermutation(stratum, blockIndex) {
  const values = CONDITIONS.slice();
  const random = mulberry32(stringHash(`${stratum}|${blockIndex}`));
  for (let i = values.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1));
    [values[i], values[j]] = [values[j], values[i]];
  }
  return values;
}

function readJsonBody(request) {
  return new Promise((resolve, reject) => {
    let raw = "";
    request.on("data", (chunk) => {
      raw += chunk;
      if (Buffer.byteLength(raw, "utf8") > MAX_BODY_BYTES) {
        reject(new Error("Request body is too large"));
        request.destroy();
      }
    });
    request.on("end", () => {
      try {
        resolve(JSON.parse(raw || "{}"));
      } catch (_error) {
        reject(new Error("Request body is not valid JSON"));
      }
    });
    request.on("error", reject);
  });
}

function isAllowedOrigin(request) {
  const origin = request.headers.origin;
  if (!origin) return true;
  const host = request.headers.host;
  if (host) {
    try {
      if (new URL(origin).host === host) return true;
    } catch (_error) {
      return false;
    }
  }
  const allowed = (process.env.ALLOWED_ORIGINS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return allowed.includes(origin);
}

function supabaseHeaders(extra = {}) {
  return {
    "Accept": "application/json",
    "apikey": process.env.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}`,
    ...extra
  };
}

async function countAssignments(stratum) {
  const baseUrl = process.env.SUPABASE_URL.replace(/\/+$/, "");
  const query = `stratum=eq.${encodeURIComponent(stratum)}&select=id`;
  const result = await fetch(`${baseUrl}/rest/v1/${TABLE_NAME}?${query}`, {
    method: "HEAD",
    headers: supabaseHeaders({
      "Prefer": "count=exact",
      "Range": "0-0"
    })
  });
  if (!result.ok) {
    throw new Error(`Supabase count failed with HTTP ${result.status}`);
  }
  const contentRange = result.headers.get("content-range") || "";
  const match = contentRange.match(/\/(\d+)$/);
  if (!match) throw new Error("Supabase count response omitted total");
  return Number(match[1]);
}

async function insertAssignment(record) {
  const baseUrl = process.env.SUPABASE_URL.replace(/\/+$/, "");
  const result = await fetch(`${baseUrl}/rest/v1/${TABLE_NAME}`, {
    method: "POST",
    headers: supabaseHeaders({
      "Content-Type": "application/json",
      "Prefer": "return=minimal"
    }),
    body: JSON.stringify(record)
  });
  if (!result.ok) {
    const detail = await result.text();
    throw new Error(detail || `Supabase insert failed with HTTP ${result.status}`);
  }
}

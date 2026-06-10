module.exports = async function handler(request, response) {
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.setHeader("Cache-Control", "no-store");

  if (request.method !== "GET") {
    response.setHeader("Allow", "GET");
    response.status(405).json({
      status: "error",
      error: "Method not allowed"
    });
    return;
  }

  response.status(200).json({
    status: "ok",
    storage_configured: Boolean(
      process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY
    ),
    study: "fukui_nudge_pilot"
  });
};

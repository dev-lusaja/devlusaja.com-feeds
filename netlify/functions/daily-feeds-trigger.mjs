// Netlify Scheduled Function: dispara daily-feeds.yml en GitHub Actions vía workflow_dispatch.
// Reemplaza al "schedule" de GitHub, que se retrasa horas o se salta ejecuciones.
// Requiere GH_DISPATCH_TOKEN (fine-grained PAT, "Actions: write" sobre este repo) en las env vars de Netlify.
export default async () => {
  const res = await fetch(
    "https://api.github.com/repos/dev-lusaja/devlusaja.com-feeds/actions/workflows/daily-feeds.yml/dispatches",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.GH_DISPATCH_TOKEN}`,
        Accept: "application/vnd.github+json",
      },
      body: JSON.stringify({ ref: "main" }),
    }
  );
  if (res.status !== 204) throw new Error(`dispatch daily-feeds falló: ${res.status} ${await res.text()}`);
  console.log("dispatch daily-feeds OK");
};

// Cada 2 h de 6:00 a 24:00 hora Colombia (UTC-5) = 11:00..05:00 UTC
export const config = { schedule: "0 11,13,15,17,19,21,23,1,3,5 * * *" };

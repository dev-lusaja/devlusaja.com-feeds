// Netlify Scheduled Function: dispara googlenews-hourly.yml en GitHub Actions vía workflow_dispatch.
// Reemplaza al "schedule" de GitHub, que se retrasa horas o se salta ejecuciones.
// Requiere GH_DISPATCH_TOKEN (fine-grained PAT, "Actions: write" sobre este repo) en las env vars de Netlify.
export default async () => {
  const res = await fetch(
    "https://api.github.com/repos/dev-lusaja/devlusaja.com-feeds/actions/workflows/googlenews-hourly.yml/dispatches",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.GH_DISPATCH_TOKEN}`,
        Accept: "application/vnd.github+json",
      },
      body: JSON.stringify({ ref: "main" }),
    }
  );
  if (res.status !== 204) throw new Error(`dispatch googlenews-hourly falló: ${res.status} ${await res.text()}`);
  console.log("dispatch googlenews-hourly OK");
};

// Cada hora de 6:30 a 23:30 hora Colombia (UTC-5) = 11:30..04:30 UTC
export const config = { schedule: "30 0-4,11-23 * * *" };

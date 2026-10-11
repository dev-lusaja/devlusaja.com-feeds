// Netlify Scheduled Function: dispara daily-top.yml (top de noticias del día → Discord) vía workflow_dispatch.
// Usa el mismo GH_DISPATCH_TOKEN que daily-feeds-trigger.mjs.
export default async () => {
  const res = await fetch(
    "https://api.github.com/repos/dev-lusaja/devlusaja.com-feeds/actions/workflows/daily-top.yml/dispatches",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.GH_DISPATCH_TOKEN}`,
        Accept: "application/vnd.github+json",
      },
      body: JSON.stringify({ ref: "main" }),
    }
  );
  if (res.status !== 204) throw new Error(`dispatch daily-top falló: ${res.status} ${await res.text()}`);
  console.log("dispatch daily-top OK");
};

// 10:10 hora Colombia (UTC-5) = 15:10 UTC, con margen para que terminen el daily de 10:00 y googlenews de 9:30
export const config = { schedule: "10 15 * * *" };

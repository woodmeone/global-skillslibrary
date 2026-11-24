import { connect, waitForPageLoad } from "@/client.js";

const client = await connect();
const page = await client.page("resume", { viewport: { width: 1280, height: 900 } });

await page.goto("http://localhost:5173/");
await waitForPageLoad(page);

await page.screenshot({ path: "tmp/resume-preview.png", fullPage: true });
console.log({ title: await page.title(), url: page.url() });
await client.disconnect();

import { connect, waitForPageLoad } from "@/client.js";

const client = await connect();
const page = await client.page("resume-pdf", { viewport: { width: 1280, height: 900 } });

await page.goto("http://localhost:5173/");
await waitForPageLoad(page);

// 等待字体加载
await page.waitForTimeout(2000);

// 导出PDF
await page.pdf({
  path: "tmp/resume.pdf",
  format: "A4",
  printBackground: true,
  margin: {
    top: "8mm",
    bottom: "8mm",
    left: "8mm",
    right: "8mm"
  }
});

console.log("PDF exported to tmp/resume.pdf");
await client.disconnect();
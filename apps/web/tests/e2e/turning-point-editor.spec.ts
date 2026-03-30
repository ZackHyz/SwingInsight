import { expect, test } from "@playwright/test";

test.skip("user can add and persist a trough point", async ({ page }) => {
  await page.goto("/stocks/000001");
  await page.getByRole("button", { name: "标记波谷" }).click();
  await page.getByTestId("kline-canvas").click({ position: { x: 420, y: 280 } });
  await page.getByRole("button", { name: "保存修正" }).click();
  await expect(page.getByText("保存成功")).toBeVisible();
});

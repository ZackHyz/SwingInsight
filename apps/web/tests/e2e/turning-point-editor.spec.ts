import { expect, test } from "@playwright/test";

test("user can add and persist a trough point", async ({ page }) => {
  await page.goto("/stocks/000001");
  await page.getByRole("button", { name: "标记波谷" }).click();
  await page.getByTestId("kline-canvas").click({ position: { x: 420, y: 180 } });
  await page.getByRole("button", { name: "保存修正" }).click();
  await expect(page.getByText("保存成功")).toBeVisible();
  await expect(page.getByText("重算完成: 1 个波段 / 8 个特征 / 1 条预测")).toBeVisible();
});

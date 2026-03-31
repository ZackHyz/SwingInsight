import { expect, test } from "@playwright/test";

test("research workflow loads chart, saves correction, and shows prediction", async ({ page }) => {
  await page.goto("/stocks/000001");

  await expect(page.getByRole("heading", { name: "预测面板" })).toBeVisible();
  await expect(page.getByText("当前状态: 主升初期").first()).toBeVisible();
  await expect(page.getByText("相似历史样本")).toBeVisible();
  await expect(page.getByTestId("kline-canvas")).toBeVisible();

  await page.getByRole("button", { name: "标记波谷" }).click();
  await page.getByTestId("kline-canvas").click();
  await page.getByRole("button", { name: "保存修正" }).click();

  await expect(page.getByText("保存成功")).toBeVisible();
});

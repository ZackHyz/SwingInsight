import http from "node:http";

const html = `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SwingInsight Demo Research</title>
    <style>
      body { font-family: sans-serif; margin: 0; padding: 24px; background: #f4f1e8; color: #1f2a1f; }
      main { max-width: 960px; margin: 0 auto; display: grid; gap: 20px; }
      section, aside { background: #fffaf0; border: 1px solid #d7c9aa; border-radius: 16px; padding: 20px; }
      .toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
      button { border: 1px solid #6d7f52; background: #eef5dd; border-radius: 999px; padding: 10px 16px; cursor: pointer; }
      #kline-canvas { height: 260px; border-radius: 12px; background: linear-gradient(135deg, #dce8bf, #f8efcf); border: 1px dashed #6d7f52; display: flex; align-items: center; justify-content: center; }
      ul { padding-left: 20px; }
    </style>
  </head>
  <body>
    <main>
      <section>
        <h1>Ping An Bank (000001)</h1>
        <p>当前状态: 主升初期</p>
      </section>
      <aside>
        <h2>预测面板</h2>
        <p>当前状态: 主升初期</p>
        <p>主升初期，10日上行概率 0.58</p>
        <h3>相似历史样本</h3>
        <ul>
          <li>000001 0.93 23.46</li>
        </ul>
      </aside>
      <section>
        <div class="toolbar">
          <button id="mark-trough" type="button">标记波谷</button>
          <button id="save" type="button">保存修正</button>
        </div>
        <div id="kline-canvas" data-testid="kline-canvas">KLine Chart Loaded</div>
        <ul id="points"></ul>
        <p id="status"></p>
      </section>
    </main>
    <script>
      let pendingAction = null;
      let hasDraftPoint = false;
      const points = document.getElementById("points");
      const status = document.getElementById("status");
      document.getElementById("mark-trough").addEventListener("click", () => {
        pendingAction = "trough";
        status.textContent = "已进入波谷标记模式";
      });
      document.getElementById("kline-canvas").addEventListener("click", () => {
        if (!pendingAction) return;
        hasDraftPoint = true;
        points.innerHTML = "<li>2024-06-18 trough 9.6</li>";
        status.textContent = "已添加草稿拐点";
        pendingAction = null;
      });
      document.getElementById("save").addEventListener("click", () => {
        status.textContent = hasDraftPoint ? "保存成功" : "暂无变更";
      });
    </script>
  </body>
</html>`;

const server = http.createServer((request, response) => {
  if (request.url === "/stocks/000001" || request.url === "/") {
    response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    response.end(html);
    return;
  }

  response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
  response.end("not found");
});

server.listen(4173, "127.0.0.1", () => {
  console.log("playwright-smoke-server listening on http://127.0.0.1:4173");
});

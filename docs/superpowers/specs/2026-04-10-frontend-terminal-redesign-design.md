# Frontend Terminal Redesign Design

## Goal

把当前前端从浅色原型式页面，重构成统一的深色高密度研究终端，视觉和信息架构参考 `awesome-design-md` 中偏 `Kraken` 的交易台方向，但保持 SwingInsight 作为 A 股研究工具的产品语义。

这次改造的目标不是简单换皮，而是把首页、个股研究页、样本库页、波段详情页收敛到同一套产品语言、导航结构和分析工作流中。

## Approved Scope

### In Scope

- 重做全站视觉语言，统一为深色终端式界面
- 引入全局 App Shell，包括侧边导航、顶部命令栏和统一内容容器
- 重构首页，使其成为研究终端入口页
- 重构个股研究页，使其成为全站主工作台
- 重构样本库页，使其成为高密度分析台
- 重构波段详情页，使其成为样本下钻分析页
- 建立全局设计 token、布局基元和终端组件层
- 统一加载、空态、错误态和弹层的视觉与语义
- 更新前端测试，使其适配新的结构和主要交互

### Out Of Scope

- 不修改后端接口协议
- 不新增实时行情源、WebSocket 或推送能力
- 不新增 watchlist 持久化
- 不新增多标签工作区状态管理
- 不新增新的量化指标计算逻辑
- 不引入重量级 UI 框架
- 不改变现有研究、预测、样本数据的业务口径

## Requirements Confirmed

- 改造范围为整个前端，而不是单页美化
- 主风格选择 `Kraken` 方向
- 改造深度选择激进型，即允许重构导航、首页定位和页面布局
- 主题策略为只做深色主题
- 保持现有接口和核心行为不退化

## Recommended Approach

采用“终端化重构 + 组件系统收敛”的方式，而不是逐页修补。

当前前端的主要问题不是单个控件不够好看，而是：

- 页面彼此孤立，缺少统一导航和产品骨架
- 视觉值分散在大量内联样式中，难以形成系统
- 个股研究页虽然信息量最大，但没有真正体现主工作台地位
- 样本库和波段详情页更像占位页面，不像研究终端中的分析层级

因此，本次最稳妥也最有效的方案不是继续在现有页面上叠加视觉装饰，而是先建立统一的全局外壳、token 和组件层，再把核心页面迁入这套终端结构中。这样可以在不改后端协议的前提下，显著提升整体产品感和专业气质。

## Product Direction

### Visual Baseline

整体视觉采用深色高密度研究终端方向。

- 主背景为炭黑到深蓝黑的分层底色
- 强调色采用克制的紫色，用于高亮、选中、关键 CTA 和 focus ring
- 上涨、下跌、告警、说明等状态色独立定义，不复用强调紫
- 大面积装饰让位于分区、边界、栅格和节奏

目标不是复刻 crypto 交易所，而是借用其“专业、高密度、面板化”的表达方式，服务 A 股研究工作流。

### Information Density

产品整体采用高信息密度，但不能牺牲扫描效率。

要求：

- 重要指标优先横向概览
- 说明性内容避免堆成长段文本
- 面板内尽量使用短标签、数值、状态 pill 和结构化列表
- 表格、图表、事件流保持分析工具而非营销页面风格

## Global Architecture

### App Shell

全站引入统一的 `AppShell`。

建议结构：

- 左侧 `SideNav`
- 顶部 `TopCommandBar`
- 主内容区 `AppContent`

`SideNav` 承载主导航、当前页面高亮和辅助入口。`TopCommandBar` 承载全局搜索、股票代码快速跳转、页面上下文标题和状态区域。这样首页、研究页、样本库页、详情页都运行在同一套产品容器内，而不是四个相互割裂的页面。

### Route Hierarchy

保留现有基础路由能力，但在信息架构上统一成四层：

- `Overview`
- `Research`
- `Pattern Library`
- `Segment Detail`

对应现有页面：

- `/` 作为 `Overview`
- `/stocks/[stockCode]` 作为 `Research`
- `/library` 作为 `Pattern Library`
- `/segments/[segmentId]` 作为 `Segment Detail`

## Page Design

### Home Page

首页从占位页升级为终端入口页。

其职责不是展示伪行情，而是帮助用户进入研究流程。

建议结构：

- Hero 区：产品标题、研究终端定位、一键输入股票代码
- Quick Actions：进入个股研究、进入样本库、查看示例波段
- Capability Panels：拐点编辑、新闻事件、相似样本这三类能力摘要
- Demo Entry：预置 demo 股票代码入口

视觉上应体现产品身份，但仍服从终端化语言：深色背景、强分区、有限渐变、短文案、高可扫描度。

### Stock Research Page

个股研究页是本次改造的核心，应升级为主工作台。

推荐布局：

- 左侧 `Instrument Context Rail`
- 中间 `Chart Workspace`
- 右侧 `Intelligence Rail`
- 下半区 `Event Flow`

具体分工：

- `Instrument Context Rail`
  - 股票名称、代码、市场、行业
  - 当前状态标签
  - 摘要信息
  - 新闻窗口摘要
- `Chart Workspace`
  - K 线图与拐点编辑器
  - 图表控制条
  - 当前研究区间提示
- `Intelligence Rail`
  - 方向概率
  - 风险提示
  - 相似样本统计
  - 相似样本入口
- `Event Flow`
  - 新闻事件流
  - 事件标签
  - 情绪和冲突信息

该页面的核心原则是“先看状态，再看图，再看解释”。当前散落的信息要重新排位，确保图表成为主画布，预测与相似样本作为解释层，新闻作为事件流补充。

### Pattern Library Page

样本库页应从简单表格页升级为分析台。

建议结构：

- 左侧固定筛选栏
- 顶部结果摘要条
- 右侧高密度结果表格
- 行级交互支持 hover、选中和详情入口

如实现成本可控，可加入页内 detail drawer 作为轻量预览；若不适合本轮范围，可以保留跳转详情页，但视觉上必须仍属于同一套终端系统。

### Segment Detail Page

波段详情页是样本库的 drill-down 页面，不应再是独立风格的普通详情页。

建议结构：

- 顶部波段摘要指标带
- 中部新闻时间线
- 下部标签与辅助解释

页面应复用研究页的面板、指标卡、状态标签和列表语言，让用户感知到自己是在同一个分析环境中继续向下钻取。

## Design System

### Tokens

建立统一设计 token，替代页面内散落的视觉常量。

至少包括：

- 背景层级
- 面板背景层级
- 边框层级
- 文字层级
- 强调紫
- 上涨绿
- 下跌红
- 告警橙
- 圆角
- 阴影
- 间距
- 页面最大宽度与 grid gap

所有页面和组件都消费 token，不再直接在业务组件中硬编码大量色值和阴影值。

### Typography

采用双字体体系：

- 界面标题和正文使用具备金融终端气质的无衬线字体
- 代码、日期、百分比、统计数字使用等宽字体

推荐方向：

- Sans: `IBM Plex Sans` 或同类风格
- Mono: `IBM Plex Mono` 或同类风格

目标是提升数据阅读的秩序感和专业感，摆脱当前默认系统字体的原型气质。

### Core Components

建议抽象如下通用组件：

- `AppShell`
- `SideNav`
- `TopCommandBar`
- `PanelSurface`
- `SectionHeader`
- `MetricCard`
- `StatusPill`
- `FilterField`
- `DataTable`
- `InsightListItem`
- `OverlayDialog`
- `LoadingSkeleton`
- `EmptyState`
- `ErrorBanner`

这样可以把视觉和布局约束从页面中抽离，使后续页面演进不会再次回到散装内联样式状态。

## Data Visualization

### Kline Chart

保留现有 SVG K 线图实现，不在本轮引入新的图表库。

但其视觉和容器表达应升级为终端主画布：

- 深色 plot background
- 更克制的网格线
- 更清晰的涨跌配色
- 更明确的高亮区间遮罩
- 更稳的控制条、缩放按钮和范围滑块样式

重点是强化“主工作区”定位，而不是重写交互逻辑。

### Data Table

样本库表格要从普通 HTML table 提升为分析表格：

- 数字右对齐
- 状态色明确
- 行 hover 可扫描
- 链接与次级操作层次清晰
- 在深色背景中仍保持良好对比度

## State Design

### Loading States

统一加载态：

- 首屏使用 skeleton，而不是纯文字占位
- 面板级局部刷新保留局部 loading
- 图表和列表分别有自己的 loading 呈现

### Empty States

统一空态表达：

- 不只显示“暂无数据”
- 提示当前模块想表达什么、为什么为空
- 对可继续操作的页面提供下一步引导

### Error States

统一错误态表达：

- 页面级失败使用统一 `ErrorBanner`
- 行内失败与弹层失败采用轻量错误提示
- 不让错误信息破坏版面秩序

## Motion

动效应克制，只承担节奏与层级强化作用。

建议保留：

- 页面初载渐入
- 面板轻微上浮
- drawer / dialog 平稳进出

不做大幅度炫技动画，不使用会干扰数据阅读的持续运动背景。

## Implementation Architecture

### Styling Strategy

沿用当前 React + Vite 结构，不引入新 UI 框架或 CSS-in-JS 体系。

建议：

- 在 `apps/web` 内新增全局样式与 token 层
- 把页面级内联样式逐步替换为语义化 class 或集中样式定义
- 优先抽通用布局和面板组件，再改业务页面

### Page Migration Order

推荐按以下顺序落地：

1. 全局基础层
2. 个股研究页
3. 首页
4. 样本库页
5. 波段详情页
6. 测试补齐与清理

原因：

- 个股研究页决定终端语言是否成立
- 首页和样本库页可以复用研究页形成的布局与组件
- 波段详情页依赖前两者沉淀出的视觉与分析组件

## Testing Strategy

本轮重点验证行为、结构与关键语义，不追求视觉截图测试。

### Required Test Coverage

- App Shell 导航存在且页面可识别
- 股票搜索行为保持成立
- 样本库筛选行为保持成立
- 相似样本弹层或详情入口保持可用
- 研究页在 loading / success / error 三种状态下都有明确可识别结构
- 详情页保留基本摘要、时间线和标签信息

### Testing Philosophy

允许测试断言随新结构更新，但不允许业务行为退化。

测试应证明：

- 产品已经变成统一终端
- 关键页面仍然可导航、可搜索、可筛选、可查看详情

## Risks And Mitigations

### Risk 1: Visual rewrite without systemization

如果只改页面，不先收敛 token 和组件层，最终会得到一套更复杂但仍难维护的 UI。

缓解方式：

- 先做 App Shell、token 和通用面板组件

### Risk 2: Scope expansion into new product features

终端化改造很容易滑向 watchlist、workspace tabs、实时行情等新需求。

缓解方式：

- 明确本期只重构表现层和信息架构，不新增持久化与实时能力

### Risk 3: Breaking current page behavior

大改布局时，搜索、筛选、对话框和详情跳转容易被视觉重构破坏。

缓解方式：

- 用现有测试行为作为回归基线，并在重构后补齐新结构测试

## Acceptance Criteria

- 首页、研究页、样本库页、波段详情页一眼可见属于同一深色终端产品
- 个股研究页明确成为主工作台，图表是主画布
- 样本库页和详情页具备分析工具感，而不是普通占位页
- 股票搜索、样本筛选、详情查看、相似样本查看等现有行为不退化
- 前端测试更新后保持通过

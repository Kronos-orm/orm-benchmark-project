# 官网性能报告嵌入与发布契约

核对：2026-10-27。官网源码只读，当前已发布结果未修改。原始观察见[嵌入取证](embed-evidence.json)。

## 已存在的入口

官网`kronos-docs/src/app/components/benchmark.component.ts`的`BenchmarkComponent`使用`ngx-markdown`，直接GET：

`https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/readme.md`

主发布文件必须保持result分支根目录的小写`readme.md`。现有图表引用位于同一仓库result分支的完整raw HTTPS URL。此次HTTP观察的Content-Type为text/plain，跨域允许头与缓存头已保存在embed-evidence.json；发布后仍需实际GET/浏览器核验。

现有性能组件没有iframe、postMessage事件、JSON数据消费或父子页面主题消息。`wiki.component.ts`里的iframe属于另一组件，不能作为性能页协议依据。发布普通Markdown、图片和绝对详情链接即可继续当前集成。

## 文档路由与部署基址

Angular启用withHashLocation，`src/index.html`的base为`/`。中英文入口分别为：

- `https://kotlinorm.com/#/documentation/en/resources/benchmark`
- `https://kotlinorm.com/#/documentation/zh-CN/resources/benchmark`

对应静态页：

- `https://kotlinorm.com/documentation/en/resources/benchmark/`
- `https://kotlinorm.com/documentation/zh-CN/resources/benchmark/`

静态生成器`kronos-docs/scripts/build-static-docs.mjs`将非Logo的ng-doc demo替换为`/#<page.route>`交互入口，所以静态页通过链接进入上述交互报告。`merge-site.mjs`保持static route与SPA fallback顺序。此次不需要改变这些路由、base或主仓文件。

远程仓库API当前default_branch为result、has_pages=false、homepage为空，Pages API返回404。没有把`Kronos-orm.github.io/orm-benchmark-project/`当作已工作的发布地址。

## 主交付与目录分层

`export_publication.py`只从同一source/candidate且已过正确性/SQL门禁的实测run生成本地publication目录，不执行push/deploy。Markdown、双语分析、HTML与JSON共用同一canonical report对象，数值不由两个展示层分别计算；validator从raw重新核对fork均值、median、95%区间和覆盖。没有实测fork会拒绝导出；不覆盖已有输出目录。部分实验要求具体partial-reason并保留全部预定场景状态。

- `readme.md`：官网现有组件直接呈现的简洁中英双语摘要、完整性信息、最多3张预先固定关键图与详细证据入口。
- `runs/<report-id>/report-en.md`与`report-zh-CN.md`：由同一analysis对象派生的英文/中文完整分析，包含全部场景；report.md保留英文别名。
- `runs/<report-id>/measure/`：原始JMH JSON、逐迭代CSV、状态/日志、schedule及AC/节能/热/空闲CPU等证据。
- `runs/<report-id>/validation/`与build-manifest/source归档：SQL/正确性、制品与源码证据。
- `runs/<report-id>/analysis/`、`figures/`、`cases/`：派生统计、标准PNG/SVG/PDF和各场景明细。
- `index.html`、`assets/`、`data/report.json`：可静态HTTP托管的交互报告，作为同一报告包的浏览界面。
- `publication-files.json`：文件摘要；report.zip及其SHA-256方便本地查看和复核。

report-id由candidate/source摘要和analysis摘要组成；版本化目录不复用。主入口readme.md指向该次不可变目录，两个语言的官网页面共读同一双语摘要。关键图在测量前固定为100000行表uniform实体单行、实体100行、100行事务写入，不根据结果择优替换；其余图与156个框架/场景组合按需打开。所有Markdown图片、报告、源码/明细/原始证据链接都使用完整HTTPS URL，图片/原始数据默认基址固定为上述result raw根URL；英文/中文详细Markdown使用完整GitHub blob URL以便浏览器渲染；不能让ngx-markdown按官网当前路由解析相对路径。

## 静态Web与JSON契约

JSON schemaVersion=1，包含reportId、candidateGitSha、benchmarkSourceSha256、runRangeUTC、coverage、environment、requestedVersions、resolvedArtifacts、downloads与scenarios。场景定义完整保留kind/parameters/unit，框架项保留forkMeansUS/n/status/区间/raw引用；原始单位和缺失状态不由前端猜测。

根JSON只载入场景索引与统计，原始引用按所选case明细JSON取用；版本化report.json保留完整对象。JSON内部保留包内文件路径供可搬运的静态界面定位，并同时生成absoluteDownloadUrls、absoluteDetailsUrl、figure.absoluteUrls和raw.absoluteUrls。面向官网Markdown的URL一律采用这些绝对URL。Web前端用document.baseURI把包内路径转换为绝对DOM URL，资源不以`/`开头、不依赖Angular base、CDN或Pages；可部署到任意HTTP子目录。`?case=<case-id>`只选择当前静态界面的场景，不与Angular hash路由通信。

报告不定义postMessage协议，不要求修改父站事件监听；未增加iframe消费依赖。若未来要将交互HTML直接iframe嵌入，应先单独确认真实静态托管URL、父站许可及消息格式，再提出docs改动。

## 发布工作流

原workflow调用旧`benchmark`/`generateBenchmarkReport`任务并清空result目录。当前benchmark侧`.github/workflows/benchmark.yml`已改为手动发布已复核的publication包：输入本仓含`publication/`的精确40位commit；使用工作流提交中的validator检查，再保存Actions artifact并部署result。`clean:false`与保留历史提交保护既有结果及版本化证据。

仓库默认分支当前为result，因此将来显式从main工作流ref调度，例如`gh workflow run benchmark.yml --ref main -f report_source_sha=<reviewed-report-commit>`。该命令属于未来发布步骤，本任务未执行，也没有创建/推送报告分支。

导出与发布分开：只有完成测量、分析、秘密扫描、包验证和人工/实施者复核后，才准备真实publication提交。当前没有生成新成绩包，不覆盖线上旧结果。

## 主仓docs的具体兼容建议

组件URL与路由可保持不变。工具名称若要同步，仅涉及：

- `kronos-docs/src/app/docs/en/8.resources/benchmark/index.md`：将介绍中的kotlinx-benchmark/JMH改为JMH，并说明typed JDBC baseline。
- `kronos-docs/src/app/docs/zh-CN/8.resources/benchmark/index.md`：等价更新为JMH与显式类型JDBC基线。

这是后续可独立审查的两处文案调整，不影响嵌入数据契约；此次未编辑主仓docs，待主任务CI修复收敛后再决定同步。

## 验证状态

只读核对了本地/远程main、result SHA与文件，官网组件、两语言路由、静态demo处理、base和共享Markdown配置。已做绝对URL、HTTP子目录资源解析、Python/JS语法等轻量检查。完整导出、ZIP/原始数据数值交叉验证、浏览器内嵌和最终发布均需真实测量后运行，当前未执行。

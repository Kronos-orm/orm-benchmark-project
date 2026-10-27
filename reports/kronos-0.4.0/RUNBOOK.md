# 源码准备后的运行手册

更新：2026-10-27。当前执行方式已转为[CI运行协议](CI-RUNBOOK.md)。candidate7已获临时API编译放行并通过；本手册保留为本地复现途径，DB、正确性、pilot、measure/profile仍须另行放行。

## 放行与候选

主任务先单独放行构建/正确性/pilot，并提供修复后candidate Maven仓库与40位Git SHA；正式性能与profile另等主机空闲及正式测量放行。当前均未获放行。使用主任务提供的值设置`BENCH_CANDIDATE_REPO`、`BENCH_CANDIDATE_SHA`；不要填旧M2或历史候选。固定JDK为`/usr/local/Cellar/openjdk@21/21.0.10/libexec/openjdk.jdk/Contents/Home`，runner会校验存在。

从benchmark仓库根目录执行。`BENCH_PRIVATE_DIR`指定仓库外独立私有目录；原配置备份保留在私有目录，不加入Git或复制到公开报告。

## 编译与隔离数据库

仅在构建/正确性/pilot放行后设置`BENCH_ALLOW_LOAD=1`。先用`python3 scripts/run_experiment.py build --candidate-repo "$BENCH_CANDIDATE_REPO" --candidate-sha "$BENCH_CANDIDATE_SHA" --private-dir "$BENCH_PRIVATE_DIR" --out "$BENCH_RUN_DIR"`构建并锁定制品；其中后两变量应分别是上述私有目录、`reports/kronos-0.4.0/runs/`下的新专属目录。源码及制品hash不一致时必须重建，不绕过门禁。

然后运行`python3 scripts/manage_mysql.py initialize --private-dir "$BENCH_PRIVATE_DIR"`，再运行相同命令的`start`动作。脚本只允许独立13307端口、独立datadir和socket，会生成私有database-secrets.json。初始化拒绝已有datadir，失败时保留日志，不删除不明目录、不杀全局进程。

## 验证、pilot与正式矩阵

复用上述runner的所有参数，将stage依次换成`validate`、`pilot`。validate要求六适配器全字段值、范围/缺失结果、SQL投影/绑定、逐行INSERT/一次commit/无生成键、连接关闭均通过。失败先修适配器和门禁语义，不能继续给该场景造跑分。

pilot不进入正式统计。检查每框架的预热/measurement趋势与方差，记录具体证据到run目录`pilot-review.json`：至少有对应`sourceSha256`和实际统计`findings`。这是实施者基于数据的审查记录，不是另一次用户批准。若需统一加预热，修改源码参数、重新构建/验证/pilot后再冻结。

另收到正式测量放行后，再设置`BENCH_ALLOW_MEASUREMENT=1`并运行`measure`阶段。runner按固定seed在5个block内洗牌场景和ORM，单次命令一个独立fork，完整记录argv/日志/JSON/逐迭代CSV。合计780个正式JVM命令，查询部分计时时长下限约6小时。`--resume`只跳过同一制品下已成功的case；失败结果不覆盖，修复后使用新run目录并保留旧证据。

## 独立诊断与分析

在正式测量/profile放行后，分别运行`profile --profiler gc`与`profile --profiler jfr`（复用同一候选/输出参数）。当前代表组是entity、100000行、uniform、返回1/100行、六适配器。诊断值不进入主统计。JFR配置会关闭初始环境变量/系统属性事件；交付前仍要扫描实际秘密值，不能输出匹配内容。

运行`python3 scripts/analyze_results.py --run "$BENCH_RUN_DIR"`重建fork统计、CSV与PNG/SVG/PDF。先通过依赖工具找可用matplotlib运行环境；不能为画图启动大规模重编译。summary保留失败/未跑状态；若完全无主数据会拒绝生成空图。

最后逐项核对解释是否有SQL/JDBC调用、分配与profile证据，生成可供官网加载的完整Markdown报告、静态Web界面与辅助canvas。单行端到端延迟不能推出ORM纯CPU优劣；100减1行仍包括数据库/传输/驱动；由时延倒数得到的操作率必须标为折算值。

## 清理与交付

完成后用`python3 scripts/manage_mysql.py stop --private-dir "$BENCH_PRIVATE_DIR"`只停止拥有的专用实例。保留私有datadir与全部日志以便复核；没有授权不推送/提PR/发布。交付链接应包含报告、raw与命令、源码快照/候选标识、统计脚本/独立图及canvas。

## 官网报告包导出（测量后）

在真实分析与图完成后运行：`python3 scripts/export_publication.py --run "$BENCH_RUN_DIR" --out "$BENCH_RUN_DIR/publication" --secret-file "$BENCH_PRIVATE_DIR/database-secrets.json"`。secret-file只用于扫描本次生成的实验凭据，不读取用户原配置备份。默认生成result/readme.md所需完整绝对URL；部分数据必须提供明确partial-reason。

再运行`python3 scripts/validate_publication.py "$BENCH_RUN_DIR/publication"`，核对文件/ZIP摘要、场景矩阵、原始fork到展示均值、绝对Markdown链接与子路径资源。可以用本地静态HTTP服务查看index.html，并在官网相同ngx-markdown条件下核验readme与图片；不需要主仓docs改动。确认前不推送/部署，线上旧结果保持原样。发布入口详见reporting/embed-contract.md。

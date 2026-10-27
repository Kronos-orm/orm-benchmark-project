# Kronos 0.4.0 benchmark 工作记录

更新：2026-10-27（Asia/Shanghai）

本目录保存 benchmark 方法审计、源码适配与验证清单。candidate7临时API编译已通过，尚未启数据库或测量，没有性能结果。当前执行方式已转为CI一次构建、分片复用、统一汇总，见[CI运行协议](CI-RUNBOOK.md)。

源码基线：`Kronos-orm/orm-benchmark-project`，HEAD `c8cfb23a4e2478def2feb8d579d81b9782d77aa7`，分支 `main`。审计开始前已有用户配置改动与 `.DS_Store`；首轮审计保留原样，后续适配使用私有环境配置并保留原文件备份。工作区及其祖先未发现适用 `AGENTS.md`。

## 当前判断

现有实现会丢弃结果、持续扩大插入表、混用不同生成主键/批处理/事务策略，且只运行一个 fork；不能直接据此声称 ORM 整体快慢。查询固定 `id=1` 代表热行负载，不能代表 100000 行随机读取。

用户配置已在 benchmark 与主仓之外保存为私有备份，目录权限 700、文件权限 600，内容未展示；后续配置迁移须保留用户 `useServerPrepStmts=true` 意图。报告与 Git 不得包含该备份或凭据。

当前状态：五ORM+JDBC、JMH和报告源码已重构；临时candidate7（d71132478b7282202d375d6579bd943331fa4fd3）仅API编译通过，本地编译记录保留在仓库外私有工作记录。该候选不是最终测量制品；SQL/正确性、DB、pilot、JMH/JFR/GC均未运行。CI正式矩阵仍等待主任务最终SHA与明确放行；PR入口只构建，不启DB。

## 文档入口

- [设计约束](00-design-locks.md)
- [任务一：公平性缺陷审计](01-audit.md)
- [任务二：候选接入与适配](02-adaptation.md)
- [任务三：实验与统计](03-experiment.md)
- [任务四：报告交付](04-delivery.md)
- [执行顺序](implementation-order.md)
- [验证记录](verification-log.md)
- [验证缺口](verification-gaps.md)
- [范围边界](out-of-scope.md)
- [源码准备完成后的运行手册](RUNBOOK.md)
- [当前稳定版本与兼容性证据](versions/README.md)
- [统计与解释规则](reporting/statistical-interpretation.md)
- [报告结构与证据链](reporting/report-design.md)
- [官网内嵌与发布契约](reporting/embed-contract.md)

## 后续交付

预计保留可复现运行脚本、固定版本依赖、SQL/绑定类型证据、全字段正确性结果、环境 manifest、JMH raw JSON/CSV、命令与退出码、统计分析与独立图文件。最终报告区分已运行、失败、跳过与未运行；主交付保留result/readme.md双语摘要、固定关键图与绝对资源链接；中文/英文完整分析及场景/raw按需打开，同时提供静态Web报告与辅助canvas，所有图表有指标、单位、来源与范围。

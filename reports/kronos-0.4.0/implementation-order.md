# 执行顺序与阶段门禁

1. 公平性审计、原配置私有备份、共同fixture/DDL、JDBC基线与五ORM源码适配：已完成。
2. 临时candidate7 API编译、首次CI一次构建+完整不可变runtime bundle：已完成；正式候选尚待主任务批准。
3. 最终SHA批准后运行CI validate，关闭真实SQL/值/事务/资源生命周期差异；失败先修实现，不能直接跑分。
4. 运行pilot并审阅预热、raw数据、host噪声和有界写入；必要时统一修改参数后重新pilot。记录该producer run、bundle seal、源码/runtime摘要。
5. 正式矩阵另等明确放行：复用已审阅pilot原artifact，按8组×5block分片运行780单元，不重新编译、不按ORM跨机器比分。
6. always aggregate保存完整缺失/失败与host证据；按fork/block统计，不将iteration当独立样本。独立GC/JFR诊断按具体机制问题安排。
7. 从同一analysis导出双语官网Markdown、详细分析、HTML/JSON与独立科学图；raw数值/绝对URL/嵌入/秘密扫描通过后再单独审阅发布。当前无数据库或性能结果。

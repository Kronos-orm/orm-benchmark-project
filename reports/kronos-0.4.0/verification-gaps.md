# 当前验证缺口

更新：2026-10-28。build-only与真实MySQL正确性门禁已运行；Jdbc/Kronos/JPA/Jimmer/Ktorm通过，MyBatis官方支持组合待新validate；尚无性能成绩。

## 已关闭

- candidate7仅用于临时API编译；五ORM、JDBC/JMH、Kotlin2.4.21、Jimmer0.12.4/KSP2.3.12生成源码均已编译。MyBatisPlus3.5.18+core3.6.0通过编译，仍需运行时验证。
- [build-only CI](https://github.com/Kronos-orm/orm-benchmark-project/actions/runs/40528058784)成功完成Kronos JVM candidate一次构建、所有adapter编译、candidate身份强校验、runtime/source/锁定版本bundle与seal上传。numeric workflow_dispatch可直接运行feature ref，默认result分支未修改。
- 5项轻量合同测试覆盖780唯一单元、40分片无额外fork、篡改/缺失/新增/symlink拒绝、零成功不生成数字、reviewed bundle拒绝不同源码身份。没有用模拟成绩生成报告。

## 下一阶段必须关闭

1. 等主任务批准最终Kronos40位SHA，再在对应feature ref运行build/validate/pilot。现有candidate7和远端临时分支的编译结果不代替最终候选。
2. 前五adapter正确性/SQL门禁已过，MyBatis仍待支持组合复验。核对六适配器实际SQL列/谓词/绑定类型、单次查询往返API调用数、连接/事务生命周期、所有行内容、时间/Boolean/VARBINARY/decimal往返。严格SQL检查如遇合法括号/别名需据实修正语义解析，不能绕过检查。
3. CI独立MySQL8.0.46实例启动/清理、Connector/J9.7.0、共同DDL、插入reset均已有实际门禁记录；MyBatis3.6.0组合已因NoSuchMethodError失败，改官方Plus3.5.18.1/core3.5.19后待复验，SingleShotTime性能尚未测量。
4. pilot需审阅预热轨迹、fork/host方差和背景CPU基线。SingleShotTime默认10轮warmup可能不足；必要时统一修改全部框架配置后重新pilot。
5. 正式measure的artifact复用分支尚未实跑：必须匹配已审阅pilot原bundle/seal、Kronos/benchmark SHA、producer run、完整48个pilot PASS与raw摘要。不能靠同SHA重建替代同字节制品。
6. 正式矩阵仍未放行。批准后按26场景×6框架×5独立block=780单元执行；每场景/block在同一runner VM/DB上比较全部框架，保留全部FAIL/NOT_RUN及host噪声。
7. 统计/科学图/报告导出尚未运行：核对5个fork均值、paired block/host、95%区间、raw到显示数值和完整expected cells。CI物理硬件不受控，不泛化为生产/纯ORM CPU/KMP全平台结论。
8. GC/JFR代表场景诊断尚未运行；如补充，单独artifact与主成绩隔离，记录观测范围与采样限制。
9. 官网主入口契约已核对；真实结果须验证双语result/readme.md、最多3张关键图、完整绝对链接、详情/JSON按需加载、ZIP摘要与浏览器嵌入。方法canvas仅辅助，宿主渲染/TypeScript类型检查仍待核验。
10. 本地预检与个人路径不纳入代码PR；原私密配置备份仍位于Git外。最终报告须扫描本次实验生成的凭据，并在审阅后独立手动发布；目前没有部署或覆盖线上结果。

# 分阶段CI命令与配置耗时估算

以下是运行命令模板，当前没有触发新的DB任务；等待主任务提供更新后的Kronos源SHA。工作流ID398381230，源码ref为codex/reproducible-040-benchmark-ci。

## Pilot：同run构建一次、正确性、试跑

```bash
BENCH_REF=codex/reproducible-040-benchmark-ci
KRONOS_EXPECTED_SHA='<主任务给出的最终40位SHA>'
gh workflow run 398381230 --repo Kronos-orm/orm-benchmark-project \
  --ref "$BENCH_REF" -f mode=pilot -f kronos_ref=codex/kmp-continuation \
  -f expected_kronos_sha="$KRONOS_EXPECTED_SHA"
```

不先单独validate。pilot会完成一次Kronos/JMH producer、真实独立MySQL正确性/SQL/连接生命周期验证、48单元试跑及上传前真实secret扫描。记录实际run ID、benchmark SHA、candidate SHA、bundle seal和自动pilot统计；主仓若再改SHA，此次保留为provisional并用新SHA重跑pilot。

## 正式矩阵：复用原pilot字节

同一Kronos SHA主仓门禁与pilot通过后可运行，不必等发布tag。BENCH_REF必须仍指向pilot时的同一benchmark commit。

```bash
PILOT_RUN_ID='<通过的pilot实际run ID>'
gh workflow run 398381230 --repo Kronos-orm/orm-benchmark-project \
  --ref "$BENCH_REF" -f mode=measure -f kronos_ref=codex/kmp-continuation \
  -f expected_kronos_sha="$KRONOS_EXPECTED_SHA" \
  -f producer_run_id="$PILOT_RUN_ID"
```

无额外确认口令。自动验证源run成功/attempt1/benchmark SHA，冻结两份artifact的精确ID、ZIP digest和size，校验下载、seal、正确性marker、48个pilot raw及自动统计。正式producer只复用原bundle，40个shard不执行Gradle/Kotlin。不要使用rerun按钮混入旧artifact；重试使用新的dispatch/run ID，保留失败记录和原因。

## 耗时：配置推算，不是性能实测

- 最近一次完整build-only producer耗时4分45秒（run40576147336）；新的SDK/网络/源码可能改变构建耗时。
- pilot包含36个read JVM命令，各2×1秒warmup+3×1秒measurement，读取计时下限180秒；另12个write命令各5次warmup+5次single-shot，不存在固定秒数下限。48次JVM启动、100000行fixture生成/入库、ORM初始化、MySQL启动、正确性校验和artifact I/O都额外计时。**预计约15–30分钟，不含排队**；冷缓存或慢fixture可能更长。
- 正式包含720个read命令，各5×2秒warmup+10×2秒measurement，总读取计时21600秒=6 runner-hours。30个read shard各24命令，单shard纯读取计时12分钟；max-parallel8时读取至少4波≈48分钟，另10个write shard、全部fixture/JVM/DB启动、校验/下载/汇总/作图额外计时。**配置规划约1–2小时，不含排队**；持续八并发不可保证，实际并发、排队与host VM身份须从run记录，不能当作实测时长。
- GitHub队列、账户并发额度和host噪声不确定，不能给出确定结束时刻。发现正确性/预热问题需修复和重新pilot，不能为赶时间降低门禁。

完整raw与来源/run链接随同一analysis导出的双语网站报告保留；result/readme.md稳定入口、不可变图/明细目录和独立发布流程不变。

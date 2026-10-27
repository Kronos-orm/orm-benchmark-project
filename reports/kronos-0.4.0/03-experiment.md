# 任务三：实验与统计

状态：Pending（harness/runner/统计源码已准备，实验未运行）；所有数值为计划参数，不是结果。

## 目标

生成可复现的本地受控性能数据，并限定结论的适用范围。

## 预计主实验

查询：五ORM+JDBC，entity/map/scalar三投影，表规模1000与100000；每op查一行。对100000表分别跑固定热主键与预生成均匀id序列，数据集与序列seed固定。entity/map选择全部17列，scalar只name。均匀序列游标成本包含在每方，另有纯id-sequence基线只用于理解固定开销，不从DB结果机械相减。entity表示各框架完全物化的原生对象，结果中披露代理/不可变对象差异；map/native转换差异单独说明。

查询JMH：AverageTime、us/op、threads=1、forks=5、warmup=5×2s、measurement=10×2s。一次op包含连接/会话获取关闭。正式命令显式设置参数，避免依赖注解默认值。primary不混用Throughput与AverageTime误差；如另跑吞吐，独立列出。GC profiler记录分配量，若影响/支持不确定先pilot确认；profiling诊断与主跑分开，任何合并须统一。

写入：应用赋值id、相同列、每op一事务且包含commit，单行插入与100行批量分别测试。SingleShotTime，forks=5，warmup=10个迭代，measurement=30个迭代，每迭代batchSize=1，只调用一次benchmark方法。迭代setup重置固定起始表状态、创建新输入实体，计时只含插入/commit/必要生成。所有框架起始表规模一致，每次结束校验行数，避免持续增表。报告us/batch与派生rows/s，并明确单次事务耐久提交成本；不能把批次ops/s当成行吞吐。

物理批量策略可能不同：共同逐行SQL/一次提交已作为主harness配置；每事务100行不称为原生JDBC批处理。原生batch仍是可选独立场景，若不实现/不运行则在最终报告明确未测，不能由此评价原生batch能力。IDENTITY生成键场景若兼容再补独立组，不能与assigned-id混排。

重置带来页缓存、redo和checkpoint影响：所有ORM用相同重置方式、固定DDL且单独写表；pilot记录迭代耗时/等待背景flush稳定性。SingleShotTime属于固定规模事务延迟，不描述为持续大容量摄入。若需要持续吞吐另设计有界循环并把维护成本纳入该独立工作负载。

## 环境与顺序

- 独立MySQL8.0.22进程，datadir位于Git外专属目录，bind-address127.0.0.1，port13307，skip-log-bin如选择则所有运行一致，记录所有非默认值。
- 记录InnoDB buffer pool、innodb_flush_log_at_trx_commit、sync_binlog、transaction isolation、字符集/排序规则、sql_mode、timezone、表DDL和行数。确认数据热缓存定义；不宣称冷盘测试。
- 使用固定JDK21.0.10与JVM Xms1g/Xmx1g/G1GC，记录供应商/完整版本；不强制无意义CPU绑核（macOS），记录温度/电源/后台负荷可取得信息与限制。
- 与主仓CI/大编译互斥。仅一项JMH负载运行；记录CPU/RAM/swap快照，机器须接电且无明显争用。发现争用保留数据并标记受影响，不悄悄挑选最快结果。
- 每个独立block（fork外层）按固定seed洗牌ORM/场景顺序，将命令顺序写入manifest。至少5个独立fork；不把一个JVM内30个iteration当作30个独立试验。
- 先编译/正确性/短pilot，pilot不进入最终统计。若pilot明确显示预热不足或高方差，在所有相关ORM上统一增加预热/测量并记录原因，正式配置冻结后全组运行。

## 分离RTT、映射和诊断证据

JDBC基线与1/100行固定结果规模共同用于观察端到端固定成本和行数敏感性。100行减1行仍包含数据库执行、网络传输、驱动、映射与分配，不能直接称为纯ORM CPU成本；单行热缓存延迟也不能推出CPU优劣。

代表性profile组独立运行六适配器、entity投影、100000表、uniform访问、返回1/100行。GC profiler与JFR分两轮；GC分配量和JFR栈/CPU/阻塞证据用于解释而不进入主成绩。JFR关闭初始环境变量/系统属性采集，避免将私有密码写入文件，交付前仍须秘密检查。

SQL proxy证明的是JDBC API执行/prepare/commit调用与连接生命周期，不自动等于真实wire往返；prepared statement缓存会改变实际prepare请求。报告必须区分，若需要归因于网络请求次数，应另做服务器/驱动层诊断。

## 统计约定

保存完整JMH JSON含rawData、stderr/stdout与CSV；将每fork均值作为独立样本，展示所有fork点、均值/中位数、标准差与基于独立fork均值的Student t 95% CI，同时保留JMH原始默认置信区间及其置信水平。比值定义统一为competitor latency/Kronos latency；大于1表示Kronos延迟较小。展示成对block比值、log-ratio的t区间及有固定seed的block bootstrap 95%CI，不把迭代层伪重复当独立样本。5个block的bootstrap精度有限，应明确披露，不能据微小差异强行排名。

CI重叠不等于同等，CI不重叠也不提供跨环境普遍结论。若证据不足，结论写未分辨出稳定差异；不使用“快X倍”替代区间、分母和负载说明。多场景探索性比较不冒充预注册显著性检验。

## 验收与产物

- `manifest.json`：候选SHA、benchmark基线/修改hash、依赖解析与JAR hash、硬件/JVM/MySQL/配置与seed。
- `commands.jsonl`：脱敏argv、工作目录、环境变量名称（不含秘密值）、开始结束时间、退出码、输入输出路径。
- `validation/`：DDL、SQL模板/绑定类型、正确性断言结果、各框架执行计数。
- `raw/`：每block/场景JSON、CSV及日志；失败也保留。
- `analysis/`：固定分析脚本、统计JSON/CSV、独立PNG/SVG/PDF图（matplotlib等标准工具）。
- 报告覆盖所有预定case的状态，不使用零值代替失败或未运行；所有图可由raw重建。

## 验证记录

未运行：未初始化datadir、未启动mysqld、未编译、未pilot、未测量。

## 预定工作量

正式矩阵144个查询组合+12个事务写入组合，每个5个独立JVM，合计780个正式命令。仅查询预热/计时下限为144×5×30秒=21600秒，尚不含fixture、JVM启动、校验、写入与诊断。此为配置推算，不是实际耗时或测量结果。

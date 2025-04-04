// JpaInitializer.kt
package com.kotlinorm.jpaBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.jpaBenchmark.pojo.User
import org.hibernate.SessionFactory
import org.hibernate.boot.MetadataSources
import org.hibernate.boot.registry.StandardServiceRegistryBuilder
import org.hibernate.cfg.AvailableSettings
import javax.sql.DataSource

class JpaInitializer : BenchmarkExecutor {
    private lateinit var users: List<User>
    private lateinit var sessionFactory: SessionFactory

    // 初始化配置（每个基准测试只执行一次）
    override fun init(dataSource: DataSource, listOfMap: List<Map<String, Any>>) {
        prepareData(listOfMap)
        val registry = StandardServiceRegistryBuilder().apply {
            // 基础配置
            applySettings(
                mapOf(
                    AvailableSettings.DATASOURCE to dataSource,
                    AvailableSettings.DIALECT to "org.hibernate.dialect.MySQL8Dialect",
                    AvailableSettings.SHOW_SQL to false,
                    AvailableSettings.HBM2DDL_AUTO to "validate",
                    AvailableSettings.STATEMENT_BATCH_SIZE to 1000,
                    AvailableSettings.ORDER_INSERTS to true,
                    AvailableSettings.SHOW_SQL to false,
                    AvailableSettings.FORMAT_SQL to false,
                    AvailableSettings.GENERATE_STATISTICS to false,
                    AvailableSettings.LOG_JDBC_WARNINGS to false,
                    AvailableSettings.USE_QUERY_CACHE to false,
                    AvailableSettings.QUERY_PLAN_CACHE_ENABLED to false
                )
            )
        }.build()

        sessionFactory = MetadataSources(registry)
            .addAnnotatedClass(User::class.java)
            .buildMetadata()
            .buildSessionFactory()
    }

    override fun prepareData(listOfMap: List<Map<String, Any>>) {
        // 预处理数据
        users = listOfMap.map { map ->
            User(
                name = map["name"] as String,
                age = map["age"] as Int
            )
        }
    }

    override fun executeInsert() {
        sessionFactory.openSession().use { session ->
            val transaction = session.beginTransaction()
            try {
                // 直接遍历全部数据（不手动分批）
                users.map { User(name = it.name, age = it.age) }
                    .forEach { session.persist(it) }

                session.flush() // 单次刷入所有数据
                transaction.commit()
            } catch (e: Exception) {
                transaction.rollback()
                throw e
            } finally {
                session.clear() // 清理一级缓存
            }
        }
    }

    // 查询逻辑（示例）
    override fun querySingleEntity() {
        sessionFactory.openSession().use { session ->
            session.get(User::class.java, 1)
        }
    }

    // 清理资源（基准测试结束时调用）
    override fun onDestroy() {
        sessionFactory.openSession().use { session ->
            session.beginTransaction().apply {
                try {
                    // truncate 表
                    session.createNativeQuery("TRUNCATE TABLE tb_user").executeUpdate()
                    commit()
                } catch (e: Exception) {
                    rollback()
                    throw e
                }
            }
        }
        sessionFactory.close()
    }
}
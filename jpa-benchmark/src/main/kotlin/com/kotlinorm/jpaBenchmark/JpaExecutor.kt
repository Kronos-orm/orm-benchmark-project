// JpaExecutor.kt
package com.kotlinorm.jpaBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.jpaBenchmark.pojo.User
import org.hibernate.SessionFactory
import org.hibernate.boot.MetadataSources
import org.hibernate.boot.registry.StandardServiceRegistryBuilder
import org.hibernate.cfg.AvailableSettings
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime
import javax.sql.DataSource

class JpaExecutor : BenchmarkExecutor {
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
                uid = map["uid"] as Long,
                name = map["name"] as String,
                age = map["age"] as Int,
                sex = map["sex"] as Boolean,
                height = map["height"] as Float,
                weight = map["weight"] as Float,
                score = map["score"] as Double,
                salary = map["salary"] as BigDecimal,
                birthday = map["birthday"] as LocalDate,
                email = map["email"] as String,
                address = map["address"] as String,
                comment = map["comment"] as ByteArray,
                version = map["version"] as Int,
                deleted = map["deleted"] as Boolean,
                createTime = map["createTime"] as LocalDateTime,
                updateTime = map["updateTime"] as LocalDateTime
            )
        }
    }

    override fun executeInsert() {
        sessionFactory.openSession().use { session ->
            val transaction = session.beginTransaction()
            try {
                users
                    .forEach {
                        it.id = null
                        session.persist(it)
                    }

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

    override fun querySingleEntity() {
        sessionFactory.openSession().use { session ->
            session.get(User::class.java, 1)
        }
    }

    override fun querySingleMap() {
        sessionFactory.openSession().use { session ->
            val query = """
                SELECT new map(
                    u.id as id, 
                    u.uid as uid,
                    u.name as name, 
                    u.age as age,
                    u.sex as sex,
                    u.height as height,
                    u.weight as weight,
                    u.score as score,
                    u.salary as salary,
                    u.birthday as birthday,
                    u.email as email,
                    u.address as address,
                    u.comment as comment,
                    u.version as version,
                    u.deleted as deleted,
                    u.createTime as createTime,
                    u.updateTime as updateTime
                ) 
                FROM User u 
                WHERE u.id = :id
            """

            session.createQuery(query, Map::class.java)
                .setParameter("id", 1L)
                .uniqueResult() as Map<String, Any>
        }
    }

    override fun querySingleField() {
        sessionFactory.openSession().use { session ->
            val query = "SELECT u.name FROM User u WHERE u.id = :id"
            session.createQuery(query, String::class.java)
                .setParameter("id", 1L)
                .uniqueResult()
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
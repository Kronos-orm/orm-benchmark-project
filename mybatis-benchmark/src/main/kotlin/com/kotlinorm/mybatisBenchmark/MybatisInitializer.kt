package com.kotlinorm.mybatisBenchmark

import com.baomidou.mybatisplus.core.MybatisConfiguration
import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.mybatisBenchmark.dao.User
import com.kotlinorm.mybatisBenchmark.mapper.UserMapper
import org.apache.ibatis.mapping.Environment
import org.apache.ibatis.session.*
import org.apache.ibatis.transaction.jdbc.JdbcTransactionFactory
import javax.sql.DataSource

class MybatisInitializer(
    private val users: List<User> = listOf()
) : BenchmarkExecutor {

    private lateinit var sqlSessionFactory: SqlSessionFactory

    override fun init(dataSource: DataSource) {
        val configuration = MybatisConfiguration().apply {
            environment = Environment(
                "benchmark",
                JdbcTransactionFactory(),
                dataSource
            )
            isMapUnderscoreToCamelCase = true
            isUseGeneratedKeys = true
            defaultExecutorType = ExecutorType.BATCH
            isCacheEnabled = false
            addMapper(UserMapper::class.java)
        }

        sqlSessionFactory = SqlSessionFactoryBuilder()
            .build(configuration)
    }

    override fun executeInsert1000() {
        sqlSessionFactory.openSession(ExecutorType.BATCH).use { session ->
            val mapper = session.getMapper(UserMapper::class.java)
            users.forEach { mapper.insert(it) }
            session.commit()
        }
    }

    override fun querySingleEntity() {
        sqlSessionFactory.openSession().use { session ->
            session.getMapper(UserMapper::class.java).selectById(1)
        }
    }

    override fun onDestroy() {
        sqlSessionFactory.openSession().use { session ->
            val connection = session.connection
            // 1. 删除所有非初始数据
            connection.prepareStatement("DELETE FROM tb_user WHERE id != 1").executeUpdate()
            // 2. 重置自增主键计数器
            connection.prepareStatement("ALTER TABLE tb_user AUTO_INCREMENT = 1").executeUpdate()
            session.commit()
        }
    }
}
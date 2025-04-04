package com.kotlinorm.mybatisBenchmark

import com.baomidou.mybatisplus.core.MybatisConfiguration
import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.mybatisBenchmark.dao.User
import com.kotlinorm.mybatisBenchmark.mapper.UserMapper
import org.apache.ibatis.mapping.Environment
import org.apache.ibatis.session.ExecutorType
import org.apache.ibatis.session.SqlSessionFactory
import org.apache.ibatis.session.SqlSessionFactoryBuilder
import org.apache.ibatis.transaction.jdbc.JdbcTransactionFactory
import javax.sql.DataSource

class MybatisInitializer() : BenchmarkExecutor {
    private lateinit var sqlSessionFactory: SqlSessionFactory
    private lateinit var users: List<User>
    override fun init(dataSource: DataSource, listOfMap: List<Map<String, Any>>) {
        prepareData(listOfMap)
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
            connection.prepareStatement("TRUNCATE table tb_user").executeUpdate()
            session.commit()
        }
    }
}
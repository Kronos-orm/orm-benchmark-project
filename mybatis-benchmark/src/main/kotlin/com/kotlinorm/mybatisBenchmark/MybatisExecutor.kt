package com.kotlinorm.mybatisBenchmark

import com.baomidou.mybatisplus.core.MybatisConfiguration
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper
import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.mybatisBenchmark.dao.User
import com.kotlinorm.mybatisBenchmark.mapper.UserMapper
import org.apache.ibatis.mapping.Environment
import org.apache.ibatis.session.ExecutorType
import org.apache.ibatis.session.SqlSessionFactory
import org.apache.ibatis.session.SqlSessionFactoryBuilder
import org.apache.ibatis.transaction.jdbc.JdbcTransactionFactory
import java.math.BigDecimal
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import javax.sql.DataSource

class MybatisExecutor() : BenchmarkExecutor {
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
                updateTime = map["createTime"] as LocalDateTime
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

    override fun querySingleMap() {
        sqlSessionFactory.openSession().use { session ->
            session.getMapper(UserMapper::class.java).selectMaps(QueryWrapper<User>().eq("id", 1)).single()
        }
    }

    override fun querySingleField() {
        sqlSessionFactory.openSession().use { session ->
            session.getMapper(UserMapper::class.java).selectList(QueryWrapper<User>().select("name").eq("id", 1)).single().name
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
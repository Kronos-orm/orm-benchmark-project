package com.kotlinorm.mybatisBenchmark

import com.baomidou.mybatisplus.core.MybatisConfiguration
import com.baomidou.mybatisplus.core.MybatisSqlSessionFactoryBuilder
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper
import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.FixtureRow
import com.kotlinorm.mybatisBenchmark.dao.User
import com.kotlinorm.mybatisBenchmark.mapper.UserMapper
import org.apache.ibatis.logging.nologging.NoLoggingImpl
import org.apache.ibatis.mapping.Environment
import org.apache.ibatis.session.*
import org.apache.ibatis.transaction.jdbc.JdbcTransactionFactory
import javax.sql.DataSource

class MybatisExecutor : BenchmarkExecutor {
    private lateinit var factory: SqlSessionFactory
    private var users: List<User> = emptyList()

    override fun init(dataSource: DataSource) {
        val configuration = MybatisConfiguration().apply {
            environment = Environment("benchmark", JdbcTransactionFactory(), dataSource)
            isMapUnderscoreToCamelCase = true
            isUseGeneratedKeys = false
            defaultExecutorType = ExecutorType.SIMPLE
            localCacheScope = LocalCacheScope.STATEMENT
            isCacheEnabled = false
            logImpl = NoLoggingImpl::class.java
            addMapper(UserMapper::class.java)
        }
        factory = MybatisSqlSessionFactoryBuilder().build(configuration)
    }

    private fun range(firstId: Int, rowCount: Int) = QueryWrapper<User>()
        .ge("id", firstId).lt("id", firstId + rowCount).orderByAsc("id")

    override fun queryEntities(firstId: Int, rowCount: Int): List<Any> = factory.openSession(true).use {
        it.getMapper(UserMapper::class.java).selectList(range(firstId, rowCount))
    }

    override fun queryMaps(firstId: Int, rowCount: Int): List<Map<String, Any?>> = factory.openSession(true).use {
        it.getMapper(UserMapper::class.java).selectMaps(range(firstId, rowCount))
    }

    override fun queryNames(firstId: Int, rowCount: Int): List<String> = factory.openSession(true).use {
        // Scalar projection avoids constructing partially populated User objects.
        it.getMapper(UserMapper::class.java).selectObjs<String>(range(firstId, rowCount).select("name"))
    }

    override fun prepareInsert(rows: List<FixtureRow>) {
        users = rows.map { row -> User(
                id = row.id,
                uid = row.uid,
                name = row.name,
                age = row.age,
                sex = row.sex,
                height = row.height,
                weight = row.weight,
                score = row.score,
                salary = row.salary,
                birthday = row.birthday,
                email = row.email,
                address = row.address,
                comment = row.comment,
                version = row.version,
                deleted = row.deleted,
                createTime = row.createTime,
                updateTime = row.updateTime,
        ) }
    }

    override fun insertTransaction(): Int = factory.openSession(ExecutorType.SIMPLE, false).use { session ->
        try {
            val mapper = session.getMapper(UserMapper::class.java)
            val affected = users.sumOf { mapper.insert(it) }
            session.commit()
            affected
        } catch (failure: Throwable) {
            session.rollback()
            throw failure
        }
    }

    override fun close() { users = emptyList() }
}

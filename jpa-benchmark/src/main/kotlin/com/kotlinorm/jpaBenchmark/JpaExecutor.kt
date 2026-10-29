package com.kotlinorm.jpaBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.FixtureRow
import com.kotlinorm.jpaBenchmark.pojo.User
import org.hibernate.SessionFactory
import org.hibernate.boot.MetadataSources
import org.hibernate.boot.registry.StandardServiceRegistry
import org.hibernate.boot.registry.StandardServiceRegistryBuilder
import javax.sql.DataSource

class JpaExecutor : BenchmarkExecutor {
    private lateinit var registry: StandardServiceRegistry
    private lateinit var factory: SessionFactory
    private var users: List<User> = emptyList()

    override fun init(dataSource: DataSource) {
        registry = StandardServiceRegistryBuilder().applySettings(mapOf(
            "hibernate.connection.datasource" to dataSource,
            "hibernate.dialect" to "org.hibernate.dialect.MySQLDialect",
            "hibernate.hbm2ddl.auto" to "validate",
            "hibernate.show_sql" to false,
            "hibernate.format_sql" to false,
            "hibernate.generate_statistics" to false,
            "hibernate.cache.use_second_level_cache" to false,
            "hibernate.cache.use_query_cache" to false,
            "hibernate.jdbc.batch_size" to 0,
            "hibernate.jdbc.time_zone" to "UTC"
        )).build()
        try {
            factory = MetadataSources(registry).addAnnotatedClass(User::class.java)
                .buildMetadata().buildSessionFactory()
        } catch (failure: Throwable) {
            StandardServiceRegistryBuilder.destroy(registry)
            throw failure
        }
    }

    override fun queryEntities(firstId: Int, rowCount: Int): List<Any> = factory.openSession().use {
        it.createQuery("from User u where u.id >= :first and u.id < :end order by u.id", User::class.java)
            .setParameter("first", firstId).setParameter("end", firstId + rowCount).resultList
    }

    @Suppress("UNCHECKED_CAST")
    override fun queryMaps(firstId: Int, rowCount: Int): List<Map<String, Any?>> = factory.openSession().use {
        it.createQuery("select new map(u.id as id, u.uid as uid, u.name as name, u.age as age, u.sex as sex, u.height as height, u.weight as weight, u.score as score, u.salary as salary, u.birthday as birthday, u.email as email, u.address as address, u.comment as comment, u.version as version, u.deleted as deleted, u.createTime as createTime, u.updateTime as updateTime) from User u where u.id >= :first and u.id < :end order by u.id", Map::class.java)
            .setParameter("first", firstId).setParameter("end", firstId + rowCount).resultList as List<Map<String, Any?>>
    }

    override fun queryNames(firstId: Int, rowCount: Int): List<String> = factory.openSession().use {
        it.createQuery("select u.name from User u where u.id >= :first and u.id < :end order by u.id", String::class.java)
            .setParameter("first", firstId).setParameter("end", firstId + rowCount).resultList
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

    override fun insertTransaction(): Int = factory.openSession().use { session ->
        val transaction = session.beginTransaction()
        try {
            users.forEach(session::persist)
            session.flush()
            transaction.commit()
            users.size
        } catch (failure: Throwable) {
            if (transaction.isActive) transaction.rollback()
            throw failure
        }
    }

    override fun close() {
        try { if (::factory.isInitialized) factory.close() }
        finally { if (::registry.isInitialized) StandardServiceRegistryBuilder.destroy(registry) }
        users = emptyList()
    }
}

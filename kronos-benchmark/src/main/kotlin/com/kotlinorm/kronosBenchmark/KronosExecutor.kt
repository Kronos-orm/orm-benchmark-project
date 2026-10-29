package com.kotlinorm.kronosBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.FixtureRow
import com.kotlinorm.Kronos
import com.kotlinorm.kronosBenchmark.pojo.User
import com.kotlinorm.orm.insert.insert
import com.kotlinorm.orm.select.select
import com.kotlinorm.wrappers.KronosJdbcWrapper
import javax.sql.DataSource

class KronosExecutor : BenchmarkExecutor {
    private lateinit var wrapper: KronosJdbcWrapper
    private var users: List<User> = emptyList()

    override fun init(dataSource: DataSource) {
        Kronos.logging.enabled = false
        Kronos.fieldNamingStrategy = Kronos.lineHumpNamingStrategy
        Kronos.tableNamingStrategy = Kronos.lineHumpNamingStrategy
        Kronos.timeZone = "UTC"
        // All candidates use normal checked type conversion; no per-ORM strict-mode shortcut.
        Kronos.strictSetValue = false
        wrapper = KronosJdbcWrapper(dataSource)
        Kronos.dataSource = { wrapper }
    }

    override fun queryEntities(firstId: Int, rowCount: Int): List<Any> {
        val end = firstId + rowCount
        return User().select().where { it.id >= firstId && it.id < end }
            .orderBy { it.id.asc() }.cascade(false).toList(wrapper)
    }

    override fun queryMaps(firstId: Int, rowCount: Int): List<Map<String, Any?>> {
        val end = firstId + rowCount
        return User().select().where { it.id >= firstId && it.id < end }
            .orderBy { it.id.asc() }.cascade(false).toMapList(wrapper)
    }

    override fun queryNames(firstId: Int, rowCount: Int): List<String> {
        val end = firstId + rowCount
        return User().select { it.name }.where { it.id >= firstId && it.id < end }
            .orderBy { it.id.asc() }.cascade(false).toList<String>(wrapper)
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

    override fun insertTransaction(): Int = Kronos.transact(wrapper) {
        users.sumOf { it.insert().cascade(false).execute(wrapper).affectedRows }
    } as Int

    override fun close() { users = emptyList() }
}

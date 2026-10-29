package com.kolinorm.ktormBenchmark

import com.kolinorm.ktormBenchmark.table.Users
import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.FixtureRow
import org.ktorm.database.Database
import org.ktorm.dsl.*
import org.ktorm.logging.NoOpLogger
import javax.sql.DataSource

class KtromExecutor : BenchmarkExecutor {
    private lateinit var database: Database
    private var rows: List<FixtureRow> = emptyList()

    override fun init(dataSource: DataSource) {
        database = Database.connect(dataSource, logger = NoOpLogger)
    }

    override fun queryEntities(firstId: Int, rowCount: Int): List<Any> = database.from(Users)
        .select(Users.columns).where { (Users.id greaterEq firstId) and (Users.id less firstId + rowCount) }
        .orderBy(Users.id.asc()).map { Users.createEntity(it) }

    override fun queryMaps(firstId: Int, rowCount: Int): List<Map<String, Any?>> = database.from(Users)
        .select(Users.columns).where { (Users.id greaterEq firstId) and (Users.id less firstId + rowCount) }
        .orderBy(Users.id.asc()).map { row -> Users.columns.associate { it.name to row[it] } }

    override fun queryNames(firstId: Int, rowCount: Int): List<String> = database.from(Users)
        .select(Users.name).where { (Users.id greaterEq firstId) and (Users.id less firstId + rowCount) }
        .orderBy(Users.id.asc()).map { it[Users.name]!! }

    override fun prepareInsert(rows: List<FixtureRow>) { this.rows = rows.toList() }

    override fun insertTransaction(): Int = database.useTransaction {
        rows.sumOf { row ->
            database.insert(Users) {
                    set(it.id, row.id)
                    set(it.uid, row.uid)
                    set(it.name, row.name)
                    set(it.age, row.age)
                    set(it.sex, row.sex)
                    set(it.height, row.height)
                    set(it.weight, row.weight)
                    set(it.score, row.score)
                    set(it.salary, row.salary)
                    set(it.birthday, row.birthday)
                    set(it.email, row.email)
                    set(it.address, row.address)
                    set(it.comment, row.comment)
                    set(it.version, row.version)
                    set(it.deleted, row.deleted)
                    set(it.createTime, row.createTime)
                    set(it.updateTime, row.updateTime)
            }
        }
    }

    override fun close() { rows = emptyList() }
}

package com.kotlinorm

import javax.sql.DataSource

/** Every terminal method must return fully materialized values to the JMH Blackhole. */
interface BenchmarkExecutor : AutoCloseable {
    fun init(dataSource: DataSource)
    fun queryEntities(firstId: Int, rowCount: Int): List<Any>
    fun queryMaps(firstId: Int, rowCount: Int): List<Map<String, Any?>>
    fun queryNames(firstId: Int, rowCount: Int): List<String>
    /** Build fresh framework inputs outside timing; all IDs are application-assigned. */
    fun prepareInsert(rows: List<FixtureRow>)
    /** Row-wise INSERTs in one durable transaction; this is not a native JDBC-batch test. */
    fun insertTransaction(): Int
    override fun close()
}

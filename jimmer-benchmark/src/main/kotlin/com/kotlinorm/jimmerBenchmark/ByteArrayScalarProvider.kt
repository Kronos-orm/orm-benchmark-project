package com.kotlinorm.jimmerBenchmark

import org.babyfish.jimmer.sql.runtime.ScalarProvider

class ByteArrayScalarProvider : ScalarProvider<ByteArray, ByteArray> {
    override fun toScalar(sqlValue: ByteArray): ByteArray = sqlValue
    override fun toSql(propValue: ByteArray): ByteArray = propValue
}
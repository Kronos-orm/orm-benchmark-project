package com.kotlinorm

import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

/** Deterministic non-null data; bytes are compared by content during validation. */
data class FixtureRow(
    val id: Int,
    val uid: Long,
    val name: String,
    val age: Int,
    val sex: Boolean,
    val height: Float,
    val weight: Float,
    val score: Double,
    val salary: BigDecimal,
    val birthday: LocalDate,
    val email: String,
    val address: String,
    val comment: ByteArray,
    val version: Int,
    val deleted: Boolean,
    val createTime: LocalDateTime,
    val updateTime: LocalDateTime
)

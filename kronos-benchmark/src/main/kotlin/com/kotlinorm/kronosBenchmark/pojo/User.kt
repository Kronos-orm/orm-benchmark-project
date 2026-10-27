package com.kotlinorm.kronosBenchmark.pojo

import com.kotlinorm.annotations.PrimaryKey
import com.kotlinorm.annotations.Table
import com.kotlinorm.interfaces.KPojo
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

@Table("tb_user")
class User(
    @PrimaryKey
    var id: Int = 0,
    var uid: Long = 0L,
    var name: String = "",
    var age: Int = 0,
    var sex: Boolean = false,
    var height: Float = 0f,
    var weight: Float = 0f,
    var score: Double = 0.0,
    var salary: BigDecimal = BigDecimal.ZERO,
    var birthday: LocalDate = LocalDate.of(2000, 1, 1),
    var email: String = "",
    var address: String = "",
    var comment: ByteArray = byteArrayOf(),
    var version: Int = 0,
    var deleted: Boolean = false,
    var createTime: LocalDateTime = LocalDateTime.of(2020, 1, 1, 0, 0),
    var updateTime: LocalDateTime = LocalDateTime.of(2020, 1, 1, 0, 0)
) : KPojo

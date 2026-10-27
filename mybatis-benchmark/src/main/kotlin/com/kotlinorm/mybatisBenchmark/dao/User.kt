package com.kotlinorm.mybatisBenchmark.dao

import com.baomidou.mybatisplus.annotation.*
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

@TableName("tb_user")
class User(
    @TableId(type = IdType.INPUT)
    var id: Int = 0,
    @TableField("uid")
    var uid: Long = 0L,
    @TableField("name")
    var name: String = "",
    @TableField("age")
    var age: Int = 0,
    @TableField("sex")
    var sex: Boolean = false,
    @TableField("height")
    var height: Float = 0f,
    @TableField("weight")
    var weight: Float = 0f,
    @TableField("score")
    var score: Double = 0.0,
    @TableField("salary")
    var salary: BigDecimal = BigDecimal.ZERO,
    @TableField("birthday")
    var birthday: LocalDate = LocalDate.of(2000, 1, 1),
    @TableField("email")
    var email: String = "",
    @TableField("address")
    var address: String = "",
    @TableField("comment")
    var comment: ByteArray = byteArrayOf(),
    @TableField("version")
    var version: Int = 0,
    @TableField("deleted")
    var deleted: Boolean = false,
    @TableField("create_time")
    var createTime: LocalDateTime = LocalDateTime.of(2020, 1, 1, 0, 0),
    @TableField("update_time")
    var updateTime: LocalDateTime = LocalDateTime.of(2020, 1, 1, 0, 0)
)

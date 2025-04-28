package com.kotlinorm.mybatisBenchmark.dao

import com.baomidou.mybatisplus.annotation.IdType
import com.baomidou.mybatisplus.annotation.TableId
import com.baomidou.mybatisplus.annotation.TableName
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
@TableName("tb_user")
class User(
    @TableId(type = IdType.INPUT)
    var id: Long? = null,

    var uid: Long? = null,

    var name: String?,

    var age: Int?,

    var sex: Boolean? = null,

    var height: Float? = null,

    var weight: Float? = null,

    var score: Double? = null,

    var salary: BigDecimal? = null,

    var birthday: LocalDate? = null,

    var email: String? = null,

    var address: String? = null,

    var comment: ByteArray? = null,

    var version: Int? = null,

    var deleted: Boolean? = null,

    var createTime: LocalDateTime? = null,

    var updateTime: LocalDateTime? = null
)
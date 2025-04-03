package com.kotlinorm.kronosBenchmark.pojo

import com.kotlinorm.annotations.PrimaryKey
import com.kotlinorm.annotations.Table
import com.kotlinorm.interfaces.KPojo

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
@Table("tb_user")
data class User(
    @PrimaryKey
    val id: Int? = null,
    val name: String? = null, // 学生姓名
    val age: Int? = null, // 学生年龄
) : KPojo
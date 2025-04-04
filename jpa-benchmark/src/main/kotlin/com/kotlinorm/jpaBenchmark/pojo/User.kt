package com.kotlinorm.jpaBenchmark.pojo

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.Table
/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
@Entity
@Table(name = "tb_user")
data class User(
    @Id
    @Column(name = "id")
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Int? = null,  // 必须使用可空类型

    @Column(name = "name")
    val name: String,

    @Column(name = "age")
    val age: Int
) {
    // 必须的默认构造函数
    constructor() : this(null, "", 0)
}
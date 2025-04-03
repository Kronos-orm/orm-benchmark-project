package com.kotlinorm.jpaBenchmark.pojo

import jakarta.persistence.Column
import jakarta.persistence.Entity
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
    val id: Int,

    @Column(name = "name")
    val name: String,

    @Column(name = "age")
    val age: Int
)
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
class User(
    @Id
    @Column(name = "id")
    val id: Int? = null,

    @Column(name = "name")
    val name: String? = null,

    @Column(name = "age")
    val age: Int? = null,
)
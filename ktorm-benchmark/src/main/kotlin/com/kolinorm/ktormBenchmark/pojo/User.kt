package com.kolinorm.ktormBenchmark.pojo

import org.ktorm.entity.Entity

/**
 *@program: orm-benchmark-project
 *@author: Jieyao Lu
 *@description:
 *@create: 2025/4/7 10:38
 **/
interface User : Entity<User> {
    companion object : Entity.Factory<User>()
    val id: Int
    var name: String
    var age: Int
}
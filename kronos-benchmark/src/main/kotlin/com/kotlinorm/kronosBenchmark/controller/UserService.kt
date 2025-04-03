package com.kotlinorm.kronosBenchmark.controller

import com.kotlinorm.kronosBenchmark.pojo.User
import com.kotlinorm.orm.insert.InsertClause.Companion.execute
import com.kotlinorm.orm.insert.insert
import com.kotlinorm.orm.select.select
import org.springframework.stereotype.Service

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
@Service
class UserService {

    fun createUser(users: List<User>) {
        users.insert().execute()
    }

    fun getAllUsers(): List<User> {
        return User().select().queryList()
    }

}
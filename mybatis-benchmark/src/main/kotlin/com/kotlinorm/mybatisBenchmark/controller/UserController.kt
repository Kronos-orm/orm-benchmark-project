package com.kotlinorm.mybatisBenchmark.controller

import com.kotlinorm.mybatisBenchmark.dao.User
import com.kotlinorm.mybatisBenchmark.service.UserService
import org.springframework.beans.factory.annotation.Autowired

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
class UserController(
    @Autowired val userService: UserService
) {
    fun createUser(users: List<User>) {
        userService.saveBatch(users)
    }

    fun getAllUsers(): List<User?> {
        return userService.list()
    }
}
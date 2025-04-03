package com.kotlinorm.mybatisBenchmark.service

import com.kotlinorm.mybatisBenchmark.dao.User
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
@Service
class UserFunctionService(
    @Autowired val userService: UserService
) {
    fun createUser(users: List<User>) {
        userService.saveBatch(users)
    }

    fun getAllUsers(): List<User?> {
        return userService.list()
    }
}
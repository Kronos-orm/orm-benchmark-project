package com.kotlinorm.jpaBenchmark.controller

import com.kotlinorm.jpaBenchmark.pojo.User
import com.kotlinorm.jpaBenchmark.repo.UserRepository
import org.springframework.beans.factory.annotation.Autowired

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/2
 */
class UserController(
    @Autowired val userRepository: UserRepository
) {

    fun createUser(users: List<User>) {
        userRepository.saveAll<User>(users)
    }

    fun getAllUsers(): List<User?> {
        return userRepository.findAll()
    }

}
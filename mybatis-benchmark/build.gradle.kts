plugins {
    alias { libs.plugins.kotlin.jvm }
    alias { libs.plugins.kotlin.noArg }
}

noArg.annotation("com.baomidou.mybatisplus.annotation.TableName")

dependencies {
    implementation(libs.mybatis.plus)
    implementation(libs.mybatis.typehandlers)
}

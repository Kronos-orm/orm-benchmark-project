plugins {
    alias { libs.plugins.kotlin.jvm }
    alias { libs.plugins.ksp }
    alias { libs.plugins.kapt }
}

dependencies {
    implementation(project(":benchmark-convention"))
    implementation(libs.jimmer.core)
    implementation(libs.jimmer.sql)
    implementation(libs.jackson.module)
    ksp(libs.jimmer.ksp)
    kapt(libs.jimmer.apt)
}

kotlin {
    sourceSets.main {
        kotlin.srcDir("build/generated/ksp/main/kotlin")
    }
}

kapt {
    arguments {
        arg("jimmer.sourcePackages", "com.kotlinorm.jimmerBenchmark.pojo") // 替换为你的实体包路径
    }
}

tasks.withType<Jar>().configureEach {
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
}
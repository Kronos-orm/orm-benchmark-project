plugins {
    alias { libs.plugins.kotlin.jvm }
    alias { libs.plugins.ksp }
}

dependencies {
    implementation(project(":benchmark-convention"))
    implementation(libs.jimmer.core)
    implementation(libs.jimmer.sql)
    ksp(libs.jimmer.ksp)
}

kotlin {
    sourceSets.main {
        kotlin.srcDir("build/generated/ksp/main/kotlin")
    }
}
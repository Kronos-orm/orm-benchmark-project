plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kronos.gradle.plugin)
}
kotlin { compilerOptions { freeCompilerArgs.addAll("-Xcollection-literals", "-Xcontext-sensitive-resolution") } }
dependencies {
    implementation(project(":benchmark-convention"))
    implementation(libs.kronos.core)
    implementation(libs.kronos.jdbc.wrapper)
}

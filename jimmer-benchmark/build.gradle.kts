plugins {
    alias { libs.plugins.kotlin.jvm }
}

dependencies {
    implementation(project(":benchmark-convention"))
    implementation(libs.jimmer.core)
    implementation(libs.jimmer.sql)
}

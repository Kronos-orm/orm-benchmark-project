plugins {
    alias { libs.plugins.kotlin.jvm }
}

dependencies {
    implementation(project(":benchmark-convention"))
    implementation(libs.ktorm)
}
plugins {
    alias { libs.plugins.kotlin.jvm }
    alias { libs.plugins.kotlin.jpa }
}


dependencies {
    implementation(project(":benchmark-convention"))
    implementation(libs.hibernate.core)
}
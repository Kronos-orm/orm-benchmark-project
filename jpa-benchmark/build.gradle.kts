plugins {
    alias { libs.plugins.kotlin.jvm }
    alias { libs.plugins.kotlin.jpa }
}


dependencies {
    implementation(libs.hibernate.core)
}
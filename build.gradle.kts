plugins {
	alias { libs.plugins.kotlin.jvm }
	alias { libs.plugins.kotlinx.benchmark}
	alias { libs.plugins.kotlin.allopen }
}

allOpen {
	annotation("org.openjdk.jmh.annotations.State")
}

benchmark {
	targets {
		register("main")
	}

	configurations {
		named("main") {
			warmups = 20
			iterations = 10
			iterationTime = 3
			iterationTimeUnit = "s"
		}
	}
}


dependencies {
	implementation(project(":benchmark-convention"))
	implementation(project(":kronos-benchmark"))
	implementation(libs.benchmark.runtime)
	implementation(libs.driver.jdbc.mysql)
	implementation(libs.druid)
	testImplementation(libs.kotlin.test)
	testImplementation(libs.kotlin.reflect)
}
package com.kotlinorm.benchmark.utils

import org.apache.poi.ss.format.CellFormatPart.group
import org.jetbrains.kotlinx.dataframe.DataFrame
import org.jetbrains.kotlinx.dataframe.api.forEach
import org.jetbrains.kotlinx.dataframe.api.groupBy
import org.jetbrains.kotlinx.dataframe.api.rows
import org.jetbrains.kotlinx.dataframe.io.readCSV
import org.jetbrains.kotlinx.kandy.dsl.plot
import org.jetbrains.kotlinx.kandy.letsplot.export.save
import org.jetbrains.kotlinx.kandy.letsplot.feature.layout
import org.jetbrains.kotlinx.kandy.letsplot.layers.bars
import org.jetbrains.kotlinx.kandy.letsplot.style.Theme
import java.io.File

fun generateReport(csvPath: String, outputDir: String) {
    val df = DataFrame.readCSV(File(csvPath))

    File(outputDir).apply {
        mkdirs()
        resolve("images").mkdir()
    }

    val mdFile = File("$outputDir/report.md").apply {
        writeText("# Benchmark Report\n\n")
    }

    df.groupBy("Benchmark", "Param: count").forEach { (benchmarkName, group) ->
        val (benchmarkName, countValue) = benchmarkName.values()
        val plotFileName = "${benchmarkName.toString().sanitize()}_count${countValue}.png"
        val plotPath = File("$outputDir/images/$plotFileName")

        // 生成柱状图
        plot(group) {
            bars {
                x("Param: ormType")
                y("Score") {
                    axis.name = "Operations/s"
                }
                fillColor("Param: ormType") {
                    legend.name = "ORM Type"
                }
            }
            layout {
                title = "${benchmarkName.toString().replace("com.kotlinorm.benchmark.", "")}"
                size = 1000 to 600
                theme = Theme.HIGH_CONTRAST_LIGHT
            }
        }.save(plotPath.absolutePath)

        // 生成Markdown表格
        mdFile.appendText(
            """
            |## ${benchmarkName.toString().replace("com.kotlinorm.benchmark.", "")}
            |
            |![${benchmarkName} Performance Chart](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/images/$plotFileName)
            |
            |${group.toMarkdownTable()}
            |
            |---
            |
        """.trimMargin()
        )
    }
}

private fun String.sanitize() = replace(Regex("[^\\w-]"), "_")

private fun DataFrame<*>.toMarkdownTable(): String {
    val sb = StringBuilder().apply {
        appendLine("| ORM Type | Counts | Score (ops/s) | Error (±) |")
        appendLine("|----------|--------|---------------|-----------|")
        rows().sortedByDescending { it["Score"] as Double }.forEach {
            appendLine("| ${it["Param: ormType"]} | ${it["Param: count"]} | ${"%,.2f".format(it["Score"])} | ±${"%.2f".format(it["Score Error (99.9%)"])} |")
        }
    }
    return sb.toString()
}

fun main(args: Array<String>) {
    require(args.size == 2) { "Usage: <csvPath> <outputDir>" }
    generateReport(args[0], args[1])
}
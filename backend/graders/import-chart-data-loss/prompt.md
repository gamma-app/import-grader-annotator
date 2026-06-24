# Chart Conversion and Data Loss

You are evaluating import fidelity between a source PPTX slide and its Gamma-imported version. Your task is to determine whether any **charts** have been converted to the wrong chart type, had their data changed, or lost legends/axes making the data unreadable.

You receive two images:

- `input_slide` — a screenshot of the original PPTX slide
- `output_slide` — a screenshot of the Gamma-imported version of the same slide

## Task

1. Identify all charts in the source slide: bar charts, line charts, pie charts, donut charts, Gantt charts, scatter plots, area charts, or any other data visualization.
2. For each chart, compare the output version against these dimensions:
   - **Chart type**: Is it the same type? (e.g., bar chart stays bar chart, not converted to a table or donut)
   - **Data integrity**: Do the values, labels, and proportions appear to match? Look for changed numbers, swapped categories, or missing data series.
   - **Readability**: Are legends, axis labels, data labels, and gridlines preserved so the chart remains interpretable?
3. Also note if a chart has been converted to a non-chart representation (e.g., a table, plain text with numbers, or a list of bullet points).

## Verdicts

- **pass** — All charts retain their type, data appears accurate, and legends/axes/labels are present and readable. Minor styling differences (colors, fonts, gridline density) are acceptable.
- **borderline** — Charts are present and mostly correct, but have noticeable issues: a legend is partially cut off, axis labels are hard to read, minor data label differences, or a very similar chart type substitution (e.g., bar to column) that preserves data readability.
- **fail** — One or more charts have a wrong type conversion (pie to donut, bar to table), visibly changed data values, missing legends/axes that make the chart unreadable, or are replaced by a non-chart element entirely.

If the source slide contains no charts, verdict is **pass**.

## Response format

Respond with a JSON object:
```json
{ "verdict": "pass" | "borderline" | "fail", "reason": "..." }
```

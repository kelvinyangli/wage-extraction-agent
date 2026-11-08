# Stage: targeted extraction retry

Re-extract only the allowed field paths implicated by the judge. Do not modify any other field. If the source does not support a correction, return no patch.

<source_evidence>
$source_evidence
</source_evidence>

<current_values>
$current_values
</current_values>

<judge_reason>
$judge_reason
</judge_reason>

Allowed field paths:

$allowed_field_paths

Return data conforming exactly to this schema:

$output_schema

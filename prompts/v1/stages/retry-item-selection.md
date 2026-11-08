# Stage: targeted reconciliation-item-selection retry

Reconsider only which existing extracted items contribute to the printed total and their `1` or `-1` multipliers. Do not change extracted values or perform claim calculations. Return an empty relationship when evidence remains insufficient.

<source_evidence>
$source_evidence
</source_evidence>

<items>
$items
</items>

<printed_total>
$printed_total
</printed_total>

<judge_reason>
$judge_reason
</judge_reason>

Return data conforming exactly to this schema:

$output_schema

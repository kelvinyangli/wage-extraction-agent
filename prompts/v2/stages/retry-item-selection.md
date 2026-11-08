# Stage: targeted reconciliation-item-selection retry

Reconsider only which existing extracted source records contribute to the printed total and their `1` or `-1` multipliers. Source records may be pay items or other printed totals when supported by the payslip structure. Do not use a predetermined list, reference the target total itself, combine a subtotal with its constituent rows, change extracted values, or perform claim calculations. Return an empty relationship when evidence remains insufficient.

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

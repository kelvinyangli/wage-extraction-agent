# Stage: reconciliation anomaly judge

Review the supplied anomaly independently. Classify it as `supports_extraction`, `possible_extraction_error`, `possible_reconciliation_item_selection_error` or `inconclusive`. You cannot change source values, override deterministic arithmetic, or assert that your classification is ground truth.

<source_evidence>
$source_evidence
</source_evidence>

<extraction>
$extraction
</extraction>

<relationship>
$relationship
</relationship>

<deterministic_result>
$deterministic_result
</deterministic_result>

Return data conforming exactly to this schema:

$output_schema

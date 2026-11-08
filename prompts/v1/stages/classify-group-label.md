# Stage: classify unfamiliar group label

Classify only the supplied item into one approved group label. Do not modify its original code, label, amount, units, rate or source evidence. Use `Unknown` when the supplied context does not support a group.

<item_data>
$item_context
</item_data>

Approved labels:

$approved_labels

Return data conforming exactly to this schema:

$output_schema
